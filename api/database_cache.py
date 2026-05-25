import configparser
import logging
import os
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


class DatabaseCache:
    def __init__(self, config_path: str):
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

        self.data_dir = Path(self.config["local"]["validations_csv_path"]).parent
        self.datamarts = {}
        self._load_datamarts()

    def _load_datamarts(self):
        validations_path = self.config["local"]["validations_csv_path"]
        stations_path = self.config["local"]["stations_csv_path"]
        regularite_path = self.config["local"]["regularite_csv_path"]

        try:
            df_validations = pd.read_csv(validations_path, sep=";", on_bad_lines='skip')
            df_stations = pd.read_csv(stations_path, sep=";", on_bad_lines='skip')
            df_regularite = pd.read_csv(regularite_path, sep=";", on_bad_lines='skip')

            logger.info(f"Validations chargees: {len(df_validations)} lignes")
            logger.info(f"Stations chargees: {len(df_stations)} lignes")
            logger.info(f"Regularite chargee: {len(df_regularite)} lignes")

            self._build_datamarts(df_validations, df_stations, df_regularite)

        except Exception as e:
            logger.error(f"Erreur lors du chargement: {e}")
            raise

    def _build_datamarts(self, df_validations, df_stations, df_regularite):
        dm1 = df_validations.copy()
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
        logger.info(f"DM1 construit: {len(dm1)} lignes")

        dm2 = pd.DataFrame()
        dm2['date'] = df_regularite['Date'].fillna('').astype(str) if 'Date' in df_regularite.columns else [''] * len(df_regularite)
        dm2['ligne'] = df_regularite['Ligne'].fillna('').astype(str) if 'Ligne' in df_regularite.columns else [''] * len(df_regularite)
        dm2['nom_ligne'] = df_regularite['Nom de la ligne'].fillna('').astype(str) if 'Nom de la ligne' in df_regularite.columns else [''] * len(df_regularite)
        dm2['taux_ponctualite'] = pd.to_numeric(df_regularite['Taux de ponctualité'], errors='coerce').fillna(0) if 'Taux de ponctualité' in df_regularite.columns else [0] * len(df_regularite)
        dm2['rang_regularite'] = dm2.groupby('date')['taux_ponctualite'].rank(method='dense', ascending=True).fillna(0)
        self.datamarts['dm_regularite_par_ligne'] = dm2.copy()
        logger.info(f"DM2 construit: {len(dm2)} lignes")

        dm3 = dm1.groupby(['jour_type', 'ligne']).agg({
            'nb_validations': 'sum',
            'id_station': 'count'
        }).reset_index()
        dm3.columns = ['date', 'ligne', 'frequentation_cumulee', 'nb_stations']
        jour_types_map = {'DIJFP': 'Monday', 'SAMEDI': 'Saturday', 'DIMANCHE': 'Sunday', 'JFPAL': 'Monday'}
        dm3['jour_semaine'] = dm3['date'].map(jour_types_map).fillna('Monday')
        dm3['variation_semaine_precedente'] = 0.0
        self.datamarts['dm_evolution_frequentation'] = dm3.copy()
        logger.info(f"DM3 construit: {len(dm3)} lignes")

        dm4 = dm1.copy()
        dm4['taux_ponctualite'] = 100.0
        dm4['est_saturation'] = (dm4['pourcentage_validations'] >= 50).astype(int)
        self.datamarts['dm_saturation_ml'] = dm4.copy()
        logger.info(f"DM4 construit: {len(dm4)} lignes")

    def query_paginated(self, table_name: str, page: int = 1, page_size: int = 100):
        if table_name not in self.datamarts:
            raise Exception(f"Datamart '{table_name}' non trouve")
        df = self.datamarts[table_name]
        total = len(df)
        offset = (page - 1) * page_size
        paginated_df = df.iloc[offset:offset + page_size]
        data = paginated_df.to_dict(orient='records')
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
        return list(self.datamarts.keys())

    def get_summary(self):
        summary = {}
        for name, df in self.datamarts.items():
            summary[name] = {
                "rows": len(df),
                "columns": list(df.columns)
            }
        return summary
