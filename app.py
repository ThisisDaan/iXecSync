from flask import Flask, render_template, send_from_directory, request, session
from jinja2 import Template
from flask_socketio import SocketIO, emit
import time
import os

app = Flask(__name__)
socketio = SocketIO(app)

folder_location = os.path.join(
    os.path.dirname(os.path.realpath(__file__)) + os.sep + "video" + os.sep
)
video_dir = folder_location
video_filename = ""


class iXecSync:
    clients = []

    def __init__(self, request):
        self.id = request.sid
        self.update_client_time(0)
        self.paused = True

        iXecSync.clients.append(self)
        print(f"{self.id} - Client connected")
        emit("sync", {"time": False, "paused": True}, broadcast=True, skip_sid=self.id)
        self.push()

    def remove_client(self):
        iXecSync.clients.remove(self)
        print(f"{self.id} - Client disconnected")

    #
    # NOTE sometimes client doesn't sync with reference on startup
    #
    def push(self):
        reference = self.get_reference()
        delay = self.epoch - reference.epoch
        profile = {
            "time": reference.time + delay,
            "paused": True,
        }
        emit("push", profile, room=self.id)

    def update_client_time(self, client_time):
        self.time = client_time
        self.epoch = int(round(time.time() * 1000))

    def update_client(self, client_data):
        self.update_client_time(client_data["time"])
        self.paused = client_data["paused"]
        self.check_client_in_sync()

    def sync_other_clients(self, client_data):
        self.update_client_time(client_data["time"])
        emit("sync", client_data, broadcast=True, skip_sid=self.id)

    def sync_client(self):
        emit("sync", self.get_reference_profile(), room=self.id)

    def get_reference(self):
        return iXecSync.clients[0]

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
                    f"{self.id} - not in sync - slowing down ({round(delay_between_players)}ms)"
                )
                outofsync = 2
            else:
                print(
                    f"{self.id} - not in sync - speeding up ({round(delay_between_players)}ms)"
                )
                outofsync = 1
        else:
            print(f"{self.id} - We are in sync ({round(delay_between_players)}ms)")
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


@app.after_request
def add_header(r):
    r.cache_control.max_age = 0
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers["Cache-Control"] = "public, max-age=0"
    return r


@app.route("/file/<path:path>/<string:file_name>")
def index(path, file_name):
    global video_dir
    global video_filename

    video_dir = folder_location + path
    video_filename = file_name

    return render_template("index.html", filename=video_filename)


# @app.route("/overview")
# def overview():
#     return render_template("overview.html", videos=getVideos())


# def getVideos():
#     list = []
#     for (root, dirs, files) in os.walk(folder_location):
#         for filename in files:
#             if filename.endswith(".mkv") or filename.endswith(".mp4"):
#                 json = {
#                     "filename": filename,
#                     "path": os.path.join(root, filename),
#                 }
#                 list.append(json)

#     return list


#
# NOTE create rooms for each video file that is playing
#


@app.route("/player/<string:file_name>")
def stream(file_name):
    return send_from_directory(directory=video_dir, filename=video_filename)


@socketio.on("user sync", namespace="/sync")
def sync_time(client_data):
    session.client.sync_other_clients(client_data)


@socketio.on("interval sync", namespace="/sync")
def sync_time(client_data):
    session.client.update_client(client_data)


@socketio.on("connect", namespace="/sync")
def on_connect():
    session.client = iXecSync(request)


@socketio.on("disconnect", namespace="/sync")
def on_disconnect():
    session.client.remove_client()


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")
