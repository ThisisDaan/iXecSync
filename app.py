from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit
import datetime
import json
import time
import copy

app = Flask(__name__)
socketio = SocketIO(app)


class iXecSync:
    clients = {}
    reference = []

    def __init__(self, request):
        self.id = request.sid
        self.update_client_time(0)
        self.paused = True

        iXecSync.reference.append(self)
        iXecSync.clients[self.id] = self
        print(f"{self.id} - Client connected")
        self.push()

    def update_client_time(self, time):
        self.time = time
        self.epoch = self.get_time()

    def get_time(self):
        return int(round(time.time() * 1000))

    def update_client(self, client_data):
        self.update_client_time(client_data["time"])
        self.paused = client_data["paused"]
        if self.time != 0:
            self.check_client_in_sync()

    def sync_client(self):
        emit("sync", self.get_reference_profile(), room=self.id)

    def push(self):
        reference = self.get_reference()
        delay = self.epoch - reference.epoch
        profile = {
            "time": reference.time + delay,
            "paused": True,
        }
        emit("push", profile, room=self.id)

    def get_reference(self):
        return iXecSync.reference[0]

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
                    f"{request.sid} - not in sync - slowing down ({round(delay_between_players)}ms)"
                )
                outofsync = 2
            else:
                print(
                    f"{request.sid} - not in sync - speeding up ({round(delay_between_players)}ms)"
                )
                outofsync = 1
        else:
            print(f"{request.sid} - We are in sync ({round(delay_between_players)}ms)")
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


def get_client(request):
    return iXecSync.clients[request.sid]


def remove_client(request):
    client = iXecSync.clients[request.sid]
    iXecSync.reference.remove(client)
    del client
    print(f"{request.sid} - Client disconnected")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/video/<string:file_name>")
def stream(file_name):
    video_dir = "./video"
    return send_from_directory(directory=video_dir, filename=file_name)


@socketio.on("user sync", namespace="/sync")
def sync_time(client_data):
    client = get_client(request)
    client.update_client_time(client_data["time"])
    emit("sync", client_data, broadcast=True, include_self=False)


@socketio.on("interval sync", namespace="/sync")
def sync_time(client_data):
    client = get_client(request)
    client.update_client(client_data)


@socketio.on("connect", namespace="/sync")
def on_connect():
    iXecSync(request)
    emit("sync", {"time": False, "paused": True}, broadcast=True, include_self=False)


@socketio.on("disconnect", namespace="/sync")
def on_disconnect():
    remove_client(request)


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")
