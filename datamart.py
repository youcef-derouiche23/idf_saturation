# -*- coding: utf-8 -*-
"""
datamart.py - Création des 4 datamarts PostgreSQL (couche Gold)

Datamarts :
  1. dm_frequentation_par_station_ligne : Fréquentation par station/ligne/heure
  2. dm_regularite_par_ligne : Régularité inter-lignes
  3. dm_evolution_frequentation : Tendances temporelles
  4. dm_saturation_ml : Features pour modèle ML prédictif

Lancement (depuis le container spark-master) :
    spark-submit --master local[*] datamart.py --config config/config.ini
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


# =====================================================
# LOGGING
# =====================================================

def setup_logger(log_dir):
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "datamart.txt")

    logger = logging.getLogger("datamart")
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
    parser = argparse.ArgumentParser(description="Datamart - creation des datamarts PostgreSQL")
    parser.add_argument("--config", required=True, help="Chemin vers config.ini")
    return parser.parse_args()


# =====================================================
# CHARGEMENT TABLE SILVER
# =====================================================

def load_silver_data(spark, logger, config):
    """Charge la table silver enrichie depuis Hive"""
    logger.info("=" * 60)
    logger.info("CHARGEMENT TABLE SILVER")
    logger.info("=" * 60)

    try:
        db = config["hive"]["database"]
        table = config["hive"]["table_validations"]
        df = spark.sql(f"SELECT * FROM {db}.{table}")

        logger.info(f"Table chargée : {df.count()} lignes")
        logger.info(f"Colonnes : {df.columns}")

        return df

    except Exception as e:
        logger.error(f"✗ Erreur lors du chargement : {e}")
        raise


# =====================================================
# DATAMART 1 : FREQUENTATION PAR STATION/LIGNE
# =====================================================

def create_dm_frequentation(spark, logger, df, config):
    """
    DM1 : Fréquentation par station, ligne, heure, jour
    Colonnes : ligne, id_station, nom_station, heure, jour_semaine, nb_validations, rank_station_par_ligne
    """
    logger.info("=" * 60)
    logger.info("DATAMART 1 : FRÉQUENTATION PAR STATION/LIGNE")
    logger.info("=" * 60)

    try:
        dm1 = df.select(
            F.col("ligne"),
            F.col("id_station"),
            F.col("nom_station"),
            F.col("heure"),
            F.col("jour_semaine"),
            F.col("jour_nom"),
            F.col("nb_validations"),
            F.col("rank_station_par_ligne"),
            F.col("date"),
            F.current_timestamp().alias("load_timestamp")
        ).where(F.col("rank_station_par_ligne").isNotNull())

        dm1 = dm1.groupBy("ligne", "id_station", "nom_station", "heure", "jour_semaine", "jour_nom") \
            .agg(
                F.avg("nb_validations").alias("nb_validations_avg"),
                F.max("nb_validations").alias("nb_validations_max"),
                F.min("nb_validations").alias("nb_validations_min"),
                F.count("*").alias("nb_observations")
            ) \
            .orderBy(F.desc("nb_validations_avg"))

        logger.info(f"DM1 : {dm1.count()} lignes")
        return dm1

    except Exception as e:
        logger.error(f"✗ Erreur lors de la création du DM1 : {e}")
        raise


# =====================================================
# DATAMART 2 : REGULARITE PAR LIGNE
# =====================================================

def create_dm_regularite(spark, logger, df, config):
    """
    DM2 : Régularité des lignes
    Colonnes : date, ligne, taux_ponctualite, nb_retards, delai_moyen, rang_regularite
    """
    logger.info("=" * 60)
    logger.info("DATAMART 2 : RÉGULARITÉ PAR LIGNE")
    logger.info("=" * 60)

    try:
        dm2 = df.select(
            F.col("date"),
            F.col("ligne"),
            F.col("taux_ponctualite"),
            F.col("nb_retards"),
            F.col("delai_moyen_minutes")
        ).where(F.col("taux_ponctualite").isNotNull())

        # Agrégation par ligne et date
        dm2 = dm2.groupBy("date", "ligne") \
            .agg(
                F.avg("taux_ponctualite").alias("taux_ponctualite_avg"),
                F.sum("nb_retards").alias("nb_retards_total"),
                F.avg("delai_moyen_minutes").alias("delai_moyen")
            )

        # Ranking par taux de ponctualité
        w_rank = Window.partitionBy("date").orderBy(F.asc("taux_ponctualite_avg"))
        dm2 = dm2.withColumn("rang_regularite", F.rank().over(w_rank))

        dm2 = dm2.withColumn("load_timestamp", F.current_timestamp())

        logger.info(f"DM2 : {dm2.count()} lignes")
        return dm2

    except Exception as e:
        logger.error(f"✗ Erreur lors de la création du DM2 : {e}")
        raise


# =====================================================
# DATAMART 3 : EVOLUTION TEMPORELLE
# =====================================================

def create_dm_evolution(spark, logger, df, config):
    """
    DM3 : Évolution temporelle fréquentation
    Colonnes : date, jour_semaine, periode_vacances, ligne, id_station, nb_validations_cumul, evolution_vs_semaine_precedente
    """
    logger.info("=" * 60)
    logger.info("DATAMART 3 : ÉVOLUTION TEMPORELLE")
    logger.info("=" * 60)

    try:
        dm3 = df.select(
            F.col("date"),
            F.col("jour_semaine"),
            F.col("jour_nom"),
            F.col("est_vacances"),
            F.col("ligne"),
            F.col("id_station"),
            F.col("nom_station"),
            F.col("nb_validations"),
            F.col("evolution_pct")
        )

        # Agrégation par date, station, ligne
        dm3 = dm3.groupBy("date", "jour_semaine", "jour_nom", "est_vacances", "ligne", "id_station", "nom_station") \
            .agg(
                F.sum("nb_validations").alias("nb_validations_cumul"),
                F.avg("evolution_pct").alias("evolution_vs_semaine_precedente_pct")
            )

        dm3 = dm3.orderBy(F.asc("date"), F.asc("ligne"))
        dm3 = dm3.withColumn("load_timestamp", F.current_timestamp())

        logger.info(f"DM3 : {dm3.count()} lignes")
        return dm3

    except Exception as e:
        logger.error(f"✗ Erreur lors de la création du DM3 : {e}")
        raise


# =====================================================
# DATAMART 4 : SATURATION ML (Features pour prédiction)
# =====================================================

def create_dm_saturation_ml(spark, logger, df, config):
    """
    DM4 : Datamart pour ML - Prédiction de saturation
    Colonnes : date, heure, ligne, id_station, nb_validations, taux_ponctualite,
               jour_semaine, is_vacances, jour_ferie, est_saturation (label)
    """
    logger.info("=" * 60)
    logger.info("DATAMART 4 : SATURATION ML")
    logger.info("=" * 60)

    try:
        saturation_threshold = int(config["thresholds"]["saturation_threshold"])

        dm4 = df.select(
            F.col("date"),
            F.col("heure"),
            F.col("ligne"),
            F.col("id_station"),
            F.col("nom_station"),
            F.col("nb_validations"),
            F.col("taux_ponctualite"),
            F.col("jour_semaine"),
            F.col("jour_nom"),
            F.col("est_vacances").alias("is_vacances"),
            F.col("rank_station_par_ligne")
        )

        # Création du label : saturation = 1 si nb_validations > seuil, 0 sinon
        dm4 = dm4.withColumn(
            "est_saturation",
            F.when(F.col("nb_validations") > saturation_threshold, 1).otherwise(0)
        )

        # Détection jour férié (simplifié)
        dm4 = dm4.withColumn(
            "jour_ferie",
            F.when(F.dayofyear(F.col("date")).isin(1, 365), 1).otherwise(0)  # À améliorer avec liste complète
        )

        dm4 = dm4.withColumn("load_timestamp", F.current_timestamp())

        # Sélection des features pertinentes
        dm4 = dm4.select(
            "date", "heure", "ligne", "id_station", "nom_station",
            "nb_validations", "taux_ponctualite", "jour_semaine", "jour_nom",
            "is_vacances", "jour_ferie", "rank_station_par_ligne",
            "est_saturation", "load_timestamp"
        )

        logger.info(f"DM4 : {dm4.count()} lignes")
        logger.info(f"Répartition saturation : {dm4.select('est_saturation').groupBy('est_saturation').count().collect()}")

        return dm4

    except Exception as e:
        logger.error(f"✗ Erreur lors de la création du DM4 : {e}")
        raise


# =====================================================
# ÉCRITURE DES DATAMARTS DANS POSTGRESQL
# =====================================================

def write_to_postgres(df, table_name, logger, config):
    """Écrit un dataframe dans PostgreSQL"""
    try:
        jdbc_url = config["postgres"]["jdbc_url"]
        jdbc_driver = config["postgres"]["jdbc_driver_path"]
        db_user = config["postgres"]["user"]
        db_pass = config["postgres"]["password"]

        logger.info(f"Écriture table PostgreSQL : {table_name}")

        df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", table_name) \
            .option("user", db_user) \
            .option("password", db_pass) \
            .option("driver", "org.postgresql.Driver") \
            .mode("overwrite") \
            .save()

        logger.info(f"✓ {table_name} écrite avec succès")

    except Exception as e:
        logger.error(f"✗ Erreur lors de l'écriture de {table_name} : {e}")
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
        logger.info("🚀 DÉMARRAGE DATAMART")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        spark = SparkSession.builder \
            .appName(config["spark"]["app_name_datamart"]) \
            .master(config["spark"]["master"]) \
            .config("spark.jars", config["postgres"]["jdbc_driver_path"]) \
            .enableHiveSupport() \
            .getOrCreate()

        logger.info("✓ SparkSession créée")

        # Chargement données silver
        df_silver = load_silver_data(spark, logger, config)

        # Création des 4 datamarts
        dm1 = create_dm_frequentation(spark, logger, df_silver, config)
        dm2 = create_dm_regularite(spark, logger, df_silver, config)
        dm3 = create_dm_evolution(spark, logger, df_silver, config)
        dm4 = create_dm_saturation_ml(spark, logger, df_silver, config)

        # Écriture dans PostgreSQL
        write_to_postgres(dm1, "dm_frequentation_par_station_ligne", logger, config)
        write_to_postgres(dm2, "dm_regularite_par_ligne", logger, config)
        write_to_postgres(dm3, "dm_evolution_frequentation", logger, config)
        write_to_postgres(dm4, "dm_saturation_ml", logger, config)

        spark.stop()
        logger.info("✓ SparkSession fermée")
        logger.info("🏁 DATAMART TERMINÉ AVEC SUCCÈS")

    except Exception as e:
        logger.error(f"🔥 ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
