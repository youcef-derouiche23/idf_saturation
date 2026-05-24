# 📁 Structure Complète du Projet IDFM

Vue d'ensemble complète de tous les fichiers et leur rôle.

---

## 📂 Organisation des Répertoires

```
Projet_IDFM_Frequentation/
│
├── 📄 README.md                           [Documentation principale]
├── 📄 GUIDE_DEMARRAGE.md                 [Guide quick-start]
├── 📄 TRANSFORMATIONS.md                 [Jointures + agrégations détaillées]
├── 📄 WINDOW_FUNCTIONS.md                [Window functions expliquées]
├── 📄 STRUCTURE_COMPLETE.md              [Ce fichier]
│
├── 🐍 feeder.py                          [Ingestion CSV → HDFS Parquet]
├── 🐍 processor.py                       [Transformation Silver]
├── 🐍 datamart.py                        [Datamarts PostgreSQL]
│
├── 🔧 config/
│   └── config.ini                        [Configuration centralisée]
│
├── 💾 data/
│   ├── validations_2025.csv              [Source brute - Validations]
│   ├── stations_referentiel.csv          [Source brute - Stations]
│   └── regularite_lignes.csv             [Source brute - Régularité]
│
├── 📋 logs/
│   ├── feeder.txt                        [Logs ingestion]
│   ├── processor.txt                     [Logs transformation]
│   └── datamart.txt                      [Logs datamarts]
│
├── 🌐 api/
│   ├── __init__.py                       [Package init]
│   ├── app.py                            [FastAPI endpoints]
│   ├── auth.py                           [JWT authentication]
│   ├── models.py                         [Pydantic schemas]
│   └── database.py                       [PostgreSQL connection]
│
├── 📊 dashboard/
│   └── app.py                            [Streamlit dashboard]
│
├── 🐘 postgresql-42.6.0.jar              [JDBC driver]
│
├── 📦 requirements.txt                   [Python dependencies]
│
├── 🚀 start_api_dashboard.sh             [Startup script Unix/Mac]
└── 🚀 start_api_dashboard.bat            [Startup script Windows]
```

---

## 📄 Fichiers Détaillés

### 1. **README.md** 
- **Taille :** ~500 lignes
- **Contenu :**
  - Contexte projet + problématique métier
  - Architecture médaillon
  - Stack technique complète
  - Structure fichiers
  - Données sources
  - Transformations (jointures, agrégations, window functions)
  - Datamarts détaillés
  - Prérequis + lancement étape par étape
  - API endpoints
  - Dashboard Streamlit
  - Configuration
  - Troubleshooting
  - Ressources

### 2. **GUIDE_DEMARRAGE.md**
- **Taille :** ~300 lignes
- **Contenu :**
  - Quick-start 5 minutes
  - Format CSV attendu
  - Test API avec curl
  - Export données
  - Vérification logs
  - Problèmes courants + solutions
  - Pipeline automatisé
  - SQL utiles
  - Prochaines étapes

### 3. **TRANSFORMATIONS.md**
- **Taille :** ~400 lignes
- **Contenu :**
  - Pipeline complet (Raw → Silver → Gold)
  - Jointures détaillées (validations ↔ stations ↔ régularité)
  - Agrégations (jour semaine, vacances)
  - Window functions (RANK, LAG, ROW_NUMBER)
  - Table Silver finale
  - Agrégations datamarts
  - Diagramme relationnel
  - Vérification transformations
  - Performance

### 4. **WINDOW_FUNCTIONS.md**
- **Taille :** ~350 lignes
- **Contenu :**
  - Vue d'ensemble window functions
  - RANK() pour classement fréquentation
  - LAG() pour évolution semaine
  - ROW_NUMBER() pour numérotation
  - DENSE_RANK() pour régularité
  - AVG() mobile
  - Exemples pratiques Hive/Spark SQL
  - Performance + optimisations
  - Ressources

### 5. **STRUCTURE_COMPLETE.md** 
- **Taille :** Ce fichier
- **Contenu :**
  - Vue d'ensemble structure
  - Description chaque fichier
  - Flux données
  - Responsabilités
  - Dépendances

---

## 🐍 Fichiers Python Principaux

### **feeder.py** (~240 lignes)
```
Responsabilité : Ingestion CSV → HDFS Parquet
Fonction : Charger données brutes
```

| Fonction | Rôle |
|----------|------|
| `setup_logger()` | Configuration logging |
| `parse_args()` | Arguments CLI |
| `ingest_validations()` | CSV validations → Parquet |
| `ingest_stations()` | CSV stations → Parquet |
| `ingest_regularite()` | CSV régularité → Parquet |
| `main()` | Orchestration |

