from __main__ import app
from flask import redirect, request
from routes_logic import (
    home,
    media,
    scan_library,
    overview,
    trailer,
    player_video,
    overview_play,
    overview_tmdb,
    page_not_found,
)


"""
Here we create the routes and then connect them to a function.
This file should not contain any real logic, except for the routes.
We place the logic inside routes_logic.py
"""


@app.route("/")
def route_index():
    return redirect("/library/", code=303)


@app.route("/library/")
def route_home():
    return home()


@app.route("/library/<string:library_name>/<string:genre>/", methods=["POST", "GET"])
@app.route("/library/<string:library_name>/", methods=["POST", "GET"])
def route_media(library_name, genre=None):
    return media(request, library_name, genre)


@app.route(
    "/library/<string:library_name>/<int:video_id>/<int:season_number>/<int:episode_number>/"
)
@app.route("/library/<string:library_name>/<int:video_id>/<int:season_number>/")
@app.route("/library/<string:library_name>/<int:video_id>/")
def route_media_overview(
    library_name, video_id, season_number=None, episode_number=None
):
    return overview(library_name, video_id, season_number, episode_number)


@app.route(
    "/library/<string:library_name>/<int:video_id>/<int:season_number>/<int:episode_number>/trailer/"
)
@app.route("/library/<string:library_name>/<int:video_id>/<int:season_number>/trailer/")
@app.route("/library/<string:library_name>/<int:video_id>/trailer/")
def route_media_overview_trailer(
    library_name, video_id, season_number=None, episode_number=None
):
    return trailer(library_name, video_id)


@app.route("/library/<string:library_name>/<int:video_id>/play/")
@app.route(
    "/library/<string:library_name>/<int:video_id>/<int:season_number>/<int:episode_number>/play"
)
def route_media_overview_play(
    library_name, video_id, season_number=None, episode_number=None
):
    return overview_play(request, library_name, video_id, season_number, episode_number)


@app.route("/video/<int:video_id>")
@app.route("/video/<int:video_id>/<int:season_number>/<int:episode_number>")
def route_player_play_video(video_id, season_number=None, episode_number=None):
    return player_video(request, video_id, season_number, episode_number)


@app.route("/tmdb/<string:content_type>/<int:video_id>/")
def route_tmdb_overview(content_type, video_id):
    return overview_tmdb(content_type, video_id)


@app.route("/scan_library")
def route_scan_library():
    return scan_library()


@app.errorhandler(404)
def route_page_not_found(e):
    return page_not_found(e)
