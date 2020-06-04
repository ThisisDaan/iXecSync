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
    duration = -1
    FNULL = open(os.devnull, "w")
    proc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=FNULL)
    try:

        class LocalBreak(Exception):
            pass

        for line in iter(proc.stderr.readline, ""):
            line = line.rstrip()
            # Duration: 00:00:45.13, start: 0.000000, bitrate: 302 kb/s
            m = re.search("Duration: (..):(..):(..)\...", line.decode("utf-8"))
            if m is not None:
                print(m)
                duration = (
                    int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3)) + 1
                )
                print("Video duration= " + str(duration))
                return jsonify(duration=duration)
                break
                exit
                ##wtf waarom komt dit drie keer?!?!
    finally:
        proc.kill()


def transcodeMime(format):
    transcode_mime = {"*": "video/mp4", "mp3": "audio/mp3", "jpg": "image/jpg"}
    """Translate file format to Mime type."""
    return transcode_mime.get(format) or transcode_mime["*"]


def transcode(path, start, format, vcodec, acodec):
    # ffmpeg_transcode_args = {
    #     "*": " -ss {} -i {} -f {} -vcodec {} -acodec {} -strict experimental -preset ultrafast -movflags frag_keyframe+empty_moov+faststart pipe:1",
    #     "mp3": ["-f", "mp3", "-codec", "copy", "pipe:1"],
    # }
    # """Transcode in ffmpeg subprocess."""
    # args = ffmpeg_transcode_args["*"]
    # cmdline = ffmpeg + args.format(int(start), path, format, vcodec, acodec)
    # print(cmdline)
    ffmpeg_parameters = f""" -ss {start} -i "{path}" -f {format} -vcodec {vcodec} -acodec {acodec} -strict experimental -preset ultrafast -movflags frag_keyframe+empty_moov+faststart pipe:1"""
    cmdline = ffmpeg + ffmpeg_parameters  # + " -loglevel quiet"
    proc = subprocess.Popen(cmdline, stdout=subprocess.PIPE)
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
    acodec = "mp3"
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
