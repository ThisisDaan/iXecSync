var socket
var user_action = false
var heartbeat = 6000
var sync_speed = 10 // percentage for speeding up or slowing down


var player = videojs('player', {
    width: window.innerWidth,
    height: window.innerHeight,
});

player.on("play", user_sync);
player.on("pause", user_sync);
player.on("seeking", user_sync);
player.on("volumechange", saveVolume);
player.on("timeupdate", timeUpdate);

function ready() {
    var hostname = location.hostname;
    var port = location.port;
    var protocol = (location.protocol === 'https:' ? 'https://' : 'http://');
    var url = protocol + hostname + ':' + port + '/sync';
    socket = io.connect(url);
    socket.on('sync', m => sync_player(m));
    socket.on('out of sync', m => out_of_sync(m));
    socket.on('message', m => message(m));
    socket.on('push', m => sync_player(m));

    var player_volume = window.localStorage.getItem('player_volume') || 100
    player.volume(player_volume)

    $(document).click(function (e) {
        if (e.button == 0) {
            user_action = true
        }
    });

    $(".vjs-progress-control, .vjs-progress-holder, .vjs-load-progress, .vjs-mouse-display, .vjs-control-text, vjs-play-progress, .vjs-live-control")
        .click(
            function () {
                sync_data('user sync')
            });
}

setInterval(function () {
    if (!player.paused()) {
        sync_data('interval sync')
    }
}, heartbeat);

function message(msg) {
    console.log(msg)
}

var debug_field = document.getElementById("debugfield");

function timeUpdate() {
    debug_field.textContent = player.currentTime()
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
    player.currentTime(player.currentTime() + seconds)
}

function user_sync() {
    if (user_action) {
        user_action = false
        sync_data('user sync')
    }
}

function saveVolume() {
    window.localStorage.setItem('player_volume', player.volume()); // saves volume to local storage
}

function sync_player(data) {
    player.currentTime(data["time"] / 1000)
    data["paused"] ? player.pause() : player.play()
}

function sync_data(data_request) {
    socket.emit(data_request, {
        "time": (Math.round(player.currentTime() * 1000)), // Time in milliseconds
        "paused": player.paused(), // if the player is playing
        "heartbeat": heartbeat,
    });
}