#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pipeline_local.py - Pipeline complet SANS Spark (pandas + PostgreSQL)
Fonctionne sur macOS ARM64 sans problèmes NumPy

Utilisation :
    python3 pipeline_local.py --config config/config.ini
"""

import argparse
import configparser
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch


# =====================================================
# LOGGING
# =====================================================

def setup_logger(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, f"pipeline_local_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

    logger = logging.getLogger("pipeline_local")
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
    parser = argparse.ArgumentParser(description="Pipeline local (sans Spark) - Pandas + PostgreSQL")
    parser.add_argument("--config", required=True, help="Chemin vers config.ini")
    parser.add_argument("--skip-load", action="store_true", help="Sauter le chargement des données")
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
                id_station INTEGER REFERENCES stations(id_station) ON DELETE SET NULL,
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

        # CREATE DATAMARTS TABLES
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dm_frequentation_par_station_ligne (
                id SERIAL PRIMARY KEY,
                ligne VARCHAR(50),
                id_station INTEGER,
                nom_station VARCHAR(255),
                heure VARCHAR(10),
                jour_semaine VARCHAR(20),
                nb_validations FLOAT,
                rank_station_par_ligne INTEGER
            );
        """)
        logger.info("✓ Table dm_frequentation_par_station_ligne créée/existe")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dm_regularite_par_ligne (
                id SERIAL PRIMARY KEY,
                date DATE,
                ligne VARCHAR(50),
                nom_ligne VARCHAR(255),
                taux_ponctualite FLOAT,
                nb_retards FLOAT,
                delai_moyen_minutes FLOAT,
                rang_regularite INTEGER
            );
        """)
        logger.info("✓ Table dm_regularite_par_ligne créée/existe")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dm_evolution_frequentation (
                id SERIAL PRIMARY KEY,
                date DATE,
                jour_semaine VARCHAR(20),
                periode_vacances VARCHAR(50),
                ligne VARCHAR(50),
                id_station INTEGER,
                nom_station VARCHAR(255),
                nb_validations_cumul FLOAT,
                evolution_vs_semaine_precedente FLOAT
            );
        """)
        logger.info("✓ Table dm_evolution_frequentation créée/existe")

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dm_saturation_ml (
                id SERIAL PRIMARY KEY,
                date DATE,
                heure VARCHAR(10),
                ligne VARCHAR(50),
                id_station INTEGER,
                nom_station VARCHAR(255),
                nb_validations FLOAT,
                taux_ponctualite FLOAT,
                jour_semaine VARCHAR(20),
                is_vacances BOOLEAN,
                jour_ferie BOOLEAN,
                est_saturation BOOLEAN
            );
        """)
        logger.info("✓ Table dm_saturation_ml créée/existe")

        conn.commit()

    except Exception as e:
        logger.error(f"✗ Erreur création tables : {e}")
        conn.rollback()
        raise


# =====================================================
# CHARGEMENT DES DONNÉES
# =====================================================

def load_stations(config, logger, conn):
    """Charge les stations depuis arrets.csv"""
    logger.info("=" * 60)
    logger.info("ÉTAPE 1: CHARGEMENT STATIONS")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["stations_csv_path"]
        logger.info(f"Lecture : {csv_path}")
        
        df = pd.read_csv(csv_path, delimiter=";", encoding="utf-8-sig")
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
            """,
            records,
            page_size=1000
        )
        
        conn.commit()
        logger.info(f"✓ {len(records)} stations chargées")

    except Exception as e:
        logger.error(f"✗ Erreur chargement stations : {e}")
        conn.rollback()
        raise


def load_validations(config, logger, conn):
    """Charge les validations depuis le CSV"""
    logger.info("=" * 60)
    logger.info("ÉTAPE 2: CHARGEMENT VALIDATIONS")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["validations_csv_path"]
        logger.info(f"Lecture : {csv_path}")
        
        df = pd.read_csv(csv_path, delimiter=";", encoding="utf-8-sig")
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
        logger.info(f"✓ {len(records)} validations chargées")

    except Exception as e:
        logger.error(f"✗ Erreur chargement validations : {e}")
        conn.rollback()
        raise


def load_regularite(config, logger, conn):
    """Charge la régularité depuis le CSV ponctualité"""
    logger.info("=" * 60)
    logger.info("ÉTAPE 3: CHARGEMENT RÉGULARITÉ")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["ponctualite_csv_path"]
        logger.info(f"Lecture : {csv_path}")
        
        df = pd.read_csv(csv_path, delimiter=";", encoding="utf-8-sig")
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
        logger.info(f"✓ {len(records)} lignes de régularité chargées")

    except Exception as e:
        logger.error(f"✗ Erreur chargement régularité : {e}")
        conn.rollback()
        raise


# =====================================================
# CRÉATION DES DATAMARTS
# =====================================================

