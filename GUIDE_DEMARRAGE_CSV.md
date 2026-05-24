# 🚀 GUIDE DE DÉMARRAGE RAPIDE - Avec fichiers CSV

## Fichiers CSV intégrés

Les fichiers CSV suivants ont été ajoutés au dossier `data/`:

- **arrets.csv** : Référentiel des stations/arrêts (ID, nom, localisation, accessibilité)
- **validations-reseau-ferre-profils-horaires-par-jour-type-3eme-trimestre.csv** : Données de validations par heure et type de jour
- **histo-validations-reseau-ferre.csv** : Historique des validations par année
- **ponctualite-mensuelle-transilien.csv** : Données de ponctualité mensuelle par ligne

## Configuration mise à jour

Le fichier `config/config.ini` a été modifié pour pointer vers ces fichiers CSV:

```ini
[local]
validations_csv_path  = ./data/validations-reseau-ferre-profils-horaires-par-jour-type-3eme-trimestre.csv
stations_csv_path     = ./data/arrets.csv
regularite_csv_path   = ./data/histo-validations-reseau-ferre.csv
ponctualite_csv_path  = ./data/ponctualite-mensuelle-transilien.csv
log_dir               = ./logs
```

## Option 1 : Chargement local (RECOMMANDÉ pour développement)

Utilise le nouveau script `data_loader.py` pour charger les CSV directement en PostgreSQL:

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Démarrer PostgreSQL (localement ou Docker)
docker run --name postgres-idfm -e POSTGRES_PASSWORD=idfm_pass -e POSTGRES_USER=idfm_user \
  -e POSTGRES_DB=idfm_datamarts -p 5433:5432 -d postgres:15

# 3. Créer la base de données si nécessaire
# (Passez cette étape si la base existe déjà)

# 4. Lancer le data loader
python data_loader.py --config config/config.ini

# 5. Lancer l'API
cd api
python -m uvicorn app:app --reload --port 8000

# 6. Lancer le Dashboard (dans un autre terminal)
streamlit run dashboard/app.py
```

## Option 2 : Chargement avec PySpark (pour production)

Si vous avez Spark/HDFS configurés:

```bash
# 1. Lancer le feeder (ingestion vers HDFS)
spark-submit --master local[*] feeder.py --config config/config.ini

# 2. Lancer le processor (transformations silver)
spark-submit --master local[*] processor.py --config config/config.ini

# 3. Lancer le datamart (création des datamarts PostgreSQL)
spark-submit --master local[*] datamart.py --config config/config.ini
```

## Structure des données

### Table `stations`
```
id_station (INT) → Clé primaire
nom_station (VARCHAR)
ville (VARCHAR)
zone_tarifaire (VARCHAR)
accessibilite (VARCHAR)
localisation (VARCHAR)
```

### Table `validations`
```
id (SERIAL) → Clé primaire
ligne (VARCHAR) → Code ligne
id_station (INT) → FK stations
nom_station (VARCHAR)
heure (VARCHAR) → Format "HH-HH" (ex: "10H-11H")
pct_validations (FLOAT) → Pourcentage
type_jour (VARCHAR) → DIJFP, DIMANCHE, etc.
```

### Table `regularite`
```
id (SERIAL) → Clé primaire
date (DATE)
ligne (VARCHAR)
nom_ligne (VARCHAR)
taux_ponctualite (FLOAT) → %
ratio_voyageurs_retard (FLOAT)
```

## Endpoints API disponibles

L'API expose les données chargées:

```
GET  /api/stations              - Lister toutes les stations
GET  /api/stations/{id}         - Détail d'une station
GET  /api/validations           - Lister les validations
GET  /api/validations/line/{ligne} - Validations par ligne
GET  /api/regularite            - Données de régularité
GET  /api/regularite/line/{ligne}  - Régularité par ligne
```

## Dépannage

### Erreur de connexion PostgreSQL
- Vérifier que PostgreSQL est en écoute sur `localhost:5433`
- Vérifier les identifiants dans `config/config.ini` (section `[api]`)

### Erreur "fichier CSV non trouvé"
- Vérifier que les chemins dans `config/config.ini` sont corrects
- Les chemins doivent être relatifs au répertoire racine du projet

### Erreur d'encoding UTF-8
- Les fichiers CSV utilisent le BOM UTF-8 (caractère `\ufeff`)
- Le script data_loader.py gère cela automatiquement

## Architecture actuelle

```
CSV Files (data/)
        ↓
data_loader.py (chargement local)
        ↓
PostgreSQL Database
        ↓
API REST (FastAPI)
        ↓
Dashboard (Streamlit)
```

Pour la version Spark/Big Data:

```
CSV Files (data/)
        ↓
feeder.py
        ↓
HDFS/Parquet (raw layer)
        ↓
processor.py
        ↓
HDFS/Parquet (silver layer)
        ↓
datamart.py
        ↓
PostgreSQL Database (datamarts)
        ↓
API REST (FastAPI)
```

## Prochaines étapes

1. ✅ Charger les données avec `data_loader.py`
2. ✅ Tester l'API avec les endpoints de requête
3. ✅ Visualiser dans le dashboard
4. 📝 Enrichir les datamarts avec des agrégations
5. 📝 Créer des modèles ML de prédiction de saturation
