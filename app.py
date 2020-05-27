from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit
import datetime
import json
import time

app = Flask(__name__)
socketio = SocketIO(app)


# clients = {}
# reference = []


class iXecSync:
    clients = {}
    reference = []

    def __init__(self, request):
        self.id = request.sid
        self.epoch = int(round(time.time() * 1000))
        iXecSync.reference.append(self)
        iXecSync.clients[self.id] = self
        print(f"{self.id} - Client connected")

    def update_client(self, client_data):
        self.time = client_data["time"]
        self.playing = client_data["playing"]
        self.ready = client_data["ready"]
        self.last_epoch = self.epoch
        self.epoch = int(round(time.time() * 1000))
        self.latency = abs((self.epoch - self.last_epoch) - client_data["heartbeat"])
        self.check_client_in_sync()

    def sync_client(self):
        emit("sync", self.get_reference_profile(), room=self.id)

    def sync_all_clients(self):
        emit(
            "sync", self.get_reference_profile(), broadcast=True,
        )

    def get_reference(self):
        return iXecSync.reference[0]

    def get_reference_profile(self):
        reference = self.get_reference()
        return reference.get_json_profile()

    def get_json_profile(self):
        profile = {
            "id": self.id,
            "time": self.time,
            "playing": self.playing,
            "ready": self.ready,
            "epoch": self.epoch,
        }
        return profile

    def message(self, message):
        emit(
            "message", message, room=self.id,
        )

    def check_client_in_sync(self):
        reference = self.get_reference()

        if reference == self:
            self.message("You are the reference")
            return

        max_delay = 100  # in milliseconds
        max_out_of_sync = 5000  # in milliseconds

        delay = self.epoch - reference.epoch
        reference_time_delay = reference.time + delay

        delay_between_players = abs(self.time - reference_time_delay) + self.latency

        if delay_between_players > max_delay:
            if self.time > reference_time_delay:
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
def sync_time(data):
    emit("sync", data, broadcast=True, include_self=False)


# @socketio.on("latency", namespace="/sync")
# def sync_time(data):
#     emit("latency", data, room=request.sid)


@socketio.on("interval sync", namespace="/sync")
def sync_time(client_data):
    client = get_client(request)
    client.update_client(client_data)


@socketio.on("connect", namespace="/sync")
def on_connect():
    iXecSync(request)


@socketio.on("disconnect", namespace="/sync")
def on_disconnect():
    remove_client(request)


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")
