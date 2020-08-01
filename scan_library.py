from __main__ import config
from pathlib import Path
from tmdb_api import search, trailer
import urllib.request
import re
from routes_file_request import thumbnail_path
import database_manager as dbm
from database_queries import save_tmdb_genres, all_genres, file_exists
import tmdb_api
from collections import defaultdict

import threading
import time


scanning = False
scanned_items = 0
total_items = 0


def scanning_and_threading():
    if scanning == False:
        scan_thread = threading.Thread(target=scan)
        scan_thread.start()


def return_scan_percentage():
    if scanned_items != 0 and total_items != 0:
        percentage = round((scanned_items / total_items) * 100)
    else:
        percentage = 0

    return percentage


def scan():
    global scanning
    global scanned_items
    global total_items

    scanning = True

    save_tmdb_genres()

    results = all_genres()
    genres = {}

    for genre in results:
        genres[genre["id"]] = genre["name"]

    for library in config["library"]:
        if library["type"] == "movie":
            scan_library_movie(library, genres)
        elif library["type"] == "tv":
            scan_library_tv(library, genres)
        else:
            print("Invalid library type")

    time.sleep(60)
    scanning = False
    total_items = 0
    scanned_items = 0


"""
Scans a directory and returns the path of all supported files.
"""


def get_supported_files(directory):

    directory = Path(directory)
    file_types = [".mp4", ".mkv"]

    supported_files = [
        file for file_type in file_types for file in directory.rglob(f"*{file_type}")
    ]

    return supported_files


def scan_library_movie(library, genres):
    global scanning
    global scanned_items
    global total_items

    # opening database connection
    db = dbm.database_manager()

    files = get_supported_files(library["path"])

    total_items += len(files)

    for file in files:
        scanned_items += 1
        if not file_exists(file.parent, file.name):

            print(f"Scanned file - {file.name}")

            # Getting the movie name from parent direcotry
            name = file.parent.name
            title = name.split(" (")[0]
            release_date = name.split(" (")[1].replace(")", "")

            # Searching TMDB for movie details
            tmdb_data = tmdb_api.search("movie", title, release_date)

            # Checking if we have any results
            if tmdb_data:
                tmdb_data["video"] = tmdb_api.trailer("movie", tmdb_data["id"])

                for genre in tmdb_data["genre_ids"]:
                    json_data = {"id": tmdb_data["id"], "genre_id": genre}
                    db.sql_update_by_json("media_genre", json_data)

                del tmdb_data["genre_ids"]
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


def scan_library_tv(library, genres):
    global scanning
    global scanned_items
    global total_items

    # opening database connection
    db = dbm.database_manager()

    files = get_supported_files(library["path"])
    total_items += len(files)

    collected_files = defaultdict(lambda: defaultdict(list))

    for file in files:
        scanned_items += 1
        if not file_exists(file.parent, file.name):

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

    for tv in collected_files:
        print(f"TVSHOW - {tv}")

        # Getting the movie name from parent direcotry
        name = tv

        if "(" in name:
            title = name.split(" (")[0]
            release_date = name.split(" (")[1].replace(")", "")
        else:
            title = name
            release_date = None

        # Searching TMDB for movie details
        tmdb_data = search("tv", title, release_date)

        # Checking if we have any results
        if tmdb_data:
            tmdb_data["video"] = tmdb_api.trailer("tv", tmdb_data["id"])

            for genre in tmdb_data["genre_ids"]:
                json_data = {"id": tmdb_data["id"], "genre_id": genre}
                db.sql_update_by_json("media_genre", json_data)

            del tmdb_data["genre_ids"]
            tmdb_data["library_name"] = library["name"]

            # Writing movie to database
            db.sql_update_by_json("tv", tmdb_data)
            print(f"Saving movie to DB - {file.name}")

            download_poster(tmdb_data)

            for season in collected_files[tv]:

                tv_id = tmdb_data["id"]
                season_number = season

                api_url = f"https://api.themoviedb.org/3/tv/{tv_id}/season/{season_number}?api_key={config['TMDB_API_KEY']}"
                api_response = tmdb_api.tmdb_api_request(api_url)

                if api_response:
                    tv_episodes = dict(api_response)
                    tv_season = dict(api_response)

                    del tv_season["episodes"]
                    tv_season["show_id"] = tmdb_data["id"]
                    print(f"Adding {name} Season {tv_season['season_number']}")
                    db.sql_update_by_json("tv_season", tv_season)

                    for episode in collected_files[tv][season]:

                        # Adding episodes to database

                        for tmdb_episode in tv_episodes["episodes"]:
                            tmdb_episode["show_id"] = tmdb_data["id"]
                            print(
                                f"Adding S{tmdb_episode['season_number']}E{tmdb_episode['episode_number']}"
                            )
                            print("=" * 80)
                            db.sql_update_by_json("tv_episode", tmdb_episode)

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

                else:
                    print("error no response")

    db.connection.close()


def download_poster(tmdb_data):
    if "poster_path" in tmdb_data:
        url = f"https://image.tmdb.org/t/p/w500{tmdb_data['poster_path']}"

        try:
            urllib.request.urlretrieve(
                url, f"""{thumbnail_path()}{tmdb_data["poster_path"]}""",
            )
            print(f"Downloading poster")
        except Exception:
            print(f"Error downloading poster")
    else:
        print(f"No poster")
