#!/bin/bash
# setup_spark_env.sh - Configure les variables d'environnement Spark
# Exécutez: source setup_spark_env.sh

# Détecter la version de Spark
SPARK_HOME=$(dirname $(dirname $(which spark-submit)))
SPARK_VERSION=$(spark-submit --version 2>&1 | grep "version" | awk '{print $NF}')

echo "✅ Spark détecté:"
echo "   SPARK_HOME: $SPARK_HOME"
echo "   Version: $SPARK_VERSION"

# Configuration pour Spark local
export SPARK_LOCAL_IP=127.0.0.1
export SPARK_DRIVER_MEMORY=4g
export SPARK_EXECUTOR_MEMORY=4g

# Pour logging Spark
export SPARK_LOG_DIR="./logs/spark"
mkdir -p "$SPARK_LOG_DIR"

echo "✅ Variables d'environnement configurées:"
echo "   SPARK_LOCAL_IP=$SPARK_LOCAL_IP"
echo "   SPARK_DRIVER_MEMORY=$SPARK_DRIVER_MEMORY"
echo "   SPARK_EXECUTOR_MEMORY=$SPARK_EXECUTOR_MEMORY"
echo "   SPARK_LOG_DIR=$SPARK_LOG_DIR"

# Optionnel : Configuration pour HDFS/Hive (si disponibles)
# export HADOOP_HOME=/usr/local/hadoop
# export HIVE_HOME=/usr/local/hive
# export PATH=$PATH:$HADOOP_HOME/bin:$HIVE_HOME/bin

echo ""
echo "✅ Environment ready for Spark!"
