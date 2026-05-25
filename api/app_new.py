#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
api/app.py - API FastAPI pour IDFM Data Platform
Lancement: python -m uvicorn api.app:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import configparser
import os
from typing import List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_db_config():
    config_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "config", "config.ini"))
    db_config = {"host": "localhost", "port": 5432, "database": "idfm_datamarts", "user": "youcef", "password": ""}
    
    if os.path.exists(config_path):
        try:
            config = configparser.ConfigParser()
            config.read(config_path)
            if "postgres" in config:
                db_config["host"] = config["postgres"].get("host", db_config["host"])
                db_config["port"] = int(config["postgres"].get("port", db_config["port"]))
                db_config["database"] = config["postgres"].get("database", db_config["database"])
                db_config["user"] = config["postgres"].get("user", db_config["user"])
                db_config["password"] = config["postgres"].get("password", db_config["password"])
        except Exception as e:
            logger.warning(f"Config error: {e}")
    
    return db_config

DB_CONFIG = load_db_config()

app = FastAPI(title="IDFM Data API", description="API pour servir les datamarts", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def get_db_connection():
    try:
        conn = psycopg2.connect(host=DB_CONFIG["host"], port=DB_CONFIG["port"], database=DB_CONFIG["database"], user=DB_CONFIG["user"], password=DB_CONFIG["password"])
        return conn
    except psycopg2.Error as e:
        logger.error(f"DB Error: {e}")
        raise HTTPException(status_code=500, detail="Erreur de connexion")

def execute_query(query: str, limit: int = None) -> List[Dict[str, Any]]:
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if limit and "LIMIT" not in query.upper():
            query += f" LIMIT {limit}"
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        data = [dict(row) for row in results]
        logger.info(f"{len(data)} lignes recuperees")
        return data
    except psycopg2.Error as e:
        logger.error(f"Query Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", tags=["Health"])
def health_check():
    return {"status": "OK", "service": "IDFM Data API", "version": "1.0.0"}

@app.get("/api/datamarts/frequentation-stations", tags=["Datamarts"])
def get_frequentation_stations():
    query = """
    SELECT 
        ligne,
        id_station,
        nom_station as station,
        heure,
        ROUND(nb_validations_avg::numeric, 1) as pourcentage_validations,
        ROUND(nb_validations_max::numeric, 1) as occupation_max_pct,
        ROUND(nb_validations_min::numeric, 1) as occupation_min_pct,
        nb_observations
    FROM public.dm_frequentation_par_station_ligne
    ORDER BY ligne, nom_station, heure
    """
    results = execute_query(query, limit=3000)
    return {"data": results}

@app.get("/api/datamarts/saturation-ml", tags=["Datamarts"])
def get_saturation_ml():
    query = """
    SELECT 
        ligne,
        id_station,
        nom_station as station,
        heure,
        jour_nom as jour_type,
        ROUND(pourcentage_validations::numeric, 1) as pourcentage_validations,
        CASE WHEN est_saturation = 1 THEN 'SATURE' ELSE 'NORMAL' END as statut,
        est_saturation
    FROM public.dm_saturation_ml
    WHERE pourcentage_validations IS NOT NULL
    ORDER BY ligne, nom_station, heure
    """
    results = execute_query(query, limit=2000)
    return {"data": results}

@app.get("/api/datamarts/regularite-lignes", tags=["Datamarts"])
def get_regularite_lignes():
    query = """
    SELECT 
        DATE(date) as date,
        ligne,
        ROUND((taux_ponctualite * 100)::numeric, 1) as ponctualite_pct,
        nb_retards,
        ROUND(delai_moyen::numeric, 2) as delai_moyen_minutes,
        CASE 
            WHEN taux_ponctualite >= 0.95 THEN 'EXCELLENT'
            WHEN taux_ponctualite >= 0.90 THEN 'BON'
            WHEN taux_ponctualite >= 0.85 THEN 'ACCEPTABLE'
            ELSE 'DEGRADE'
        END as qualite_service
    FROM public.dm_regularite_par_ligne
    WHERE ligne IS NOT NULL AND ligne != ''
    ORDER BY date DESC, ligne
    """
    results = execute_query(query, limit=1000)
    return {"data": results}

@app.get("/api/datamarts/ponctualite-transilien", tags=["Datamarts"])
def get_ponctualite_transilien():
    query = """
    SELECT 
        DATE(date) as date,
        ligne,
        ROUND((taux_ponctualite * 100)::numeric, 1) as ponctualite_pct,
        nb_retards,
        ROUND(delai_moyen::numeric, 2) as retard_moyen_minutes,
        CASE 
            WHEN taux_ponctualite >= 0.95 THEN 'EXCELLENTE'
            WHEN taux_ponctualite >= 0.90 THEN 'BONNE'
            WHEN taux_ponctualite >= 0.85 THEN 'DEGRADEE'
            ELSE 'TRES_DEGRADEE'
        END as niveau_service
    FROM public.dm_regularite_par_ligne
    WHERE ligne IN ('100', '760', '800')
    ORDER BY date DESC, ligne
    """
    results = execute_query(query, limit=1000)
    return {"data": results}

@app.get("/api/datamarts/evolution-temporelle", tags=["Datamarts"])
def get_evolution_temporelle():
    query = """
    SELECT 
        ligne,
        nom_station as station,
        heure,
        jour_nom as type_jour,
        ROUND(nb_validations_avg::numeric, 1) as occupation_pct,
        DATE(load_timestamp) as date_analyse
    FROM public.dm_frequentation_par_station_ligne
    ORDER BY load_timestamp DESC, ligne, nom_station, heure
    """
    results = execute_query(query, limit=2000)
    return {"data": results}

@app.get("/api/datamarts/stations", tags=["Datamarts"])
def get_stations():
    query = """SELECT * FROM public.stations"""
    results = execute_query(query, limit=5000)
    return {"data": results}

@app.get("/api/datamarts/validations", tags=["Datamarts"])
def get_validations():
    query = """
    SELECT * FROM public.validations
    LIMIT 100
    """
    results = execute_query(query, limit=1000)
    return {"data": results}

@app.get("/api/debug/tables", tags=["Debug"])
def list_tables():
    query = """SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"""
    results = execute_query(query)
    return {"tables": [row["table_name"] for row in results]}

@app.get("/api/debug/stats", tags=["Debug"])
def get_stats():
    query = """
    SELECT 
        (SELECT COUNT(DISTINCT ligne) FROM dm_frequentation_par_station_ligne) as nombre_lignes,
        (SELECT COUNT(DISTINCT nom_station) FROM dm_frequentation_par_station_ligne) as nombre_stations,
        (SELECT ROUND(AVG(nb_validations_avg)::numeric, 1) FROM dm_frequentation_par_station_ligne) as occupation_moyenne_pct,
        (SELECT COUNT(*) FROM dm_frequentation_par_station_ligne) as total_observations
    """
    results = execute_query(query)
    return {"stats": results[0] if results else {}}

@app.get("/api/health")
def detailed_health():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        db_status = "Connected"
    except Exception as e:
        db_status = f"Error: {str(e)}"
    
    return {"api_status": "Running", "database_status": db_status, "config": {"host": DB_CONFIG["host"], "port": DB_CONFIG["port"], "database": DB_CONFIG["database"]}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
