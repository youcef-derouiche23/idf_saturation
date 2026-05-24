# 📊 Projet Big Data : Analyse de la Fréquentation et Régularité du Réseau Ferré Île-de-France

## 🎯 Objectif

Analyser la **saturation** et la **régularité** du réseau ferré (métro/RER) en Île-de-France en utilisant une **data platform moderne** avec :
- Ingestion CSV
- Transformation des données
- API REST sécurisée (JWT)
- Dashboard interactif (Streamlit)
- Datamarts pour ML

---

## 📂 Fichiers CSV intégrés

Vous avez ajouté **4 fichiers CSV** dans le dossier `data/` :

| Fichier | Description | Source |
|---------|-------------|--------|
| **arrets.csv** | Référentiel des stations/arrêts | IDFM Open Data |
| **validations-reseau-ferre-profils-horaires-par-jour-type-3eme-trimestre.csv** | Validations par heure et type de jour | IDFM Open Data |
| **histo-validations-reseau-ferre.csv** | Historique des validations par année | IDFM Open Data |
| **ponctualite-mensuelle-transilien.csv** | Ponctualité mensuelle des lignes | IDFM Open Data |

---

## 🚀 Démarrage Rapide (Version Locale)

### Prérequis
- Python 3.8+
- PostgreSQL 12+ (ou Docker)
- pip

### Installation

```bash
# 1. Cloner/accéder au projet
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation

# 2. Installer les dépendances
pip install -r requirements.txt

# 3. Démarrer PostgreSQL (via Docker)
docker run --name postgres-idfm -e POSTGRES_PASSWORD=idfm_pass \
  -e POSTGRES_USER=idfm_user -e POSTGRES_DB=idfm_datamarts \
  -p 5433:5432 -d postgres:15

# 4. Charger les données CSV
python data_loader.py --config config/config.ini

# 5. Lancer l'API (terminal 1)
cd api
python -m uvicorn app:app --reload --port 8000

# 6. Lancer le dashboard (terminal 2)
streamlit run dashboard/app.py
```

### URLs d'accès

| Service | URL | Identifiants |
|---------|-----|------|
| **API Docs** | http://localhost:8000/docs | - |
| **API Health** | http://localhost:8000/ | - |
| **Dashboard** | http://localhost:8501 | - |

### Authentification API

Pour utiliser les endpoints sécurisés, authentifiez-vous d'abord :

```bash
# Obtenir un token JWT
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"

# Utiliser le token
curl http://localhost:8000/data/stations \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📡 Endpoints API

### Public (sans authentification)

```
GET  /                    Santé de l'API
```

### Authentification

```
POST /auth/login          Obtenir un token JWT
```

### Données Brutes (avec JWT)

```
GET  /data/stations                 Lister toutes les stations
GET  /data/validations?ligne=100    Validations (optionnel: filtrer par ligne)
GET  /data/regularite?ligne=100     Régularité (optionnel: filtrer par ligne)
```

### Statistiques (avec JWT)

```
GET  /stats/lignes        Statistiques agrégées par ligne
GET  /stats/stations      Top 50 stations par fréquentation
```

### Datamarts (avec JWT)

```
GET  /datamarts/frequentation-stations      Fréquentation par station/ligne
GET  /datamarts/regularite-lignes           Régularité inter-lignes
GET  /datamarts/evolution-temporelle        Évolution temporelle
GET  /datamarts/saturation-ml               Features pour ML
```

---

## 🏗️ Architecture

### Version Locale (actuelle)

```
CSV Files (data/)
    ↓
data_loader.py
    ↓
PostgreSQL DB
    ├─ stations
    ├─ validations
    └─ regularite
    ↓
API REST (FastAPI)
    ↓
Dashboard (Streamlit)
```

### Version Big Data (Spark/HDFS)

```
CSV Files
    ↓
feeder.py (ingestion)
    ↓
HDFS/Parquet (raw)
    ↓
processor.py (transformation)
    ↓
HDFS/Parquet (silver)
    ↓
datamart.py (agrégation)
    ↓
PostgreSQL (datamarts gold)
    ↓
