from tmdbv3api import TMDb, Movie, TV, Season
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
        release_date = name[:-1][-4:]

        if db.not_exists(name, library["type"]):
            movie = Movie()
            search = movie.search(title)
            if search:
                # Setting the first entry as default
                tmdb_movie = search[0]

                # Checking for specific release date
                for movie in search:
                    if hasattr(movie, "release_date"):
                        # print(f"{release_date} - {movie.release_date[:4]}")
                        if (
                            movie.release_date[:4] == release_date
                            and title in movie.title
                        ):
                            tmdb_movie = movie

                # Writing data to database
                movie_data = {
                    "library_name": library_name,
                    "content_dir": name,
                    "poster_path": tmdb_movie.poster_path,
                    "adult": tmdb_movie.adult,
                    "overview": tmdb_movie.overview,
                    "release_date": tmdb_movie.release_date,
                    "genre_ids": tmdb_movie.genre_ids,
                    "id": tmdb_movie.id,
                    "original_title": tmdb_movie.original_title,
                    "original_language": tmdb_movie.original_language,
                    "title": tmdb_movie.title,
                    "backdrop_path": tmdb_movie.backdrop_path,
                    "popularity": tmdb_movie.popularity,
                    "vote_count": tmdb_movie.vote_count,
                    "video": tmdb_movie.video,
                    "vote_average": tmdb_movie.vote_average,
                }

                db.sql_update_by_json("movie", movie_data)
                print(f"Saving data to DB for {name}")

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
        file_data = {
            "library_name": library_name,
            "library_path": library_path,
            "content_type": "movie",
            "content_dir": file.parent.name,
            "content_file": file.name,
        }

        # Writing data to database
        try:
            db.sql_update_by_json("file", file_data)
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
            release_date = name[:-1][-4:]
        else:
            title = name
            release_date = None

        if db.not_exists(name, library["type"]):
            tvshow = TV()
            search = tvshow.search(title)
            if search:
                # print(search)
                tmdb_tvshow = search[0]

                if release_date:
                    for tvshow in search:
                        if hasattr(tvshow, "release_date"):
                            if (
                                tvshow.release_date[-4:] == release_date
                                and title in tvshow.name
                            ):
                                print(tvshow.name)
                                tmdb_tvshow = tvshow

                                # Writing data to database
                                # try:
                tvshow_data = {
                    "library_name": library_name,
                    "content_dir": name,
                    "poster_path": tmdb_tvshow.poster_path,
                    "popularity": tmdb_tvshow.popularity,
                    "id": tmdb_tvshow.id,
                    "backdrop_path": tmdb_tvshow.backdrop_path,
                    "vote_average": tmdb_tvshow.vote_average,
                    "overview": tmdb_tvshow.overview,
                    "first_air_date": tmdb_tvshow.first_air_date,
                    "origin_country": tmdb_tvshow.origin_country,
                    "genre_ids": tmdb_tvshow.genre_ids,
                    "original_language": tmdb_tvshow.original_language,
                    "vote_count": tmdb_tvshow.vote_count,
                    "name": tmdb_tvshow.name,
                    "original_name": tmdb_tvshow.original_name,
                }
                db.sql_update_by_json("tvshow", tvshow_data)
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

                season = Path(os.path.join(library["path"], directory))
                for file in season.iterdir():
                    season = Season()
                    season_number = file.name.split(" ")[-1]
                    show_season = season.details(tmdb_tvshow.id, season_number)
                    # pylint: disable=no-member
                    if hasattr(show_season, "episodes"):
                        season_episodes = show_season.episodes
                    else:
                        print(f"DOES NOT HAVE EPISODES {file.name}")

                    for episode in season_episodes:
                        episode["content_dir"] = name
                        db.sql_update_by_json("tvshow_episode", episode)

    db.connection.close()


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
    sql_query_movie = f"""SELECT content_dir,title,substr(release_date, 1, 4) as release_date,library_name FROM movie WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR substr(release_date, 1, 4) LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query_tvshow = f"""SELECT content_dir,name as title,substr(first_air_date, 1, 4) as release_date,library_name FROM tvshow WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR substr(first_air_date, 1, 4) LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query = f"{sql_query_movie} UNION ALL {sql_query_tvshow} ORDER BY content_dir"
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def get_popular_movies():
    movie = Movie()
    popular = movie.popular()

    popular_movie_titles = []
    for movie in popular:
        popular_movie_titles.append('"' + movie.title + '"')

    sql_popular_movie_titles = ", ".join(popular_movie_titles)

    db = dbm.database_manager()
    sql_query = f"""SELECT content_dir,title,substr(release_date, 1, 4) as release_date,overview,vote_average,library_name FROM movie WHERE title IN ({sql_popular_movie_titles}) COLLATE NOCASE """
    sql_data = db.sql_execute(sql_query)

    for movie in sql_data:
        if movie["title"] in str(popular_movie_titles):
            popular_movie_titles.remove('"' + movie["title"] + '"')

    for movie in popular:
        if movie.title in str(popular_movie_titles):
            json = {
                "content_dir": "",
                "title": movie.title,
                "release_date": movie.release_date[:4],
                "overview": movie.overview,
                "vote_average": str(movie.vote_average),
                "poster_path": movie.poster_path,
                "id": movie.id,
            }
            sql_data.append(json)

    sql_data_sorted = sorted(sql_data, key=lambda i: i["vote_average"], reverse=True)

    db.connection.close()

    return sql_data_sorted


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
    # get_popular_movies()
    scan_library()

