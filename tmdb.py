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
import requests
from difflib import SequenceMatcher

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
            print(library)
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
        # title = name[:-7]
        title = name.split(" (")[0]

        # We slice away the ) then we take the release date
        # release_date = name[:-1][-4:]
        release_date = name.split(" (")[1].replace(")", "")

        if db.not_exists(name, library["type"]):

            tmdb_data = search("movie", title, release_date)

            if tmdb_data:
                tmdb_data["content_dir"] = name
                tmdb_data["library_name"] = library_name
                db.sql_update_by_json("movie", tmdb_data)
                print(f"Saving data to DB for {name}")

                # Checking if the movie has a poster
                if "poster_path" in tmdb_data:
                    url = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"

                    try:
                        urllib.request.urlretrieve(
                            url, f"{get_thumbnail_path()}{name}.jpg",
                        )
                        print(f"Downloaded poster for: {name}")
                    except Exception:
                        print(f"Unable download poster for {name}")

            else:
                print(f"Nothing found on TMDB for {name}")

            # Scanning directory for files
            supported_files = []
            for file in directory.rglob("*.mkv"):
                supported_files.append(file)

            for file in directory.rglob("*.mp4"):
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
            tmdb_data = search("tvshow", title, release_date)
            if tmdb_data:
                tmdb_data["content_dir"] = name
                tmdb_data["library_name"] = library_name
                db.sql_update_by_json("tvshow", tmdb_data)
                print(f"Saving data to DB for {name}")

                # Checking if the movie has a poster
                if "poster_path" in tmdb_data:
                    if tmdb_data["poster_path"]:
                        url = (
                            f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"
                        )
                        try:
                            urllib.request.urlretrieve(
                                url, f"{get_thumbnail_path()}{name}.jpg",
                            )
                            print(f"Downloaded poster for: {name}")
                        except Exception:
                            print(f"Unable download poster for {name}")
                    else:
                        print(f"no poster found on TMDB: {name}")

                    season = Path(os.path.join(library["path"], directory))
                    for file in season.iterdir():
                        tv_id = tmdb_data["id"]
                        season_number = file.name.split(" ")[-1]

                        api_url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}?api_key={config['TMDB_API_KEY']}"

                        headers = {"Accept": "application/json"}
                        response = requests.get(api_url, headers=headers)
                        print(f"THE URL: {response.url}")
                        decoded_response = response.content.decode("utf-8")
                        json_response = json.loads(decoded_response)

                        if response.status_code == 200:
                            tvshow_episodes = dict(json_response)
                            tvshow_season = dict(json_response)

                            # Adding season to database
                            try:
                                del tvshow_season["_id"]
                            except Exception:
                                print("no _id found")
                            del tvshow_season["episodes"]
                            tvshow_season["content_dir"] = name
                            print(
                                f"Adding {name} Season {tvshow_season['season_number']}"
                            )
                            db.sql_update_by_json("tvshow_season", tvshow_season)

                            # Adding episodes to database
                            for episode in tvshow_episodes["episodes"]:
                                episode["content_dir"] = name
                                print(
                                    f"Adding s{episode['season_number']}e{episode['episode_number']}"
                                )
                                db.sql_update_by_json("tvshow_episode", episode)
                        else:
                            print(f"Error status code: {response.status_code}")

            else:
                print(f"Nothing found on TMDB for {name}")

            supported_files = []
            for file in directory.rglob("*.mkv"):
                supported_files.append(file)

            for file in directory.rglob("*.mp4"):
                supported_files.append(file)

            for file in supported_files:
                file_data = {
                    "library_name": library_name,
                    "library_path": library_path,
                    "content_type": "tvshow",
                    "content_dir": file.parent.parent.name,
                    "content_file": file.name,
                }

                # Writing data to database
                try:
                    db.sql_update_by_json("file", file_data)
                    print(f"Saving data to DB for {file.name}")
                except Exception:
                    print(f"Unable to write to database for {file.name}")

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


def get_seasons(content_dir):
    db = dbm.database_manager()

    sql_query = f"""SELECT cast(season_number as integer) as season_number,poster_path FROM tvshow_season WHERE content_dir = "{content_dir}" COLLATE nocase GROUP BY season_number"""
    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sorted(sql_data, key=lambda i: i["season_number"])


