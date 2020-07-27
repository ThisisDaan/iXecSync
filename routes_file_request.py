from __main__ import app, root
from flask import redirect, send_from_directory, abort, request
from pathlib import Path
from database_queries import media_path
from transcoding import ffmpeg_transcode
import os


@app.route("/thumbnail/<string:poster_path>")
def get_thumbnail(poster_path):
    file = Path(thumbnail_path(), poster_path)

    if file.exists():
        return send_from_directory(directory=file.parent, filename=file.name)
    else:
        return redirect(f"https://image.tmdb.org/t/p/w500/{poster_path}")


"""
=-=-=-=-=-=-=-=-=-
sync_player.html
videojs source requesting the video file
=-=-=-=-=-=-=-=-=-
"""


@app.route("/player/get/<string:session_id>/<int:video_id>")
@app.route(
    "/player/get/<string:session_id>/<int:video_id>/<int:season_number>/<int:episode_number>"
)
def player_get_video(session_id, video_id, season_number=None, episode_number=None):

    transcoding = request.args.get("transcoding")
    video_time = request.args.get("time")

    path = media_path(video_id, season_number, episode_number)

    if transcoding:
        try:
            m3u8fullpath = ffmpeg_transcode(
                path, start=int(video_time), sessionid=session_id,
            )
            return send_from_directory(
                directory=Path(m3u8fullpath).parent, filename=Path(m3u8fullpath).name,
            )
        except Exception:
            return abort(404)

    else:
        return send_from_directory(directory=path.parent, filename=path.name,)


"""
=-=-=-=-=-=-=-=-=-
sync_player.html
videojs source requesting the ts files
=-=-=-=-=-=-=-=-=-
"""


@app.route(
    "/player/get/<string:session_id>/<path:useless>/<string:video_file>.<string:video_extension>"
)
@app.route(
    "/player/get/<string:session_id>/<string:video_file>.<string:video_extension>"
)
def m3u8_request_ts(session_id, video_file, video_extension, useless=None):

    directory = Path(Path(__file__).parent, "temp", session_id)
    filename = f"{video_file}.{video_extension}"

    return send_from_directory(directory=directory, filename=filename)


def thumbnail_path():
    return Path(root, "thumbnail")