API + Dashboard
```

---

## 🔄 Pipeline de Données

### 1. Ingestion (data_loader.py)

Lit les CSV et les charge directement en PostgreSQL :

- **Stations** : `data/arrets.csv` → table `stations`
- **Validations** : `data/validations-...csv` → table `validations`
- **Régularité** : `data/ponctualite-...csv` → table `regularite`

### 2. Transformation (processor.py - optionnel)

- Jointures entre validations ↔ stations ↔ régularité
- Agrégations (SUM, AVG, COUNT)
- Window functions (RANK, LAG, ROW_NUMBER)

### 3. Datamarts (datamart.py - optionnel)

Crée 4 tables **Gold** optimisées pour l'analyse :

| Datamart | Colonnes | Cas d'usage |
|----------|----------|------------|
| **dm_frequentation_par_station_ligne** | ligne, id_station, heure, nb_validations, rang | Top stations par ligne |
| **dm_regularite_par_ligne** | ligne, date, taux_ponctualite, rang | Comparaison régularité |
| **dm_evolution_frequentation** | date, ligne, nb_validations, variation_vs_semaine_precedente | Tendances |
| **dm_saturation_ml** | date, heure, ligne, station, features, est_saturation (label) | Prédiction ML |

---

## 📊 Structure de Base de Données

### Table `stations`
```sql
CREATE TABLE stations (
    id_station INTEGER PRIMARY KEY,
    nom_station VARCHAR(255),
    ville VARCHAR(255),
    zone_tarifaire VARCHAR(10),
    accessibilite VARCHAR(50),
    localisation VARCHAR(255)
);
```

### Table `validations`
```sql
CREATE TABLE validations (
    id SERIAL PRIMARY KEY,
    ligne VARCHAR(50),
    id_station INTEGER REFERENCES stations(id_station),
    nom_station VARCHAR(255),
    heure VARCHAR(10),                    -- Format "10H-11H"
    pct_validations FLOAT,
    type_jour VARCHAR(10),                -- DIJFP, DIMANCHE, etc.
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Table `regularite`
```sql
CREATE TABLE regularite (
    id SERIAL PRIMARY KEY,
    date DATE,
    ligne VARCHAR(50),
    nom_ligne VARCHAR(255),
    taux_ponctualite FLOAT,
    ratio_voyageurs_retard FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🛠️ Configuration

Fichier : `config/config.ini`

```ini
[local]
validations_csv_path  = ./data/validations-reseau-ferre-...csv
stations_csv_path     = ./data/arrets.csv
regularite_csv_path   = ./data/histo-validations-reseau-ferre.csv
ponctualite_csv_path  = ./data/ponctualite-mensuelle-transilien.csv
log_dir               = ./logs

[api]
host                  = 0.0.0.0
port                  = 8000
db_host               = localhost
db_port               = 5433
db_name               = idfm_datamarts
db_user               = idfm_user
db_password           = idfm_pass
```

---

## 📝 Fichiers Clés du Projet

| Fichier | Description |
|---------|-------------|
| **data_loader.py** | Ingestion CSV → PostgreSQL (local) |
| **feeder.py** | Ingestion CSV → HDFS (Spark) |
| **processor.py** | Transformation données (Spark) |
| **datamart.py** | Création datamarts (Spark) |
| **api/app.py** | API REST FastAPI |
| **api/models.py** | Schémas Pydantic |
| **api/database.py** | Gestion connexion PostgreSQL |
| **api/auth.py** | Authentification JWT |
| **dashboard/app.py** | Dashboard Streamlit |

---

## 🔒 Authentification JWT

L'API utilise **JWT** pour sécuriser les endpoints `/datamarts` et `/data` :

1. **Obtenir un token** :
   ```bash
   curl -X POST http://localhost:8000/auth/login \
     -d "username=admin&password=admin"
   ```

2. **Utiliser le token** :
   ```bash
   curl http://localhost:8000/data/stations \
     -H "Authorization: Bearer <token>"
   ```

**Identifiants par défaut** :
- Username: `admin`
- Password: `admin`

---

## 🐛 Dépannage

### "Could not connect to database"
- Vérifier que PostgreSQL est en écoute sur `localhost:5433`
- Vérifier les identifiants dans `config/config.ini`

### "CSV file not found"
- Vérifier que les chemins dans `config/config.ini` sont corrects
- Les chemins doivent être relatifs au répertoire racine du projet

### "UTF-8 encoding errors"
- Les fichiers CSV IDFM ont le BOM UTF-8
- `data_loader.py` gère cela automatiquement

### API répond 401 "Unauthorized"
- Vérifier que vous envoyez un token JWT valide
- Token obtenu via `/auth/login`

---

## 📈 Cas d'Usage

### 1. Identifier les stations saturées
```bash
curl http://localhost:8000/stats/stations \
  -H "Authorization: Bearer <token>" | python -m json.tool
```

### 2. Comparer la régularité des lignes
```bash
curl http://localhost:8000/data/regularite \
  -H "Authorization: Bearer <token>" | python -m json.tool
```

### 3. Obtenir features pour modèle ML
```bash
curl http://localhost:8000/datamarts/saturation-ml \
  -H "Authorization: Bearer <token>"
```

---

## 📚 Documentation Complémentaire

- **GUIDE_DEMARRAGE_CSV.md** : Guide détaillé avec données CSV
- **README.md** : Documentation générale
- **STRUCTURE_COMPLETE.md** : Détail des tables et colonnes
- **TRANSFORMATIONS.md** : Description des transformations Spark
- **WINDOW_FUNCTIONS.md** : Exemples de window functions
- **Swagger/OpenAPI** : http://localhost:8000/docs (une fois l'API lancée)

---

## ✅ Checklist de Démarrage

- [ ] Python 3.8+ installé
- [ ] PostgreSQL 12+ (Docker ou local)
- [ ] Dépendances installées : `pip install -r requirements.txt`
- [ ] PostgreSQL en écoute sur `localhost:5433`
- [ ] Données chargées : `python data_loader.py --config config/config.ini`
- [ ] API lancée : `cd api && uvicorn app:app --reload`
- [ ] Dashboard accessible : http://localhost:8501
- [ ] Tests API : http://localhost:8000/docs

---

## 🚀 Prochaines Étapes

1. **Charger les données** : `python data_loader.py --config config/config.ini`
2. **Explorer l'API** : Ouvrir http://localhost:8000/docs
3. **Visualiser les données** : Lancer le dashboard Streamlit
4. **Créer des datamarts** : Exécuter `datamart.py` (Spark)
5. **Entraîner un modèle ML** : Utiliser le datamart `dm_saturation_ml`

---

**Thème** : Analyse de la fréquentation et régularité du réseau ferré Île-de-France  
**Année** : 2025-2026  
**Dernière mise à jour** : 24 mai 2026
