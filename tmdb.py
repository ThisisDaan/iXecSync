from tmdbv3api import TMDb, Movie, TV
import urllib.request
import pathlib
from pathlib import Path
import json
import os
from collections import defaultdict
import database_manager as dbm
import base64
import glob

with open(os.path.join(os.path.dirname(__file__), "config.json")) as file:
    config = json.load(file)

tmdb = TMDb()
tmdb.api_key = str(config["TMDB_API_KEY"])
tmdb.language = "en"


def scan_library():
    db = dbm.database_manager()

    for library in config["library"]:

        if library["type"] == "movie":
            scan_library_movie(library)
        elif library["type"] == "tvshow":
            scan_library_tvshow(library)
        else:
            print("Invalid library type")

    db.connection.close()


def scan_library_movie(library):
    library_path = Path(library["path"])
    library_name = library["name"]

    # opening database connection
    db = dbm.database_manager()

    for directory in library_path.iterdir():
        # each directory is a movie
        # format of movie "title (release_date)"
        name = directory.name

        # We slice away the release date including parenthesis and space
        title = name[:-7]

        # We slice away the ) then we take the release date
        release_date = name[:-1][:-4]

        if db.not_exists(name, library["type"]):
            movie = Movie()
            search = movie.search(title)
            if search:
                # Setting the first entry as default
                tmdb_movie = search[0]

                # Checking for specific release date
                for movie in search:
                    if hasattr(movie, "release_date"):
                        if movie.release_date[-4:] == release_date:
                            tmdb_movie = movie

                # Writing data to database
                try:
                    db.sql_update_movie(name, library_name, tmdb_movie)
                    print(f"Saving data to DB for {name}")
                except Exception:
                    print(f"Unable to write to database for {name}")

                # Checking if the movie has a poster
                if tmdb_movie.poster_path:
                    url = f"https://image.tmdb.org/t/p/w500{tmdb_movie.poster_path}"

                    try:
                        urllib.request.urlretrieve(
                            url, f"{get_thumbnail_path()}{directory.name}.jpg",
                        )
                        print(f"Downloaded poster for: {name}")
                    except Exception:
                        print(f"Unable download poster for {name}")

    for file in library_path.rglob("*.mkv"):

        file_info = {}
        file_info["content_type"] = "movie"
        file_info["content_dir"] = file.parent.name
        file_info["content_file"] = file.name
        file_info["library_path"] = library_path
        file_info["library_name"] = library_name

        # Writing data to database
        try:
            db.sql_update_file(file_info)
            print(f"Saving data to DB for {file.name}")
        except Exception:
            print(f"Unable to write to database for {file.name}")

    # closing database connection
    db.connection.close()


def scan_library_tvshow(library):
    print("TV SHOWS")


def get_library(library_name):
    db = dbm.database_manager()
    library = db.get_library(library_name)
    db.connection.close()

    items = []
    for item in library:
        json = {
            "content_dir": item[0],
            "title": item[1],
            "release_date": item[2][:4],
        }
        items.append(json)
    print(items)
    return items


def get_meta(content_dir):
    db = dbm.database_manager()
    library = db.get_meta(content_dir)
    db.connection.close()

    items = []
    for item in library:
        json = {
            "content_dir": item[0],
            "title": item[1],
            "release_date": item[2][:4],
            "overview": item[3],
            "vote_average": item[4],
        }
        items.append(json)
    print(items)
    return items[0]


def get_filename(library_name, content_dir):
    db = dbm.database_manager()
    file = db.get_filename(library_name, content_dir)
    db.connection.close()

    items = []
    for item in file:
        json = {
            "library_path": item[0],
            "content_dir": item[1],
            "content_file": item[2],
        }
        items.append(json)
    print(library_name)
    print(content_dir)
    print(items)
    if items:
        return items[0]
    else:
        return False


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
