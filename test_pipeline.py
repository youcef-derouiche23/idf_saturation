#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_pipeline.py - Test du pipeline (sans PostgreSQL)
Charge les CSV et crée les datamarts en mémoire
"""

import pandas as pd
import sys
import os
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

def test_pipeline():
    print("\n" + "="*60)
    print("🚀 TEST PIPELINE - CHARGEMENT ET TRANSFORMATION DONNÉES")
    print("="*60 + "\n")
    
    # ÉTAPE 1 : Charger les CSV
    print("[1/4] 📥 Chargement des stations...")
    try:
        df_stations = pd.read_csv(
            os.path.join(PROJECT_DIR, "data/arrets.csv"),
            delimiter=";", encoding="utf-8-sig"
        )
        print(f"✅ {len(df_stations)} stations chargées")
        print(f"   Colonnes: {list(df_stations.columns)[:5]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    # ÉTAPE 2 : Charger les validations
    print("\n[2/4] 📥 Chargement des validations...")
    try:
        df_validations = pd.read_csv(
            os.path.join(PROJECT_DIR, "data/validations-reseau-ferre-profils-horaires-par-jour-type-3eme-trimestre.csv"),
            delimiter=";", encoding="utf-8-sig"
        )
        print(f"✅ {len(df_validations)} validations chargées")
        print(f"   Colonnes: {list(df_validations.columns)[:5]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    # ÉTAPE 3 : Charger la régularité
    print("\n[3/4] 📥 Chargement de la régularité...")
    try:
        df_regularite = pd.read_csv(
            os.path.join(PROJECT_DIR, "data/ponctualite-mensuelle-transilien.csv"),
            delimiter=";", encoding="utf-8-sig"
        )
        print(f"✅ {len(df_regularite)} lignes de régularité chargées")
        print(f"   Colonnes: {list(df_regularite.columns)[:5]}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    # ÉTAPE 4 : Transformations et agrégations
    print("\n[4/4] 🔄 Transformation et agrégation...")
    try:
        # DM1: Fréquentation par station/ligne
        dm1 = df_validations.groupby(
            ['code_stif_trns', 'code_stif_arret', 'libelle_arret', 'trnc_horr_60']
        ).agg({
            'pourcentage_validations': ['mean', 'max', 'min']
        }).reset_index()
        print(f"✅ DM1 créé: {len(dm1)} lignes")
        
        # DM2: Régularité par ligne
        dm2 = df_regularite.groupby(['Ligne', 'Nom de la ligne']).agg({
            'Taux de ponctualité': 'mean'
        }).reset_index()
        print(f"✅ DM2 créé: {len(dm2)} lignes")
        
        # DM3: Tendances
        dm3 = df_validations.groupby(['cat_jour', 'code_stif_trns']).agg({
            'pourcentage_validations': 'sum'
        }).reset_index()
        print(f"✅ DM3 créé: {len(dm3)} lignes")
        
        # DM4: Features ML
        dm4 = df_validations.copy()
        dm4['est_saturation'] = (dm4['pourcentage_validations'] > 5.0).astype(int)
        print(f"✅ DM4 créé: {len(dm4)} lignes avec label saturation")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    # Résumé
    print("\n" + "="*60)
    print("✅ RÉSUMÉ DES DATAMARTS")
    print("="*60)
    print(f"\nDM1 (Fréquentation)     : {len(dm1):>6} lignes")
    print(f"DM2 (Régularité)       : {len(dm2):>6} lignes")
    print(f"DM3 (Évolution)        : {len(dm3):>6} lignes")
    print(f"DM4 (Features ML)      : {len(dm4):>6} lignes")
    print(f"\nTotal stations         : {len(df_stations):>6}")
    print(f"Total validations      : {len(df_validations):>6}")
    print(f"Total régularité       : {len(df_regularite):>6}")
    
    print("\n" + "="*60)
    print("🎉 PIPELINE RÉUSSI!")
    print("="*60)
    print("\n✨ Prochaines étapes:")
    print("   1. Démarrer PostgreSQL: docker run --name postgres-idfm ...")
    print("   2. Lancer pipeline_local.py --config config/config.ini")
    print("   3. Lancer l'API: cd api && python -m uvicorn app:app --reload")
    print("   4. Lancer dashboard: streamlit run dashboard/app.py")
    
    return True

if __name__ == "__main__":
    success = test_pipeline()
    sys.exit(0 if success else 1)
