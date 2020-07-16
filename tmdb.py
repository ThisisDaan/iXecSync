import urllib.request
import pathlib
from pathlib import Path
import os
from collections import defaultdict
import database_manager as dbm
import base64
import glob
import requests
from difflib import SequenceMatcher
import re
import json

with open(os.path.join(os.path.dirname(__file__), "config.json")) as file:
    config = json.load(file)


def scan_library():
    db = dbm.database_manager()

    for library in config["library"]:

        if library["type"] == "movie":
            new_scan_library_movie(library)
        elif library["type"] == "tvshow":
            new_scan_library_tvshow(library)
        else:
            print("Invalid library type")

    db.connection.close()


def new_scan_library_movie(library):

    # opening database connection
    db = dbm.database_manager()

    files = get_supported_files(library["path"])
    genres = get_tmdb_genres()

    for file in files:
        if db.not_exists(file.parent, file.name):

            print(f"Scanned file - {file.name}")

            # Getting the movie name from parent direcotry
            name = file.parent.name
            title = name.split(" (")[0]
            release_date = name.split(" (")[1].replace(")", "")

            # Searching TMDB for movie details
            tmdb_data = search("movie", title, release_date)

            # Checking if we have any results
            if tmdb_data:
                tmdb_data["video"] = get_api_trailer("movie", tmdb_data["id"])

                tmdb_genre = []
                for genre_id in tmdb_data["genre_ids"]:
                    try:
                        tmdb_genre.append(genres[genre_id])
                    except KeyError:
                        print("genre id not found")

                tmdb_data["genre_ids"] = ",".join(tmdb_genre)
                tmdb_data["library_name"] = library["name"]

                # Writing movie to database
                db.sql_update_by_json("movie", tmdb_data)
                print(f"Saving movie to DB - {file.name}")

                file_data = {
                    "id": tmdb_data["id"],
                    "path": file.parent,
                    "filename": file.name,
                }

                # Writing file to database
                db.sql_update_by_json("file", file_data)
                print(f"Saving file to DB - {file.name}")

                download_poster(tmdb_data)

        else:
            print(f"Skipped file - {file.name}")

    db.connection.close()


def download_poster(tmdb_data):
    if "poster_path" in tmdb_data:
        url = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"

        try:
            urllib.request.urlretrieve(
                url, f"""{get_thumbnail_path()}{tmdb_data["poster_path"]}""",
            )
            print(f"Downloading poster")
        except Exception:
            print(f"Error downloading poster")
    else:
        print(f"No poster")


