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


function set_duration(duration) {
    player.video_duration = duration
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
}

// Transcoding
function load_player(video_id, video_type) {
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
                type: video_type
            });
            return time;
        };

        player.src({
            type: video_type,
            src: '/player/get/' + video_id + "?transcoding=" + transcode + "&time=" + time
        });
    }


    // playing on load

    player.play()
}



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