def get_meta_season_episode(content_dir, season_number, episode_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT content_dir,name as title,substr(air_date, 1, 4) as release_date,overview,vote_average,still_path FROM tvshow_episode WHERE content_dir="{content_dir}" COLLATE NOCASE AND season_number="{season_number}" AND episode_number = "{episode_number}" """

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_episodes(content_dir, season_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT name,overview,episode_number,still_path FROM tvshow_episode WHERE content_dir = "{content_dir}" COLLATE nocase AND season_number = "{season_number}" COLLATE nocase"""
    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sql_data


def get_episodes_info(content_dir, season_number, episode_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT name,overview,episode_number,still_path FROM tvshow_episode WHERE content_dir = "{content_dir}" COLLATE nocase AND season_number = "{season_number}" COLLATE nocase"""
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


def get_filename_episode(library_name, content_dir, season_number, episode_number):
    db = dbm.database_manager()
    sql_query = f"""SELECT library_path,content_dir,content_file from file WHERE library_name="{library_name}" COLLATE NOCASE AND content_dir="{content_dir}" COLLATE NOCASE AND content_file LIKE "%S{str(season_number).zfill(2)}E{str(episode_number).zfill(2)}%" COLLATE NOCASE;"""
    print(sql_query)
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


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def format_this(string):
    if ", " in string and "&" not in string and "and" not in string:
        string = string.split(", ")
        string = f"{string[1]} {string[0]}"

    return string


def search(content_type, keyword, release_date=None):
    if content_type == "movie":
        year = "release_date"
        title = "title"
        api_search = "movie"
    elif content_type == "tvshow":
        year = "first_air_date"
        title = "name"
        api_search = "tv"

    api_url = f"https://api.themoviedb.org/3/search/{api_search}"
    keyword = format_this(keyword)

    parameters = {}

    # Adding api key
    parameters["api_key"] = config["TMDB_API_KEY"]

    # Adding keyword
    parameters["query"] = keyword

    # Adding language
    # parameters["language"] = "en-US"

    # Adding the year
    # if release_date:
    #     if content_type == "movie":
    #         parameters["year"] = release_date
    #     elif content_type == "tvshow":
    #         parameters["first_air_date_year"] = release_date

    headers = {"Accept": "application/json"}
    response = requests.get(api_url, params=parameters, headers=headers)
    print(f"THE URL: {response.url}")
    decoded_response = response.content.decode("utf-8")
    json_response = json.loads(decoded_response)
    # print(json_response)
    json_results = json_response["results"]
    # print(f"Total results: {json_response['total_results']}")
    # print(f"keyword: {keyword}")

    # first check release date else match with just name
    matching_percentage = 0
    matching_item = None

    if json_results:
        for item in json_results:
            if release_date and "release_date" in str(item):
                if release_date == item[year][:4]:
                    item_percentage = similar(item[title].lower(), keyword.lower())
                    if item_percentage == 1.0:
                        return item
                    elif item_percentage > 0.7:
                        if item_percentage > matching_percentage:
                            matching_percentage = item_percentage
                            matching_item = item
                        print(
                            f"{bcolors.OKGREEN}Round #1 - {keyword} / {item[title]} - Matching with {item_percentage}{bcolors.ENDC}"
                        )
                    else:
                        print(
                            f"{bcolors.WARNING}Round #1 - {keyword} / {item[title]} - Not matched with {item_percentage}{bcolors.ENDC}"
                        )
        if matching_item:
            return matching_item
        else:
            for item in json_results:
                item_percentage = similar(item[title].lower(), keyword.lower())
                if item_percentage == 1.0:
                    return item
                elif item_percentage > 0.5:
                    if item_percentage > matching_percentage:
                        matching_percentage = item_percentage
                        matching_item = item
                        print(
                            f"{bcolors.OKGREEN}Round #2 - {keyword} / {item[title]} - Matching with {item_percentage}{bcolors.ENDC}"
                        )
                    else:
                        print(
                            f"{bcolors.WARNING}Round #2 - {keyword} / {item[title]} - Not matched with {item_percentage}{bcolors.ENDC}"
                        )

    return matching_item


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


if __name__ == "__main__":
    # get_popular_movies()
    scan_library()
    # movie = search("movie", "Interstellar", "2014")
    # print(movie)