def new_scan_library_tvshow(library):

    # opening database connection
    db = dbm.database_manager()

    files = get_supported_files(library["path"])
    genres = get_tmdb_genres()

    collected_files = defaultdict(lambda: defaultdict(list))

    for file in files:
        if db.not_exists(file.parent, file.name):

            match = re.findall(r"S[0-9][0-9]E[0-9][0-9]", file.name)
            if match:
                if match[0][1] == "0":
                    season_number = match[0][2]
                    print(season_number)
                else:
                    season_number = match[0][1:3]

                if match[0][-2] == "0":
                    episode_number = match[0][-1]
                    print(episode_number)
                else:
                    episode_number = match[0][-2:]

            episode = {
                "season_number": season_number,
                "episode_number": episode_number,
                "path": str(file.parent),
                "filename": str(file.name),
            }

            collected_files[file.parent.parent.name][season_number].append(episode)

        else:
            print(f"Skipped file - {file.name}")

    for tvshow in collected_files:
        print(f"TVSHOW - {tvshow}")

        # Getting the movie name from parent direcotry
        name = tvshow

        if "(" in name:
            title = name.split(" (")[0]
            release_date = name.split(" (")[1].replace(")", "")
        else:
            title = name
            release_date = None

        # Searching TMDB for movie details
        tmdb_data = search("tvshow", title, release_date)

        # Checking if we have any results
        if tmdb_data:
            tmdb_data["video"] = get_api_trailer("tv", tmdb_data["id"])

            tmdb_genre = []
            for genre_id in tmdb_data["genre_ids"]:
                try:
                    tmdb_genre.append(genres[genre_id])
                except KeyError:
                    print("genre id not found")

            tmdb_data["genre_ids"] = ",".join(tmdb_genre)
            tmdb_data["library_name"] = library["name"]

            # Writing movie to database
            db.sql_update_by_json("tvshow", tmdb_data)
            print(f"Saving movie to DB - {file.name}")

            download_poster(tmdb_data)

            for season in collected_files[tvshow]:

                tv_id = tmdb_data["id"]
                season_number = season

                api_url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}?api_key={config['TMDB_API_KEY']}"
                api_response = tmdb_api_request(api_url)

                if api_response:
                    tvshow_episodes = dict(api_response)
                    tvshow_season = dict(api_response)

                    del tvshow_season["episodes"]
                    tvshow_season["show_id"] = tmdb_data["id"]
                    print(f"Adding {name} Season {tvshow_season['season_number']}")
                    db.sql_update_by_json("tvshow_season", tvshow_season)

                else:
                    print(f"Error")

                for episode in collected_files[tvshow][season]:

                    # Adding episodes to database

                    for tmdb_episode in tvshow_episodes["episodes"]:
                        tmdb_episode["show_id"] = tmdb_data["id"]
                        print(
                            f"Adding S{tmdb_episode['season_number']}E{tmdb_episode['episode_number']}"
                        )
                        print("=" * 80)
                        db.sql_update_by_json("tvshow_episode", tmdb_episode)

                        if str(tmdb_episode["episode_number"]) == str(
                            episode["episode_number"]
                        ):
                            file_data = {
                                "id": tmdb_episode["id"],
                                "path": episode["path"],
                                "filename": episode["filename"],
                            }

                            # Writing file to database
                            db.sql_update_by_json("file", file_data)
                            print(f"Saving file to DB - {file.name}")

    db.connection.close()


def get_supported_files(directory):
    directory = Path(directory)
    supported_files = []

    for file in directory.rglob("*.mkv"):
        supported_files.append(file)

    for file in directory.rglob("*.mp4"):
        supported_files.append(file)

    return supported_files


def get_api_trailer(content_type, movie_id):
    api_url = f"""https://api.themoviedb.org/3/{content_type}/{movie_id}/videos?api_key={config["TMDB_API_KEY"]}&language=en-US"""
    api_response = tmdb_api_request(api_url)
    results = api_response["results"]

    for video in results:
        if video["type"].lower() == "trailer" and video["site"].lower() == "youtube":
            return video["key"]

    return False


def tmdb_api_request(api_url):
    headers = {"Accept": "application/json"}
    response = requests.get(api_url, headers=headers)
    decoded_response = response.content.decode("utf-8")
    json_response = json.loads(decoded_response)

    return json_response


def get_tmdb_genres():
    genre_id_to_name = {}

    # Getting genres for movies
    api_url = f"""https://api.themoviedb.org/3/genre/movie/list?api_key={config["TMDB_API_KEY"]}"""
    api_response = tmdb_api_request(api_url)
    results = api_response["genres"]

    db = dbm.database_manager()
    for genre in results:
        db.sql_update_by_json("genre", genre)
        genre_id_to_name[genre["id"]] = genre["name"]

    # Getting genres for tvshows
    api_url = f"""https://api.themoviedb.org/3/genre/movie/list?api_key={config["TMDB_API_KEY"]}"""
    api_response = tmdb_api_request(api_url)

    for genre in results:
        db.sql_update_by_json("genre", genre)
        genre_id_to_name[genre["id"]] = genre["name"]

    db.connection.close()

    return genre_id_to_name


def get_genre_list(library_name):
    db = dbm.database_manager()
    sql_query = f"""SELECT name FROM genre"""
    sql_data = db.sql_execute(sql_query)
    db.connection.close()
    sql_data_sorted = sorted(sql_data, key=lambda i: i["name"], reverse=False)
    return sql_data_sorted