def create_datamarts(logger, conn):
    """Crée les 4 datamarts"""
    logger.info("=" * 60)
    logger.info("CRÉATION DES DATAMARTS")
    logger.info("=" * 60)

    cursor = conn.cursor()

    try:
        # DATAMART 1: Fréquentation par station/ligne
        logger.info("Création DM1: Fréquentation par station/ligne...")
        cursor.execute("""
            TRUNCATE TABLE dm_frequentation_par_station_ligne CASCADE;
            
            INSERT INTO dm_frequentation_par_station_ligne 
            (ligne, id_station, nom_station, heure, jour_semaine, nb_validations, rank_station_par_ligne)
            SELECT 
                v.ligne,
                v.id_station,
                v.nom_station,
                v.heure,
                v.type_jour as jour_semaine,
                AVG(v.pct_validations) as nb_validations,
                ROW_NUMBER() OVER (PARTITION BY v.ligne ORDER BY AVG(v.pct_validations) DESC) as rank_station_par_ligne
            FROM validations v
            GROUP BY v.ligne, v.id_station, v.nom_station, v.heure, v.type_jour
            ORDER BY v.ligne, rank_station_par_ligne;
        """)
        logger.info("✓ DM1 créée")

        # DATAMART 2: Régularité par ligne
        logger.info("Création DM2: Régularité par ligne...")
        cursor.execute("""
            TRUNCATE TABLE dm_regularite_par_ligne CASCADE;
            
            INSERT INTO dm_regularite_par_ligne 
            (date, ligne, nom_ligne, taux_ponctualite, nb_retards, delai_moyen_minutes, rang_regularite)
            SELECT 
                r.date,
                r.ligne,
                r.nom_ligne,
                AVG(r.taux_ponctualite) as taux_ponctualite,
                0 as nb_retards,
                0 as delai_moyen_minutes,
                ROW_NUMBER() OVER (ORDER BY AVG(r.taux_ponctualite) ASC) as rang_regularite
            FROM regularite r
            GROUP BY r.date, r.ligne, r.nom_ligne
            ORDER BY rang_regularite;
        """)
        logger.info("✓ DM2 créée")

        # DATAMART 3: Évolution temporelle
        logger.info("Création DM3: Évolution temporelle...")
        cursor.execute("""
            TRUNCATE TABLE dm_evolution_frequentation CASCADE;
            
            INSERT INTO dm_evolution_frequentation 
            (date, jour_semaine, periode_vacances, ligne, id_station, nom_station, nb_validations_cumul, evolution_vs_semaine_precedente)
            SELECT 
                CURRENT_DATE as date,
                'N/A' as jour_semaine,
                'N/A' as periode_vacances,
                v.ligne,
                v.id_station,
                v.nom_station,
                SUM(v.pct_validations) as nb_validations_cumul,
                0 as evolution_vs_semaine_precedente
            FROM validations v
            GROUP BY v.ligne, v.id_station, v.nom_station
            ORDER BY nb_validations_cumul DESC;
        """)
        logger.info("✓ DM3 créée")

        # DATAMART 4: Features ML
        logger.info("Création DM4: Features ML (saturation)...")
        cursor.execute("""
            TRUNCATE TABLE dm_saturation_ml CASCADE;
            
            INSERT INTO dm_saturation_ml 
            (date, heure, ligne, id_station, nom_station, nb_validations, taux_ponctualite, jour_semaine, is_vacances, jour_ferie, est_saturation)
            SELECT 
                CURRENT_DATE as date,
                v.heure,
                v.ligne,
                v.id_station,
                v.nom_station,
                v.pct_validations as nb_validations,
                COALESCE(AVG(r.taux_ponctualite), 0) as taux_ponctualite,
                v.type_jour as jour_semaine,
                FALSE as is_vacances,
                FALSE as jour_ferie,
                CASE WHEN v.pct_validations > 5.0 THEN TRUE ELSE FALSE END as est_saturation
            FROM validations v
            LEFT JOIN regularite r ON v.ligne = r.ligne
            GROUP BY v.heure, v.ligne, v.id_station, v.nom_station, v.pct_validations, v.type_jour;
        """)
        logger.info("✓ DM4 créée")

        conn.commit()
        logger.info("✓ Tous les datamarts créés avec succès!")

    except Exception as e:
        logger.error(f"✗ Erreur création datamarts : {e}")
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
        logger.info("🚀 DÉMARRAGE PIPELINE LOCAL (PANDAS + PostgreSQL)")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Connexion DB
        conn = get_db_connection(config)
        logger.info("✓ Connexion PostgreSQL établie")

        # Créer tables
        create_tables(conn, logger)

        # Charger les données
        if not args.skip_load:
            load_stations(config, logger, conn)
            load_validations(config, logger, conn)
            load_regularite(config, logger, conn)
        else:
            logger.info("⏭️  Chargement données ignoré (--skip-load)")

        # Créer les datamarts
        create_datamarts(logger, conn)

        conn.close()
        logger.info("✓ Connexion fermée")
        logger.info("🏁 PIPELINE TERMINÉ AVEC SUCCÈS!")
        logger.info("")
        logger.info("📊 Résumé:")
        logger.info("  ✓ Stations chargées et indexées")
        logger.info("  ✓ Validations chargées et pré-traitées")
        logger.info("  ✓ Régularité chargée")
        logger.info("  ✓ 4 Datamarts créés (DM1, DM2, DM3, DM4)")
        logger.info("")
        logger.info("🎯 Prochaines étapes:")
        logger.info("  1. cd api && python -m uvicorn app:app --reload")
        logger.info("  2. streamlit run dashboard/app.py")
        logger.info("  3. Consulter http://localhost:8000/docs")

    except Exception as e:
        logger.error(f"🔥 ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
