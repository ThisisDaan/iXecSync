from __main__ import config
import database_manager as dbm
from pathlib import Path
import tmdb_api

"""
Check the type of content of the libraries
"""


def library_content_type(library_name):
    for item in config["library"]:
        if item["name"].lower() == library_name.lower():
            if item["type"] == "tv":
                return "tv"
            elif item["type"] == "movie":
                return "movie"
            else:
                return None


def library(library_name, orderby, genre, search_keyword):
    db = dbm.database_manager()

    orderby = orderby.split(" ")
    content_type = library_content_type(library_name)

    sql_params = []

    if content_type == "movie":
        if genre is None:
            sql_query = f"""
                        SELECT DISTINCT title,release_date as release_date,id,poster_path,library_name FROM movie
                        """

        else:
            sql_query = f"""
                        SELECT DISTINCT m.title as title,m.library_name,m.poster_path,m.release_date,m.id,g.name as genre_name from genre as g 
                        JOIN media_genre as mg ON g.id = mg.genre_id
                        JOIN movie as m ON m.id  = mg.id
                        """

    elif content_type == "tv":
        if genre is None:
            sql_query = f"""
                        SELECT DISTINCT name as title,first_air_date as release_date,id,poster_path,library_name FROM tv
                        """

        else:
            sql_query = f"""
                        SELECT DISTINCT m.name as title,m.library_name,m.poster_path,m.first_air_date as release_date,m.id,g.name as genre_name from genre as g 
                        JOIN media_genre as mg ON g.id = mg.genre_id
                        JOIN tv as m ON m.id = mg.id
                        """

    else:
        return "Invalid Library Type"

    sql_params.append(sql_query)

    if library_name:
        sql_query = f"""
                    WHERE library_name = "{library_name}" COLLATE NOCASE
                    """
        sql_params.append(sql_query)

    if search_keyword:
        sql_query = f"""
                     AND title like "%{search_keyword}%" COLLATE NOCASE
                     """
        sql_params.append(sql_query)

    if genre:
        sql_query = f"""
                    AND genre_name = "{genre}" COLLATE NOCASE
                    """
        sql_params.append(sql_query)

    if orderby:
        sql_query = f"""
                    ORDER BY {orderby[0]} COLLATE NOCASE {orderby[1]}
                    """
        sql_params.append(sql_query)

    sql_query = " ".join(sql_params)

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def all_genres():
    db = dbm.database_manager()

    sql_query = f"""
                SELECT id,name from genre
                """

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    return sql_data


def library_genres(library_name):
    db = dbm.database_manager()

    content_type = library_content_type(library_name)

    if content_type:
        sql_query = f"""
                    SELECT DISTINCT g.name from genre as g 
                    JOIN media_genre as mg ON g.id = mg.genre_id
                    JOIN {content_type} as m ON m.id = mg.id
                    WHERE m.id = mg.id 
                    AND m.library_name = "{library_name}" COLLATE NOCASE
                    """

        sql_data = db.sql_execute(sql_query)
        db.connection.close()
        sql_data_sorted = sorted(sql_data, key=lambda i: i["name"], reverse=False)

        return sql_data_sorted
    else:
        return None


def library_overview(content_type, video_id, season_number=None, episode_number=None):
    db = dbm.database_manager()

    if content_type == "movie":
        sql_query = f"""
                    SELECT title,release_date,overview,vote_average,video,poster_path,library_name,id FROM movie
                    WHERE id="{video_id}" COLLATE NOCASE
                    """

    elif content_type == "tv":
        if episode_number:
            sql_query = f"""
                        SELECT ((select name from tv where id = "{video_id}" limit 1) || ' - ' || 'Season ' || season_number || ' - Episode '|| episode_number) as title,air_date as release_date,overview,vote_average,still_path as poster_path,episode_number,season_number,show_id,name as subtitle FROM tv_episode 
                        WHERE show_id = "{video_id}" 
                        AND season_number="{season_number}" 
                        AND episode_number = "{episode_number}" 
                        """

        elif season_number:
            sql_query = f"""SELECT ((select name from tv where id = "{video_id}" limit 1) || ' - '  || 'Season ' || season_number) as title,air_date as release_date,overview,poster_path,season_number,show_id FROM tv_season 
                        WHERE show_id = "{video_id}" 
                        AND season_number="{season_number}" 
                        """

        else:
            sql_query = f"""
                        SELECT name as title,first_air_date as release_date,overview,vote_average,video,poster_path,library_name,id FROM tv 
                        WHERE id="{video_id}" COLLATE NOCASE 
                        """

    else:
        return "Invalid Library Type"

    sql_data = db.sql_execute(sql_query)

    genre_query = f"""
                  SELECT DISTINCT g.name from genre as g 
                  JOIN media_genre as mg ON g.id = mg.genre_id
                  JOIN {content_type} as m ON m.id = mg.id
                  WHERE m.id = "{video_id}"
                  """

    sql_genre = db.sql_execute(genre_query)

    sql_data[0]["genres"] = sql_genre
    sql_data[0]["content_type"] = content_type

    # print(sql_data)

    db.connection.close()

    return sql_data[0]


