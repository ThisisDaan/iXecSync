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
                content_file TEXT UNIQUE
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS movie (
                c_id INTEGER PRIMARY KEY,
                library_name TEXT,
                content_dir TEXT UNIQUE,
                poster_path TEXT,
                adult TEXT,
                overview TEXT,
                release_date TEXT,
                genre_ids TEXT,
                id TEXT,
                original_title TEXT,
                original_language TEXT,
                title TEXT,
                backdrop_path TEXT,
                popularity INTEGER,
                vote_count INTEGER,
                video TEXT,
                vote_average INTEGER
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow (
                c_id INTEGER PRIMARY KEY,
                library_name TEXT,
                content_dir TEXT UNIQUE,
                poster_path TEXT,
                popularity INTEGER,
                id TEXT,
                backdrop_path TEXT,
                vote_average INTEGER,
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
            """CREATE TABLE IF NOT EXISTS tvshow_season (
                c_id INTEGER PRIMARY KEY,
                content_dir TEXT,
                air_date TEXT,
                name TEXT,
                overview TEXT,
                id TEXT,
                poster_path TEXT,
                season_number TEXT
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
                vote_average INTEGER,
                vote_count INTEGER
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS genre (
                c_id INTEGER PRIMARY KEY,
                id TEXT UNIQUE,
                name TEXT
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

    def sql_execute(self, sql_query):
        cur = self.connection.cursor()
        cur.execute(sql_query)
        sql_result = cur.fetchall()

        sql_list = []
        for item in sql_result:
            sql_list.append(dict(item))

        cur.close()
        return sql_list

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
            # print(sql_query)
            cur = self.connection.cursor()
            cur.execute(sql_query, (json_values))
            self.connection.commit()
            cur.close()
        else:
            print("no connection")

    def close(self):
        self.connection.close()
        del self.connection
