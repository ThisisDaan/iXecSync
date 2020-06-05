import subprocess
import sys
import re
import os
from flask import Response, abort, jsonify
import time
import queue
import threading

libs_path = f"{os.path.dirname(os.path.realpath(__file__))}{os.sep}Libs{os.sep}"
ffmpeg = f"{libs_path}ffmpeg"
ffprobe = f"{libs_path}ffprobe"
if sys.platform == "win32":
    ffmpeg += ".exe"
    ffprobe += ".exe"

# if sys.platform == "win32":
#     ffmpeg = (
#         os.path.dirname(os.path.realpath(__file__))
#         + os.sep
#         + "Libs"
#         + os.sep
#         + "ffmpeg.exe"
#     )
# else:
#     ffmpeg = (
#         os.path.dirname(os.path.realpath(__file__))
#         + os.sep
#         + "Libs"
#         + os.sep
#         + "ffmpeg"
#     )

# if sys.platform == "win32":
#     ffprobe = (
#         os.path.dirname(os.path.realpath(__file__))
#         + os.sep
#         + "Libs"
#         + os.sep
#         + "ffprobe.exe"
#     )
# else:
#     ffprobe = (
#         os.path.dirname(os.path.realpath(__file__))
#         + os.sep
#         + "Libs"
#         + os.sep
#         + "ffprobe"
#     )


def ffmpeg_getduration(path):
    cmdline = list()
    cmdline.append(ffmpeg)
    cmdline.append("-i")
    cmdline.append(path)
    cmdline.append("-loglevel")
    cmdline.append("verbose")
    duration = -1
    proc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL)
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


def ffprobe_getduration(path):
    cmdline = list()
    cmdline.append(ffprobe)
    cmdline.append("-i")
    cmdline.append(path)
    cmdline.extend(["-show_entries", "format=duration"])
    cmdline.extend(["-v", "quiet"])
    cmdline.extend(["-of", 'csv="p=0"'])
    proc = subprocess.Popen(cmdline, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    try:
        out, err = proc.communicate()
        print("==========output==========")
        print(out)
        if err:
            print("========= error ========")
            print(err)
    finally:
        proc.kill()


# def _watch_output(process: subprocess.Popen, queue):
#     for line in iter(process.stdout.readline, ""):
#         queue.put(line)
#     if process.poll() is not None:
#         return
# f = process.stdout
# byte = f.read(65536)
# while byte:
#     yield byte
#     # queue.put(byte)
#     byte = f.read(65536)
#     if process.poll() is not None:
#         return


# @property
# def stdout(self):
#     return self.process.stdout


# @property
# def stderr(self):
#     return self.process.stderr


def transcode(path, start, vformat, vcodec, acodec):
    # ffprobe_getduration(path)
    start_time = time.time()
    wait_limit = 15
    return_code = None
    process = None  # type: subprocess.Popen
    run_time = 0

    cmdline = []
    cmdline.append(ffmpeg)
    cmdline.append("-nostdin")
    # cmdline.append("-noaccurate_seek")
    # -re is useful when live streaming (use input media frame rate), do not use it if you are creating a file,
    # cmdline.append("-re")
    # cmdline.append("00:08:00")
    # cmdline.append("-itsoffset")
    # cmdline.append("00:00:04.00")
    cmdline.extend(["-i", path])
    # -g 52 forces (at least) every 52nd frame to be a keyframe
    # cmdline.append("-g")
    # cmdline.append("52")
    cmdline.extend(["-f", "mp4"])

    # cmdline.extend(["-ignore_editlist", "1"])
    cmdline.extend(["-vcodec", vcodec])
    cmdline.extend(["-acodec", acodec])
    # cmdline.extend(["-ab", "190k"])
    # cmdline.extend(["-ar", "44100"])
    # cmdline.extend(["-strict", "experimental"])
    cmdline.extend(["-preset", "veryfast"])
    # frag_keyframe causes fragmented output,
    # empty_moov will cause output to be 100% fragmented; without this the first fragment will be muxed as a short movie (using moov) followed by the rest of the media in fragments,
    cmdline.extend(["-movflags", "frag_keyframe+empty_moov+faststart"])
    # cmdline.extend(["-movflags", "frag_keyframe"])
    ##audiosyncfix
    # cmdline.append("-af")
    # cmdline.append("aresample=async=1:first_pts=0")
    # cmdline.append("-vf")
    # cmdline.append("setpts='if(eq(N\,0),0,PTS)'")
    # cmdline.append("-async")
    # cmdline.append("1")
    cmdline.append("-hide_banner")
    cmdline.append("-nostats")
    cmdline.extend(["-loglevel", "warning"])
    ##putting the timestamp logic to the output instead of the input creates magic!
    cmdline.extend(["-ss", str(start)])
    cmdline.append("pipe:1")
    print(cmdline)
    process = subprocess.Popen(cmdline, shell=False, stdout=subprocess.PIPE)
    try:
        f = process.stdout
        byte = f.read(65536)
        while byte:
            yield byte
            byte = f.read(65536)
    finally:
        process.kill()
    # returned = None
    # last_output = time.time()
    # q = queue.Queue()
    # t = threading.Thread(target=_watch_output, args=(process, q,))
    # t.daemon = True
    # t.start()
    # while returned is None or not q.empty():
    #     returned = process.poll()
    #     try:
    #         bytefromqueue = q.get(timeout=0.5)
    #         # bytefromqueue = q.get_nowait()

    #     except queue.Empty:
    #         continue

    #     if not bytefromqueue:
    #         continue

    #     yield bytefromqueue
    # t.join()


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
