# -*- coding: utf-8 -*-
"""
database.py - Gestion de la connexion PostgreSQL
"""

import configparser
import os

import psycopg2
from psycopg2.extras import RealDictCursor


class Database:
    """Classe de gestion de la connexion PostgreSQL"""

    def __init__(self, config_path: str):
        """
        Initialise la connexion depuis config.ini

        Args:
            config_path: Chemin vers le fichier config.ini
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        self.host = self.config["api"].get("db_host", "localhost")
        self.port = int(self.config["api"].get("db_port", 5433))
        self.dbname = self.config["api"].get("db_name", "idfm_datamarts")
        self.user = self.config["api"].get("db_user", "idfm_user")
        self.password = self.config["api"].get("db_password", "idfm_pass")

        self.conn = None

    def connect(self):
        """Établit la connexion à PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.dbname,
                user=self.user,
                password=self.password,
            )
        except psycopg2.Error as e:
            raise Exception(f"Erreur de connexion PostgreSQL : {e}")

    def disconnect(self):
        """Ferme la connexion"""
        if self.conn:
            self.conn.close()

    def query(self, sql: str, params: tuple = None):
        """
        Exécute une requête SELECT

        Args:
            sql: Requête SQL
            params: Paramètres de la requête

        Returns:
            Liste de dictionnaires
        """
        if not self.conn:
            self.connect()

        try:
            with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, params or ())
                return cur.fetchall()
        except psycopg2.Error as e:
            raise Exception(f"Erreur d'exécution : {e}")

    def query_count(self, sql: str, params: tuple = None) -> int:
        """
        Retourne le nombre de lignes pour une requête

        Args:
            sql: Requête SQL
            params: Paramètres

        Returns:
            Nombre de lignes
        """
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
        """
        Exécute une requête avec pagination

        Args:
            sql: Requête SQL (sans ORDER BY ou LIMIT)
            page: Numéro de page (commence à 1)
            page_size: Nombre de lignes par page
            params: Paramètres

        Returns:
            (data, total, page, page_size, total_pages)
        """
        # Calcul de l'offset
        offset = (page - 1) * page_size

        # Requête avec LIMIT et OFFSET
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
        """
        Exécute une requête SELECT brute sans pagination

        Args:
            sql: Requête SQL
            params: Paramètres

        Returns:
            Liste de dictionnaires
        """
        return self.query(sql, params)
