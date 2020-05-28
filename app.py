from flask import Flask, render_template, send_from_directory, request
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
    clients = {}

    def add_client(self, request):
        self.id = request.sid
        self.update_client_time(0)
        self.paused = True

        iXecSync.clients[self.id] = self
        print(f"{self.id} - Client connected")
        self.push()

    def get_client(self, request):
        return iXecSync.clients[request.sid]

    def remove_client(self):
        del iXecSync.clients[self.id]
        print(f"{self.id} - Client disconnected")

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

    def sync_client(self):
        emit("sync", self.get_reference_profile(), room=self.id)

    def get_reference(self):
        reference = next(iter(iXecSync.clients.items()))
        return reference[1]

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


@app.route("/file/<path:path>/<string:file_name>")
def index(path, file_name):
    global video_dir
    global video_filename

    video_dir = folder_location + path
    video_filename = file_name

    return render_template("index.html")


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


@app.route("/player/video.sync")
def stream():
    print(video_dir)
    print(video_filename)
    return send_from_directory(directory=video_dir, filename=video_filename)


@socketio.on("user sync", namespace="/sync")
def sync_time(client_data):
    client = iXecSync().get_client(request)
    client.update_client_time(client_data["time"])
    emit("sync", client_data, broadcast=True, include_self=False)


@socketio.on("interval sync", namespace="/sync")
def sync_time(client_data):
    client = iXecSync().get_client(request)
    client.update_client(client_data)


@socketio.on("connect", namespace="/sync")
def on_connect():
    client = iXecSync()
    client.add_client(request)
    emit("sync", {"time": False, "paused": True}, broadcast=True, include_self=False)


@socketio.on("disconnect", namespace="/sync")
def on_disconnect():
    client = iXecSync().get_client(request)
    client.remove_client()


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")