**Inputs :**
- `/validations_2025.csv`
- `/stations_referentiel.csv`
- `/regularite_lignes.csv`

**Outputs :**
- `hdfs://namenode:9000/raw/validations`
- `hdfs://namenode:9000/raw/stations`
- `hdfs://namenode:9000/raw/regularite`

---

### **processor.py** (~365 lignes)
```
Responsabilité : Transformation couche Silver
Fonction : Jointures, agrégations, window functions
```

| Fonction | Rôle |
|----------|------|
| `load_raw_data()` | Charger Parquet depuis HDFS |
| `join_data()` | Jointures validations ↔ stations ↔ régularité |
| `aggregate_and_enrich()` | Jour semaine, vacances, enrichissements |
| `apply_window_functions()` | RANK, LAG, ROW_NUMBER |
| `create_hive_tables()` | Écrire table Hive silver |
| `main()` | Orchestration |

**Inputs :**
- `hdfs://namenode:9000/raw/*`

**Outputs :**
- `hdfs://namenode:9000/silver/validations_enrichies`
- Hive table : `silver.validations_enrichies`

---

### **datamart.py** (~329 lignes)
```
Responsabilité : Création datamarts PostgreSQL
Fonction : Lire Silver → Créer 4 datamarts Gold → PostgreSQL
```

| Fonction | Rôle |
|----------|------|
| `load_silver_data()` | Charger table Hive silver |
| `create_dm_frequentation()` | Datamart 1 : fréquentation |
| `create_dm_regularite()` | Datamart 2 : régularité |
| `create_dm_evolution()` | Datamart 3 : évolution |
| `create_dm_saturation_ml()` | Datamart 4 : ML features |
| `write_to_postgres()` | Écrire dans PostgreSQL |
| `main()` | Orchestration |

**Inputs :**
- Hive table : `silver.validations_enrichies`

**Outputs :**
- PostgreSQL : `dm_frequentation_par_station_ligne`
- PostgreSQL : `dm_regularite_par_ligne`
- PostgreSQL : `dm_evolution_frequentation`
- PostgreSQL : `dm_saturation_ml`

---

## 🌐 Fichiers API (FastAPI)

### **api/__init__.py**
- Fichier vide (init package)

### **api/auth.py** (~90 lignes)
```
Responsabilité : Authentification JWT
Exports : 
  - create_access_token()
  - get_current_user()
  - authenticate_user()
```

### **api/models.py** (~60 lignes)
```
Responsabilité : Schémas Pydantic
Exports :
  - Token
  - PaginatedResponse
  - FrequentationStationResponse
  - RegulariteResponse
  - EvolutionResponse
  - SaturationMLResponse
```

### **api/database.py** (~120 lignes)
```
Responsabilité : Gestion PostgreSQL
Classe : Database
Méthodes :
  - connect()
  - disconnect()
  - query()
  - query_count()
  - query_paginated()
```

### **api/app.py** (~250 lignes)
```
Responsabilité : Endpoints FastAPI
Endpoints :
  GET  /                              → health check
  POST /auth/login                    → JWT token
  GET  /datamarts/frequentation-stations    → DM1 paginé
  GET  /datamarts/regularite-lignes         → DM2 paginé
  GET  /datamarts/evolution-temporelle      → DM3 paginé
  GET  /datamarts/saturation-ml             → DM4 paginé (ML)
```

---

## 📊 Fichier Dashboard

### **dashboard/app.py** (~400 lignes)
```
Responsabilité : Dashboard Streamlit
Pages :
  1. Fréquentation par station/ligne
  2. Régularité des lignes
  3. Évolution temporelle
  4. Saturation (ML)

Dépendances :
  - requests (appels API)
  - pandas (dataframes)
  - plotly (visualisations)
  - streamlit (UI)
```

---

## 🔧 Fichier Configuration

### **config/config.ini** (~50 lignes)
```
[hdfs]
raw_validations_path, raw_stations_path, raw_regularite_path, silver_path

[hive]
database, table_validations, table_stations, table_regularite

[local]
validations_csv_path, stations_csv_path, regularite_csv_path, log_dir

[spark]
app_name_feeder, app_name_processor, app_name_datamart, master

[postgres]
host, port, database, user, password, jdbc_url, jdbc_driver_path

[api]
host, port, secret_key, algorithm, token_expire_minutes
db_host, db_port, db_name, db_user, db_password
login_user, login_password
api_url

[thresholds]
saturation_threshold, regularity_threshold
```

---

## 📋 Fichiers de Lancement

### **start_api_dashboard.sh** (~40 lignes)
- Vérifie requirements.txt
- Lance API (uvicorn) en background
- Lance Dashboard (streamlit)

