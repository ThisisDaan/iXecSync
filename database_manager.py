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
                c_id INTEGER PRIMARY KEY,
                library_name TEXT,
                library_path TEXT,
                content_type TEXT,
                content_dir TEXT,
                content_file TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS movie (
                c_id INTEGER PRIMARY KEY,
                library_name TEXT,
                content_dir TEXT UNIQUE,
                poster_path TEXT UNIQUE,
                adult TEXT,
                overview TEXT,
                release_date TEXT,
                genre_ids TEXT,
                id TEXT,
                original_title TEXT,
                original_language TEXT,
                title TEXT,
                backdrop_path INTEGER,
                popularity TEXT,
                vote_count TEXT,
                video TEXT,
                vote_average TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow (
                c_id INTEGER PRIMARY KEY,
                library_name TEXT,
                content_dir TEXT UNIQUE,
                poster_path TEXT,
                popularity TEXT,
                id TEXT,
                backdrop_path TEXT,
                vote_average TEXT,
                overview TEXT,
                first_air_date TEXT,
                origin_country TEXT,
                genre_ids TEXT,
                original_language TEXT,
                vote_count INTEGER,
                name TEXT,
                original_name TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow_episode (
                c_id INTEGER PRIMARY KEY,
                content_dir TEXT,
                air_date TEXT,
                crew TEXT,
                episode_number TEXT,
                guest_stars TEXT,
                name TEXT,
                overview TEXT,
                id TEXT,
                show_id TEXT,
                production_code TEXT,
                season_number TEXT,
                still_path TEXT,
                vote_average TEXT,
                vote_count TEXT
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
        sql_query = f"""SELECT content_dir FROM {library_type} WHERE content_dir COLLATE NOCASE = "{content_dir}" COLLATE NOCASE"""
        # print(sql_query)
        cur = self.connection.cursor()

        cur.execute(sql_query)
        sql_result = cur.fetchall()
        cur.close()
        if sql_result:
            return False
        else:
            return True

    # def get_movie(self, content_dir):
    #     sql_query = f"""SELECT * FROM movie WHERE content_dir COLLATE NOCASE = "{content_dir}" COLLATE NOCASE """
    #     cur = self.connection.cursor()

    #     cur.execute(sql_query)
    #     sql_result = cur.fetchall()
    #     sql_json = json.loads(json.dumps(sql_result))
    #     cur.close()
    #     return sql_json

    # def get_library_count(self, library_name):
    #     sql_query = f"""SELECT COUNT(*) FROM movie WHERE library_name COLLATE NOCASE = "{library_name}" COLLATE NOCASE"""
    #     cur = self.connection.cursor()

    #     cur.execute(sql_query)
    #     sql_result = cur.fetchall()
    #     sql_json = json.loads(json.dumps(sql_result))
    #     cur.close()
    #     return sql_json

    def sql_execute(self, sql_query):
        cur = self.connection.cursor()
        cur.execute(sql_query)
        sql_result = cur.fetchall()

        sql_list = []
        for item in sql_result:
            sql_list.append(dict(item))

        cur.close()
        return sql_list

    # def sql_update_file(self, file_info):
    #     sql_input = [
    #         str(file_info["library_name"]),
    #         str(file_info["library_path"]),
    #         str(file_info["content_type"]),
    #         str(file_info["content_dir"]),
    #         str(file_info["content_file"]),
    #     ]
    #     if self.connection:
    #         sql_query = """INSERT OR REPLACE INTO file(
    #             library_name,
    #             library_path,
    #             content_type,
    #             content_dir,
    #             content_file
    #             )
    #             VALUES(?,?,?,?,?)"""
    #         cur = self.connection.cursor()
    #         cur.execute(sql_query, (sql_input))
    #         self.connection.commit()
    #         cur.close()

    #         # id INTEGER PRIMARY KEY,
    #         # tmdb_id TEXT,
    #         # name TEXT,
    #         # overview TEXT,
    #         # thumbnail_path TEXT,
    #         # season_number TEXT,
    #         # episode_number TEXT

    def sql_update_by_json(self, table, json):
        json_columns = []
        json_values = []
        for column, value in json.items():
            json_columns.append(str(column))
            json_values.append(str(value))

        sql_values = ("?," * len(json_values))[:-1]

        if self.connection:
            sql_query = f"""INSERT OR REPLACE INTO {table}(
                {",".join(json_columns)}
                )
                VALUES({sql_values})"""
            cur = self.connection.cursor()
            cur.execute(sql_query, (json_values))
            self.connection.commit()
            cur.close()
        else:
            print("no connection")

    # def sql_update_episode(self, episode_info):
    #     sql_input = [
    #         str(episode_info["id"]),
    #         str(episode_info["name"]),
    #         str(episode_info["overview"]),
    #         str(episode_info["thumbnail_path"]),
    #         str(episode_info["season_number"]),
    #         str(episode_info["episode_number"]),
    #     ]
    #     if self.connection:
    #         sql_query = """INSERT OR REPLACE INTO tvshow_episode(
    #             tmdb_id,
    #             name,
    #             overview,
    #             thumbnail_path,
    #             season_number,
    #             episode_number
    #             )
    #             VALUES(?,?,?,?,?,?)"""
    #         cur = self.connection.cursor()
    #         cur.execute(sql_query, (sql_input))
    #         self.connection.commit()
    #         cur.close()

    # def sql_update_movie(self, content_dir, library_name, movie):
    #     sql_input = [
    #         library_name,
    #         content_dir,
    #         movie.id,
    #         movie.title,
    #         movie.original_title,
    #         movie.overview,
    #         movie.release_date,
    #         str(movie.genre_ids),
    #         movie.original_language,
    #         movie.poster_path,
    #         movie.backdrop_path,
    #         int(movie.popularity),
    #         movie.video,
    #         movie.vote_average,
    #         movie.vote_count,
    #     ]
    #     if self.connection:
    #         sql_query = """INSERT OR REPLACE INTO movie(
    #             library_name,
    #             content_dir,
    #             tmdb_id,
    #             title,
    #             original_title,
    #             overview,
    #             release_date,
    #             genre_ids,
    #             original_language,
    #             poster_path,
    #             backdrop_path,
    #             popularity,
    #             video,
    #             vote_average,
    #             vote_count
    #             )
    #             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    #         cur = self.connection.cursor()
    #         cur.execute(sql_query, (sql_input))
    #         self.connection.commit()
    #         cur.close()

    # def sql_update_tvshow(self, content_dir, library_name, tvshow):
    #     sql_input = [
    #         library_name,
    #         content_dir,
    #         tvshow.id,
    #         tvshow.name,
    #         tvshow.original_name,
    #         tvshow.overview,
    #         tvshow.first_air_date,
    #         str(tvshow.genre_ids),
    #         tvshow.original_language,
    #         str(tvshow.origin_country),
    #         tvshow.poster_path,
    #         tvshow.backdrop_path,
    #         int(tvshow.popularity),
    #         tvshow.vote_average,
    #         tvshow.vote_count,
    #     ]
    #     if self.connection:
    #         sql_query = """INSERT OR REPLACE INTO tvshow(
    #             library_name,
    #             content_dir,
    #             tmdb_id,
    #             name,
    #             original_name,
    #             overview,
    #             first_air_date,
    #             genre_ids,
    #             original_language,
    #             origin_country,
    #             poster_path,
    #             backdrop_path,
    #             popularity,
    #             vote_average,
    #             vote_count
    #             )
    #             VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
    #         cur = self.connection.cursor()
    #         cur.execute(sql_query, (sql_input))
    #         self.connection.commit()
    #         cur.close()

    def close(self):
        self.connection.close()
        del self.connection
