from __main__ import config
import database_manager as dbm
import requests
import json
from difflib import SequenceMatcher


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def tmdb_api_request(api_url):
    headers = {"Accept": "application/json"}
    response = requests.get(api_url, headers=headers)

    if response.status_code == 200:
        decoded_response = response.content.decode("utf-8")
        json_response = json.loads(decoded_response)

        return json_response
    else:
        return None


def get_popular_movies():
    api_url = f"""https://api.themoviedb.org/3/movie/popular?api_key={config["TMDB_API_KEY"]}"""
    api_response = tmdb_api_request(api_url)
    results = api_response["results"]

    return results


def get_popular_tvshows():
    api_url = (
        f"""https://api.themoviedb.org/3/tv/popular?api_key={config["TMDB_API_KEY"]}"""
    )
    api_response = tmdb_api_request(api_url)
    results = api_response["results"]

    popular_tvshows = []

    for item in results:
        item["title"] = item["name"]
        item["release_date"] = item["first_air_date"]
        popular_tvshows.append(item)

    return popular_tvshows


def trailer(content_type, movie_id):
    api_url = f"""https://api.themoviedb.org/3/{content_type}/{movie_id}/videos?api_key={config["TMDB_API_KEY"]}&language=en-US"""
    api_response = tmdb_api_request(api_url)
    results = api_response["results"]

    for video in results:
        if video["type"].lower() == "trailer" and video["site"].lower() == "youtube":
            return video["key"]

    return False


def tmdb_overview(content_type, video_id):
    # title,release_date,overview,vote_average,video,poster_path,library_name,id
    api_url = f"""https://api.themoviedb.org/3/{content_type}/{video_id}?api_key={config["TMDB_API_KEY"]}&language=en-US"""

    api_response = tmdb_api_request(api_url)
    results = api_response

    if content_type == "tv":
        results["release_date"] = results["first_air_date"]
        results["title"] = results["name"]

    results["content_type"] = content_type

    return results


def format_this(string):
    if ", " in string and "&" not in string and "and" not in string:
        string = string.split(", ")
        string = f"{string[1]} {string[0]}"

    return string


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def search(content_type, keyword, release_date=None):
    if content_type == "movie":
        year = "release_date"
        title = "title"
        api_search = "movie"
    elif content_type == "tv":
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

    headers = {"Accept": "application/json"}
    response = requests.get(api_url, params=parameters, headers=headers)
    print(f"SEARCH API URL - {response.url}")
    decoded_response = response.content.decode("utf-8")
    json_response = json.loads(decoded_response)
    json_results = json_response["results"]

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


def genres(content_type):

    # Getting genres for movies
    api_url = f"""https://api.themoviedb.org/3/genre/{content_type}/list?api_key={config["TMDB_API_KEY"]}"""
    api_response = tmdb_api_request(api_url)
    results = api_response["genres"]

    return results

