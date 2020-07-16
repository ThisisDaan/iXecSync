import sqlite3
from sqlite3 import Error
import os
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
                id TEXT,
                path TEXT,
                filename TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS movie (
                id TEXT PRIMARY KEY,
                library_name TEXT,
                title TEXT,
                overview TEXT,
                release_date TEXT,
                poster_path TEXT,
                backdrop_path TEXT,
                genre_ids TEXT,
                original_title TEXT,
                original_language TEXT,
                adult TEXT,
                popularity INTEGER,
                vote_count INTEGER,
                vote_average INTEGER,
                video TEXT
                );"""
        )
        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow (
                id TEXT PRIMARY KEY,
                library_name TEXT,
                name TEXT,
                overview TEXT,
                first_air_date TEXT,
                original_name TEXT,
                poster_path TEXT,
                backdrop_path TEXT,
                origin_country TEXT,
                original_language TEXT,
                genre_ids TEXT,
                popularity INTEGER,
                vote_average INTEGER,
                vote_count INTEGER,
                video
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow_season (
                id TEXT PRIMARY KEY,
                show_id TEXT,
                name TEXT,
                season_number TEXT,
                air_date TEXT,
                overview TEXT,
                poster_path TEXT,
                _id TEXT
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS tvshow_episode (
                id TEXT PRIMARY KEY,
                show_id TEXT,
                name TEXT,
                season_number TEXT,
                episode_number TEXT,
                overview TEXT,
                air_date TEXT,
                crew TEXT,
                guest_stars TEXT,
                production_code TEXT,
                still_path TEXT,
                vote_average INTEGER,
                vote_count INTEGER
                );"""
        )

        self.sql_create_table(
            """CREATE TABLE IF NOT EXISTS genre (
                id INTEGER PRIMARY KEY,
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

    def not_exists(self, directory, filename):
        sql_query = f"""SELECT * FROM file WHERE path = "{directory}" COLLATE NOCASE AND filename = "{filename}" """
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