def get_library(library_name, orderby):
    db = dbm.database_manager()

    orderby = orderby.split(" ")

    content_type = library_content_type(library_name)

    if content_type == "movie":
        sql_query = f"""SELECT title,release_date as release_date,id,poster_path,library_name FROM movie WHERE library_name ="{library_name}" COLLATE NOCASE ORDER BY {orderby[0]} COLLATE NOCASE {orderby[1]}"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,first_air_date as release_date,id,poster_path,library_name FROM tvshow WHERE library_name ="{library_name}" COLLATE NOCASE ORDER BY {orderby[0]} COLLATE NOCASE {orderby[1]}"""
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
    sql_query_movie = f"""SELECT content_dir,title,release_date,library_name,id FROM movie WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR substr(release_date, 1, 4) LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query_tvshow = f"""SELECT content_dir,name as title,first_air_date as release_date,library_name,id FROM tvshow WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR substr(first_air_date, 1, 4) LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query = f"{sql_query_movie} UNION ALL {sql_query_tvshow} ORDER BY content_dir"
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def get_media_by_genre(library_name, genre, orderby):

    db = dbm.database_manager()

    orderby = orderby.split(" ")

    content_type = library_content_type(library_name)

    if content_type == "movie":
        sql_query = f"""SELECT title,release_date,overview,vote_average,video,poster_path,genre_ids,library_name,id FROM movie WHERE library_name = "{library_name}" COLLATE NOCASE AND genre_ids LIKE "%{genre}%" COLLATE NOCASE ORDER BY {orderby[0]} COLLATE NOCASE {orderby[1]}"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,first_air_date as release_date,overview,vote_average,video,poster_path,genre_ids,library_name,id FROM tvshow WHERE library_name = "{library_name}" COLLATE NOCASE AND genre_ids LIKE "%{genre}%" COLLATE NOCASE ORDER BY {orderby[0]} COLLATE NOCASE {orderby[1]}"""
    else:
        return None

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def get_popular_movies():

    api_url = f"""https://api.themoviedb.org/3/movie/popular?api_key={config["TMDB_API_KEY"]}"""
    api_response = tmdb_api_request(api_url)
    results = api_response["results"]

    popular_movie_titles = []
    for movie in results:
        popular_movie_titles.append('"' + movie["title"] + '"')

    sql_popular_movie_titles = ", ".join(popular_movie_titles)

    db = dbm.database_manager()
    sql_query = f"""SELECT title,release_date,id,poster_path,library_name,popularity,vote_average FROM movie WHERE title IN ({sql_popular_movie_titles}) COLLATE NOCASE """

    sql_data = db.sql_execute(sql_query)

    for movie in sql_data:
        if movie["title"] in str(popular_movie_titles):
            popular_movie_titles.remove('"' + movie["title"] + '"')

    for movie in results:
        if movie["title"] in str(popular_movie_titles):
            json_data = {
                "library_name": "",
                "title": movie["title"],
                "release_date": movie["release_date"],
                "poster_path": movie["poster_path"],
                "popularity": movie["popularity"],
                "vote_average": movie["vote_average"],
                "id": movie["id"],
                "notavailable": True,
            }
            sql_data.append(json_data)

    sql_data_sorted = sorted(sql_data, key=lambda i: i["vote_average"], reverse=True)

    db.connection.close()

    return sql_data_sorted


def get_seasons(video_id):
    db = dbm.database_manager()

    sql_query = f"""SELECT cast(season_number as integer) as season_number,poster_path FROM tvshow_season WHERE show_id = "{video_id}" GROUP BY season_number"""
    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sorted(sql_data, key=lambda i: i["season_number"])


