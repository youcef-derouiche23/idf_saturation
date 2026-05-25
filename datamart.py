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
    try:
        df_validations = spark.read.parquet("data/raw/validations")
        df_stations = spark.read.parquet("data/raw/stations")
        df_regularite = spark.read.parquet("data/raw/regularite")

        df_stations = df_stations.withColumnRenamed("nom_station", "nom_station_ref").drop("year", "month", "day")
        df_joined = df_validations.join(df_stations, on="id_station", how="left")
        df_joined = df_joined.join(df_regularite, on=["ligne", "year", "month", "day"], how="left")

        from pyspark.sql.window import Window
        w_rank = Window.partitionBy("ligne", "heure").orderBy(F.desc("pct_validations"))
        df = df_joined.withColumn("rank_station_par_ligne", F.rank().over(w_rank))

        df = df.withColumn("evolution_pct", F.lit(0))
        df = df.withColumn("est_vacances", F.lit(0))
        df = df.withColumn("jour_semaine", F.lit(1))
        df = df.withColumn("jour_nom", F.lit("Lundi"))

        logger.info(f"Table reconstruite : {df.count()} lignes")
        
        return df

    except Exception as e:
        logger.error(f"Erreur lors du chargement : {e}")
        raise


# =====================================================
# DATAMART 1 : FREQUENTATION PAR STATION/LIGNE
# =====================================================

def create_dm_frequentation(spark, logger, df, config):
    try:
        dm1 = df.select(
            F.col("ligne"),
            F.col("id_station"),
            F.col("nom_station"),
            F.col("heure"),
            F.col("jour_semaine"),
            F.col("jour_nom"),
            F.col("pct_validations"),
            F.col("rank_station_par_ligne"),
            F.col("date"),
            F.current_timestamp().alias("load_timestamp")
        ).where(F.col("rank_station_par_ligne").isNotNull())

        dm1 = dm1.groupBy("ligne", "id_station", "nom_station", "heure", "jour_semaine", "jour_nom") \
            .agg(
                F.avg("pct_validations").alias("pct_validations_avg"),
                F.max("pct_validations").alias("pct_validations_max"),
                F.min("pct_validations").alias("pct_validations_min"),
                F.count("*").alias("nb_observations")
            ) \
            .orderBy(F.desc("pct_validations_avg"))

        logger.info(f"DM1 : {dm1.count()} lignes")
        return dm1

    except Exception as e:
        logger.error(f"Erreur lors de la creation du DM1 : {e}")
        raise


# =====================================================
# DATAMART 2 : REGULARITE PAR LIGNE
# =====================================================

def create_dm_regularite(spark, logger, df, config):
    try:
        dm2 = df.select(
            F.col("date"),
            F.col("ligne"),
            F.col("taux_ponctualite"),
            F.col("ratio_voyageurs_retard")
        ).where(F.col("taux_ponctualite").isNotNull())

        dm2 = dm2.groupBy("date", "ligne") \
            .agg(
                F.avg("taux_ponctualite").alias("taux_ponctualite_avg"),
                F.avg("ratio_voyageurs_retard").alias("ratio_voyageurs_retard_avg")
            )

        w_rank = Window.partitionBy("date").orderBy(F.asc("taux_ponctualite_avg"))
        dm2 = dm2.withColumn("rang_regularite", F.rank().over(w_rank))

        dm2 = dm2.withColumn("load_timestamp", F.current_timestamp())

        logger.info(f"DM2 : {dm2.count()} lignes")
        return dm2

    except Exception as e:
        logger.error(f"Erreur lors de la creation du DM2 : {e}")
        raise


# =====================================================
# DATAMART 3 : EVOLUTION TEMPORELLE
# =====================================================

def create_dm_evolution(spark, logger, df, config):
    try:
        dm3 = df.select(
            F.col("date"),
            F.col("jour_semaine"),
            F.col("jour_nom"),
            F.col("est_vacances"),
            F.col("ligne"),
            F.col("id_station"),
            F.col("nom_station"),
            F.col("pct_validations"),
            F.col("evolution_pct")
        )

        dm3 = dm3.groupBy("date", "jour_semaine", "jour_nom", "est_vacances", "ligne", "id_station", "nom_station") \
            .agg(
                F.sum("pct_validations").alias("pct_validations_cumul"),
                F.avg("evolution_pct").alias("evolution_vs_semaine_precedente_pct")
            )

        dm3 = dm3.orderBy(F.asc("date"), F.asc("ligne"))
        dm3 = dm3.withColumn("load_timestamp", F.current_timestamp())

        logger.info(f"DM3 : {dm3.count()} lignes")
        return dm3

    except Exception as e:
        logger.error(f"Erreur lors de la creation du DM3 : {e}")
        raise


