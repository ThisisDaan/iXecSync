var socket
var user_action = false
var heartbeat = 5000
var sync_speed = 10 // percentage for speeding up or slowing down
var interval_time = heartbeat
var interval_start_time
var interval_loop
var interval_latency = 0


var player = videojs('player', {
    width: window.innerWidth,
    height: window.innerHeight,
});

player.on("play", user_sync);
player.on("pause", user_sync);
player.on("seeking", user_sync);
player.on("volumechange", saveVolume);

function ready() {
    socket = io.connect('http://' + document.domain + ':' + location.port + '/sync');
    socket.on('sync', m => sync_player(m));
    socket.on('out of sync', m => out_of_sync(m));
    socket.on('reference', m => reference(m));
    socket.on('latency', m => latency(m));

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
    interval_start_time = new Date().getTime()
    if (!player.paused()) {
        sync_data('interval sync')
    }
    latency_check()
}, heartbeat);

function reference(data) {
    console.log("=== Reference ===")
}

function latency_check() {
    socket.emit("latency", {
        "time": new Date().getTime()
    });
}

function latency(request) {
    interval_latency = Math.abs(new Date().getTime() - request["time"])
}

function out_of_sync(request) {
    out_of_sync_speed(request)
}



function out_of_sync_speed(request) {
    switch (request["outofsync"]) {
        case 0:
            player.playbackRate(1)
            console.log("playing video at normal speed")
            break;
        case 1:
            player_speed = 1 + (1 / sync_speed)
            player.playbackRate(player_speed)
            out_of_sync_time_needed(request)
            console.log("speeding up video by " + sync_speed + "%")
            break;
        case 2:
            player_speed = 1 - (1 / sync_speed)
            player.playbackRate(player_speed)
            out_of_sync_time_needed(request)
            console.log("slowing down video by " + sync_speed + "%")
            break;
    }
}

function out_of_sync_time_needed(request) {
    var time_needed = (request["delay"] * sync_speed) + interval_latency
    if (time_needed < heartbeat) {
        console.log("Out of sync - give me " + Math.round((time_needed / 1000)) + " seconds to fix this please")
        setTimeout(normal_speed, time_needed)
    } else {
        console.log("Out of sync - give me " + Math.round((time_needed / 1000)) + " seconds to fix this please")
    }
}

function normal_speed() {
    player.playbackRate(1)
    console.log("In sync - sorry for the trouble")
}

function skipForward(seconds) {
    player.currentTime(player.currentTime() + seconds)
}

function user_sync() {
    setTimeout(user_sync_delay, 100)
}

function user_sync_delay() {
    if (user_action) {
        user_action = false
        sync_data('user sync')
    }
}

function saveVolume() {
    window.localStorage.setItem('player_volume', player.volume()); // saves volume to local storage
}

function sync_player(data) {
    console.log(data)
    sync_player_time = data["time"] / 1000
    player.currentTime(sync_player_time)
    if (data["playing"]) {
        player.play()
    } else {
        player.pause()
    }
}

function sync_data(data_request) {
    socket.emit(data_request, {
        "time": (player.currentTime() * 1000), // Time in milliseconds
        "playing": !player.paused(), // if the player is playing
        "ready": player.readyState(), // ready state
    });
}