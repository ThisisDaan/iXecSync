from __main__ import socketio, join_room, emit
from flask import session, request
from collections import defaultdict
import uuid
import time


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