# =====================================================
# DATAMART 4 : SATURATION ML (Features pour prédiction)
# =====================================================

def create_dm_saturation_ml(spark, logger, df, config):
    try:
        saturation_threshold = int(config["thresholds"]["saturation_threshold"]) 

        dm4 = df.select(
            F.col("date"),
            F.col("heure"),
            F.col("ligne"),
            F.col("id_station"),
            F.col("nom_station"),
            F.col("pct_validations"),
            F.col("taux_ponctualite"),
            F.col("jour_semaine"),
            F.col("jour_nom"),
            F.col("est_vacances").alias("is_vacances"),
            F.col("rank_station_par_ligne")
        )

        dm4 = dm4.withColumn(
            "est_saturation",
            F.when(F.col("pct_validations") > saturation_threshold, 1).otherwise(0)
        )

        dm4 = dm4.withColumn(
            "jour_ferie",
            F.when(F.dayofyear(F.col("date")).isin(1, 365), 1).otherwise(0)
        )

        dm4 = dm4.withColumn("load_timestamp", F.current_timestamp())

        dm4 = dm4.select(
            "date", "heure", "ligne", "id_station", "nom_station",
            "pct_validations", "taux_ponctualite", "jour_semaine", "jour_nom",
            "is_vacances", "jour_ferie", "rank_station_par_ligne",
            "est_saturation", "load_timestamp"
        )

        logger.info(f"DM4 : {dm4.count()} lignes")
        logger.info(f"Repartition saturation : {dm4.select('est_saturation').groupBy('est_saturation').count().collect()}")

        return dm4

    except Exception as e:
        logger.error(f"Erreur lors de la creation du DM4 : {e}")
        raise


# =====================================================
# ÉCRITURE DES DATAMARTS DANS POSTGRESQL
# =====================================================

def write_to_postgres(df, table_name, logger, config):
    try:
        jdbc_url = config["postgres"]["jdbc_url"]
        jdbc_driver = config["postgres"]["jdbc_driver_path"]
        db_user = config["postgres"]["user"]
        db_pass = config["postgres"]["password"]

        logger.info(f"Ecriture table PostgreSQL : {table_name}")

        df.write \
            .format("jdbc") \
            .option("url", jdbc_url) \
            .option("dbtable", table_name) \
            .option("user", db_user) \
            .option("password", db_pass) \
            .option("driver", "org.postgresql.Driver") \
            .mode("overwrite") \
            .save()

        logger.info(f"{table_name} ecrite avec succes")

    except Exception as e:
        logger.error(f"Erreur lors de l'ecriture de {table_name} : {e}")
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
        logger.info("DEMARRAGE DATAMART")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        spark = SparkSession.builder \
            .appName(config["spark"]["app_name_datamart"]) \
            .master(config["spark"]["master"]) \
            .config("spark.jars", config["postgres"]["jdbc_driver_path"]) \
            .enableHiveSupport() \
            .getOrCreate()

        logger.info("SparkSession creee")

        df_silver = load_silver_data(spark, logger, config)

        dm1 = create_dm_frequentation(spark, logger, df_silver, config)
        dm2 = create_dm_regularite(spark, logger, df_silver, config)
        dm3 = create_dm_evolution(spark, logger, df_silver, config)
        dm4 = create_dm_saturation_ml(spark, logger, df_silver, config)

        write_to_postgres(dm1, "dm_frequentation_par_station_ligne", logger, config)
        write_to_postgres(dm2, "dm_regularite_par_ligne", logger, config)
        write_to_postgres(dm3, "dm_evolution_frequentation", logger, config)
        write_to_postgres(dm4, "dm_saturation_ml", logger, config)

        spark.stop()
        logger.info("SparkSession fermee")
        logger.info("DATAMART TERMINE AVEC SUCCES")

    except Exception as e:
        logger.error(f"ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
