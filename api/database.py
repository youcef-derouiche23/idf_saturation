import configparser
import os

import psycopg2
from psycopg2.extras import RealDictCursor


class Database:
    def __init__(self, config_path: str):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        self.host = self.config["api"].get("db_host", "localhost")
        self.port = int(self.config["api"].get("db_port", 5432))
        self.dbname = self.config["api"].get("db_name", "idfm_datamarts")
        self.user = self.config["api"].get("db_user", "youcef")
        self.password = self.config["api"].get("db_password", None) or None

        self.conn = None

    def connect(self):
        try:
            kwargs = {
                "host": self.host,
                "port": self.port,
                "database": self.dbname,
                "user": self.user,
            }
            if self.password:
                kwargs["password"] = self.password
            self.conn = psycopg2.connect(**kwargs)
        except psycopg2.Error as e:
            raise Exception(f"Erreur de connexion PostgreSQL : {e}")

    def disconnect(self):
        if self.conn:
            self.conn.close()

    def query(self, sql: str, params: tuple = None):
        if not self.conn:
            self.connect()
        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()
        except psycopg2.Error as e:
            raise Exception(f"Erreur d'execution : {e}")

    def query_count(self, sql: str, params: tuple = None) -> int:
        if not self.conn:
            self.connect()
        try:
            count_sql = f"SELECT COUNT(*) as cnt FROM ({sql}) as subquery"
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(count_sql, params or ())
                result = cur.fetchone()
                return result["cnt"]
        except psycopg2.Error as e:
            raise Exception(f"Erreur de comptage : {e}")

    def query_paginated(self, sql: str, page: int = 1, page_size: int = 100, params: tuple = None):
        offset = (page - 1) * page_size
        paginated_sql = f"{sql} LIMIT %s OFFSET %s"
        new_params = (params or ()) + (page_size, offset)
        data = self.query(paginated_sql, new_params)
        total = self.query_count(sql, params)
        total_pages = (total + page_size - 1) // page_size
        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    def query_raw(self, sql: str, params: tuple = None):
        return self.query(sql, params)