def library_overview_seasons(video_id):
    db = dbm.database_manager()

    sql_query = f"""
                SELECT cast(season_number as integer) as season_number,poster_path FROM tv_season 
                WHERE show_id = "{video_id}" 
                GROUP BY season_number
                """

    sql_data = db.sql_execute(sql_query)

    db.connection.close()

    return sorted(sql_data, key=lambda i: i["season_number"])


def library_overview_episodes(video_id, season_number):
    db = dbm.database_manager()

    # sql_query = f"""SELECT name,overview,episode_number,still_path FROM tv_episode WHERE show_id = "{video_id}" AND season_number = "{season_number}" COLLATE nocase"""
    sql_query = f"""
                SELECT name,overview,episode_number,still_path,id,show_id,season_number FROM tv_episode
                WHERE show_id = "{video_id}" 
                AND season_number = "{season_number}" COLLATE nocase 
                AND id IN (SELECT id FROM file)
                """

    local_episodes = db.sql_execute(sql_query)

    sql_query = f"""
                SELECT name,overview,episode_number,still_path,id,show_id,season_number FROM tv_episode
                WHERE show_id = "{video_id}" 
                AND season_number = "{season_number}"
                """

    total_episodes = db.sql_execute(sql_query)
    db.connection.close()

    for episode in total_episodes:
        if episode in local_episodes:
            episode["available"] = True
        else:
            episode["available"] = False

    return total_episodes


def library_overview_trailer(library_name, video_id):
    db = dbm.database_manager()

    content_type = library_content_type(library_name)
    if content_type == "movie":
        sql_query = f"""
                    SELECT title,video from movie
                    WHERE id="{video_id}" COLLATE NOCASE 
                    limit 1
                    """

    elif content_type == "tv":
        sql_query = f"""
                    SELECT name as title,video from tv
                    WHERE id="{video_id}" COLLATE NOCASE 
                    limit 1
                    """

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    if sql_data:
        return sql_data[0]
    else:
        return None


def media_path(video_id, season_number=None, episode_number=None):
    db = dbm.database_manager()

    if episode_number:
        sql_query = f"""
                    SELECT DISTINCT f.path,f.filename from file as f 
                    JOIN tv_episode as tve ON tve.id = f.id
                    JOIN tv as tv ON tv.id = tve.show_id
                    WHERE f.id = tve.id AND tve.season_number = "{season_number}" 
                    AND tve.episode_number = "{episode_number}" 
                    AND tv.id = "{video_id}"
                    """
    else:
        sql_query = f"""
                    SELECT f.path,f.filename from file as f
                    JOIN movie as m ON m.id = f.id 
                    WHERE f.id="{video_id}" 
                    AND m.id="{video_id}"
                    """

    sql_data = db.sql_execute(sql_query)
    db.connection.close()

    if sql_data:
        data = sql_data[0]
        path = Path(data["path"], data["filename"])
        return path
    else:
        return None


def file_exists(directory, filename):
    db = dbm.database_manager()

    sql_query = f"""
                SELECT * FROM file
                WHERE path = "{directory}" COLLATE NOCASE 
                AND filename = "{filename}" 
                """

    sql_data = db.sql_execute(sql_query)

    if sql_data:
        return True
    else:
        return False


def save_tmdb_genres():

    content_types = ["movie", "tv"]

    for content_type in content_types:
        db = dbm.database_manager()

        results = tmdb_api.genres(content_type)

        for genre in results:
            db.sql_update_by_json("genre", genre)

        db.connection.close()


def get_popular_movies():

    results = tmdb_api.get_popular_movies()

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

    return sql_data_sorted[:18]


def get_popular_tvshows():

    results = tmdb_api.get_popular_tvshows()

    popular_movie_titles = []
    for movie in results:
        popular_movie_titles.append('"' + movie["name"] + '"')

    sql_popular_movie_titles = ", ".join(popular_movie_titles)

    db = dbm.database_manager()
    sql_query = f"""SELECT name as title,first_air_date as release_date,id,poster_path,library_name,popularity,vote_average FROM tv WHERE name IN ({sql_popular_movie_titles}) COLLATE NOCASE """

    sql_data = db.sql_execute(sql_query)

    for movie in sql_data:
        if movie["title"] in str(popular_movie_titles):
            popular_movie_titles.remove('"' + movie["title"] + '"')

    for movie in results:
        if movie["name"] in str(popular_movie_titles):
            json_data = {
                "library_name": "",
                "title": movie["name"],
                "release_date": movie["first_air_date"],
                "poster_path": movie["poster_path"],
                "popularity": movie["popularity"],
                "vote_average": movie["vote_average"],
                "id": movie["id"],
                "notavailable": True,
            }
            sql_data.append(json_data)

    sql_data_sorted = sorted(sql_data, key=lambda i: i["vote_average"], reverse=True)

    db.connection.close()

    return sql_data_sorted[:18]
