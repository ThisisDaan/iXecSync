from tmdbv3api import TMDb, Movie, TV
import urllib.request
import pathlib
import json
import os
from collections import defaultdict
import database_manager as dbm
import base64

with open(os.path.join(os.path.dirname(__file__), "config.json")) as file:
    config = json.load(file)

tmdb = TMDb()
tmdb.api_key = str(config["TMDB_API_KEY"])
tmdb.language = "en"


def scan_library():
    try:
        db = dbm.database_manager()
        for library in config["library"]:
            if library["type"] == "movie":
                for (root, dirs, files) in os.walk(library["path"]):
                    for directory in dirs:
                        name = directory[:-5]
                        release_date = directory[-4:]

                        if db.not_exists(directory, library["type"]):

                            movie = Movie()
                            search = movie.search(name)

                            if search:
                                tmdb_movie = search[0]

                                for item in search:
                                    try:
                                        if item.release_date[-4:] == release_date:
                                            tmdb_movie = item
                                            break
                                    except Exception:
                                        print("Has no release date")

                                db.sql_update_movie(
                                    tmdb_movie, library["path"], directory
                                )
                                if tmdb_movie.poster_path:
                                    url = f"https://image.tmdb.org/t/p/w500{tmdb_movie.poster_path}"
                                    urllib.request.urlretrieve(
                                        url, f"{get_thumbnail_path()}{directory}.jpg"
                                    )
                                print(f"downloaded and saved database: {directory}")
                    break
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.connection.close()


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


def meta(media_name, library):
    db = dbm.database_manager()
    sql_data = db.get_movie(media_name)[0]
    json = {
        "title": sql_data[4],
        "original_title": sql_data[5],
        "overview": sql_data[6],
        "release_date": sql_data[7],
        "genre_ids": sql_data[8],
        "thumbnail": f"/thumbnail/{media_name}.jpg",
        "backdrop_path": f"/thumbnail/{media_name}.jpg",
        "popularity": sql_data[12],
        "video": sql_data[13],
        "vote_average": sql_data[14],
        "vote_count": sql_data[15],
    }
    db.connection.close()

    return json


if __name__ == "__main__":
    scan_library()
