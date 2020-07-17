from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    session,
    redirect,
    abort,
    Response,
    jsonify,
)
from jinja2 import Template
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import os
from collections import defaultdict
import uuid
from iso639 import languages
import io
import transcoding as acid_transcode
import sys
import tmdb as tmdb
import json
from pathlib import Path
import random


app = Flask(__name__)
socketio = SocketIO(app)

folder_location = os.path.join(
    os.path.dirname(os.path.realpath(__file__)) + os.sep + "video" + os.sep
)

subtitle_folder_location = os.path.join(
    os.path.dirname(os.path.realpath(__file__)) + os.sep + "subtitles" + os.sep
)

session_storage = {}


class iXecSync:
    clients = defaultdict(list)

    def __init__(self, request, session_id):
        self.id = request.sid
        self.join_session(session_id)

        print(f"{self.id}@{self.session} - Client connected")

    def remove_client(self):
        iXecSync.clients[self.session].remove(self)
        print(f"{self.id}@{self.session} - Client disconnected")

    def join_session(self, session_id):
        self.session = session_id
        join_room(session_id)
        iXecSync.clients[session_id].append(self)
        self.sync_with_session()
        self.push(self.get_json_profile())

    def sync_with_session(self):
        if self.is_reference():
            try:
                if session_storage[self.session]["time"] is not None:
                    session_time = session_storage[self.session]["time"]
                    session_paused = True
                else:
                    session_time = 0
                    session_paused = True
            except KeyError:
                session_time = 0
                session_paused = True
        else:
            reference = self.get_reference()
            session_time = reference.time
            session_paused = reference.paused

        self.time = session_time
        self.paused = session_paused

    def push(self, json):
        emit("sync", json, room=self.id)

    def update_client_time(self, client_time):
        self.time = client_time
        self.epoch = int(round(time.time() * 1000))

    def update_session(self):
        if self.is_reference():
            session_storage[self.session]["time"] = self.time
            session_storage[self.session]["paused"] = self.paused

    def update_client(self, client_data):
        if "time" in client_data:
            self.update_client_time(client_data["time"])
        if "paused" in client_data:
            self.paused = client_data["paused"]
        self.update_session()

    def sync_other_clients(self, client_data):
        self.update_client(client_data)
        self.update_client_in_session()
        emit("sync", client_data, room=self.session, skip_sid=self.id)

    def update_client_in_session(self):
        for client in iXecSync.clients[self.session]:
            if client.id != self.id:
                client.update_client_time(self.time)
                client.paused = self.paused

    def sync_client(self):
        reference = self.get_reference()
        self.update_client_time(reference.time)
        emit("sync", reference.get_json_profile(), room=self.id)

    def is_reference(self):
        if self.get_reference() == self:
            return True
        else:
            return False

    def get_reference(self):
        return iXecSync.clients[self.session][0]

    def get_reference_profile(self):
        reference = self.get_reference()
        return reference.get_json_profile()

    def get_json_profile(self):
        try:
            profile = {
                "time": self.time,
                "paused": self.paused,
            }

            return profile
        except AttributeError:
            return False

    def message(self, message):
        emit(
            "message", message, room=self.id,
        )

    def check_client_in_sync(self):
        reference = self.get_reference()

        if self.is_reference():
            self.message("You are the reference")
            return

        max_delay = 100  # in milliseconds
        max_out_of_sync = 5000  # in milliseconds

        delay = self.epoch - reference.epoch

        if not reference.paused:
            reference.update_client_time(reference.time + delay)

        delay_between_players = abs(self.time - reference.time)

        if delay_between_players > max_delay:
            if self.time > reference.time:
                print(
                    f"{self.id}@{self.session} - not in sync - slowing down ({round(delay_between_players)}ms)"
                )
                outofsync = 2
            else:
                print(
                    f"{self.id}@{self.session} - not in sync - speeding up ({round(delay_between_players)}ms)"
                )
                outofsync = 1
        else:
            print(
                f"{self.id}@{self.session} - We are in sync ({round(delay_between_players)}ms)"
            )
            outofsync = 0

        if delay_between_players > max_out_of_sync:
            print(f"{self.id}@{self.session} - Syncing client (+{max_out_of_sync}ms)")
            self.sync_client()
        else:
            emit(
                "out of sync",
                {
                    "outofsync": outofsync,
                    "max_out_of_sync": max_out_of_sync,
                    "delay": delay_between_players,
                    "max_delay": max_delay,
                },
                room=self.id,
            )


