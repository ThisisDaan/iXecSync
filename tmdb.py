from tmdbv3api import TMDb, Movie, TV
import urllib.request
import pathlib
import json
import os
from collections import defaultdict

with open(os.path.join(os.path.dirname(__file__), "config.json")) as file:
    config = json.load(file)

tmdb = TMDb()
tmdb.api_key = str(config["TMDB_API_KEY"])
tmdb.language = "en"


def scan_library():
    try:
        for item in config["library"]:
            for (root, dirs, files) in os.walk(item["path"]):
                for directory in dirs:
                    download_thumbnail_poster(directory, item["type"])
                break
    except Exception as e:
        print(f"ERROR: {e}")


def search_by_name(name, media_type):
    if media_type == "tvshow":
        video = TV()
        video_name = name
        video_release_date = False
        search = video.search(video_name)

        if search:
            for item in search:
                if item.name.lower() == video_name.lower():
                    return item

    else:
        video = Movie()
        video_name = name.split(" (")[0]
        video_release_date = name.split(" (")[1].replace(")", "")
        search = video.search(video_name)

        if search:
            for item in search:
                if item.title.lower() == video_name.lower():
                    if video_release_date == item.release_date[:4]:
                        return item

    return False


def download_thumbnail_poster(name, media_type):
    print(f"thumbnail poster: {name}")
    thumbnail = get_thumbnail_path() + name + ".jpg"
    file = pathlib.Path(thumbnail)
    if file.exists() is False:
        search = search_by_name(name, media_type)
        if search:
            url = f"https://image.tmdb.org/t/p/w500{search.poster_path}"
            print(f"Downloading: {name} - {url}")
            if search.poster_path:
                urllib.request.urlretrieve(url, f"{get_thumbnail_path()}{name}.jpg")
    else:
        print(f"Skipped: {name}")


def get_thumbnail_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)) + os.sep + "thumbnail" + os.sep
    )


def popular():
    popular_list = []

    movie = Movie()
    popular = movie.popular()

    for item in popular:
        json = {
            "name": item.title,
            "thumbnail": f"https://image.tmdb.org/t/p/w500/{item.poster_path}",
        }
        popular_list.append(json)

    return popular_list


def meta(name, library):
    search = search_by_name(name, "movie")

    if search:
        json = {
            "title": search.title,
            "overview": search.overview,
            "thumbnail": f"https://image.tmdb.org/t/p/w500/{search.poster_path}",
            "backdrop_path": f"https://image.tmdb.org/t/p/w500/{search.backdrop_path}",
            "release_date": search.release_date,
            "genre_ids": search.genre_ids,
            "vote_average": search.vote_average,
            "popularity": search.popularity,
        }

    return json


if __name__ == "__main__":
    scan_library()
