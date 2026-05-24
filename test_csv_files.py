#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_csv_files.py - Valide que les fichiers CSV peuvent être chargés correctement

Utilisation :
    python test_csv_files.py
"""

import os
import pandas as pd

CSV_DIR = "./data"

FILES_TO_CHECK = {
    "arrets.csv": {
        "encoding": "utf-8-sig",
        "delimiter": ";",
        "expected_columns": ["ArRId", "ArRName", "ArRTown"],
    },
    "validations-reseau-ferre-profils-horaires-par-jour-type-3eme-trimestre.csv": {
        "encoding": "utf-8-sig",
        "delimiter": ";",
        "expected_columns": ["code_stif_trns", "code_stif_arret", "pourcentage_validations"],
    },
    "ponctualite-mensuelle-transilien.csv": {
        "encoding": "utf-8-sig",
        "delimiter": ";",
        "expected_columns": ["Date", "Ligne", "Taux de ponctualité"],
    },
    "histo-validations-reseau-ferre.csv": {
        "encoding": "utf-8-sig",
        "delimiter": ";",
        "expected_columns": ["annee", "reseau_ferre"],
    },
}


def test_file(filename, config):
    """Teste un fichier CSV"""
    filepath = os.path.join(CSV_DIR, filename)
    
    print(f"\n{'='*60}")
    print(f"Testing: {filename}")
    print(f"{'='*60}")
    
    if not os.path.exists(filepath):
        print(f"❌ FICHIER NON TROUVÉ: {filepath}")
        return False
    
    try:
        df = pd.read_csv(
            filepath,
            encoding=config["encoding"],
            delimiter=config["delimiter"],
            nrows=5
        )
        
        print(f"✓ Fichier chargé")
        print(f"  - Lignes (sample): {len(df)}")
        print(f"  - Colonnes: {list(df.columns)}")
        
        # Vérifier les colonnes attendues
        missing = [col for col in config["expected_columns"] if col not in df.columns]
        if missing:
            print(f"⚠️  Colonnes manquantes: {missing}")
            return False
        
        print(f"✓ Toutes les colonnes attendues présentes")
        
        # Afficher un aperçu
        print(f"\nAperçu des données:")
        print(df.head(3).to_string())
        
        return True
        
    except Exception as e:
        print(f"❌ ERREUR: {e}")
        return False


def main():
    """Test tous les fichiers CSV"""
    print("🧪 VALIDATION DES FICHIERS CSV")
    print(f"Répertoire: {os.path.abspath(CSV_DIR)}")
    
    results = {}
    for filename, config in FILES_TO_CHECK.items():
        results[filename] = test_file(filename, config)
    
    print(f"\n{'='*60}")
    print("RÉSUMÉ")
    print(f"{'='*60}")
    
    total = len(results)
    success = sum(1 for v in results.values() if v)
    
    for filename, success_flag in results.items():
        status = "✅" if success_flag else "❌"
        print(f"{status} {filename}")
    
    print(f"\nRésultat: {success}/{total} fichiers OK")
    
    if success == total:
        print("\n✅ TOUS LES FICHIERS SONT VALIDES!")
        print("Vous pouvez lancer: python data_loader.py --config config/config.ini")
        return 0
    else:
        print(f"\n❌ {total - success} fichier(s) problématique(s)")
        return 1


if __name__ == "__main__":
    exit(main())
