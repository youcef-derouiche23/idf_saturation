#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
populate_datamarts.py - Remplissage des datamarts depuis les CSVs

Lancement :
    python3 populate_datamarts.py --config config/config.ini
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

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger("populate_datamarts")

logger = setup_logger()

# =====================================================
# ARGUMENTS
# =====================================================

def parse_args():
    parser = argparse.ArgumentParser(description="Populate datamarts from CSV files")
    parser.add_argument("--config", required=True, help="Path to config.ini")
    return parser.parse_args()

# =====================================================
# CONNEXION DB
# =====================================================

def load_db_config(config_path):
    """Charge la configuration PostgreSQL"""
    config = configparser.ConfigParser()
    config.read(config_path)
    
    return {
        "host": config.get("postgres", "host", fallback="localhost"),
        "port": int(config.get("postgres", "port", fallback="5432")),
        "database": config.get("postgres", "database", fallback="idfm_datamarts"),
        "user": config.get("postgres", "user", fallback="youcef"),
        "password": config.get("postgres", "password", fallback="")
    }

def get_db_connection(db_config):
    """Établit une connexion PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )
        logger.info("✓ Connexion PostgreSQL établie")
        return conn
    except psycopg2.Error as e:
        logger.error(f"✗ Erreur de connexion : {e}")
        raise

# =====================================================
# REMPLISSAGE DES DATAMARTS
# =====================================================

def populate_dm_frequentation(conn, csv_path):
    """Remplit dm_frequentation_par_station_ligne"""
    logger.info("=" * 60)
    logger.info("Remplissage : dm_frequentation_par_station_ligne")
    logger.info("=" * 60)
    
    try:
        df = pd.read_csv(csv_path, sep=";", dtype={
            "code_stif_trns": str,
            "code_stif_arret": str,
            "libelle_arret": str,
            "trnc_horr_60": str,
            "pourcentage_validations": float,
            "cat_jour": str
        })
        
        logger.info(f"Lecture CSV : {len(df)} lignes")
        
        # Grouper par station, ligne, heure
        agg_df = df.groupby([
            "code_stif_arret",  # id_station
            "code_stif_trns",   # ligne
            "libelle_arret",    # nom_station
            "trnc_horr_60"      # heure
        ]).agg({
            "pourcentage_validations": ["mean", "max", "min", "count"]
        }).reset_index()
        
        agg_df.columns = ["id_station", "ligne", "nom_station", "heure", "nb_validations_avg", 
                         "nb_validations_max", "nb_validations_min", "nb_observations"]
        
        # Nettoyer les colonnes
        agg_df["id_station"] = pd.to_numeric(agg_df["id_station"], errors="coerce")
        agg_df["nb_validations_avg"] = agg_df["nb_validations_avg"].fillna(0)
        agg_df["nb_validations_max"] = agg_df["nb_validations_max"].fillna(0)
        agg_df["nb_validations_min"] = agg_df["nb_validations_min"].fillna(0)
        agg_df["nb_observations"] = agg_df["nb_observations"].fillna(0)
        
        cursor = conn.cursor()
        
        # Truncate table
        cursor.execute("TRUNCATE TABLE public.dm_frequentation_par_station_ligne")
        
        # Insert data
        sql = """
        INSERT INTO public.dm_frequentation_par_station_ligne 
        (ligne, id_station, nom_station, heure, nb_validations_avg, nb_validations_max, 
         nb_validations_min, nb_observations, load_timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rows = []
        for idx, row in agg_df.iterrows():
            rows.append((
                str(row["ligne"]),
                int(row["id_station"]) if pd.notna(row["id_station"]) else 0,
                str(row["nom_station"]),
                str(row["heure"]),
                float(row["nb_validations_avg"]),
                float(row["nb_validations_max"]),
                float(row["nb_validations_min"]),
                int(row["nb_observations"]),
                datetime.now()
            ))
        
        execute_batch(cursor, sql, rows, page_size=1000)
        conn.commit()
        
        logger.info(f"✓ {len(rows)} lignes insérées")
        cursor.close()
        
    except Exception as e:
        logger.error(f"✗ Erreur : {e}")
        conn.rollback()
        raise

def populate_dm_saturation_ml(conn, csv_path):
    """Remplit dm_saturation_ml"""
    logger.info("=" * 60)
    logger.info("Remplissage : dm_saturation_ml")
    logger.info("=" * 60)
    
    try:
        df = pd.read_csv(csv_path, sep=";", dtype={
            "code_stif_trns": str,
            "code_stif_arret": str,
            "libelle_arret": str,
            "trnc_horr_60": str,
            "pourcentage_validations": float,
            "cat_jour": str
        })
        
        logger.info(f"Lecture CSV : {len(df)} lignes")
        
        # Créer les features ML
        ml_df = pd.DataFrame({
            "ligne": df["code_stif_trns"],
            "id_station": df["code_stif_arret"],
            "nom_station": df["libelle_arret"],
            "heure": df["trnc_horr_60"],
            "pourcentage_validations": df["pourcentage_validations"],
            "jour_nom": df["cat_jour"]
        })
        
        # Nettoyer les colonnes
        ml_df["id_station"] = pd.to_numeric(ml_df["id_station"], errors="coerce")
        ml_df["pourcentage_validations"] = pd.to_numeric(ml_df["pourcentage_validations"], errors="coerce")
        
        # Créer le label (saturation si > 7%)
        ml_df["est_saturation"] = (ml_df["pourcentage_validations"] > 7).astype(int)
        
        # Ajouter d'autres colonnes
        ml_df["nb_validations"] = ml_df["pourcentage_validations"]
        ml_df["taux_ponctualite"] = None
        ml_df["jour_semaine"] = None
        ml_df["est_vacances"] = None
        ml_df["est_jour_ferie"] = None
        ml_df["rank_saturation"] = None
        
        cursor = conn.cursor()
        
        # Truncate table
        cursor.execute("TRUNCATE TABLE public.dm_saturation_ml")
        
        # Insert data
        sql = """
        INSERT INTO public.dm_saturation_ml 
        (date, heure, ligne, id_station, nom_station, nb_validations, pourcentage_validations,
         taux_ponctualite, jour_semaine, jour_nom, est_vacances, est_jour_ferie, 
         rank_saturation, est_saturation, load_timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        rows = []
        for idx, row in ml_df.iterrows():
            rows.append((
                None,  # date
                str(row["heure"]),
                str(row["ligne"]),
                int(row["id_station"]) if pd.notna(row["id_station"]) else 0,
                str(row["nom_station"]),
                float(row["nb_validations"]) if pd.notna(row["nb_validations"]) else 0,
                float(row["pourcentage_validations"]) if pd.notna(row["pourcentage_validations"]) else 0,
                None,  # taux_ponctualite
                None,  # jour_semaine
                str(row["jour_nom"]),
                None,  # est_vacances
                None,  # est_jour_ferie
                None,  # rank_saturation
                int(row["est_saturation"]),
                datetime.now()
            ))
        
        execute_batch(cursor, sql, rows, page_size=1000)
        conn.commit()
        
        logger.info(f"✓ {len(rows)} lignes insérées")
        cursor.close()
        
    except Exception as e:
        logger.error(f"✗ Erreur : {e}")
        conn.rollback()
        raise

def populate_dm_regularite(conn, csv_path):
    """Remplit dm_regularite_par_ligne depuis regularite_lignes.csv"""
    logger.info("=" * 60)
    logger.info("Remplissage : dm_regularite_par_ligne")
    logger.info("=" * 60)
    
    try:
        if not os.path.exists(csv_path):
            logger.warning(f"⚠️ Fichier {csv_path} non trouvé - table reste vide")
            return
        
        df = pd.read_csv(csv_path, sep=";", dtype={
            "code_stif_trns": str,
            "date": str,
            "nom_ligne": str,
            "regularite_contractuelle": float,
            "ponctualite_contractuelle": float,
            "nombre_trains_prevus": int,
            "nombre_trains_realises": int,
            "retards_moyen_mn": float
        })
        
        logger.info(f"Lecture CSV : {len(df)} lignes")
        
        cursor = conn.cursor()
        
        # Truncate table
        cursor.execute("TRUNCATE TABLE public.dm_regularite_par_ligne")
        
        # Insert data - mapper les colonnes CSV aux colonnes de la table
        sql = """
        INSERT INTO public.dm_regularite_par_ligne 
        (date, ligne, taux_ponctualite, nb_retards, delai_moyen, rang_regularite, load_timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        rows = []
        for idx, row in df.iterrows():
            try:
                rows.append((
                    str(row.get("date", "")),
                    str(row.get("code_stif_trns", "")),  # ligne
                    float(row.get("ponctualite_contractuelle", 0)) / 100,  # taux_ponctualite (en fraction)
                    int(row.get("nombre_trains_prevus", 0)) - int(row.get("nombre_trains_realises", 0)),  # nb_retards
                    float(row.get("retards_moyen_mn", 0)),  # delai_moyen
                    None,  # rang_regularite
                    datetime.now()
                ))
            except Exception as e:
                logger.warning(f"⚠️ Ligne {idx} ignorée : {e}")
                continue
        
        if rows:
            execute_batch(cursor, sql, rows, page_size=1000)
            conn.commit()
            logger.info(f"✓ {len(rows)} lignes insérées")
        else:
            logger.warning("⚠️ Aucune ligne valide")
        
        cursor.close()
        
    except Exception as e:
        logger.error(f"✗ Erreur : {e}")
        conn.rollback()

# =====================================================
# MAIN
# =====================================================

def main():
    args = parse_args()
    
    logger.info("🚀 DÉMARRAGE POPULATION DATAMARTS")
    logger.info(f"Timestamp : {datetime.now()}")
    
    try:
        # Charger configuration
        config = configparser.ConfigParser()
        config.read(args.config)
        
        # Obtenir chemins CSV
        validations_csv = config["local"]["validations_csv_path"]
        regularite_csv = config["local"].get("regularite_csv_path", "")
        
        logger.info(f"CSV Validations : {validations_csv}")
        logger.info(f"CSV Régularité : {regularite_csv}")
        
        # Connexion DB
        db_config = load_db_config(args.config)
        conn = get_db_connection(db_config)
        
        # Remplissage
        populate_dm_frequentation(conn, validations_csv)
        populate_dm_saturation_ml(conn, validations_csv)
        if regularite_csv and os.path.exists(regularite_csv):
            populate_dm_regularite(conn, regularite_csv)
        
        conn.close()
        
        logger.info("=" * 60)
        logger.info("✅ POPULATION DATAMARTS TERMINÉE AVEC SUCCÈS")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"🔥 ERREUR FATALE : {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