def get_library_items():
    with open(os.path.join(os.path.dirname(__file__), "config.json")) as file:
        config = json.load(file)

    return config["library"]


def get_media_filters(request, library_name, genre=None):
    sortby = request.form.get("sortby")

    if sortby is None:
        sortby = "popularity DESC"

    if genre is None:
        genre = "all"

    genres = tmdb.get_genre_list(library_name)

    media_filters = {
        "sortby": {"selected": sortby,},
        "genres": {"selected": genre, "list": genres},
        "search": True,
    }

    return media_filters


@app.route("/")
def index():
    return redirect("/library", code=303)


@app.route("/library/")
def library_home():
    return render_template(
        "library_home.html.j2",
        selected="Home",
        library=get_library_items(),
        movie=tmdb.get_popular_movies(),
        tvshow=tmdb.get_popular_tvshows(),
        goback=False,
    )


# library


@app.route("/library/<string:library_name>/", methods=["POST", "GET"])
def library_content(library_name):
    sortby = request.form.get("sortby")

    if sortby is None:
        sortby = "popularity DESC"

    files = tmdb.get_library(library_name, sortby)
    genres = tmdb.get_genre_list(library_name)

    return render_template(
        "library_media.html.j2",
        selected=library_name,
        library=get_library_items(),
        media=files,
        goback=False,
        meta={"library_name": library_name},
        media_filters={
            "sortby": {"selected": sortby,},
            "genres": {"selected": "all", "list": genres},
            "search": True,
        },
    )


# Genre filters


@app.route("/library/<string:library_name>/<string:genre>/", methods=["POST", "GET"])
def library_media_genre(library_name, genre):

    media_filters = get_media_filters(request, library_name, genre)
    files = tmdb.get_media_by_genre(
        library_name, genre, media_filters["sortby"]["selected"]
    )

    return render_template(
        "library_media.html.j2",
        selected=library_name,
        library=get_library_items(),
        media=files,
        goback=False,
        meta={"library_name": library_name},
        media_filters=media_filters,
    )


# Trailer page of movie or tvshow


@app.route("/library/<string:library_name>/<int:video_id>/trailer/")
def movie_trailer(video_id, library_name=None, content_type=None):

    trailer = tmdb.get_trailer(library_name, video_id)
    youtube = trailer["video"]
    title = f"""Trailer - {trailer["title"]}"""

    return render_template("youtube.html", sync=False, youtube=youtube, title=title,)


# overview page of movie or tv show


@app.route("/library/<string:library_name>/<int:video_id>/")
def library_media_overview(library_name, video_id):

    meta = tmdb.get_meta(library_name, video_id)

    if tmdb.library_content_type(library_name) == "movie":
        return render_template(
            "library_media_overview.html.j2",
            selected=library_name,
            library=get_library_items(),
            meta=meta,
            movie=True,
            goback=True,
            content_type="movie",
        )
    elif tmdb.library_content_type(library_name) == "tvshow":
        season = tmdb.get_seasons(video_id)
        return render_template(
            "library_media_overview.html.j2",
            selected=library_name,
            library=get_library_items(),
            meta=meta,
            season=season,
            goback=True,
            content_type="tvshow",
        )


# overview page of a season


@app.route("/library/<string:library_name>/<int:video_id>/<int:season_number>/")
def library_media_overview_season(library_name, video_id, season_number):

    meta = tmdb.get_meta(library_name, video_id)
    episode = tmdb.get_episodes(video_id, season_number)

    return render_template(
        "library_media_overview.html.j2",
        selected=library_name,
        library=get_library_items(),
        meta=meta,
        episode=episode,
        season_number=season_number,
        goback=True,
        content_type="tvshow",
    )


# overview page of not available media


@app.route("/tmdb/<string:content_type>/<int:video_id>/")
def library_tmdb_overview(content_type, video_id):

    if content_type == "movie" or content_type == "tvshow":
        meta = tmdb.get_tmdb_data(content_type, video_id)

        return render_template(
            "library_tmdb_overview.html.j2",
            selected="home",
            library=get_library_items(),
            meta=meta,
            goback=True,
            content_type=content_type,
        )
    else:
        redirect("/")


