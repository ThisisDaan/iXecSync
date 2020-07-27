from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from pathlib import Path
import json
import sys

app = Flask(__name__)
socketio = SocketIO(app)

"""
Loads the config.json on launch.
"""
root = Path(__file__).parent
with open(Path(root, "config.json")) as file:
    config = json.load(file)

"""
Importing the modules we want to use.
"""
import routes


""" 
Enables debugging under Windows.
The server is running Linux.
"""
debug = sys.platform == "win32"

if __name__ == "__main__":
    socketio.run(app, debug=debug, host="0.0.0.0")
