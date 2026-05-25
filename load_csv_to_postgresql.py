#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
load_csv_to_postgresql.py - Charger les données CSV dans PostgreSQL

Utilisation :
    python3 load_csv_to_postgresql.py
"""

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
import sys
from pathlib import Path

# Configuration
DB_HOST = "localhost"
DB_PORT = 5432
DB_NAME = "idfm_datamarts"
DB_USER = Path.home().name  # Nom d'utilisateur courant
DB_PASSWORD = None  # Pas de mot de passe (trust auth)

DATA_DIR = Path(__file__).parent / "data"

def get_connection():
    """Établit une connexion PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"❌ Erreur de connexion : {e}")
        sys.exit(1)

def load_stations():
    """Charger les données stations"""
    print("\n📥 Chargement des stations...")
    csv_path = DATA_DIR / "arrets.csv"
    
    if not csv_path.exists():
        print(f"⚠️ Fichier non trouvé : {csv_path}")
        return
    
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8", on_bad_lines="skip")
        print(f"   Colonnes : {list(df.columns)}")
        
        # Mapper les colonnes
        if "code_stif_arret" in df.columns:
            df["id_station"] = df["code_stif_arret"]
        if "libelle_arret" in df.columns:
            df["nom_station"] = df["libelle_arret"]
        
        df_stations = df[["id_station", "nom_station"]].drop_duplicates()
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Effacer les données existantes
        cursor.execute("TRUNCATE TABLE stations")
        
        # Insérer
        values = [tuple(row) for row in df_stations.values]
        execute_values(cursor, "INSERT INTO stations (id_station, nom_station) VALUES %s", values)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"   ✅ {len(df_stations)} stations chargées")
        
    except Exception as e:
        print(f"   ❌ Erreur : {e}")

def load_validations():
    """Charger les données de validations"""
    print("\n📥 Chargement des validations...")
    csv_path = DATA_DIR / "validations-reseau-ferre-profils-horaires-par-jour-type-3eme-trimestre.csv"
    
    if not csv_path.exists():
        print(f"⚠️ Fichier non trouvé : {csv_path}")
        return
    
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8", on_bad_lines="skip")
        print(f"   Colonnes disponibles : {list(df.columns)[:10]}...")
        
        # Mapper les colonnes
        df_val = pd.DataFrame()
        df_val["ligne"] = df.get("code_stif_trns", "").astype(str)
        df_val["id_station"] = pd.to_numeric(df.get("code_stif_arret", 0), errors="coerce").fillna(0).astype(int)
        df_val["heure"] = df.get("trnc_horr_60", "").astype(str)
        df_val["pourcentage_validations"] = pd.to_numeric(df.get("pourcentage_validations", 0), errors="coerce").fillna(0)
        df_val["nb_validations"] = (df_val["pourcentage_validations"] * 1000).round(0).astype(int)
        
        # Limiter pour éviter d'insérer trop de données
        df_val = df_val.head(50000)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Effacer les données existantes
        cursor.execute("TRUNCATE TABLE validations")
        
        # Insérer
        values = [tuple(row) for row in df_val[["ligne", "id_station", "heure", "nb_validations", "pourcentage_validations"]].values]
        execute_values(
            cursor,
            "INSERT INTO validations (ligne, id_station, heure, nb_validations, pourcentage_validations) VALUES %s",
            values
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"   ✅ {len(df_val)} validations chargées")
        
    except Exception as e:
        print(f"   ❌ Erreur : {e}")

def load_regularite():
    """Charger les données de régularité"""
    print("\n📥 Chargement des régularités...")
    csv_path = DATA_DIR / "ponctualite-mensuelle-transilien.csv"
    
    if not csv_path.exists():
        print(f"⚠️ Fichier non trouvé : {csv_path}")
        return
    
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8", on_bad_lines="skip")
        print(f"   Colonnes : {list(df.columns)}")
        
        df_reg = pd.DataFrame()
        df_reg["date"] = df.get("Mois", "").astype(str)
        df_reg["ligne"] = df.get("Nom de la ligne", "").astype(str)
        df_reg["taux_ponctualite"] = pd.to_numeric(df.get("Taux de ponctualité", 0), errors="coerce").fillna(0)
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # Effacer les données existantes
        cursor.execute("TRUNCATE TABLE regularite")
        
        # Insérer
        values = [tuple(row) for row in df_reg.values]
        execute_values(
            cursor,
            "INSERT INTO regularite (date, ligne, taux_ponctualite) VALUES %s",
            values
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"   ✅ {len(df_reg)} régularités chargées")
        
    except Exception as e:
        print(f"   ❌ Erreur : {e}")

def load_datamarts():
    """Charger les datamarts depuis les données brutes"""
    print("\n🔨 Construction des datamarts...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # DM1 : Fréquentation par station/ligne
        print("   DM1 : Fréquentation...")
        cursor.execute("""
            INSERT INTO dm_frequentation_par_station_ligne 
            (ligne, id_station, heure, nb_validations_avg, nb_observations)
            SELECT 
                ligne, 
                id_station, 
                heure,
                AVG(pourcentage_validations)::FLOAT,
                COUNT(*)
            FROM validations
            GROUP BY ligne, id_station, heure
            ORDER BY AVG(pourcentage_validations) DESC
            LIMIT 10000
        """)
        print(f"      ✅ {cursor.rowcount} lignes")
        
        # DM2 : Régularité par ligne
        print("   DM2 : Régularité...")
        cursor.execute("""
            INSERT INTO dm_regularite_par_ligne 
            (date, ligne, taux_ponctualite)
            SELECT 
                date,
                ligne,
                AVG(taux_ponctualite)::FLOAT
            FROM regularite
            GROUP BY date, ligne
        """)
        print(f"      ✅ {cursor.rowcount} lignes")
        
        # DM3 : Évolution
        print("   DM3 : Évolution temporelle...")
        cursor.execute("""
            INSERT INTO dm_evolution_frequentation 
            (ligne, id_station, frequentation_cumulee, nb_observations)
            SELECT 
                ligne,
                id_station,
                SUM(nb_validations)::INTEGER,
                COUNT(*)
            FROM validations
            GROUP BY ligne, id_station
        """)
        print(f"      ✅ {cursor.rowcount} lignes")
        
        # DM4 : Saturation ML
        print("   DM4 : Saturation ML...")
        cursor.execute("""
            INSERT INTO dm_saturation_ml 
            (ligne, id_station, heure, nb_validations, pourcentage_validations, est_saturation)
            SELECT 
                ligne,
                id_station,
                heure,
                nb_validations,
                pourcentage_validations,
                CASE WHEN pourcentage_validations > 7.0 THEN 1 ELSE 0 END
            FROM validations
            WHERE pourcentage_validations > 0
        """)
        print(f"      ✅ {cursor.rowcount} lignes")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n✅ Tous les datamarts sont chargés !")
        
    except Exception as e:
        print(f"   ❌ Erreur : {e}")

def main():
    print("=" * 60)
    print("📊 Chargement CSV → PostgreSQL")
    print("=" * 60)
    
    load_stations()
    load_validations()
    load_regularite()
    load_datamarts()
    
    print("\n" + "=" * 60)
    print("✅ Chargement terminé !")
    print("=" * 60)

if __name__ == "__main__":
    main()
