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
from pyspark.sql.functions import lit


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
    try:
        csv_path = config["local"]["validations_csv_path"]
        hdfs_path = config["hdfs"]["raw_validations_path"]

        logger.info(f"Lecture CSV depuis : {csv_path}")
        df_validations = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(csv_path)

        logger.info(f"Nombre de lignes : {df_validations.count()}")
        logger.info(f"Colonnes : {df_validations.columns}")

        df_validations = df_validations.dropna()

        df_validations = df_validations.select(
            F.col("code_stif_trns").alias("ligne"),
            F.col("code_stif_arret").alias("id_station"),
            F.col("libelle_arret").alias("nom_station"),
            F.col("trnc_horr_60").alias("heure"),
            F.col("pourcentage_validations").alias("pct_validations"),
            F.col("cat_jour").alias("type_jour")
        )

        now = datetime.now()
        df_validations = df_validations.withColumn("year", F.lit(now.year)) \
                                       .withColumn("month", F.lit(now.month)) \
                                       .withColumn("day", F.lit(now.day))

        logger.info(f"Ecriture Parquet vers : {hdfs_path}")
        df_validations.write.mode("overwrite").partitionBy("year", "month", "day").parquet(hdfs_path)
        logger.info("Validations ingerees avec succes")
        
        return df_validations
        
    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion des validations : {e}")
        raise e
# =====================================================
# INGESTION DU REFERENTIEL STATIONS
# =====================================================

def ingest_stations(spark, logger, config):
    try:
        csv_path = config["local"]["stations_csv_path"]
        hdfs_path = config["hdfs"]["raw_stations_path"]

        logger.info(f"Lecture CSV depuis : {csv_path}")
        df_stations = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(csv_path)

        logger.info(f"Nombre de lignes : {df_stations.count()}")
        logger.info(f"Colonnes : {df_stations.columns}")

        from datetime import datetime
        now = datetime.now()
        df_stations = df_stations.withColumn("year", F.lit(now.year)) \
                                 .withColumn("month", F.lit(now.month)) \
                                 .withColumn("day", F.lit(now.day))

        df_stations = df_stations.select(
            F.col("ZdAId").alias("id_station"), 
            F.col("ArRName").alias("nom_station"),
            F.col("ArRTown").alias("ville"),
            F.col("ArRFareZone").alias("zone_tarifaire"),
            F.col("ArRAccessibility").alias("accessibilite"),
            F.col("ArRGeopoint").alias("localisation"),
            F.col("year"),  
            F.col("month"),
            F.col("day")
        )

        df_stations = df_stations.dropna(subset=["id_station"])

        logger.info(f"Ecriture Parquet vers : {hdfs_path}")
        df_stations.write.mode("overwrite").partitionBy("year", "month", "day").parquet(hdfs_path)

        logger.info("Referentiel des stations ingere avec succes")
        return df_stations

    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion du referentiel : {e}")
        raise
# =====================================================
# INGESTION DE LA REGULARITE DES LIGNES
# =====================================================

def ingest_regularite(spark, logger, config):
    try:
        regularite_csv = config["local"]["regularite_csv_path"]
        ponctualite_csv = config["local"]["ponctualite_csv_path"]
        hdfs_path = config["hdfs"]["raw_regularite_path"]

        logger.info(f"Lecture CSV historique : {regularite_csv}")
        df_regularite_histo = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(regularite_csv)
        
        logger.info(f"Lecture CSV ponctualite : {ponctualite_csv}")
        df_ponctualite = spark.read.option("header", "true").option("inferSchema", "true").option("delimiter", ";").csv(ponctualite_csv)

        logger.info(f"Historique : {df_regularite_histo.count()} lignes - Colonnes : {df_regularite_histo.columns}")
        logger.info(f"Ponctualite : {df_ponctualite.count()} lignes - Colonnes : {df_ponctualite.columns}")

        df_ponctualite = df_ponctualite.select(
            F.col("Date").alias("date"),
            F.col("Ligne").alias("ligne"),
            F.col("Nom de la ligne").alias("nom_ligne"),
            F.col("Taux de ponctualité").alias("taux_ponctualite"),
            F.col("Nombre de voyageurs à l'heure pour un voyageur en retard").alias("ratio_voyageurs_retard")
        )
        
        df_regularite = df_ponctualite.dropna(subset=["ligne"])

        now = datetime.now()
        df_regularite = df_regularite.withColumn("year", F.lit(now.year)) \
                                     .withColumn("month", F.lit(now.month)) \
                                     .withColumn("day", F.lit(now.day))

        logger.info(f"Total apres nettoyage : {df_regularite.count()} lignes")
        logger.info(f"Ecriture Parquet vers : {hdfs_path}")
        df_regularite.write.mode("overwrite").partitionBy("year", "month", "day").parquet(hdfs_path)

        logger.info("Regularite des lignes ingeree avec succes")
        return df_regularite

    except Exception as e:
        logger.error(f"Erreur lors de l'ingestion de la regularite : {e}")
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
        logger.info("DEMARRAGE FEEDER")
        logger.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        spark = SparkSession.builder \
            .appName(config["spark"]["app_name_feeder"]) \
            .master(config["spark"]["master"]) \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .getOrCreate()

        logger.info("SparkSession creee")

        ingest_validations(spark, logger, config)
        ingest_stations(spark, logger, config)
        ingest_regularite(spark, logger, config)

        spark.stop()
        logger.info("SparkSession fermee")
        logger.info("FEEDER TERMINE AVEC SUCCES")

    except Exception as e:
        logger.error(f"ERREUR FATALE : {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
