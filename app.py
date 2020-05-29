from flask import (
    Flask,
    render_template,
    send_from_directory,
    request,
    session,
    redirect,
)
from jinja2 import Template
from flask_socketio import SocketIO, emit, join_room, leave_room
import time
import os
from collections import defaultdict
import uuid

app = Flask(__name__)
socketio = SocketIO(app)

folder_location = os.path.join(
    os.path.dirname(os.path.realpath(__file__)) + os.sep + "video" + os.sep
)

video_location = {}


class iXecSync:
    clients = defaultdict(list)

    def __init__(self, request, session):
        self.id = request.sid
        self.update_client_time(0)
        self.paused = True
        self.session = session
        self.join_session()
        print(f"{self.id}@{self.session} - Client connected")

    def remove_client(self):
        iXecSync.clients[self.session].remove(self)
        print(f"{self.id}@{self.session} - Client disconnected")
        self.cleanup_after()

    # NOTE if only one client, and the client refreshes, the video_location will be deleted. #ERROR BUG FIX THISDFSLFKDSJFDSJFSD

    def cleanup_after(self):
        if len(iXecSync.clients[self.session]) < 1:
            del video_location[self.session]

    # NOTE sometimes client doesn't sync with reference on startup

    def join_session(self):
        join_room(self.session)
        iXecSync.clients[self.session].append(self)
        emit(
            "sync", {"time": False, "paused": True}, room=self.session, skip_sid=self.id
        )
        self.push()

    def push(self):
        reference = self.get_reference()
        delay = self.epoch - reference.epoch
        profile = {
            "time": reference.time + delay,
            "paused": True,
        }
        emit("sync", profile, room=self.id)

    def update_client_time(self, client_time):
        self.time = client_time
        self.epoch = int(round(time.time() * 1000))

    def update_client(self, client_data):
        self.update_client_time(client_data["time"])
        self.paused = client_data["paused"]
        self.check_client_in_sync()

    def sync_other_clients(self, client_data):
        self.update_client_time(client_data["time"])
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

        if reference.id == self.id:
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
            print("syncing client")
            self.sync_client()
        else:
            emit(
                "out of sync",
                {
                    "outofsync": outofsync,
                    "delay": delay_between_players,
                    "max_delay": max_delay,
                },
                room=self.id,
            )


def create_session_id(filename, session):
    return f"{filename}/{session}"


@app.after_request
def add_header(r):
    r.cache_control.max_age = 0
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers["Cache-Control"] = "public, max-age=0"
    return r


@app.route("/")
def index():
    redirect_url = f"{request.base_url}/file/"
    return redirect(redirect_url, code=302)


@app.route("/file/", defaults={"path": ""})
@app.route("/file/<path:path>")
def file_browsing_root(path):
    content = getContent(folder_location + path)
    return render_template(
        "file_browser.html",
        dirs=content["dirs"],
        files=content["files"],
        empty=content["empty"],
    )


def getContent(folder_dir):
    folder = defaultdict(list)
    for (root, dirs, files) in os.walk(folder_dir):
        for directory in dirs:
            json = {
                "name": directory,
                "path": os.path.join(root, directory),
            }
            folder["dirs"].append(json)
        for filename in files:
            if filename.endswith(".mkv") or filename.endswith(".mp4"):
                json = {
                    "name": filename,
                    "path": os.path.join(root, filename),
                }
                folder["files"].append(json)
        break

    if len(folder) == 0:
        folder["empty"].append({"name": "This folder is empty"})

    return folder


@app.route("/file/<string:filename>.<string:extension>", defaults={"path": ""})
@app.route("/file/<path:path>/<string:filename>.<string:extension>")
def player(path, filename, extension):
    session_id = request.args.get("session")
    file = filename + "." + extension
    if session_id:
        video_id = create_session_id(file, session_id)
        video_location[video_id] = {
            "directory": folder_location + path,
            "filename": file,
        }

        video_filename = video_location[video_id]["filename"]

        return render_template("player.html", filename=video_filename)
    else:
        redirect_url = f"{request.base_url}?session={uuid.uuid4()}"
        return redirect(redirect_url, code=302)


@app.route("/player/<string:filename>/<string:session_id>")
def stream(session_id, filename):
    video_id = create_session_id(filename, session_id)
    return send_from_directory(
        directory=video_location[video_id]["directory"],
        filename=video_location[video_id]["filename"],
    )


@socketio.on("client request sync", namespace="/sync")
def sync_time(client_data):
    session.client.sync_other_clients(client_data)


@socketio.on("client update", namespace="/sync")
def sync_time(client_data):
    session.client.update_client(client_data)


@socketio.on("connect", namespace="/sync")
def on_connect():
    client_session = create_session_id(
        request.args.get("filename"), request.args.get("session")
    )
    session.client = iXecSync(request, client_session)


@socketio.on("disconnect", namespace="/sync")
def on_disconnect():
    session.client.remove_client()


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")
