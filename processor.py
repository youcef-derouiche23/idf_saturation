# -*- coding: utf-8 -*-
"""
processor.py - Transformation couche Silver (nettoyage, jointures, agrégations, window functions)

Transformations :
  1. Jointures : validations ↔ stations (id_station) ↔ régularité (date + ligne)
  2. Agrégations : SUM validations, AVG taux ponctualité, COUNT stations saturées
  3. Window Functions : RANK(), LAG(), ROW_NUMBER() sur fréquentation/régularité

Lancement (depuis le container spark-master) :
    spark-submit --master local[*] processor.py --config config/config.ini
"""

import argparse
import configparser
import logging
import os
import sys
from datetime import datetime

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import FloatType, IntegerType


# =====================================================
# LOGGING
# =====================================================

def setup_logger(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "processor.txt")

    logger = logging.getLogger("processor")
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
    parser = argparse.ArgumentParser(description="Processor - nettoyage et enrichissement vers silver")
    parser.add_argument("--config", required=True, help="Chemin vers config.ini")
    return parser.parse_args()


# =====================================================
# CHARGEMENT DES DONNEES RAW
# =====================================================

def load_raw_data(spark, logger, config):
    """Charge les 3 sources depuis HDFS/Parquet"""
    logger.info("=" * 60)
    logger.info("CHARGEMENT DONNÉES RAW")
    logger.info("=" * 60)

    try:
        df_validations = spark.read.parquet(config["hdfs"]["raw_validations_path"])
        df_stations = spark.read.parquet(config["hdfs"]["raw_stations_path"])
        df_regularite = spark.read.parquet(config["hdfs"]["raw_regularite_path"])

        logger.info(f"Validations : {df_validations.count()} lignes")
        logger.info(f"Stations : {df_stations.count()} lignes")
        logger.info(f"Régularité : {df_regularite.count()} lignes")

        return df_validations, df_stations, df_regularite

    except Exception as e:
        logger.error(f"✗ Erreur lors du chargement : {e}")
        raise


# =====================================================
# JOINTURES
# =====================================================

def join_data(spark, logger, df_validations, df_stations, df_regularite):
    """
    Effectue les jointures :
      validations ↔ stations (id_station)
      result ↔ régularité (date + ligne)
    """
    logger.info("=" * 60)
    logger.info("JOINTURES")
    logger.info("=" * 60)

    try:
        # Jointure 1 : validations + stations
        df_joined = df_validations.join(
            df_stations,
            on="id_station",
            how="left"
        )

        logger.info(f"Après jointure avec stations : {df_joined.count()} lignes")

        # Jointure 2 : result + régularité (sur date + ligne)
        df_joined = df_joined.join(
            df_regularite,
            on=["date", "ligne"],
            how="left"
        )

        logger.info(f"Après jointure avec régularité : {df_joined.count()} lignes")

        return df_joined

    except Exception as e:
        logger.error(f"✗ Erreur lors des jointures : {e}")
        raise


# =====================================================
# AGRÉGATIONS ET FEATURES
# =====================================================

def aggregate_and_enrich(spark, logger, df_joined, config):
    """
    Agrégations et enrichissement :
      - Détection jour de semaine
      - Détection période de vacances
      - Agrégation par station/ligne/heure
      - Ranking des stations saturées
    """
    logger.info("=" * 60)
    logger.info("AGRÉGATIONS ET ENRICHISSEMENT")
    logger.info("=" * 60)

    try:
        # Conversion date en timestamp
        df_joined = df_joined.withColumn("date", F.to_date(F.col("date")))

        # Jour de la semaine (1=lundi, 7=dimanche)
        df_joined = df_joined.withColumn("jour_semaine", F.dayofweek(F.col("date")))

        # Noms des jours
        jour_names = {1: "Dimanche", 2: "Lundi", 3: "Mardi", 4: "Mercredi", 5: "Jeudi", 6: "Vendredi", 7: "Samedi"}
        df_joined = df_joined.withColumn(
            "jour_nom",
            F.when(F.col("jour_semaine") == 1, "Dimanche")
             .when(F.col("jour_semaine") == 2, "Lundi")
             .when(F.col("jour_semaine") == 3, "Mardi")
             .when(F.col("jour_semaine") == 4, "Mercredi")
             .when(F.col("jour_semaine") == 5, "Jeudi")
             .when(F.col("jour_semaine") == 6, "Vendredi")
             .when(F.col("jour_semaine") == 7, "Samedi")
        )

        # Détection période de vacances scolaires (simplifié)
        # Vacances d'été : juillet-août, Noël : décembre 20-31, février, avril
        df_joined = df_joined.withColumn(
            "est_vacances",
            F.when(
                (F.month(F.col("date")).isin(7, 8)) |
                ((F.month(F.col("date")) == 12) & (F.dayofmonth(F.col("date")) >= 20)) |
                (F.month(F.col("date")).isin(2, 4)),
                1
            ).otherwise(0)
        )

        logger.info("✓ Enrichissement complété")
        return df_joined

    except Exception as e:
        logger.error(f"✗ Erreur lors de l'enrichissement : {e}")
        raise


