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


def transcode(path, start, vformat, vcodec, acodec):
    cmdline = []
    cmdline.append(ffmpeg)
    cmdline.append("-nostdin")
    # -re is useful when live streaming (use input media frame rate), do not use it if you are creating a file,
    # cmdline.append("-re")
    # cmdline.append("00:08:00")
    # cmdline.append("-itsoffset")
    # cmdline.append("00:00:04.00")
    cmdline.extend(["-i", path])
    # -g 52 forces (at least) every 52nd frame to be a keyframe
    # cmdline.append("-g")
    # cmdline.append("52")
    cmdline.extend(["-f", vformat])
    cmdline.extend(["-vcodec", vcodec])
    cmdline.extend(["-acodec", acodec])
    cmdline.extend(["-strict", "experimental"])
    cmdline.extend(["-preset", "ultrafast"])
    # frag_keyframe causes fragmented output,
    # empty_moov will cause output to be 100% fragmented; without this the first fragment will be muxed as a short movie (using moov) followed by the rest of the media in fragments,
    # # cmdline.append("-movflags")
    # # cmdline.append("frag_keyframe+empty_moov+faststart")
    cmdline.extend(["-movflags", "frag_keyframe+empty_moov+faststart"])
    ##audiosyncfix
    # cmdline.append("-af")
    # cmdline.append("aresample=async=1:first_pts=0")
    # cmdline.append("-vf")
    # cmdline.append("setpts='if(eq(N\,0),0,PTS)'")
    # cmdline.append("-async")
    # cmdline.append("1")
    cmdline.extend(["-loglevel", "debug"])
    ##putting the timestamp logic to the output instead of the input creates magic!
    cmdline.extend(["-ss", str(start)])
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


def ffmpeg_transcode(path="video/video.mkv", vformat="mp4", start=0):
    vcodec = "copy"
    acodec = "libmp3lame"
    try:
        mime = "video/mp4"
        return Response(
            response=transcode(path, start, vformat, vcodec, acodec),
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
