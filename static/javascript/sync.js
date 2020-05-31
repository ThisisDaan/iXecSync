var socket
var session_id
var user_action = false
var heartbeat = 6000
var sync_speed = 10 // percentage for speeding up or slowing down


var player = videojs('player', {
    width: window.innerWidth,
    height: window.innerHeight,
    textTrackSettings: false
});

player.on("play", user_sync);
player.on("pause", user_sync);
player.on("seeking", user_sync);
player.on("volumechange", player_save_volume);
player.on("useractive", player_show_overlay);
player.on("userinactive", player_hide_overlay);
// player.on("timeupdate", timeUpdate);

// player.on("useractive", useractive);
// player.on("userinactive", userinactive);
// function useractive() {
//     $("#video-overlay").show();
// }

// function userinactive() {
//     $("#video-overlay").hide();
// }

function ready() {
    if (get_session() == true) {
        player.src({
            type: 'video/mp4',
            src: '/player/' + session_id
        });
        create_websocket()
    }
    player_set_volume()
}

function get_session() {
    const queryString = window.location.search;
    const urlParams = new URLSearchParams(queryString);
    const param_session = urlParams.get('session')
    if (param_session != null) {
        session_id = param_session
        return true
    } else {
        return false
    }
}

function create_websocket() {
    var hostname = location.hostname;
    var port = location.port;
    var protocol = (location.protocol === 'https:' ? 'https://' : 'http://');
    var url = protocol + hostname + ':' + port + '/sync';
    var query = {
        "query": {
            "session": session_id
        }
    }
    socket = io.connect(url, query);
    socket.on('sync', m => sync_player(m));
    socket.on('out of sync', m => out_of_sync(m));
    socket.on('message', m => message(m));
    socket.on('meta', m => player_meta_data(m));
    connect_sync_player()
    setInterval(function () {
        if (!player.paused()) {
            sync_data('client update')
        }
    }, heartbeat);
}

function player_hide_overlay() {
    $(".video-overlay").fadeOut(300);
}

function player_show_overlay() {
    $(".video-overlay").fadeIn(300);
}

function player_meta_data(metadata) {
    overlay_content = "<h2>" + metadata["title"] + "</h2>";
    player.overlay({
        overlays: [{
            class: 'video-overlay',
            start: 0,
            content: overlay_content,
            align: 'top'
        }]
    });
    for (i = 0; i < metadata["lang"].length; i++) {
        player.addRemoteTextTrack({
            kind: 'captions',
            label: metadata["lang"][i]["name"],
            src: '/subtitle/' + session_id + "/" + metadata["lang"][i]["code"]
        })
    }

}

function player_set_volume() {
    var player_volume = window.localStorage.getItem('player_volume') || 100
    player.volume(player_volume)
}

function player_save_volume() {
    window.localStorage.setItem('player_volume', player.volume()); // saves volume to local storage
}

function player_speed_normal() {
    player.playbackRate(1)
    if (player.playbackRate() != '1') {
        console.log("playing video at normal speed")
    } else {
        console.log("You are in sync")
    }
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

function connect_sync_player() {
    $(document).click(function (e) {
        if (e.button == 0) {
            user_action = true
        }
    });

    $(".vjs-progress-control, .vjs-progress-holder, .vjs-load-progress, .vjs-mouse-display, .vjs-control-text, vjs-play-progress, .vjs-live-control")
        .click(
            function () {
                sync_data('client request sync')
            });
}

function message(msg) {
    console.log(msg)
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
    if (user_action) {
        user_action = false
        sync_data('client request sync')
    }
}

function sync_player(data) {
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