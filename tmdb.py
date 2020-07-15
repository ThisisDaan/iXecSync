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
import re

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

                if "poster_path" in tmdb_data:
                    url = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"

                    try:
                        urllib.request.urlretrieve(
                            url,
                            f"""{get_thumbnail_path()}{tmdb_data["poster_path"]}""",
                        )
                        print(f"Downloading poster - {file.name}")
                    except Exception:
                        print(f"Error downloading poster - {file.name}")
                else:
                    print(f"No poster - {file.name}")

        else:
            print(f"Skipped file - {file.name}")

    db.connection.close()


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
                season_number = match[0][2]
                episode_number = match[-1]

            episode = {
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

            if "poster_path" in tmdb_data:
                url = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"

                try:
                    urllib.request.urlretrieve(
                        url, f"""{get_thumbnail_path()}{tmdb_data["poster_path"]}""",
                    )
                    print(f"Downloading poster - {file.name}")
                except Exception:
                    print(f"Error downloading poster - {file.name}")
            else:
                print(f"No poster - {file.name}")

        for season in collected_files[tvshow]:

            tv_id = tmdb_data["id"]
            season_number = season

            api_url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}?api_key={config['TMDB_API_KEY']}"

            headers = {"Accept": "application/json"}
            response = requests.get(api_url, headers=headers)
            print(f"Connecting to TMDB - {response.url}")
            decoded_response = response.content.decode("utf-8")
            json_response = json.loads(decoded_response)

            if response.status_code == 200:
                tvshow_episodes = dict(json_response)
                tvshow_season = dict(json_response)

                del tvshow_season["episodes"]
                tvshow_season["show_id"] = tmdb_data["id"]
                print(f"Adding {name} Season {tvshow_season['season_number']}")
                db.sql_update_by_json("tvshow_season", tvshow_season)

                # Adding episodes to database
                for episode in tvshow_episodes["episodes"]:
                    episode["show_id"] = tmdb_data["id"]
                    print(
                        f"Adding s{episode['season_number']}e{episode['episode_number']}"
                    )
                    db.sql_update_by_json("tvshow_episode", episode)
            else:
                print(f"Error status code: {response.status_code}")

            for episode in collected_files[tvshow][season]:
                file_data = {
                    "id": tmdb_data["id"],
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


# def scan_library_movie(library):

#     library_path = Path(library["path"])
#     library_name = library["name"]

#     # opening database connection
#     db = dbm.database_manager()

#     for directory in library_path.iterdir():
#         # each directory is a movie
#         # format of movie "title (release_date)"
#         name = directory.name

#         # We slice away the release date including parenthesis and space
#         # title = name[:-7]
#         title = name.split(" (")[0]

#         # We slice away the ) then we take the release date
#         # release_date = name[:-1][-4:]
#         release_date = name.split(" (")[1].replace(")", "")

#         if db.not_exists(name, library["type"]):

#             tmdb_data = search("movie", title, release_date)

#             if tmdb_data:
#                 # tmdb_data["library_name"] = library_name
#                 tmdb_data["video"] = get_api_trailer(tmdb_data["id"])
#                 db.sql_update_by_json("movie", tmdb_data)
#                 print(f"Saving data to DB for {name}")

#                 # Checking if the movie has a poster
#                 if "poster_path" in tmdb_data:
#                     url = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"

#                     try:
#                         urllib.request.urlretrieve(
#                             url, f"{get_thumbnail_path()}{name}.jpg",
#                         )
#                         print(f"Downloaded poster for: {name}")
#                     except Exception:
#                         print(f"Unable download poster for {name}")

#                 # Scanning directory for files
#                 supported_files = []
#                 for file in directory.rglob("*.mkv"):
#                     supported_files.append(file)

#                 for file in directory.rglob("*.mp4"):
#                     supported_files.append(file)

#                 for file in supported_files:
#                     file_data = {
#                         "id": tmdb_data["id"],
#                         "path": file.parent,
#                         "filename": file.name,
#                     }

#                     # Writing data to database
#                     try:
#                         db.sql_update_by_json("file", file_data)
#                         print(f"Saving data to DB for {file.name}")
#                     except Exception:
#                         print(f"Unable to write to database for {file.name}")

#             else:
#                 print(f"Nothing found on TMDB for {name}")

#     # closing database connection
#     db.connection.close()


# def scan_library_tvshow(library):
#     library_path = Path(library["path"])
#     library_name = library["name"]

#     # opening database connection
#     db = dbm.database_manager()

#     for directory in library_path.iterdir():
#         # each directory is a movie
#         # format of movie "title (release_date)"
#         name = directory.name

#         # check if (release_date) its not fool proof but should work.
#         if "(" in name:
#             title = name[:-7]
#             release_date = name[:-1][-4:]
#         else:
#             title = name
#             release_date = None

#         if db.not_exists(name, library["type"]):
#             tmdb_data = search("tvshow", title, release_date)
#             if tmdb_data:
#                 tmdb_data["content_dir"] = name
#                 tmdb_data["library_name"] = library_name
#                 db.sql_update_by_json("tvshow", tmdb_data)
#                 print(f"Saving data to DB for {name}")

#                 # Checking if the movie has a poster
#                 if "poster_path" in tmdb_data:
#                     if tmdb_data["poster_path"]:
#                         url = (
#                             f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"
#                         )
#                         try:
#                             urllib.request.urlretrieve(
#                                 url, f"{get_thumbnail_path()}{name}.jpg",
#                             )
#                             print(f"Downloaded poster for: {name}")
#                         except Exception:
#                             print(f"Unable download poster for {name}")
#                     else:
#                         print(f"no poster found on TMDB: {name}")

#                     season = Path(os.path.join(library["path"], directory))
#                     for file in season.iterdir():
# tv_id = tmdb_data["id"]
# season_number = file.name.split(" ")[-1]

# api_url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}?api_key={config['TMDB_API_KEY']}"

# headers = {"Accept": "application/json"}
# response = requests.get(api_url, headers=headers)
# print(f"Connecting to TMDB - {response.url}")
# decoded_response = response.content.decode("utf-8")
# json_response = json.loads(decoded_response)

# if response.status_code == 200:
#     tvshow_episodes = dict(json_response)
#     tvshow_season = dict(json_response)

#     del tvshow_season["episodes"]
#     tvshow_season["show_id"] = tmdb_data["id"]
#     print(
#         f"Adding {name} Season {tvshow_season['season_number']}"
#     )
#     db.sql_update_by_json("tvshow_season", tvshow_season)

#     # Adding episodes to database
#     for episode in tvshow_episodes["episodes"]:
#         episode["show_id"] = tmdb_data["id"]
#         print(
#             f"Adding s{episode['season_number']}e{episode['episode_number']}"
#         )
#         db.sql_update_by_json("tvshow_episode", episode)
# else:
#     print(f"Error status code: {response.status_code}")

#                 supported_files = []
#                 for file in directory.rglob("*.mkv"):
#                     supported_files.append(file)

#                 for file in directory.rglob("*.mp4"):
#                     supported_files.append(file)

#                 for file in supported_files:
#                     file_data = {
#                         "id": tmdb_data["id"],
#                         "library_name": library_name,
#                         "library_path": library_path,
#                         "content_type": "tvshow",
#                         "content_dir": file.parent.parent.name,
#                         "content_file": file.name,
#                     }

#                     # Writing data to database
#                     try:
#                         db.sql_update_by_json("file", file_data)
#                         print(f"Saving data to DB for {file.name}")
#                     except Exception:
#                         print(f"Unable to write to database for {file.name}")

#             else:
#                 print(f"Nothing found on TMDB for {name}")

#     db.connection.close()


def get_api_trailer(content_type, movie_id):
    api_url = f"""https://api.themoviedb.org/3/{content_type}/{movie_id}/videos?api_key={config["TMDB_API_KEY"]}&language=en-US"""
    print(f"TRAILER API URL - {api_url}")
    headers = {"Accept": "application/json"}
    response = requests.get(api_url, headers=headers)
    decoded_response = response.content.decode("utf-8")
    json_response = json.loads(decoded_response)
    json_results = json_response["results"]

    for video in json_results:
        if video["type"].lower() == "trailer" and video["site"].lower() == "youtube":
            return video["key"]

    return False


def get_tmdb_genres():
    genre_id_to_name = {}

    # Getting genres for movies
    api_url = f"""https://api.themoviedb.org/3/genre/movie/list?api_key={config["TMDB_API_KEY"]}"""
    headers = {"Accept": "application/json"}
    response = requests.get(api_url, headers=headers)
    decoded_response = response.content.decode("utf-8")
    json_response = json.loads(decoded_response)

    for item in json_response["genres"]:
        genre_id_to_name[item["id"]] = item["name"]

    # Getting genres for tvshows
    api_url = f"""https://api.themoviedb.org/3/genre/movie/list?api_key={config["TMDB_API_KEY"]}"""
    headers = {"Accept": "application/json"}
    response = requests.get(api_url, headers=headers)
    decoded_response = response.content.decode("utf-8")
    json_response = json.loads(decoded_response)

    for item in json_response["genres"]:
        genre_id_to_name[item["id"]] = item["name"]

    return genre_id_to_name


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
    sql_query_movie = f"""SELECT content_dir,title,substr(release_date, 1, 4) as release_date,library_name,id FROM movie WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR substr(release_date, 1, 4) LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query_tvshow = f"""SELECT content_dir,name as title,substr(first_air_date, 1, 4) as release_date,library_name,id FROM tvshow WHERE title LIKE "%{keyword}%" COLLATE NOCASE OR substr(first_air_date, 1, 4) LIKE "%{keyword}%" COLLATE NOCASE"""
    sql_query = f"{sql_query_movie} UNION ALL {sql_query_tvshow} ORDER BY content_dir"
    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def get_media_by_genre(library_name, genre, orderby):

    db = dbm.database_manager()

    orderby = orderby.split(" ")

    content_type = library_content_type(library_name)

    if content_type == "movie":
        sql_query = f"""SELECT title,substr(release_date, 1, 4) as release_date,overview,vote_average,video,poster_path,genre_ids,library_name,id FROM movie WHERE genre_ids LIKE "%{genre}%" COLLATE NOCASE ORDER BY {orderby[0]} COLLATE NOCASE {orderby[1]}"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,substr(first_air_date, 1, 4) as release_date,overview,vote_average,video,poster_path,genre_ids,library_name,id FROM tvshow WHERE genre_ids LIKE "%{genre}%" COLLATE NOCASE ORDER BY {orderby[0]} COLLATE NOCASE {orderby[1]}"""
    else:
        return None

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def get_popular_movies():
    # movie = Movie()
    # popular = movie.popular()

    # popular_movie_titles = []
    # for movie in popular:
    #     popular_movie_titles.append('"' + movie.title + '"')

    # sql_popular_movie_titles = ", ".join(popular_movie_titles)

    # db = dbm.database_manager()
    # sql_query = f"""SELECT content_dir,title,substr(release_date, 1, 4) as release_date,overview,vote_average,library_name FROM movie WHERE title IN ({sql_popular_movie_titles}) COLLATE NOCASE """
    # sql_data = db.sql_execute(sql_query)

    # for movie in sql_data:
    #     if movie["title"] in str(popular_movie_titles):
    #         popular_movie_titles.remove('"' + movie["title"] + '"')

    # for movie in popular:
    #     if movie.title in str(popular_movie_titles):
    #         json = {
    #             "content_dir": "",
    #             "title": movie.title,
    #             "release_date": movie.release_date[:4],
    #             "overview": movie.overview,
    #             "vote_average": movie.vote_average,
    #             "poster_path": movie.poster_path,
    #             "id": movie.id,
    #         }
    #         sql_data.append(json)

    # sql_data_sorted = sorted(sql_data, key=lambda i: i["vote_average"], reverse=True)

    # db.connection.close()

    return None


def get_seasons(video_id):
    db = dbm.database_manager()

    sql_query = f"""SELECT cast(season_number as integer) as season_number,poster_path FROM tvshow_season WHERE show_id = "{video_id}" GROUP BY season_number"""
    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sorted(sql_data, key=lambda i: i["season_number"])


def get_meta_season_episode(video_id, season_number, episode_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT ('Episode ' || episode_number || ' - '|| name) as title,substr(air_date, 1, 4) as release_date,overview,vote_average,still_path as poster_path FROM tvshow_episode WHERE show_id = "{video_id}" AND season_number="{season_number}" AND episode_number = "{episode_number}" """

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_episodes(video_id, season_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT name,overview,episode_number,still_path FROM tvshow_episode WHERE show_id = "{video_id}" AND season_number = "{season_number}" COLLATE nocase"""
    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sql_data


def get_episodes_info(content_dir, season_number, episode_number):
    db = dbm.database_manager()

    sql_query = f"""SELECT name,overview,episode_number,still_path FROM tvshow_episode WHERE content_dir = "{content_dir}" COLLATE nocase AND season_number = "{season_number}" COLLATE nocase"""
    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sql_data


def get_meta_by_id(content_type, video_id):
    db = dbm.database_manager()

    if content_type == "movie":
        sql_query = f"""SELECT title,substr(release_date, 1, 4) as release_date,overview,vote_average,video FROM movie WHERE id="{video_id}" COLLATE NOCASE"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,substr(first_air_date, 1, 4) as release_date,overview,vote_average FROM tvshow WHERE id="{video_id}" COLLATE NOCASE """
    else:
        return None

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data[0]


def get_meta(library_name, video_id):
    db = dbm.database_manager()

    content_type = library_content_type(library_name)
    if content_type == "movie":
        sql_query = f"""SELECT title,substr(release_date, 1, 4) as release_date,overview,vote_average,video,poster_path,genre_ids,library_name FROM movie WHERE id="{video_id}" COLLATE NOCASE"""
    elif content_type == "tvshow":
        sql_query = f"""SELECT name as title,substr(first_air_date, 1, 4) as release_date,overview,vote_average,video,poster_path,genre_ids,library_name FROM tvshow WHERE id="{video_id}" COLLATE NOCASE """
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
    sql_query = f"""SELECT path,filename from file WHERE id="{video_id}" AND filename LIKE "%S{str(season_number).zfill(2)}E{str(episode_number).zfill(2)}%" COLLATE NOCASE;"""
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
    sql_query = f"""SELECT title,video from movie WHERE id="{video_id}" COLLATE NOCASE limit 1;"""
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

