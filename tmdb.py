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

    supported_files = []
    for file in library_path.rglob("*.mkv"):
        supported_files.append(file)

    for file in library_path.rglob("*.mp4"):
        supported_files.append(file)

    for file in supported_files:
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
    library_path = Path(library["path"])
    library_name = library["name"]

    # opening database connection
    db = dbm.database_manager()

    for directory in library_path.iterdir():
        # each directory is a movie
        # format of movie "title (release_date)"
        name = directory.name

        # check if (release_date) its not fool proof but should work.
        if "(" in name:
            title = name[:-7]
            release_date = name[:-1][:-4]
        else:
            title = name
            release_date = False

        if db.not_exists(name, library["type"]):
            tvshow = TV()
            search = tvshow.search(title)
            if search:
                tmdb_tvshow = search[0]

                if release_date:
                    for tvshow in search:
                        if hasattr(tvshow, "release_date"):
                            if tvshow.release_date[-4:] == release_date:
                                tmdb_tvshow = tvshow

                # Writing data to database
                # try:
                db.sql_update_tvshow(name, library_name, tmdb_tvshow)
                print(f"Saving data to DB for {name}")
                # except Exception:
                #     print(f"Unable to write to database for {name}")

                # Checking if the movie has a poster
                if tmdb_tvshow.poster_path:
                    url = f"https://image.tmdb.org/t/p/w500{tmdb_tvshow.poster_path}"

                    try:
                        urllib.request.urlretrieve(
                            url, f"{get_thumbnail_path()}{directory.name}.jpg",
                        )
                        print(f"Downloaded poster for: {name}")
                    except Exception:
                        print(f"Unable download poster for {name}")


def get_library(library_name):
    db = dbm.database_manager()

    content_type = library_content_type(library_name)

    if content_type == "movie":
        sql_query = f"""SELECT content_dir,title,substr(release_date, 1, 4) as release_date FROM movie WHERE library_name ="{library_name}" COLLATE NOCASE ORDER BY popularity DESC"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT content_dir,name as title,substr(first_air_date, 1, 4) as release_date FROM tvshow WHERE library_name ="{library_name}" COLLATE NOCASE ORDER BY popularity DESC"""
    else:
        return None

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def library_content_type(library_name):
    for item in config["library"]:
        if item["name"].lower() == library_name.lower():
            return item["type"]


def get_media_by_keyword(keyword):
    db = dbm.database_manager()
    sql_query_movie = f"""SELECT content_dir,title,substr(release_date, 1, 4) as release_date,library_name FROM movie WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR release_date LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query_tvshow = f"""SELECT content_dir,name as title,substr(first_air_date, 1, 4) as release_date,library_name FROM tvshow WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR release_date LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query = f"{sql_query_movie} UNION ALL {sql_query_tvshow} ORDER BY content_dir"
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def get_meta(library_name, content_dir):
    db = dbm.database_manager()

    content_type = library_content_type(library_name)
    if content_type == "movie":
        sql_query = f"""SELECT content_dir,title,substr(release_date, 1, 4) as release_date,overview,vote_average FROM movie WHERE content_dir="{content_dir}" COLLATE NOCASE """
    elif content_type == "tvshow":
        sql_query = f"""SELECT content_dir,name as title,substr(first_air_date, 1, 4) as release_date,overview,vote_average FROM tvshow WHERE content_dir="{content_dir}" COLLATE NOCASE """
    else:
        return None

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_filename(library_name, content_dir):
    db = dbm.database_manager()
    sql_query = f"""SELECT library_path,content_dir,content_file from file WHERE library_name="{library_name}" COLLATE NOCASE AND content_dir="{content_dir}" COLLATE NOCASE;"""
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_thumbnail_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)) + os.sep + "thumbnail" + os.sep
    )


def meta(content_dir, library_name):
    db = dbm.database_manager()
    sql_query = (
        f"""SELECT * FROM movie WHERE content_dir ="{content_dir}" COLLATE NOCASE """
    )
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


if __name__ == "__main__":
    scan_library()
