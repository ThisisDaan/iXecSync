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
        # self.push_session_meta()

    # def push_session_meta(self):
    #     try:
    #         metadata = session_storage[self.session]["meta"]
    #         emit("meta", metadata, room=self.id)
    #     except Exception as e:
    #         print(f"invalid session: {e}")

    def update_client_time(self, client_time):
        self.time = client_time
        self.epoch = int(round(time.time() * 1000))

    def update_session(self):
        if self.is_reference():
            session_storage[self.session]["time"] = self.time
            session_storage[self.session]["paused"] = self.paused

    def update_client(self, client_data):
        self.update_client_time(client_data["time"])
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


@app.after_request
def add_header(r):
    r.cache_control.max_age = 0
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers["Cache-Control"] = "public, max-age=0"
    return r


@app.route("/search")
@app.route("/")
def index():
    return redirect("/file", code=303)


@app.route("/file/", defaults={"path": ""})
@app.route("/file/<path:path>")
def file_browsing_root(path):
    content = getContent(folder_location + path)
    return render_template(
        "file_browser.html",
        folders=content["folders"],
        files=content["files"],
        empty=content["empty"],
    )


@app.route("/search/<string:search>")
def file_browsing_search(search):
    content = getContent(folder_location, search)
    return render_template(
        "file_browser.html",
        folders=content["folders"],
        files=content["files"],
        empty=content["empty"],
        search=True,
    )


def getContent(folder, search_string=None):
    content = defaultdict(list)

    for (root, dirs, files) in os.walk(folder):

        for directory in dirs:
            if search_string is None or search_string.lower() in directory.lower():

                json = {
                    "name": f"{directory}",
                    "path": f"{os.path.join(root.replace(folder_location, ''), directory)}",
                    "type": "folder",
                }
                content["folders"].append(json)

        for filename in files:
            if search_string is None or search_string.lower() in filename.lower():
                if filename:  # )
                    json = {
                        "name": f"{filename}",
                        "path": f"{os.path.join(root.replace(folder_location, ''), filename)}",
                        "type": "file",
                    }
                    if filename.endswith((".mp4", ".mkv")):
                        json["format"] = "video"
                        json["order"] = 0
                        content["files"].insert(0, json)
                    else:
                        json["format"] = "other"
                        json["order"] = 1
                        content["files"].append(json)

        if search_string is None:
            break

    if len(content) == 0:
        if search_string:
            content["empty"].append({"name": "No items match your search."})
        else:
            content["empty"].append({"name": "This folder is empty."})

    content["folders"] = sorted(content["folders"], key=lambda k: (k["name"].lower()))
    content["files"] = sorted(
        content["files"], key=lambda k: (k["order"], k["name"].lower())
    )
    return content


@app.route("/file/<string:name>.<string:extension>", defaults={"path": ""})
@app.route("/file/<path:path>/<string:name>.<string:extension>")
def file_browser_video(path, name, extension):
    if extension.startswith(("mp4", "mkv")):
        session_id = f"{uuid.uuid4()}"
        directory = folder_location + path
        filename = f"{name}.{extension}"
        create_new_session(session_id, directory, filename)
        return redirect(f"/video.sync?session={session_id}", code=303)


def create_new_session(session_id, directory, filename):
    srtToVtt_directory(directory)
    lang = get_subtitles(filename)
    path = os.path.join(directory, filename)
    duration = 0
    duration = acid_transcode.ffmpeg_getduration(path)

    session_storage[session_id] = {
        "directory": directory,
        "filename": filename,
        "path": path,
        "time": None,
        "meta": {"title": filename, "duration": duration, "lang": lang,},
    }
    print(session_storage[session_id]["meta"])


def get_subtitles(video_filename):
    video_filename = video_filename.split(".")
    subtitles_list = []
    for (root, dirs, files) in os.walk(subtitle_folder_location):
        for filename in files:
            if video_filename[0] in filename:
                try:
                    filename = filename.split(".")
                    lang_code = str(filename[-2])
                    lang_name = languages.get(alpha2=lang_code).name
                    subtitles_list.append({"name": lang_name, "code": lang_code})
                except Exception as e:
                    print(f"Error get_subtitles: {e}")

        break
    return subtitles_list


@app.route("/video.sync")
def player():
    session_id = request.args.get("session")
    if session_id in session_storage:
        return render_template("sync_player.html")
    else:
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


@app.route("/player/meta/<string:session_id>")
def session_duration(session_id):
    return jsonify(session_storage[session_id]["meta"])


@app.route("/player/<string:session_id>")
def video(session_id):
    transcode = request.args.get("transcoding")
    transcode_time = request.args.get("time")
    try:
        # video_directory = session_storage[session_id]["directory"]
        # video_filename = session_storage[session_id]["filename"]
        # video_path = os.path.join(video_directory, video_filename)
        # ffmpeg_getduration(video_path)
        if transcode == "1":
            return acid_transcode.ffmpeg_transcode(
                session_storage[session_id]["path"], start=int(transcode_time)
            )
        else:
            return send_from_directory(
                directory=session_storage[session_id]["directory"],
                filename=session_storage[session_id]["filename"],
            )
    except KeyError:
        return abort(404)


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
    for (root, dirs, files) in os.walk(directory):
        for filename in files:
            if filename.endswith(".srt"):
                srt_path = os.path.join(root, filename)
                srtToVtt(srt_path)
        break


@app.route("/subtitle/<string:session_id>/<string:language_code>")
def subtitle(session_id, language_code):
    try:
        return send_from_directory(
            directory=subtitle_folder_location,
            filename=f"{session_storage[session_id]['filename'].split('.')[0]}.{language_code}.vtt",
        )
    except KeyError:
        return abort(404)


@socketio.on("client request sync", namespace="/sync")
def sync_time(client_data):
    session.client.sync_other_clients(client_data)


@socketio.on("client update", namespace="/sync")
def sync_time(client_data):
    session.client.update_client(client_data)
    session.client.check_client_in_sync()


@socketio.on("connect", namespace="/sync")
def on_connect():
    client_session = request.args.get("session")
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