def get_meta_season_episode(video_id, season_number, episode_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT ('Episode ' || episode_number || ' - '|| name) as title,air_date as release_date,overview,vote_average,still_path as poster_path FROM tvshow_episode WHERE show_id = "{video_id}" AND season_number="{season_number}" AND episode_number = "{episode_number}" """

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_episodes(video_id, season_number):
    db = dbm.database_manager()

    # sql_query = f"""SELECT name,overview,episode_number,still_path FROM tvshow_episode WHERE show_id = "{video_id}" AND season_number = "{season_number}" COLLATE nocase"""
    sql_query = f"""SELECT name,overview,episode_number,still_path,id,show_id,season_number FROM tvshow_episode WHERE show_id = "{video_id}" AND season_number = "{season_number}" COLLATE nocase AND id IN (SELECT id FROM file)"""
    local_episodes = db.sql_execute(sql_query)

    sql_query = f"""SELECT name,overview,episode_number,still_path,id,show_id,season_number FROM tvshow_episode WHERE show_id = "{video_id}" AND season_number = "{season_number}";"""
    total_episodes = db.sql_execute(sql_query)
    db.connection.close()

    for episode in total_episodes:
        if episode in local_episodes:
            episode["available"] = True
        else:
            episode["available"] = False

    return total_episodes


def get_episodes_info(content_dir, season_number, episode_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT name,overview,episode_number,still_path FROM tvshow_episode WHERE content_dir = "{content_dir}" COLLATE nocase AND season_number = "{season_number}" COLLATE nocase"""
    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sql_data


def get_meta_by_id(content_type, video_id):
    db = dbm.database_manager()

    if content_type == "movie":
        sql_query = f"""SELECT title,release_date,overview,vote_average,video FROM movie WHERE id="{video_id}" COLLATE NOCASE"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,first_air_date as release_date,overview,vote_average FROM tvshow WHERE id="{video_id}" COLLATE NOCASE """
    else:
        return None

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_meta(library_name, video_id):
    db = dbm.database_manager()

    content_type = library_content_type(library_name)
    if content_type == "movie":
        sql_query = f"""SELECT title,release_date,overview,vote_average,video,poster_path,genre_ids,library_name,id FROM movie WHERE id="{video_id}" COLLATE NOCASE"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,first_air_date as release_date,overview,vote_average,video,poster_path,genre_ids,library_name,id FROM tvshow WHERE id="{video_id}" COLLATE NOCASE """
    else:
        return None

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_filename(video_id):
    db = dbm.database_manager()
    sql_query = f"""SELECT path,filename from file WHERE id="{video_id}";"""
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    if sql_data:
        return sql_data[0]
    else:
        return None


def get_path(video_id):
    db = dbm.database_manager()
    sql_query = f"""SELECT path,filename from file WHERE id="{video_id}";"""
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    if sql_data:
        data = sql_data[0]
        path = os.path.join(data["path"], data["filename"])
        return path
    else:
        return None


def get_filename_episode(video_id, season_number, episode_number):
    db = dbm.database_manager()
    # sql_query = f"""SELECT path,filename from file WHERE id="{video_id}" AND filename LIKE "%S{str(season_number).zfill(2)}E{str(episode_number).zfill(2)}%" COLLATE NOCASE;"""
    sql_query = f"""SELECT path,filename from file WHERE id=(SELECT id FROM tvshow_episode WHERE show_id= "{video_id}" AND season_number = "{season_number}" AND episode_number = "{episode_number}")"""
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    if sql_data:
        return sql_data[0]
    else:
        return None


def get_path_episode(video_id, season_number, episode_number):
    db = dbm.database_manager()
    sql_query = f"""SELECT path,filename from file WHERE id="{video_id}" AND filename LIKE "%S{str(season_number).zfill(2)}E{str(episode_number).zfill(2)}%" COLLATE NOCASE;"""
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    if sql_data:
        data = sql_data[0]
        path = os.path.join(data["path"], data["filename"])
        return path
    else:
        return None


def get_video_id(library_name, content_dir):
    db = dbm.database_manager()
    sql_query = (
        f"""SELECT id from movie WHERE content_dir="{content_dir}" COLLATE NOCASE;"""
    )
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_trailer(library_name, video_id):

    db = dbm.database_manager()

    content_type = library_content_type(library_name)
    if content_type == "movie":
        sql_query = f"""SELECT title,video from movie WHERE id="{video_id}" COLLATE NOCASE limit 1;"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,video from tvshow   WHERE id="{video_id}" COLLATE NOCASE limit 1;"""

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    if sql_data:
        return sql_data[0]
    else:
        return None


def get_thumbnail_path():
    return os.path.join(
        os.path.dirname(os.path.realpath(__file__)) + os.sep + "thumbnail"
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
    print(f"SEARCH API URL - {response.url}")
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
    # get_tmdb_genres()
    # movie = search("movie", "Interstellar", "2014")
    # print(movie)

