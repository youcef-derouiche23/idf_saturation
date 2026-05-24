#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_spark_simple.py - Lancer le pipeline Spark avec une config simplifiée
Évite les problèmes NumPy sur macOS ARM64

Utilisation :
    python3 run_spark_simple.py feeder
    python3 run_spark_simple.py processor
    python3 run_spark_simple.py datamart
    python3 run_spark_simple.py all
"""

import subprocess
import sys
import os
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(PROJECT_DIR, "config/config.ini")
LOG_DIR = os.path.join(PROJECT_DIR, "logs")

# Couleurs
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

def print_header(msg):
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{msg}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

def print_success(msg):
    print(f"{GREEN}✅ {msg}{NC}")

def print_error(msg):
    print(f"{RED}❌ {msg}{NC}")

def print_info(msg):
    print(f"{YELLOW}ℹ️  {msg}{NC}")

def run_spark_job(script_name, job_type):
    """Run a Spark job with proper configuration"""
    script_path = os.path.join(PROJECT_DIR, f"{script_name}.py")
    log_file = os.path.join(LOG_DIR, f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    os.makedirs(LOG_DIR, exist_ok=True)
    
    if not os.path.exists(script_path):
        print_error(f"Script non trouvé: {script_path}")
        return False
    
    print_header(f"🔄 {job_type}")
    print_info(f"Script: {script_path}")
    print_info(f"Config: {CONFIG}")
    print_info(f"Log: {log_file}")
    
    # Commande Spark sans NumPy
    cmd = [
        "spark-submit",
        "--master", "local[*]",
        "--driver-memory", "4g",
        "--executor-memory", "4g",
        "--conf", "spark.python.version=3",
        "--conf", "spark.driver.maxResultSize=2g",
        script_path,
        "--config", CONFIG
    ]
    
    try:
        with open(log_file, 'w') as log_f:
            process = subprocess.Popen(
                cmd,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                text=True
            )
            returncode = process.wait()
            
        if returncode == 0:
            print_success(f"{job_type} terminé")
            # Afficher les dernières lignes du log
            print_info("Dernières lignes du log:")
            with open(log_file, 'r') as f:
                lines = f.readlines()[-5:]
                for line in lines:
                    print(f"  {line.rstrip()}")
            return True
        else:
            print_error(f"{job_type} échoué (code: {returncode})")
            print_info("Consulter le log pour plus de détails:")
            with open(log_file, 'r') as f:
                lines = f.readlines()[-10:]
                for line in lines:
                    print(f"  {line.rstrip()}")
            return False
            
    except Exception as e:
        print_error(f"Erreur lors de l'exécution: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print_header("USAGE")
        print("python3 run_spark_simple.py [feeder|processor|datamart|all]")
        print("\nExemples:")
        print("  python3 run_spark_simple.py feeder")
        print("  python3 run_spark_simple.py processor")
        print("  python3 run_spark_simple.py datamart")
        print("  python3 run_spark_simple.py all")
        sys.exit(1)
    
    job = sys.argv[1].lower()
    
    print_header("🚀 PIPELINE SPARK - IDFM")
    print_info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_info(f"Projet: {PROJECT_DIR}")
    
    success = True
    
    if job in ["feeder", "all"]:
        if not run_spark_job("feeder", "ÉTAPE 1: FEEDER (Ingestion CSV → Parquet)"):
            success = False
    
    if job in ["processor", "all"] and success:
        if not run_spark_job("processor", "ÉTAPE 2: PROCESSOR (Transformation Silver)"):
            success = False
    
    if job in ["datamart", "all"] and success:
        if not run_spark_job("datamart", "ÉTAPE 3: DATAMART (Gold Tables)"):
            success = False
    
    if success:
        print_header("🎉 SUCCÈS!")
        print_success("Pipeline terminé avec succès")
    else:
        print_header("⚠️  ATTENTION")
        print_error("Le pipeline a rencontré des erreurs")
        print_info(f"Consulter les logs dans: {LOG_DIR}")
        sys.exit(1)

if __name__ == "__main__":
    main()