# overview page of an episode


@app.route(
    "/library/<string:library_name>/<int:video_id>/<int:season_number>/<int:episode_number>/"
)
def library_media_overview_season_episode(
    library_name, video_id, season_number, episode_number
):

    meta = tmdb.get_meta_season_episode(video_id, season_number, episode_number)

    return render_template(
        "overview/library_media_overview.html",
        selected=library_name,
        library=get_library_items(),
        meta=meta,
        goback=True,
    )


# Play buttons


@app.route(
    "/library/<string:library_name>/<int:video_id>/<int:season_number>/<int:episode_number>/play"
)
def library_media_overview_season_episode_play(
    library_name, video_id, season_number, episode_number
):

    data = tmdb.get_filename_episode(video_id, season_number, episode_number)

    if data:
        session_id = f"{uuid.uuid4()}"[:8]
        create_new_session(f"{video_id}/{season_number}/{episode_number}")

        redirect_url = f"""/video/{video_id}/{season_number}/{episode_number}?session={session_id}"""

        transcode = request.args.get("transcoding")
        if transcode:
            redirect_url += f"""&transcoding={request.args.get("transcoding")}"""

        return redirect(redirect_url)
    else:
        meta = tmdb.get_meta_season_episode(video_id, season_number, episode_number)
        return render_template(
            "overview/library_media_overview.html",
            selected=library_name,
            library=get_library_items(),
            meta=meta,
            error=f"Error - File not found",
            goback=True,
        )


@app.route("/library/<string:library_name>/<int:video_id>/play/")
def library_media_overview_play(library_name, video_id):

    data = tmdb.get_filename(video_id)

    if data:
        session_id = f"{uuid.uuid4()}"[:8]
        create_new_session(video_id)

        redirect_url = f"""/video/{video_id}?session={session_id}"""

        transcode = request.args.get("transcoding")
        if transcode:
            redirect_url += f"""&transcoding={request.args.get("transcoding")}"""

        return redirect(redirect_url)
    else:
        meta = tmdb.get_meta(library_name, video_id)
        return render_template(
            "overview/library_media_overview.html",
            selected=library_name,
            library=get_library_items(),
            meta=meta,
            error=f"Error - File not found",
            goback=True,
        )


#
#  PLAYER - MOVIES
#


@app.route("/video/<int:video_id>")
def play_video(video_id):

    meta = tmdb.get_meta_by_id("movie", video_id)

    # try:
    #     path = tmdb.get_path(video_id)
    #     duration = acid_transcode.ffprobe_getduration(path)
    # except Exception as e:
    #     duration = 0
    #     print(f"Can not get duration of video: {e}")

    return render_template(
        "sync_player.html.j2",
        title=meta["title"],
        video=video_id,
        sync=request.args.get("session"),
        transcode=request.args.get("transcoding"),
    )


@app.route("/player/get/<int:video_id>")
def player_get_video(video_id):

    transcode = request.args.get("transcoding")
    transcode_time = request.args.get("time")

    try:
        if transcode == "1":
            m3u8fullpath = acid_transcode.ffmpeg_transcode(
                tmdb.get_path(video_id), start=int(transcode_time)
            )

            return send_from_directory(
                directory=os.path.dirname(m3u8fullpath),
                filename=os.path.basename(m3u8fullpath),
            )
        else:
            data = tmdb.get_filename(video_id)
            return send_from_directory(
                directory=data["path"], filename=data["filename"]
            )
    except KeyError:
        return abort(404)


#
#  PLAYER - TV SHOWS
#


@app.route("/video/<int:video_id>/<int:season_number>/<int:episode_number>")
def play_episode(video_id, season_number, episode_number):

    meta = tmdb.get_meta_by_id("tvshow", video_id)

    # try:
    #     path = tmdb.get_path_episode(video_id, season_number, episode_number)
    #     duration = acid_transcode.ffprobe_getduration(path)
    # except Exception as e:
    #     duration = 0
    #     print(f"Can not get duration of video: {e}")

    return render_template(
        "sync_player.html.j2",
        title=f"""{meta["title"]} - S{str(season_number).zfill(2)}E{str(episode_number).zfill(2)}""",
        video=f"{video_id}/{season_number}/{episode_number}",
        sync=request.args.get("session"),
        transcode=request.args.get("transcoding"),
    )


