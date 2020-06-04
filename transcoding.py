import subprocess
import sys
import re
import os
from flask import Response, abort, jsonify

if sys.platform == "win32":
    ffmpeg = (
        os.path.dirname(os.path.realpath(__file__))
        + os.sep
        + "Libs"
        + os.sep
        + "ffmpeg.exe"
    )
else:
    ffmpeg = (
        os.path.dirname(os.path.realpath(__file__))
        + os.sep
        + "Libs"
        + os.sep
        + "ffmpeg"
    )


def ffmpeg_getduration(path):
    cmdline = list()
    cmdline.append(ffmpeg)
    cmdline.append("-i")
    cmdline.append(path)
    cmdline.append("-loglevel")
    cmdline.append("verbose")
    duration = -1
    FNULL = open(os.devnull, "w")
    proc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=FNULL)
    try:
        for line in iter(proc.stderr.readline, ""):
            line = line.rstrip()
            # Duration: 00:00:45.13, start: 0.000000, bitrate: 302 kb/s
            m = re.search("Duration: (..):(..):(..)\...", line.decode("utf-8"))
            if m is not None:
                print(m)
                duration = (
                    int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + 1
                )
                print("*" * 80)
                print("Video duration= " + str(duration))
                print("*" * 80)
                return int(duration)
                break
                ##wtf waarom komt dit drie keer?!?!
    finally:
        proc.kill()


def transcodeMime(format):
    transcode_mime = {"*": "video/mp4", "mp3": "audio/mp3", "jpg": "image/jpg"}
    """Translate file format to Mime type."""
    return transcode_mime.get(format) or transcode_mime["*"]


def transcode(path, start, format, vcodec, acodec):
    cmdline = list()
    cmdline.append(ffmpeg)
    cmdline.append("-ss")
    cmdline.append(str(start))
    cmdline.append("-i")
    cmdline.append(path)
    cmdline.append("-f")
    cmdline.append(format)
    cmdline.append("-vcodec")
    cmdline.append(vcodec)
    cmdline.append("-acodec")
    cmdline.append(acodec)
    cmdline.append("-strict")
    cmdline.append("experimental")
    cmdline.append("-preset")
    cmdline.append("ultrafast")
    cmdline.append("-movflags")
    cmdline.append("frag_keyframe+empty_moov+faststart")
    ##audiosyncfix
    cmdline.append("-filter:a")
    cmdline.append("aresample=async=1000")
    cmdline.append("-loglevel")
    cmdline.append("verbose")
    cmdline.append("pipe:1")
    print(cmdline)
    proc = subprocess.Popen(cmdline, shell=False, stdout=subprocess.PIPE)
    try:
        f = proc.stdout
        byte = f.read(65536)
        while byte:
            yield byte
            byte = f.read(65536)
    finally:
        proc.kill()


def ffmpeg_transcode(path="video/video.mkv", format="mp4", start=0):
    vcodec = "copy"
    acodec = "libmp3lame"
    try:
        mime = transcodeMime(format)
        return Response(
            response=transcode(path, start, format, vcodec, acodec),
            status=200,
            mimetype=mime,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Content-Type": mime,
                "Content-Disposition": "inline",
                "Content-Transfer-Enconding": "binary",
            },
        )
    except FileNotFoundError:
        abort(404)
