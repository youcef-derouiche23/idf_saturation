#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
data_loader.py - Chargement local des CSV dans la base PostgreSQL
Version simplifiée pour environnement local (sans Spark/HDFS)

Utilisation :
    python data_loader.py --config config/config.ini
"""

import argparse
import configparser
import logging
import os
import sys
from datetime import datetime

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch


# =====================================================
# LOGGING
# =====================================================

def setup_logger(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "data_loader.txt")

    logger = logging.getLogger("data_loader")
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# =====================================================
# ARGUMENTS
# =====================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Data Loader - Charge les CSV locaux en PostgreSQL")
    parser.add_argument("--config", required=True, help="Chemin vers config.ini")
    return parser.parse_args()


# =====================================================
# CONNEXION DATABASE
# =====================================================

def get_db_connection(config):
    """Établit la connexion PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=config["api"]["db_host"],
            port=config["api"]["db_port"],
            database=config["api"]["db_name"],
            user=config["api"]["db_user"],
            password=config["api"]["db_password"]
        )
        return conn
    except Exception as e:
        raise Exception(f"Erreur de connexion DB : {e}")


# =====================================================
# CRÉATION TABLES
# =====================================================

def create_tables(conn, logger):
    """Crée les tables si elles n'existent pas"""
    logger.info("=" * 60)
    logger.info("CRÉATION DES TABLES")
    logger.info("=" * 60)

    cursor = conn.cursor()
    
    try:
        # Table stations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stations (
                id_station INTEGER PRIMARY KEY,
                nom_station VARCHAR(255),
                ville VARCHAR(255),
                zone_tarifaire VARCHAR(10),
                accessibilite VARCHAR(50),
                localisation VARCHAR(255)
            );
        """)
        logger.info("✓ Table stations créée/existe")

        # Table validations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validations (
                id SERIAL PRIMARY KEY,
                ligne VARCHAR(50),
                id_station INTEGER REFERENCES stations(id_station),
                nom_station VARCHAR(255),
                heure VARCHAR(10),
                pct_validations FLOAT,
                type_jour VARCHAR(10),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        logger.info("✓ Table validations créée/existe")

        # Table regularite
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS regularite (
                id SERIAL PRIMARY KEY,
                date DATE,
                ligne VARCHAR(50),
                nom_ligne VARCHAR(255),
                taux_ponctualite FLOAT,
                ratio_voyageurs_retard FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        logger.info("✓ Table regularite créée/existe")

        conn.commit()

    except Exception as e:
        logger.error(f"✗ Erreur création tables : {e}")
        conn.rollback()
        raise


# =====================================================
# CHARGEMENT STATIONS
# =====================================================

def load_stations(config, logger, conn):
    """Charge les stations depuis arrets.csv"""
    logger.info("=" * 60)
    logger.info("CHARGEMENT : STATIONS")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["stations_csv_path"]
        logger.info(f"Lecture : {csv_path}")
        
        df = pd.read_csv(csv_path, delimiter=";")
        logger.info(f"Lignes lues : {len(df)}")
        
        # Sélectionner et nettoyer
        df = df[["ArRId", "ArRName", "ArRTown", "ArRFareZone", "ArRAccessibility", "ArRGeopoint"]].copy()
        df.columns = ["id_station", "nom_station", "ville", "zone_tarifaire", "accessibilite", "localisation"]
        df = df.dropna(subset=["id_station"])
        
        # Convertir id_station en entier
        df["id_station"] = pd.to_numeric(df["id_station"], errors="coerce").astype("Int64")
        df = df.dropna(subset=["id_station"])
        
        logger.info(f"Lignes après nettoyage : {len(df)}")

        # Insérer en DB
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE stations CASCADE;")
        
        records = [tuple(row) for row in df.values]
        execute_batch(
            cursor,
            """
            INSERT INTO stations (id_station, nom_station, ville, zone_tarifaire, accessibilite, localisation)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_station) DO UPDATE SET
                nom_station = EXCLUDED.nom_station,
                ville = EXCLUDED.ville,
                zone_tarifaire = EXCLUDED.zone_tarifaire
            """,
            records,
            page_size=1000
        )
        
        conn.commit()
        logger.info(f"✓ {cursor.rowcount} stations chargées")

    except Exception as e:
        logger.error(f"✗ Erreur chargement stations : {e}")
        conn.rollback()
        raise


# =====================================================
# CHARGEMENT VALIDATIONS
# =====================================================

def load_validations(config, logger, conn):
    """Charge les validations depuis le CSV"""
    logger.info("=" * 60)
    logger.info("CHARGEMENT : VALIDATIONS")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["validations_csv_path"]
        logger.info(f"Lecture : {csv_path}")
        
        df = pd.read_csv(csv_path, delimiter=";")
        logger.info(f"Lignes lues : {len(df)}")
        
        # Sélectionner et renommer
        df = df[["code_stif_trns", "code_stif_arret", "libelle_arret", "trnc_horr_60", "pourcentage_validations", "cat_jour"]].copy()
        df.columns = ["ligne", "id_station", "nom_station", "heure", "pct_validations", "type_jour"]
        df = df.dropna()
        
        # Convertir types
        df["id_station"] = pd.to_numeric(df["id_station"], errors="coerce").astype("Int64")
        df["pct_validations"] = pd.to_numeric(df["pct_validations"], errors="coerce").astype("float")
        df = df.dropna(subset=["id_station", "pct_validations"])
        
        logger.info(f"Lignes après nettoyage : {len(df)}")

        # Insérer en DB
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE validations CASCADE;")
        
        records = [tuple(row) for row in df.values]
        execute_batch(
            cursor,
            """
            INSERT INTO validations (ligne, id_station, nom_station, heure, pct_validations, type_jour)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            records,
            page_size=1000
        )
        
        conn.commit()
        logger.info(f"✓ {cursor.rowcount} validations chargées")

    except Exception as e:
        logger.error(f"✗ Erreur chargement validations : {e}")
        conn.rollback()
        raise


