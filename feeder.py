# -*- coding: utf-8 -*-
"""
feeder.py - Ingestion des données brutes vers HDFS/Parquet (couche Raw)

Sources :
  1. validations_2025.csv - Validations réseau ferré par heure/station/ligne
  2. stations_referentiel.csv - Référentiel des stations (ID, nom, ligne, zone)
  3. regularite_lignes.csv - Régularité des lignes (taux ponctualité, retards)

Lancement (depuis le container spark-master) :
    spark-submit --master local[*] feeder.py --config config/config.ini
"""

import argparse
import configparser
import logging
import os
import sys
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


# =====================================================
# LOGGING
# =====================================================

def setup_logger(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "feeder.txt")

    logger = logging.getLogger("feeder")
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
    parser = argparse.ArgumentParser(description="Feeder - ingestion CSV vers HDFS Parquet")
    parser.add_argument("--config", required=True, help="Chemin vers config.ini")
    return parser.parse_args()


# =====================================================
# INGESTION DES VALIDATIONS
# =====================================================

def ingest_validations(spark, logger, config):
    """
    Ingère les validations réseau ferré depuis le fichier real
    Colonnes source : code_stif_trns, code_stif_res, code_stif_arret, id_zdc, libelle_arret, cat_jour, trnc_horr_60, pourcentage_validations
    """
    logger.info("=" * 60)
    logger.info("INGESTION : Validations réseau ferré")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["validations_csv_path"]
        hdfs_path = config["hdfs"]["raw_validations_path"]

        logger.info(f"Lecture CSV depuis : {csv_path}")
        df_validations = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(csv_path)

        logger.info(f"Nombre de lignes : {df_validations.count()}")
        logger.info(f"Colonnes : {df_validations.columns}")

        # Nettoyage basique
        df_validations = df_validations.dropna()
        
        # Renommer les colonnes pour homogénéité
        df_validations = df_validations.select(
            F.col("code_stif_trns").alias("ligne"),
            F.col("code_stif_arret").alias("id_station"),
            F.col("libelle_arret").alias("nom_station"),
            F.col("trnc_horr_60").alias("heure"),
            F.col("pourcentage_validations").alias("pct_validations"),
            F.col("cat_jour").alias("type_jour")
        )

        # Écriture en Parquet sur HDFS
        logger.info(f"Écriture Parquet vers : {hdfs_path}")
        df_validations.write.mode("overwrite").parquet(hdfs_path)

        logger.info("✓ Validations ingérées avec succès")
        return df_validations

    except Exception as e:
        logger.error(f"✗ Erreur lors de l'ingestion des validations : {e}")
        raise


# =====================================================
# INGESTION DU REFERENTIEL STATIONS
# =====================================================

def ingest_stations(spark, logger, config):
    """
    Ingère le référentiel des stations (arrets.csv)
    Colonnes : ArRId, ArRName, ArRTown, ArRFareZone, ArRAccessibility, ArRGeopoint
    """
    logger.info("=" * 60)
    logger.info("INGESTION : Référentiel des stations")
    logger.info("=" * 60)

    try:
        csv_path = config["local"]["stations_csv_path"]
        hdfs_path = config["hdfs"]["raw_stations_path"]

        logger.info(f"Lecture CSV depuis : {csv_path}")
        df_stations = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(csv_path)

        logger.info(f"Nombre de lignes : {df_stations.count()}")
        logger.info(f"Colonnes : {df_stations.columns}")

        # Sélectionner et renommer les colonnes utiles
        df_stations = df_stations.select(
            F.col("ArRId").alias("id_station"),
            F.col("ArRName").alias("nom_station"),
            F.col("ArRTown").alias("ville"),
            F.col("ArRFareZone").alias("zone_tarifaire"),
            F.col("ArRAccessibility").alias("accessibilite"),
            F.col("ArRGeopoint").alias("localisation")
        )

        df_stations = df_stations.dropna(subset=["id_station"])

        logger.info(f"Écriture Parquet vers : {hdfs_path}")
        df_stations.write.mode("overwrite").parquet(hdfs_path)

        logger.info("✓ Référentiel des stations ingéré avec succès")
        return df_stations

    except Exception as e:
        logger.error(f"✗ Erreur lors de l'ingestion du référentiel : {e}")
        raise


# =====================================================
# INGESTION DE LA REGULARITE DES LIGNES
# =====================================================

def ingest_regularite(spark, logger, config):
    """
    Ingère la régularité des lignes depuis les fichiers CSV
    Combine histo-validations-reseau-ferre.csv et ponctualite-mensuelle-transilien.csv
    """
    logger.info("=" * 60)
    logger.info("INGESTION : Régularité des lignes")
    logger.info("=" * 60)

    try:
        regularite_csv = config["local"]["regularite_csv_path"]
        ponctualite_csv = config["local"]["ponctualite_csv_path"]
        hdfs_path = config["hdfs"]["raw_regularite_path"]

        logger.info(f"Lecture CSV historique : {regularite_csv}")
        df_regularite_histo = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(regularite_csv)
        
        logger.info(f"Lecture CSV ponctualité : {ponctualite_csv}")
        df_ponctualite = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(ponctualite_csv)

        logger.info(f"Historique : {df_regularite_histo.count()} lignes - Colonnes : {df_regularite_histo.columns}")
        logger.info(f"Ponctualité : {df_ponctualite.count()} lignes - Colonnes : {df_ponctualite.columns}")

        # Traiter la ponctualité
        df_ponctualite = df_ponctualite.select(
            F.col("Date").alias("date"),
            F.col("Ligne").alias("ligne"),
            F.col("Nom de la ligne").alias("nom_ligne"),
            F.col("Taux de ponctualité").alias("taux_ponctualite"),
            F.col("Nombre de voyageurs à l'heure pour un voyageur en retard").alias("ratio_voyageurs_retard")
        )
        
        # Union avec historique (si structure compatible)
        df_regularite = df_ponctualite.dropna(subset=["ligne"])

        logger.info(f"Total après nettoyage : {df_regularite.count()} lignes")
        logger.info(f"Écriture Parquet vers : {hdfs_path}")
        df_regularite.write.mode("overwrite").parquet(hdfs_path)

        logger.info("✓ Régularité des lignes ingérée avec succès")
        return df_regularite

    except Exception as e:
        logger.error(f"✗ Erreur lors de l'ingestion de la régularité : {e}")
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
        logger.info("🚀 DÉMARRAGE FEEDER")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Initialiser SparkSession
        spark = SparkSession.builder \
            .appName(config["spark"]["app_name_feeder"]) \
            .master(config["spark"]["master"]) \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .getOrCreate()

        logger.info("✓ SparkSession créée")

        # Ingérer les 3 sources de données
        ingest_validations(spark, logger, config)
        ingest_stations(spark, logger, config)
        ingest_regularite(spark, logger, config)

        spark.stop()
        logger.info("✓ SparkSession fermée")
        logger.info("🏁 FEEDER TERMINÉ AVEC SUCCÈS")

    except Exception as e:
        logger.error(f"🔥 ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