@app.route("/player/get/<int:video_id>/<int:season_number>/<int:episode_number>")
def player_get_episode(video_id, season_number, episode_number):

    transcode = request.args.get("transcoding")
    transcode_time = request.args.get("time")

    try:
        if transcode == "1":

            m3u8fullpath = acid_transcode.ffmpeg_transcode(
                tmdb.get_path_episode(video_id, season_number, episode_number),
                start=int(transcode_time),
            )

            return send_from_directory(
                directory=os.path.dirname(m3u8fullpath),
                filename=os.path.basename(m3u8fullpath),
            )
        else:
            data = tmdb.get_filename_episode(video_id, season_number, episode_number)

            return send_from_directory(
                directory=data["path"], filename=data["filename"]
            )
    except KeyError:
        return abort(404)


@app.route("/search/", methods=["POST", "GET"])
def search_query():

    if request.method == "POST":
        search = request.form.get("search")

        files = tmdb.get_media_by_keyword(search)

        return render_template(
            "library_search.html",
            selected="Search",
            library=get_library_items(),
            media=files,
            search=search,
        )

    else:
        return render_template(
            "library_search.html", selected="Search", library=get_library_items(),
        )


# file manager


@app.route("/files/")
@app.route("/files/<string:library_name>/")
@app.route("/files/<string:library_name>/<path:path>")
def library_files(path="", library_name=None):
    file_browser = []
    library_items = get_library_items()

    if library_name:

        for library in library_items:
            if library["name"] == library_name:
                library_path = library["path"]

        directory = Path(library_path, path)
        for item in directory.iterdir():
            if item.is_file():
                json = {
                    "title": item.name,
                    "content_dir": item.name,
                    "type": "file",
                }
                file_browser.append(json)

            else:
                json = {
                    "title": item.name,
                    "content_dir": item.name,
                    "type": "folder",
                }
                file_browser.append(json)

        return render_template(
            "library_files.html.j2",
            selected="Files",
            library=library_items,
            media=file_browser,
            goback=True,
            current_dir=directory.name,
        )

    else:
        for library in library_items:

            json_data = {
                "title": library["name"],
                "content_dir": library["name"],
                "type": "folder",
            }
            file_browser.append(json_data)

        return render_template(
            "library_files.html.j2",
            selected="Files",
            library=library_items,
            media=file_browser,
            goback=False,
            current_dir="Files",
        )


# @app.route("/files/<string:name>.<string:extension>/", defaults={"path": ""})
# @app.route("/files/<path:path>/<string:name>.<string:extension>/")
# def file_browser_video(path, name, extension):
#     if extension.startswith(("mp4", "mkv")):
#         session_id = f"{uuid.uuid4()}"
#         directory = folder_location + path
#         filename = f"{name}.{extension}"
#         create_new_session(session_id, directory, filename)
#         return redirect(f"/video.sync?session={session_id}", code=303)


def create_new_session(video_id, session_id=None):
    if session_id in session_storage:
        return session_id
    elif session_id:
        new_session_id = session_id
        session_storage[new_session_id] = {
            "video_id": video_id,
            "time": None,
        }
        return new_session_id
    else:
        new_session_id = f"{uuid.uuid4()}"[:8]
        session_storage[new_session_id] = {
            "video_id": video_id,
            "time": None,
        }
        return new_session_id


def get_subtitles(video_filename):
    video_filename = video_filename.split(".")
    subtitles_list = []

    directory = Path(subtitle_folder_location)
    for item in directory.iterdir():
        if item.is_file() and str(video_filename) in str(item.name):
            try:
                filename = filename.split(".")
                lang_code = str(filename[-2])
                lang_name = languages.get(alpha2=lang_code).name
                subtitles_list.append({"name": lang_name, "code": lang_code})
            except Exception as e:
                print(f"Error get_subtitles: {e}")
    return subtitles_list


# @app.route("/video.sync")
# def player():
#     session_id = request.args.get("session")
#     if session_id in session_storage:
#         title = session_storage[session_id]["meta"]["title"]
#         return render_template("sync_player.html", title=title)
#     else:
#         return redirect("/", code=303)


