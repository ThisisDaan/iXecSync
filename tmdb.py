from tmdbv3api import TMDb, Movie, TV
import urllib.request
import pathlib
import json
import os

with open(os.path.join(os.path.dirname(__file__), "config.json")) as file:
    config = json.load(file)

tmdb = TMDb()
tmdb.api_key = str(config["TMDB_API_KEY"])
tmdb.language = "en"


def download_thumbnail_poster(search_str, thumbnail_location, video_path):
    file = pathlib.Path(thumbnail_location)
    if file.exists() is False:
        video_name = search_str.split(" (")
        print(f"searching for {video_name[0]}")

        if "-=Series=-" in video_path:
            video = TV()
        elif "-=Movies=-" in video_path:
            video = Movie()
        else:
            video = Movie()

        search = video.search(video_name[0])

        if search:
            url = f"https://image.tmdb.org/t/p/w500/{search[0].poster_path}"
            urllib.request.urlretrieve(url, thumbnail_location)

