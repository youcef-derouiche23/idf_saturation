import sys
import typing
sys.modules['typing.io'] = typing
import argparse
import configparser
import logging
import os
os.environ["HADOOP_HOME"] = "C:\\hadoop"
os.environ["PATH"] = "C:\\hadoop\\bin;" + os.environ.get("PATH", "")
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
    logger.info("CHARGEMENT DONNEES RAW")

    try:
        df_validations = spark.read.parquet(config["hdfs"]["raw_validations_path"])
        df_stations = spark.read.parquet(config["hdfs"]["raw_stations_path"])
        df_regularite = spark.read.parquet(config["hdfs"]["raw_regularite_path"])

        logger.info("Application des regles de validation des donnees...")

        df_validations = df_validations.filter(F.col("pct_validations").isNotNull() & (F.col("pct_validations") >= 0))
        df_validations = df_validations.filter(F.col("ligne").isNotNull())
        df_stations = df_stations.filter(F.col("id_station").isNotNull() & F.col("localisation").isNotNull())
        df_regularite = df_regularite.filter((F.col("taux_ponctualite") >= 0) & (F.col("taux_ponctualite") <= 100))
        df_regularite = df_regularite.filter(F.col("date").isNotNull())

        logger.info(f"Validations : {df_validations.count()} lignes")
        logger.info(f"Stations : {df_stations.count()} lignes")
        logger.info(f"Regularite : {df_regularite.count()} lignes")

        return df_validations, df_stations, df_regularite

    except Exception as e:
        logger.error(f"Erreur lors du chargement : {e}")
        raise


# =====================================================
# JOINTURES
# =====================================================

def join_data(spark, logger, df_validations, df_stations, df_regularite):
    df_stations = df_stations.withColumnRenamed("nom_station", "nom_station_ref")
    df_stations = df_stations.drop("year", "month", "day")

    try:
        df_joined = df_validations.join(
            df_stations,
            on="id_station",
            how="left"
        )

        logger.info(f"Apres jointure avec stations : {df_joined.count()} lignes")

        df_joined = df_joined.join(
            df_regularite,
            on=["ligne", "year", "month", "day"],
            how="left"
        )

        logger.info(f"Apres jointure avec regularite : {df_joined.count()} lignes")

        return df_joined

    except Exception as e:
        logger.error(f"Erreur lors des jointures : {e}")
        raise


# =====================================================
# AGRÉGATIONS ET FEATURES
# =====================================================

def aggregate_and_enrich(spark, logger, df_joined, config):
    try:
        df_joined = df_joined.withColumn("date", F.to_date(F.col("date")))
        df_joined = df_joined.withColumn("jour_semaine", F.dayofweek(F.col("date")))

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

        df_joined = df_joined.withColumn(
            "est_vacances",
            F.when(
                (F.month(F.col("date")).isin(7, 8)) |
                ((F.month(F.col("date")) == 12) & (F.dayofmonth(F.col("date")) >= 20)) |
                (F.month(F.col("date")).isin(2, 4)),
                1
            ).otherwise(0)
        )

        logger.info("Enrichissement complete")
        return df_joined

    except Exception as e:
        logger.error(f"Erreur lors de l'enrichissement : {e}")
        raise


# =====================================================
# WINDOW FUNCTIONS
# =====================================================

def apply_window_functions(spark, logger, df_enriched):
    try:
        w_rank = Window.partitionBy("ligne", "heure").orderBy(F.desc("pct_validations"))
        df_enriched = df_enriched.withColumn(
            "rank_station_par_ligne",
            F.rank().over(w_rank)
        )

        w_lag = Window.partitionBy("id_station", "heure").orderBy(F.col("date"))
        df_enriched = df_enriched.withColumn(
            "pct_validations_semaine_precedente",
            F.lag(F.col("pct_validations"), 7).over(w_lag)
        )

        df_enriched = df_enriched.withColumn(
            "evolution_pct",
            F.when(
                F.col("pct_validations_semaine_precedente") != 0,
                ((F.col("pct_validations") - F.col("pct_validations_semaine_precedente")) /
                 F.col("pct_validations_semaine_precedente") * 100)
            ).otherwise(0)
        )

        w_row = Window.partitionBy("ligne", "id_station").orderBy(F.col("date"), F.col("heure"))
        df_enriched = df_enriched.withColumn(
            "row_num_temps",
            F.row_number().over(w_row)
        )

        logger.info("Window functions appliquees")
        return df_enriched

    except Exception as e:
        logger.error(f"Erreur lors de l'application des window functions : {e}")
        raise

# =====================================================
# CREATION DES TABLES HIVE SILVER
# =====================================================

def create_hive_tables(spark, logger, df_enriched, config):
    try:
        db = config["hive"]["database"]
        table = config["hive"]["table_validations"]

        logger.info(f"Creation table : {db}.{table}")

        spark.sql(f"CREATE DATABASE IF NOT EXISTS {db}")

        df_enriched.write.mode("overwrite") \
            .partitionBy("year", "month", "day") \
            .option("path", f"{config['hdfs']['silver_path']}/{table}") \
            .saveAsTable(f"{db}.{table}")

        spark.sql(f"DESCRIBE TABLE {db}.{table}").show(truncate=False)

        logger.info("Table Hive cree avec succes")

    except Exception as e:
        logger.error(f"Erreur lors de la creation des tables Hive : {e}")
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
        logger.info("DEMARRAGE PROCESSOR")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        spark = SparkSession.builder \
            .appName(config["spark"]["app_name_processor"]) \
            .master(config["spark"]["master"]) \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .enableHiveSupport() \
            .getOrCreate()

        logger.info("SparkSession creee")

        # Pipeline complet
        df_val, df_sta, df_reg = load_raw_data(spark, logger, config)
        df_joined = join_data(spark, logger, df_val, df_sta, df_reg)
        df_enriched = aggregate_and_enrich(spark, logger, df_joined, config)
        df_enriched = df_enriched.cache()
        count_lignes = df_enriched.count() # Force l'évaluation et le stockage en cache
        logger.info(f"Donnees mises en cache. Nombre de lignes pretent pour les Window Functions : {count_lignes}")
        df_enriched = apply_window_functions(spark, logger, df_enriched)
        create_hive_tables(spark, logger, df_enriched, config)

        spark.stop()
        logger.info("SparkSession fermee")
        logger.info("PROCESSOR TERMINE AVEC SUCCES")

    except Exception as e:
        logger.error(f"ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
