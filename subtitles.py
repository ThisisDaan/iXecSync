def srtToVtt(srt_path):
    srt_filename = os.path.basename(srt_path)
    name = srt_filename.replace(".srt", "")

    vtt_path = f"{subtitle_folder_location}{name}.vtt"

    if not os.path.exists(srt_path):
        return
    if os.path.exists(vtt_path):
        return

    vtt = io.open(vtt_path, "w+", encoding="utf-8", errors="ignore")
    vtt.write("WEBVTT\n\n")
    srt = io.open(srt_path, "r", encoding="utf-8", errors="ignore")
    line = srt.readline()
    while line:
        if line.strip():
            if "-->" in line:
                line = line.replace(",", ".")

            if line.rstrip().isdigit():
                vtt.write(f"\n{line}")
            else:
                vtt.write(f"{line}")

        line = srt.readline()
    srt.close()
    vtt.close()


def srtToVtt_directory(directory):
    directory = Path(directory)

    for item in directory.iterdir():
        if item.is_file() and (item.name).endswith(".srt"):
            srtToVtt(item)


@app.route("/subtitle/<string:session_id>/<string:language_code>")
def subtitle(session_id, language_code):
    try:
        return send_from_directory(
            directory=subtitle_folder_location,
            filename=f"{session_storage[session_id]['filename'].split('.')[0]}.{language_code}.vtt",
        )
    except KeyError:
        return abort(404)


def get_subtitles(video_filename):
    video_filename = video_filename.split(".")
    subtitles_list = []

    directory = Path(subtitle_folder_location)
    for item in directory.iterdir():
        if item.is_file() and str(video_filename) in str(item.name):
            try:
                filename = filename.split(".")
                lang_code = str(filename[-2])
                lang_name = languages.get(alpha2=lang_code).name
                subtitles_list.append({"name": lang_name, "code": lang_code})
            except Exception as e:
                print(f"Error get_subtitles: {e}")
    return subtitles_list
