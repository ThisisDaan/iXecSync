var window_location_search = window.location.search;
var url_parameters = new URLSearchParams(window_location_search);


// Creating the player

var player = videojs('player', {
    width: window.innerWidth,
    height: window.innerHeight,
    textTrackSettings: false,
    autoplay: true,
    userActions: {
        hotkeys: function (event) {
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


// Adding the player overlay

var overlay_content = document.getElementById("video-overlay-copy").innerHTML
document.getElementById("video-overlay-copy").remove()
player.overlay({
    overlays: [{
        class: 'video-overlay',
        start: 0,
        content: overlay_content,
        align: 'top'
    }]
});


// Transcoding

transcode = url_parameters.get('transcoding')
if (transcode == "1") {
    time = 0;
    var sync_player_control = function (player) {
        return {
            duration: function () {
                return player.video_duration;
            },
            callPlay: function () {
                //return videojs.middleware.TERMINATOR;
            },
            callPause: function () {
                //return videojs.middleware.TERMINATOR;
            }
        };
    };

    videojs.use('*', sync_player_control);

    player.start = 0;
    player.oldCurrentTime = player.currentTime;
    player.currentTime = function (time) {
        if (time == undefined) {
            if (player.readyState() == 0) {
                var percentage = player.start * 100 / player.video_duration
                $(".vjs-play-progress").css("width", percentage + "%")
            }
            return player.oldCurrentTime() + player.start;
        }
        console.log(Math.floor(time))

        player.start = time;
        player.oldCurrentTime(0);
        player.src({
            src: '/player/get/' + video_id + "?transcoding=" + transcode + "&time=" + Math.floor(time),
            type: 'video/mp4'
        });
        return time;
    };

    player.src({
        type: 'video/mp4',
        src: '/player/get/' + video_id + "?transcoding=" + transcode + "&time=" + time
    });
}


// playing on load

player.play()


// Volume

player_set_volume()
player.on('volumechange', player_save_volume);

function player_set_volume() {
    var player_volume = window.localStorage.getItem('player_volume') || 100
    player.volume(player_volume)
}

function player_save_volume() {
    window.localStorage.setItem('player_volume', player.volume()); // saves volume to local storage
}

// function player_metadata() {
//     $.getJSON('/player/meta/' + session_id, function (metadata) {
//         if (metadata["title"] != null) {
//             title = document.getElementById("video-overlay-title")
//             title.textContent = metadata["title"]
//         }
//         if (metadata["duration"] != null) {
//             player.video_duration = metadata["duration"]
//         }
//         if (metadata["lang"] != null) {
//             for (i = 0; i < metadata["lang"].length; i++) {
//                 player.addRemoteTextTrack({
//                     kind: 'captions',
//                     label: metadata["lang"][i]["name"],
//                     src: '/subtitle/' + session_id + "/" + metadata["lang"][i]["code"]
//                 })
//             }
//         }
//     });
// }