@app.route("/scan_library")
def scanning_tmdb():
    tmdb.scan_library()
    return redirect("/", code=303)


@app.route("/watch")
def youtube_player():
    try:
        session_id = request.args.get("v")
        t = request.args.get("t")
        if session_id not in session_storage:
            session_storage[session_id] = {
                "directory": "",
                "filename": "Youtube",
                "meta": {"Youtube"},
            }
        return render_template("youtube.html")
    except KeyError:
        return redirect("/", code=303)


#######
#####
### OLD CODE SEE /PLAYER/GET/
####
#####
# @app.route("/player/<string:session_id>")
# def video(session_id):
#     transcode = request.args.get("transcoding")
#     transcode_time = request.args.get("time")
#     try:
#         if transcode == "1":
#             m3u8fullpath = acid_transcode.ffmpeg_transcode(
#                 session_storage[session_id]["path"], start=int(transcode_time)
#             )
#             if m3u8fullpath:
#                 session_storage[session_id]["m3u8fullpath"] = m3u8fullpath
#                 return send_from_directory(
#                     directory=os.path.dirname(m3u8fullpath),
#                     filename=os.path.basename(m3u8fullpath),
#                 )
#             else:
#                 m3u8fullpath = session_storage[session_id]["m3u8fullpath"]
#                 return send_from_directory(
#                     directory=os.path.dirname(m3u8fullpath),
#                     filename=os.path.basename(m3u8fullpath),
#                 )
#         else:
#             return send_from_directory(
#                 directory=session_storage[session_id]["directory"],
#                 filename=session_storage[session_id]["filename"],
#             )
#     except KeyError:
#         return abort(404)


@app.route("/thumbnail/<string:poster_path>")
def get_thumbnail(poster_path):
    file = Path(tmdb.get_thumbnail_path(), poster_path)

    if file.exists():
        return send_from_directory(
            directory=tmdb.get_thumbnail_path(), filename=poster_path,
        )
    else:
        return redirect(f"https://image.tmdb.org/t/p/w500/{poster_path}")


def srtToVtt(srt_path):
    srt_filename = os.path.basename(srt_path)
    name = srt_filename.replace(".srt", "")

    vtt_path = f"{subtitle_folder_location}{name}.vtt"

    if not os.path.exists(srt_path):
        return
    if os.path.exists(vtt_path):
        return

    vtt = io.open(vtt_path, "w+", encoding="utf-8", errors="ignore")
    vtt.write("WEBVTT\n\n")
    srt = io.open(srt_path, "r", encoding="utf-8", errors="ignore")
    line = srt.readline()
    while line:
        if line.strip():
            if "-->" in line:
                line = line.replace(",", ".")

            if line.rstrip().isdigit():
                vtt.write(f"\n{line}")
            else:
                vtt.write(f"{line}")

        line = srt.readline()
    srt.close()
    vtt.close()


def srtToVtt_directory(directory):
    directory = Path(directory)

    for item in directory.iterdir():
        if item.is_file() and (item.name).endswith(".srt"):
            srtToVtt(item)


@app.route("/subtitle/<string:session_id>/<string:language_code>")
def subtitle(session_id, language_code):
    try:
        return send_from_directory(
            directory=subtitle_folder_location,
            filename=f"{session_storage[session_id]['filename'].split('.')[0]}.{language_code}.vtt",
        )
    except KeyError:
        return abort(404)


@socketio.on("client update", namespace="/sync")
def client_update(client_data):
    session.client.update_client(client_data)
    session.client.check_client_in_sync()


@socketio.on("client request sync", namespace="/sync")
def sync_time(client_data):
    session.client.sync_other_clients(client_data)


@socketio.on("connect", namespace="/sync")
def on_connect():
    session_id = request.args.get("session")
    video_id = request.args.get("video_id")

    client_session = create_new_session(video_id, session_id)

    session.client = iXecSync(request, client_session)


@socketio.on("disconnect", namespace="/sync")
def on_disconnect():
    session.client.remove_client()


if sys.platform == "win32":
    debug_socketio = True
else:
    debug_socketio = False

if __name__ == "__main__":
    socketio.run(app, debug=debug_socketio, host="0.0.0.0")
