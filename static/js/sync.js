var socket
var session_id
var heartbeat = 6000
var sync_speed = 10 // percentage for speeding up or slowing down
var ignore_sync = false
var user_active = true




var window_location_search = window.location.search;
var url_parameters = new URLSearchParams(window_location_search);




// Loading the session, creating websocket connection

function start_session(video_id) {
    if (url_parameters.get('session') != null) {
        player.on('play', player_play);
        player.on('pause', player_pause);
        player.on('seeking', player_seeking);
        player.on('useractive', player_user_active);
        player.on('userinactive', player_user_inactive);

        // player_metadata()
        create_websocket()
    }
}

function create_websocket() {
    var hostname = location.hostname;
    var port = location.port;
    var protocol = (location.protocol === 'https:' ? 'https://' : 'http://');
    var url = protocol + hostname + ':' + port + '/sync';
    var query = {
        "query": {
            "session": url_parameters.get('session'),
            "video_id": video_id
        }
    }
    socket = io.connect(url, query);
    socket.on('sync', m => sync_player(m));
    socket.on('out of sync', m => out_of_sync(m));
    socket.on('message', m => message(m));
    // socket.on('meta', m => player_metadata(m));
    setInterval(function () {
        if (!player.paused()) {
            sync_data('client update')
        }
    }, heartbeat);
}



function player_user_inactive() {
    user_active = false
    if (!player.paused()) {
        $(".video-overlay").fadeTo(300, "0")
    }
}

function player_seeking() {
    user_sync()
}

function player_play() {
    if (!user_active) {
        $(".video-overlay").fadeTo(300, "0")
    }
    user_sync()
}

function player_user_active() {
    user_active = true
    $(".video-overlay").fadeTo(100, "1")
}

function player_pause() {
    $(".video-overlay").fadeTo(100, "1")
    user_sync()
}

function player_speed_normal() {
    player.playbackRate(1)
    if (player.playbackRate() != '1') {
        console.log("playing video at normal speed")
    } else {
        console.log("You are in sync")
    }
    $(".vjs-play-progress").removeClass('syncing')
    $(".vjs-play-progress").removeClass('syncing-slow')
}

function player_speed_faster(request) {
    player_speed = 1 + (1 / sync_speed)
    player.playbackRate(player_speed)
    out_of_sync_time_needed(request)
    console.log("speeding up video by " + sync_speed + "%")

}

function player_speed_slower(request) {
    player_speed = 1 - (1 / sync_speed)
    player.playbackRate(player_speed)
    out_of_sync_time_needed(request)
    console.log("slowing down video by " + sync_speed + "%")
}

function message(msg) {
    console.log(msg)
    $(".vjs-play-progress").removeClass('syncing')
    $(".vjs-play-progress").removeClass('syncing-slow')
}

function out_of_sync(request) {
    switch (request["outofsync"]) {
        case 0:
            player_speed_normal()
            break;
        case 1:
            player_speed_faster(request)
            break;
        case 2:
            player_speed_slower(request)
            break;
    }

    if (request["delay"] > (request["max_out_of_sync"] / 4)) {
        $(".vjs-play-progress").removeClass('syncing')
        $(".vjs-play-progress").addClass('syncing-slow')
    } else if (request["outofsync"] != 0) {
        $(".vjs-play-progress").removeClass('syncing-slow')
        $(".vjs-play-progress").addClass('syncing')
    }
}

function out_of_sync_time_needed(request) {
    var time_needed = (request["delay"] * sync_speed)
    if (time_needed < heartbeat) {
        console.log("Out of sync - give me " + Math.round((time_needed / 1000)) + " second(s) to fix this please")
        setTimeout(player_speed_normal, time_needed)
    } else {
        console.log("Out of sync - give me " + Math.round((time_needed / 1000)) + " second(s) to fix this please")
    }
}

function skipForward(seconds) {
    time = player.currentTime() + seconds
    player.currentTime(time)
}

function user_sync() {
    if (!ignore_sync && player.readyState() > 0 && user_active) {
        sync_data('client request sync')
    }
}

function set_ignore_sync(ignore) {
    if (ignore == true) {
        ignore_sync = true
        setTimeout(set_ignore_sync, 1000)
        $("body").css("pointer-events", "none");
    } else {
        ignore_sync = false
        $("body").css("pointer-events", "all");
    }
}

function sync_player(data) {
    set_ignore_sync(true)
    if (data["time"] != false) {
        time = data["time"] / 1000
        player.currentTime(time)
    }
    data["paused"] ? player.pause() : player.play()
}

function create_profile() {
    return {
        "time": (Math.round(player.currentTime() * 1000)), // Time in milliseconds
        "paused": player.paused(), // if the player is playing
        "heartbeat": heartbeat,
        "session": session_id,
    }

}

function sync_data(data_request) {
    socket.emit(data_request, create_profile());
}