### **start_api_dashboard.bat** (~30 lignes)
- Version Windows du script
- Même fonctionnalités

---

## 📦 Dépendances (requirements.txt)

```
API/Dashboard :
├── fastapi==0.115.6
├── uvicorn[standard]==0.34.0
├── PyJWT==2.10.1
├── python-multipart==0.0.20
├── psycopg2-binary==2.9.10
├── pydantic==2.10.4
├── streamlit==1.41.1
├── plotly==5.24.1
├── pandas==2.2.3
└── requests==2.32.3

Note : feeder.py, processor.py, datamart.py
      tournent dans le container Spark
      (PySpark déjà inclus)
```

---

## 🔄 Flux de Données Complet

```
CSV SOURCES
├── validations_2025.csv
├── stations_referentiel.csv
└── regularite_lignes.csv
         │
         ▼
    FEEDER.PY
    (ingestion)
         │
         ▼
HDFS PARQUET (/raw)
├── raw/validations
├── raw/stations
└── raw/regularite
         │
         ▼
    PROCESSOR.PY
    ├── Jointures (validations ↔ stations ↔ régularité)
    ├── Agrégations (jour semaine, vacances)
    └── Window Functions (RANK, LAG, ROW_NUMBER)
         │
         ▼
HIVE SILVER
└── silver.validations_enrichies (1 table)
         │
         ▼
    DATAMART.PY
    ├── DM1 : Fréquentation
    ├── DM2 : Régularité
    ├── DM3 : Évolution
    └── DM4 : Saturation ML
         │
         ▼
POSTGRESQL GOLD
├── dm_frequentation_par_station_ligne
├── dm_regularite_par_ligne
├── dm_evolution_frequentation
└── dm_saturation_ml
         │
         ▼
    API REST (FastAPI)
    ├── GET  /datamarts/frequentation-stations
    ├── GET  /datamarts/regularite-lignes
    ├── GET  /datamarts/evolution-temporelle
    └── GET  /datamarts/saturation-ml
         │
         ▼
    DASHBOARD (Streamlit)
    ├── Charts
    ├── Tables
    └── Exports CSV
```

---

## 🎯 Responsabilités par Fichier

| Fichier | Phase | Tâche | Input | Output |
|---------|-------|-------|-------|--------|
| feeder.py | Ingestion | CSV → Parquet | CSV local | HDFS /raw |
| processor.py | Silver | Transformation | HDFS /raw | Hive silver |
| datamart.py | Gold | 4 Datamarts | Hive silver | PostgreSQL |
| api/app.py | Exposition | REST API | PostgreSQL | JSON |
| dashboard/app.py | Visualisation | Charts | API | HTML/Streamlit |

---

## 📊 Dépendances entre Fichiers

```
config.ini
├── feeder.py (lit config HDFS, local, spark)
├── processor.py (lit config HDFS, hive, local, spark)
├── datamart.py (lit config hive, postgres, spark)
├── api/
│   ├── auth.py
│   ├── database.py (lit config api, postgres)
│   ├── models.py
│   └── app.py (dépend de database.py, auth.py, models.py)
└── dashboard/app.py (lit config api)
```

---

## ✅ Checklist Lancement

```
□ Cluster Hadoop/Spark démarré
□ PostgreSQL accessible (port 5433)
□ CSV source dans data/
□ config.ini adapté (chemins, identifiants)
□ feeder.py lancé → logs/feeder.txt ✓
□ processor.py lancé → logs/processor.txt ✓
□ datamart.py lancé → logs/datamart.txt ✓
□ requirements.txt installé
□ API lancée : http://localhost:8000
□ Dashboard lancé : http://localhost:8501
□ Token JWT obtenu : /auth/login
□ Requête API fonctionnelle : GET /datamarts/*
□ Dashboard affiche données
```

---

## 📈 Extensibilité

Pour ajouter une nouvelle fonctionnalité :

1. **Nouveau datamart :** Ajouter fonction dans `datamart.py`
2. **Nouveau endpoint API :** Ajouter route dans `api/app.py`
3. **Nouvelle page dashboard :** Ajouter section dans `dashboard/app.py`
4. **Nouvelle transformation :** Modifier `processor.py`
5. **Nouveau paramètre config :** Ajouter section dans `config/config.ini`

---

## 📚 Documentation par Thème

| Thème | Fichier |
|-------|---------|
| Démarrage rapide | GUIDE_DEMARRAGE.md |
| Jointures + Agrégations | TRANSFORMATIONS.md |
| Window Functions | WINDOW_FUNCTIONS.md |
| Configuration complète | README.md |
| Tests API | GUIDE_DEMARRAGE.md |
| Troubleshooting | README.md |

---

**Dernière mise à jour :** 24 mai 2026

