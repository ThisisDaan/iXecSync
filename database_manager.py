import sqlite3
from sqlite3 import Error
import os
from tmdbv3api import TMDb, Movie, TV
import time
import json


class database_manager:
    def __init__(self):
        db = os.path.dirname(os.path.realpath(__file__)) + os.sep + "fsociety00.db"
        self.connection = sqlite3.connect(db)

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS movie (
                                    id INTEGER PRIMARY KEY,
                                    media_name TEXT,
                                    library_path TEXT,
                                    tmdb_id TEXT,
                                    title TEXT,
                                    original_title TEXT,
                                    overview TEXT,
                                    release_date TEXT,
                                    genre_ids TEXT,
                                    original_language TEXT,
                                    poster_path TEXT,
                                    backdrop_path TEXT,
                                    popularity TEXT,
                                    video TEXT,
                                    vote_average TEXT,
                                    vote_count TEXT
                                );"""
        )

        # self.sql_create_table(
        #     """CREATE TABLE IF NOT EXISTS tvshow (
        #                             id INTEGER PRIMARY KEY,
        #                             media_name TEXT,
        #                             library_path TEXT,
        #                             tmdb_id INTEGER UNIQUE,
        #                             name TEXT,
        #                             original_nane TEXT,
        #                             overview TEXT,
        #                             first_air_date TEXT,
        #                             genre_ids TEXT,
        #                             original_language TEXT,
        #                             origin_country TEXT,
        #                             poster_path TEXT,
        #                             backdrop_path TEXT,
        #                             popularity TEXT,
        #                             video INTEGER,
        #                             vote_average TEXT,
        #                             vote_count INTEGER
        #                         );"""
        # )

    def sql_create_table(self, sql_query):
        try:
            c = self.connection.cursor()
            c.execute(sql_query)
            self.connection.commit()
        except Exception as e:
            print(f"{e}")

    def not_exists(self, media_name, library_type):
        sql_query = f"""SELECT media_name FROM {library_type} WHERE media_name ="{media_name}" COLLATE NOCASE """
        cur = self.connection.cursor()

        cur.execute(sql_query)
        sql_result = cur.fetchall()
        cur.close()

        if sql_result:
            return False
        else:
            return True

    def get_movie(self, media_name):
        sql_query = (
            f"""SELECT * FROM movie WHERE media_name ="{media_name}" COLLATE NOCASE """
        )
        cur = self.connection.cursor()

        cur.execute(sql_query)
        sql_result = cur.fetchall()
        sql_json = json.loads(json.dumps(sql_result))
        cur.close()
        return sql_json

    def get_path(self, media_name):
        sql_query = f"""SELECT library_path FROM movie WHERE media_name ="{media_name}" COLLATE NOCASE """
        cur = self.connection.cursor()

        cur.execute(sql_query)
        sql_result = cur.fetchall()
        sql_json = json.loads(json.dumps(sql_result))
        cur.close()
        return sql_json

    def sql_update_movie(self, movie, library_path, media_name):
        sql_input = [
            media_name,
            library_path,
            movie.id,
            movie.title,
            movie.original_title,
            movie.overview,
            movie.release_date,
            str(movie.genre_ids),
            movie.original_language,
            movie.poster_path,
            movie.backdrop_path,
            movie.popularity,
            movie.video,
            movie.vote_average,
            movie.vote_count,
        ]
        if self.connection:
            sql_query = """INSERT OR REPLACE INTO movie(media_name,library_path,tmdb_id,title,original_title,overview,release_date,genre_ids,original_language,poster_path,backdrop_path,popularity,video,vote_average,vote_count)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            cur = self.connection.cursor()
            cur.execute(sql_query, (sql_input))
            self.connection.commit()
            cur.close()

    def close(self):
        self.connection.close()
        del self.connection
