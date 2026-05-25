# -*- coding: utf-8 -*-
"""
database_cache.py - Gestion des datamarts en cache (CSV)
Alternative à PostgreSQL pour développement local
"""

import configparser
import logging
import os
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


class DatabaseCache:
    """
    Classe qui charge et gère les datamarts en mémoire depuis les CSV.
    Utile quand PostgreSQL n'est pas disponible.
    """

    def __init__(self, config_path: str):
        """
        Initialise le cache des datamarts

        Args:
            config_path: Chemin vers le fichier config.ini
        """
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        self.data_dir = Path(self.config["local"]["validations_csv_path"]).parent
        self.datamarts = {}
        self._load_datamarts()

    def _load_datamarts(self):
        """
        Charge les datamarts depuis les CSV bruts.
        Crée les 4 datamarts attendus par l'API.
        """
        logger.info("📦 Chargement des datamarts en mémoire...")

        # Charger les CSV sources
        validations_path = self.config["local"]["validations_csv_path"]
        stations_path = self.config["local"]["stations_csv_path"]
        regularite_path = self.config["local"]["regularite_csv_path"]

        try:
            # Charger les CSV avec gestion des erreurs de parsing
            df_validations = pd.read_csv(validations_path, sep=";", on_bad_lines='skip')
            df_stations = pd.read_csv(stations_path, sep=";", on_bad_lines='skip')
            df_regularite = pd.read_csv(regularite_path, sep=";", on_bad_lines='skip')

            logger.info(f"✅ Validations chargées: {len(df_validations)} lignes")
            logger.info(f"✅ Stations chargées: {len(df_stations)} lignes")
            logger.info(f"✅ Régularité chargée: {len(df_regularite)} lignes")

            # Construire les 4 datamarts
            self._build_datamarts(df_validations, df_stations, df_regularite)

        except Exception as e:
            logger.error(f"❌ Erreur lors du chargement: {e}")
            raise

    def _build_datamarts(self, df_validations, df_stations, df_regularite):
        """
        Construit les 4 datamarts à partir des données brutes
        """

        # ========================================
        # DATAMART 1: frequentation-stations
        # ========================================
        logger.info("🔨 Construction DM1: frequentation-stations...")

        dm1 = df_validations.copy()
        
        # Convertir les colonnes de manière sécurisée
        if 'code_stif_arret' in dm1.columns:
            dm1['id_station'] = pd.to_numeric(dm1['code_stif_arret'], errors='coerce').fillna(0).astype(int)
        else:
            dm1['id_station'] = 0
            
        if 'code_stif_trns' in dm1.columns:
            dm1['ligne'] = dm1['code_stif_trns'].fillna('').astype(str)
        else:
            dm1['ligne'] = ''
            
        if 'trnc_horr_60' in dm1.columns:
            dm1['heure'] = dm1['trnc_horr_60'].fillna('').astype(str)
        else:
            dm1['heure'] = ''
            
        if 'cat_jour' in dm1.columns:
            dm1['jour_type'] = dm1['cat_jour'].fillna('').astype(str)
        else:
            dm1['jour_type'] = ''
            
        if 'pourcentage_validations' in dm1.columns:
            dm1['pourcentage_validations'] = pd.to_numeric(dm1['pourcentage_validations'], errors='coerce').fillna(0)
        else:
            dm1['pourcentage_validations'] = 0
            
        dm1['nb_validations'] = (dm1['pourcentage_validations'] * 100).round(0)

        dm1['rang_frequentation'] = dm1.groupby('ligne')['pourcentage_validations'].rank(method='dense', ascending=False).fillna(0)

        dm1 = dm1[['id_station', 'ligne', 'heure', 'jour_type', 'pourcentage_validations', 
                   'nb_validations', 'rang_frequentation']].copy()

        self.datamarts['dm_frequentation_par_station_ligne'] = dm1
        logger.info(f"✅ DM1 construit: {len(dm1)} lignes")

        # ========================================
        # DATAMART 2: regularite-lignes
        # ========================================
        logger.info("🔨 Construction DM2: regularite-lignes...")

        dm2 = pd.DataFrame()
        dm2['date'] = df_regularite['Date'].fillna('').astype(str) if 'Date' in df_regularite.columns else [''] * len(df_regularite)
        dm2['ligne'] = df_regularite['Ligne'].fillna('').astype(str) if 'Ligne' in df_regularite.columns else [''] * len(df_regularite)
        dm2['nom_ligne'] = df_regularite['Nom de la ligne'].fillna('').astype(str) if 'Nom de la ligne' in df_regularite.columns else [''] * len(df_regularite)
        dm2['taux_ponctualite'] = pd.to_numeric(df_regularite['Taux de ponctualité'], errors='coerce').fillna(0) if 'Taux de ponctualité' in df_regularite.columns else [0] * len(df_regularite)

        dm2['rang_regularite'] = dm2.groupby('date')['taux_ponctualite'].rank(method='dense', ascending=True).fillna(0)

        self.datamarts['dm_regularite_par_ligne'] = dm2.copy()
        logger.info(f"✅ DM2 construit: {len(dm2)} lignes")

        # ========================================
        # DATAMART 3: evolution-temporelle
        # ========================================
        logger.info("🔨 Construction DM3: evolution-temporelle...")

        dm3 = dm1.groupby(['jour_type', 'ligne']).agg({
            'nb_validations': 'sum',
            'id_station': 'count'
        }).reset_index()

        dm3.columns = ['date', 'ligne', 'frequentation_cumulee', 'nb_stations']

        jour_types_map = {'DIJFP': 'Monday', 'SAMEDI': 'Saturday', 'DIMANCHE': 'Sunday', 'JFPAL': 'Monday'}
        dm3['jour_semaine'] = dm3['date'].map(jour_types_map).fillna('Monday')
        dm3['variation_semaine_precedente'] = 0.0

        self.datamarts['dm_evolution_frequentation'] = dm3.copy()
        logger.info(f"✅ DM3 construit: {len(dm3)} lignes")

        # ========================================
        # DATAMART 4: saturation-ml
        # ========================================
        logger.info("🔨 Construction DM4: saturation-ml...")

        dm4 = dm1.copy()
        dm4['taux_ponctualite'] = 100.0  # Valeur par défaut
        dm4['est_saturation'] = (dm4['pourcentage_validations'] >= 50).astype(int)

        self.datamarts['dm_saturation_ml'] = dm4.copy()
        logger.info(f"✅ DM4 construit: {len(dm4)} lignes")

    def query_paginated(self, table_name: str, page: int = 1, page_size: int = 100):
        """
        Retourne les données paginées d'une table

        Args:
            table_name: Nom du datamart
            page: Numéro de page (commence à 1)
            page_size: Nombre de lignes par page

        Returns:
            {"data": [], "total": int, "page": int, "page_size": int, "total_pages": int}
        """
        if table_name not in self.datamarts:
            raise Exception(f"Datamart '{table_name}' non trouvé")

        df = self.datamarts[table_name]
        total = len(df)

        # Pagination
        offset = (page - 1) * page_size
        paginated_df = df.iloc[offset:offset + page_size]

        # Convertir en liste de dictionnaires
        data = paginated_df.to_dict(orient='records')

        # Convertir les valeurs NaN en None pour JSON
        data = [
            {k: (None if pd.isna(v) else v) for k, v in record.items()}
            for record in data
        ]

        total_pages = (total + page_size - 1) // page_size

        return {
            "data": data,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    def get_table_names(self):
        """Retourne les noms des datamarts disponibles"""
        return list(self.datamarts.keys())

    def get_summary(self):
        """Retourne un résumé des datamarts chargés"""
        summary = {}
        for name, df in self.datamarts.items():
            summary[name] = {
                "rows": len(df),
                "columns": list(df.columns)
            }
        return summary
