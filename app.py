from flask import Flask, render_template, send_from_directory, request
from flask_socketio import SocketIO, emit
import datetime
import json
import time

app = Flask(__name__)
socketio = SocketIO(app)


clients = {}
reference = []


def addClient(request):
    clients[request.sid] = {
        "id": request.sid,
        "time": 0,
        "playing": False,
        "ready": 0,
        "epoch": time.time(),
    }
    reference.append(request.sid)
    syncAll()


def removeClient(request):
    del clients[request.sid]
    reference.remove(request.sid)


def updateClient(request, data):
    clients[request.sid]["time"] = data["time"]
    clients[request.sid]["playing"] = data["playing"]
    clients[request.sid]["ready"] = data["ready"]
    clients[request.sid]["epoch"] = int(round(time.time() * 1000))
    if reference[0] != request.sid:
        inSync(request, clients[request.sid])
    else:
        emit("reference", {"reference": True}, room=request.sid)


def syncUser(user):
    r_id = reference[0]
    emit("sync", clients[r_id], room=user)


def syncAll():
    r_id = reference[0]
    emit(
        "sync", clients[r_id], broadcast=True,
    )


def inSync(request, data):
    r_id = reference[0]

    max_delay = 100  # in milliseconds

    client_time = data["epoch"]
    client_player_time = data["time"]

    reference_time = clients[r_id]["epoch"]
    reference_player_time = clients[r_id]["time"]

    delay = client_time - reference_time
    reference_player_time = reference_player_time + delay

    delay_between_players = abs(client_player_time - reference_player_time)
    if abs(client_player_time - reference_player_time) > max_delay:
        if client_player_time > reference_player_time:
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
    if delay_between_players > 60000:
        syncUser(request.sid)
    else:
        emit(
            "out of sync",
            {
                "outofsync": outofsync,
                "delay": delay_between_players,
                "max_delay": max_delay,
            },
            room=request.sid,
        )


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


@socketio.on("latency", namespace="/sync")
def sync_time(data):
    emit("latency", data, room=request.sid)


@socketio.on("interval sync", namespace="/sync")
def sync_time(data):
    updateClient(request, data)


@socketio.on("connect", namespace="/sync")
def on_connect():
    addClient(request)
    print(f"{request.sid} - Client connected")


@socketio.on("disconnect", namespace="/sync")
def on_disconnect():
    removeClient(request)
    print(f"{request.sid} - Client disconnected")


if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0")
