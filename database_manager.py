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
        self.connection.row_factory = sqlite3.Row

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS file (
                id INTEGER PRIMARY KEY,
                library_name TEXT,
                library_path TEXT,
                content_type TEXT,
                content_dir TEXT,
                content_file TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS movie (
                id INTEGER PRIMARY KEY,
                library_name TEXT,
                content_dir TEXT UNIQUE,
                tmdb_id TEXT UNIQUE,
                title TEXT,
                original_title TEXT,
                overview TEXT,
                release_date TEXT,
                genre_ids TEXT,
                original_language TEXT,
                poster_path TEXT,
                backdrop_path TEXT,
                popularity INTEGER,
                video TEXT,
                vote_average TEXT,
                vote_count TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow (
                id INTEGER PRIMARY KEY,
                library_name TEXT,
                content_dir TEXT UNIQUE,
                tmdb_id TEXT UNIQUE,
                name TEXT,
                original_name TEXT,
                overview TEXT,
                first_air_date TEXT,
                genre_ids TEXT,
                original_language TEXT,
                origin_country TEXT,
                poster_path TEXT,
                backdrop_path TEXT,
                popularity INTEGER,
                vote_average TEXT,
                vote_count TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow_episode (
                id INTEGER PRIMARY KEY,
                tmdb_id TEXT,
                name TEXT,
                overview TEXT,
                thumbnail_path TEXT,
                season_number TEXT,
                episode_number TEXT
                );"""
        )

    def sql_create_table(self, sql_query):
        try:
            c = self.connection.cursor()
            c.execute(sql_query)
            self.connection.commit()
        except Exception as e:
            print(f"SQL_CREATE_TABLE ERROR: {e}")

    def not_exists(self, content_dir, library_type):
        sql_query = f"""SELECT content_dir FROM {library_type} WHERE content_dir ="{content_dir}" COLLATE NOCASE """
        cur = self.connection.cursor()

        cur.execute(sql_query)
        sql_result = cur.fetchall()
        cur.close()

        if sql_result:
            return False
        else:
            return True

    def get_movie(self, content_dir):
        sql_query = f"""SELECT * FROM movie WHERE content_dir ="{content_dir}" COLLATE NOCASE """
        cur = self.connection.cursor()

        cur.execute(sql_query)
        sql_result = cur.fetchall()
        sql_json = json.loads(json.dumps(sql_result))
        cur.close()
        return sql_json

    def get_library_count(self, library_name):
        sql_query = f"""SELECT COUNT(*) FROM movie WHERE library_name ="{library_name}" COLLATE NOCASE"""
        cur = self.connection.cursor()

        cur.execute(sql_query)
        sql_result = cur.fetchall()
        sql_json = json.loads(json.dumps(sql_result))
        cur.close()
        return sql_json

    def sql_execute(self, sql_query):
        cur = self.connection.cursor()
        cur.execute(sql_query)
        sql_result = cur.fetchall()

        sql_list = []
        for item in sql_result:
            sql_list.append(dict(item))

        cur.close()
        return sql_list

    def sql_update_file(self, file_info):
        sql_input = [
            str(file_info["library_name"]),
            str(file_info["library_path"]),
            str(file_info["content_type"]),
            str(file_info["content_dir"]),
            str(file_info["content_file"]),
        ]
        if self.connection:
            sql_query = """INSERT OR REPLACE INTO file(
                library_name,
                library_path,
                content_type,
                content_dir,
                content_file
                )
                VALUES(?,?,?,?,?)"""
            cur = self.connection.cursor()
            cur.execute(sql_query, (sql_input))
            self.connection.commit()
            cur.close()

    def sql_update_movie(self, content_dir, library_name, movie):
        sql_input = [
            library_name,
            content_dir,
            movie.id,
            movie.title,
            movie.original_title,
            movie.overview,
            movie.release_date,
            str(movie.genre_ids),
            movie.original_language,
            movie.poster_path,
            movie.backdrop_path,
            int(movie.popularity),
            movie.video,
            movie.vote_average,
            movie.vote_count,
        ]
        if self.connection:
            sql_query = """INSERT OR REPLACE INTO movie(
                library_name,
                content_dir,
                tmdb_id,
                title,
                original_title,
                overview,
                release_date,
                genre_ids,
                original_language,
                poster_path,
                backdrop_path,
                popularity,
                video,
                vote_average,
                vote_count
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            cur = self.connection.cursor()
            cur.execute(sql_query, (sql_input))
            self.connection.commit()
            cur.close()

    def sql_update_tvshow(self, content_dir, library_name, tvshow):
        sql_input = [
            library_name,
            content_dir,
            tvshow.id,
            tvshow.name,
            tvshow.original_name,
            tvshow.overview,
            tvshow.first_air_date,
            str(tvshow.genre_ids),
            tvshow.original_language,
            str(tvshow.origin_country),
            tvshow.poster_path,
            tvshow.backdrop_path,
            int(tvshow.popularity),
            tvshow.vote_average,
            tvshow.vote_count,
        ]
        if self.connection:
            sql_query = """INSERT OR REPLACE INTO tvshow(
                library_name,
                content_dir,
                tmdb_id,
                name,
                original_name,
                overview,
                first_air_date,
                genre_ids,
                original_language,
                origin_country,
                poster_path,
                backdrop_path,
                popularity,
                vote_average,
                vote_count
                )
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
            cur = self.connection.cursor()
            cur.execute(sql_query, (sql_input))
            self.connection.commit()
            cur.close()

    def close(self):
        self.connection.close()
        del self.connection