# =====================================================
# WINDOW FUNCTIONS
# =====================================================

def apply_window_functions(spark, logger, df_enriched):
    """
    Applique les window functions :
      - RANK() : stations les plus fréquentées par ligne
      - LAG() : évolution semaine après semaine
      - ROW_NUMBER() : classement par créneau
    """
    logger.info("=" * 60)
    logger.info("WINDOW FUNCTIONS")
    logger.info("=" * 60)

    try:
        # Window 1 : Ranking des stations par ligne et heure
        w_rank = Window.partitionBy("ligne", "heure").orderBy(F.desc("nb_validations"))
        df_enriched = df_enriched.withColumn(
            "rank_station_par_ligne",
            F.rank().over(w_rank)
        )

        # Window 2 : Évolution par rapport à la semaine précédente (LAG)
        w_lag = Window.partitionBy("id_station", "heure").orderBy(F.col("date"))
        df_enriched = df_enriched.withColumn(
            "nb_validations_semaine_precedente",
            F.lag(F.col("nb_validations"), 7).over(w_lag)
        )

        # Calcul du pourcentage d'évolution
        df_enriched = df_enriched.withColumn(
            "evolution_pct",
            F.when(
                F.col("nb_validations_semaine_precedente") != 0,
                ((F.col("nb_validations") - F.col("nb_validations_semaine_precedente")) /
                 F.col("nb_validations_semaine_precedente") * 100)
            ).otherwise(0)
        )

        # Window 3 : ROW_NUMBER pour classement temporel
        w_row = Window.partitionBy("ligne", "id_station").orderBy(F.col("date"), F.col("heure"))
        df_enriched = df_enriched.withColumn(
            "row_num_temps",
            F.row_number().over(w_row)
        )

        logger.info("✓ Window functions appliquées")
        return df_enriched

    except Exception as e:
        logger.error(f"✗ Erreur lors de l'application des window functions : {e}")
        raise


# =====================================================
# CREATION DES TABLES HIVE SILVER
# =====================================================

def create_hive_tables(spark, logger, df_enriched, config):
    """Crée/met à jour les tables Hive dans la couche Silver"""
    logger.info("=" * 60)
    logger.info("CRÉATION TABLES HIVE SILVER")
    logger.info("=" * 60)

    try:
        db = config["hive"]["database"]
        table = config["hive"]["table_validations"]

        logger.info(f"Création table : {db}.{table}")

        # Créer database si nécessaire
        spark.sql(f"CREATE DATABASE IF NOT EXISTS {db}")

        # Écrire la table Hive (mode overwrite)
        df_enriched.write.mode("overwrite").option("path", f"{config['hdfs']['silver_path']}/{table}") \
            .saveAsTable(f"{db}.{table}")

        # Vérifier la création
        spark.sql(f"DESCRIBE TABLE {db}.{table}").show(truncate=False)

        logger.info("✓ Table Hive créée avec succès")

    except Exception as e:
        logger.error(f"✗ Erreur lors de la création des tables Hive : {e}")
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
        logger.info("🚀 DÉMARRAGE PROCESSOR")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        spark = SparkSession.builder \
            .appName(config["spark"]["app_name_processor"]) \
            .master(config["spark"]["master"]) \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .enableHiveSupport() \
            .getOrCreate()

        logger.info("✓ SparkSession créée")

        # Pipeline complet
        df_val, df_sta, df_reg = load_raw_data(spark, logger, config)
        df_joined = join_data(spark, logger, df_val, df_sta, df_reg)
        df_enriched = aggregate_and_enrich(spark, logger, df_joined, config)
        df_enriched = apply_window_functions(spark, logger, df_enriched)
        create_hive_tables(spark, logger, df_enriched, config)

        spark.stop()
        logger.info("✓ SparkSession fermée")
        logger.info("🏁 PROCESSOR TERMINÉ AVEC SUCCÈS")

    except Exception as e:
        logger.error(f"🔥 ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