# =====================================================
# CHARGEMENT REGULARITE
# =====================================================

def load_regularite(config, logger, conn):
    """Charge la régularité depuis le CSV ponctualité"""
    logger.info("=" * 60)
    logger.info("CHARGEMENT : RÉGULARITÉ")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["ponctualite_csv_path"]
        logger.info(f"Lecture : {csv_path}")
        
        df = pd.read_csv(csv_path, delimiter=";")
        logger.info(f"Lignes lues : {len(df)}")
        
        # Sélectionner et renommer
        df = df[["Date", "Ligne", "Nom de la ligne", "Taux de ponctualité", "Nombre de voyageurs à l'heure pour un voyageur en retard"]].copy()
        df.columns = ["date", "ligne", "nom_ligne", "taux_ponctualite", "ratio_voyageurs_retard"]
        df = df.dropna()
        
        # Convertir types
        df["date"] = pd.to_datetime(df["date"], format="%Y-%m", errors="coerce")
        df["taux_ponctualite"] = pd.to_numeric(df["taux_ponctualite"], errors="coerce").astype("float")
        df["ratio_voyageurs_retard"] = pd.to_numeric(df["ratio_voyageurs_retard"], errors="coerce").astype("float")
        df = df.dropna()
        
        logger.info(f"Lignes après nettoyage : {len(df)}")

        # Insérer en DB
        cursor = conn.cursor()
        cursor.execute("TRUNCATE TABLE regularite CASCADE;")
        
        records = [tuple(row) for row in df.values]
        execute_batch(
            cursor,
            """
            INSERT INTO regularite (date, ligne, nom_ligne, taux_ponctualite, ratio_voyageurs_retard)
            VALUES (%s, %s, %s, %s, %s)
            """,
            records,
            page_size=1000
        )
        
        conn.commit()
        logger.info(f"✓ {cursor.rowcount} lignes de régularité chargées")

    except Exception as e:
        logger.error(f"✗ Erreur chargement régularité : {e}")
        conn.rollback()
        raise


# =====================================================
# MAIN
# =====================================================

def main():
    args = parse_args()
    config = configparser.ConfigParser()
    config.read(args.config)

    logger = setup_logger(config["local"]["log_dir"])

    try:
        logger.info("🚀 DÉMARRAGE DATA LOADER")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Connexion DB
        conn = get_db_connection(config)
        logger.info("✓ Connexion PostgreSQL établie")

        # Créer tables
        create_tables(conn, logger)

        # Charger les données
        load_stations(config, logger, conn)
        load_validations(config, logger, conn)
        load_regularite(config, logger, conn)

        conn.close()
        logger.info("✓ Connexion fermée")
        logger.info("🏁 DATA LOADER TERMINÉ AVEC SUCCÈS")

    except Exception as e:
        logger.error(f"🔥 ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
