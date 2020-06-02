var socket
var session_id
var heartbeat = 6000
var sync_speed = 10 // percentage for speeding up or slowing down
var ignore_sync = false
var user_active = true

const window_location_search = window.location.search;
const url_parameters = new URLSearchParams(window_location_search);

var player = videojs('player', {
    width: window.innerWidth,
    height: window.innerHeight,
    textTrackSettings: false,
    autoplay: true,
    userActions: {
        hotkeys: function (event) {
            console.log(event.which)
            if (event.which === 32) {
                if (this.paused()) {
                    player.play()
                } else {
                    player.pause()
                }
            }
        }
    },
    nativeControlsForTouch: false,
});
player.play()

player.on('play', player_play);
player.on('pause', player_pause);
player.on('seeking', user_sync);
player.on('volumechange', player_save_volume);
player.on('useractive', player_user_active);
player.on('userinactive', player_user_inactive);


var overlay_content = "<section class='video-overlay-container'><button onclick='window.history.back()' class='back-button'></button><span id='video-overlay-title'></span></section>";
player.overlay({
    overlays: [{
        class: 'video-overlay',
        start: 0,
        content: overlay_content,
        align: 'top'
    }]
});

$(document).ready(function () {
    if (url_parameters.get('session') != null) {
        session_id = url_parameters.get('session')
        player.src({
            type: 'video/mp4',
            src: '/player/' + session_id
        });
    } else if (url_parameters.get('v') != null) {
        session_id = url_parameters.get('v')
        player.src({
            type: 'video/youtube',
            src: 'https://www.youtube.com/watch?v=' + session_id
        });
    }
    create_websocket()
    player_set_volume()
});

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
    socket.on('meta', m => player_metadata(m));
    setInterval(function () {
        // if (!player.paused()) {
        sync_data('client update')
        // }
    }, heartbeat);
}

function player_user_inactive() {
    user_active = false
    if (!player.paused()) {
        $(".video-overlay").fadeTo(300, "0")
    }
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



function player_metadata(metadata) {
    if (metadata["title"] != null) {
        title = document.getElementById("video-overlay-title")
        title.textContent = metadata["title"]
    }
    if (metadata["lang"] != null) {
        for (i = 0; i < metadata["lang"].length; i++) {
            player.addRemoteTextTrack({
                kind: 'captions',
                label: metadata["lang"][i]["name"],
                src: '/subtitle/' + session_id + "/" + metadata["lang"][i]["code"]
            })
        }
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
    if (!ignore_sync) {
        sync_data('client request sync')
    }
}

function set_ignore_sync(ignore) {
    if (ignore == true) {
        ignore_sync = true
        setTimeout(set_ignore_sync, 2000)
    } else {
        ignore_sync = false
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

window.onresize = function () {
    player.height(window.innerHeight) // changes player to height window
    player.width(window.innerWidth) // changes player to width window
}