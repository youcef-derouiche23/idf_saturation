# 🚀 PIPELINE IDFM - GUIDE COMPLET D'EXÉCUTION

## 📊 Vue d'ensemble

Tu as **deux options** pour lancer le pipeline :

### **Option A : Pipeline Local Simple** (✅ RECOMMANDÉE - Sans Spark)
- ✅ Fonctionne sur macOS ARM64 sans problèmes
- ✅ Plus rapide et simple
- ✅ Utilise pandas + PostgreSQL
- ⏱️ Durée : 2-5 minutes

### **Option B : Pipeline Spark Complet** (Big Data)
- Pour environnements avec HDFS/Hive configurés
- ⏱️ Durée : 10-15 minutes
- Nécessite JVM configurée

---

## 🎯 OPTION A : Pipeline Local (Recommandé)

### Étape 1 : Préparer PostgreSQL

Si PostgreSQL n'est pas lancé, le démarrer via Docker :

```bash
docker run --name postgres-idfm \
  -e POSTGRES_PASSWORD=idfm_pass \
  -e POSTGRES_USER=idfm_user \
  -e POSTGRES_DB=idfm_datamarts \
  -p 5433:5432 \
  -d postgres:15
```

**Vérifier que PostgreSQL répond :**
```bash
psql -h localhost -p 5433 -U idfm_user -d idfm_datamarts -c "SELECT 1"
# Résultat : 1 (succès)
```

### Étape 2 : Installer les dépendances

```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation
pip install -r requirements.txt
```

### Étape 3 : Lancer le pipeline complet

```bash
bash start_full_pipeline.sh
```

**Ceci va :**
1. ✅ Vérifier PostgreSQL
2. ✅ Valider les fichiers CSV
3. ✅ Installer les dépendances
4. ✅ Lancer `pipeline_local.py`
5. ✅ Créer les 4 datamarts

**Output attendu :**
```
✅ Python3 trouvé
✅ PostgreSQL accessible
✅ TOUS LES FICHIERS SONT VALIDES!
✅ Dépendances installées
✅ Pipeline terminé avec succès!
✅ Données chargées dans PostgreSQL
```

---

## 🔥 OPTION B : Pipeline Spark Complet

### Prérequis

```bash
# Vérifier Spark
spark-submit --version
# Résultat attendu: Spark 3.x.x ou 4.x.x

# Vérifier Python
python3 --version
# Résultat attendu: Python 3.8+
```

### Lancer le pipeline

```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation

# Configuration
source setup_spark_env.sh

# Lancer tout
bash run_spark_pipeline.sh
```

**Ou lancer étape par étape :**
```bash
# Feeder (ingestion)
spark-submit --master local[*] feeder.py --config config/config.ini

# Processor (transformation)
spark-submit --master local[*] processor.py --config config/config.ini

# Datamart (création tables PostgreSQL)
spark-submit --master local[*] datamart.py --config config/config.ini
```

**Ou utiliser le script Python :**
```bash
python3 run_spark_simple.py feeder
python3 run_spark_simple.py processor
python3 run_spark_simple.py datamart
```

---

## ✅ Vérifier que tout fonctionne

### 1️⃣ Vérifier les tables PostgreSQL

```bash
psql -h localhost -p 5433 -U idfm_user -d idfm_datamarts

# Dans la shell psql:
\dt                 # Lister les tables
SELECT COUNT(*) FROM stations;
SELECT COUNT(*) FROM validations;
SELECT COUNT(*) FROM regularite;
SELECT COUNT(*) FROM dm_frequentation_par_station_ligne;
\q                  # Quitter
```

### 2️⃣ Consulter les logs

```bash
# Voir tous les logs
ls -lh logs/

# Lire le dernier log
tail -f logs/pipeline_local_*.log
```

---

## 🌐 Lancer l'API et le Dashboard

### Terminal 1 : API REST

```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation/api
python -m uvicorn app:app --reload --port 8000
```

**Résultat :**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

Accéder à la documentation Swagger :  
📍 http://localhost:8000/docs

### Terminal 2 : Dashboard Streamlit

```bash
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation
streamlit run dashboard/app.py
```

**Résultat :**
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

---

## 📡 Tester l'API

### 1️⃣ Endpoint public (sans auth)

```bash
curl http://localhost:8000/
```

**Résultat :**
```json
{
  "status": "ok",
  "service": "IDFM Fréquentation & Régularité",
  "datamarts": ["frequentation-stations", "regularite-lignes", "evolution-temporelle", "saturation-ml"]
}
```

### 2️⃣ S'authentifier et récupérer un token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

**Résultat :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3️⃣ Requêter les données avec le token

```bash
TOKEN="<votre_token_ici>"

# Stations
curl http://localhost:8000/data/stations \
  -H "Authorization: Bearer $TOKEN" | jq .

# Validations
curl http://localhost:8000/data/validations \
  -H "Authorization: Bearer $TOKEN" | jq .

# Régularité
curl http://localhost:8000/data/regularite \
  -H "Authorization: Bearer $TOKEN" | jq .

# Statistiques par ligne
curl http://localhost:8000/stats/lignes \
  -H "Authorization: Bearer $TOKEN" | jq .

# Top stations
curl http://localhost:8000/stats/stations \
  -H "Authorization: Bearer $TOKEN" | jq .

# Datamart fréquentation
curl http://localhost:8000/datamarts/frequentation-stations?page=1&page_size=10 \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## 📁 Structure du Projet

```
Projet_IDFM_Frequentation/
├── data/                          # Fichiers CSV source
│   ├── arrets.csv
│   ├── validations-reseau-ferre-...csv
│   ├── ponctualite-mensuelle-transilien.csv
│   └── histo-validations-reseau-ferre.csv
│
├── config/
│   └── config.ini                 # Configuration centralisée
│
├── api/
│   ├── app.py                     # API REST (FastAPI)
│   ├── auth.py                    # Authentification JWT
│   ├── database.py                # Connexion PostgreSQL
│   ├── models.py                  # Schémas Pydantic
│   └── __init__.py
│
├── dashboard/
│   └── app.py                     # Dashboard Streamlit
│
├── feeder.py                      # Ingestion CSV → Parquet/HDFS
├── processor.py                   # Transformation Silver (Spark)
├── datamart.py                    # Création 4 datamarts (Spark)
├── pipeline_local.py              # Pipeline local (pandas + PostgreSQL)
│
├── logs/                          # Fichiers de log
├── requirements.txt               # Dépendances Python
│
├── start_full_pipeline.sh         # Script de démarrage complet
├── run_spark_pipeline.sh          # Pipeline Spark
├── setup_spark_env.sh             # Configuration Spark
├── run_spark_simple.py            # Lancement Spark (Python)
├── test_csv_files.py              # Validation CSV
├── data_loader.py                 # Chargement local (deprecated)
│
└── README.md, GUIDE_*.md          # Documentation
```

---

## 🔍 Dépannage

### ❌ "PostgreSQL not accessible"

**Solution :**
```bash
# Lancer PostgreSQL
docker run --name postgres-idfm -e POSTGRES_PASSWORD=idfm_pass \
  -e POSTGRES_USER=idfm_user -e POSTGRES_DB=idfm_datamarts \
  -p 5433:5432 -d postgres:15

# Attendre 5 secondes
sleep 5

# Relancer le pipeline
bash start_full_pipeline.sh
```

### ❌ "CSV file not found"

**Solution :**
```bash
# Vérifier que les CSV existent
ls -la data/

# Vérifier le config.ini
cat config/config.ini | grep csv_path
```

### ❌ "Port 8000 already in use"

**Solution :**
```bash
# Tuer le processus sur le port
lsof -ti:8000 | xargs kill -9

# Relancer l'API
cd api && python -m uvicorn app:app --reload --port 8000
```

### ❌ "ModuleNotFoundError: No module named 'pandas'"

**Solution :**
```bash
# Réinstaller les dépendances
pip install --upgrade -r requirements.txt
```

---

## 📊 Datamarts Créés

| Datamart | Colonnes | Cas d'usage |
|----------|----------|------------|
| **dm_frequentation_par_station_ligne** | ligne, id_station, nom_station, heure, jour_semaine, nb_validations, rank | Top stations par ligne |
| **dm_regularite_par_ligne** | date, ligne, nom_ligne, taux_ponctualite, nb_retards, delai_moyen, rang | Comparaison régularité |
| **dm_evolution_frequentation** | date, jour_semaine, periode_vacances, ligne, id_station, nb_validations_cumul | Tendances temporelles |
| **dm_saturation_ml** | date, heure, ligne, id_station, nb_validations, taux_ponctualite, jour_semaine, is_vacances, jour_ferie, **est_saturation** | Prédiction ML |

---

## 🎯 Checklist de Succès

- [ ] PostgreSQL lancé et accessible (port 5433)
- [ ] `test_csv_files.py` retourne ✅ 4/4 fichiers
- [ ] `start_full_pipeline.sh` s'exécute sans erreur
- [ ] Tables PostgreSQL créées (vérifier avec `\dt`)
- [ ] API lancée sur http://localhost:8000
- [ ] Dashboard accessible sur http://localhost:8501
- [ ] Authentification JWT fonctionne (`/auth/login`)
- [ ] Requêtes API retournent des données (`/data/stations`, etc.)

---

## 📚 Documentation Supplémentaire

| Document | Contenu |
|----------|---------|
| `GUIDE_SPARK_PIPELINE.md` | Guide détaillé pipeline Spark |
| `GUIDE_DEMARRAGE_CSV.md` | Guide intégration CSV |
| `STRUCTURE_COMPLETE.md` | Détail des tables |
| `TRANSFORMATIONS.md` | Transformations Spark |
| `WINDOW_FUNCTIONS.md` | Window functions Spark |

---

## 🚀 Commandes Rapides

```bash
# Setup complet (one-liner)
docker run --name postgres-idfm -e POSTGRES_PASSWORD=idfm_pass \
  -e POSTGRES_USER=idfm_user -e POSTGRES_DB=idfm_datamarts \
  -p 5433:5432 -d postgres:15 && \
sleep 5 && \
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation && \
bash start_full_pipeline.sh

# Terminal 1 : API
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation/api && \
python -m uvicorn app:app --reload --port 8000

# Terminal 2 : Dashboard
cd /Users/youcef/Downloads/Projet_IDFM_Frequentation && \
streamlit run dashboard/app.py

# Tester l'API
curl http://localhost:8000/docs  # Swagger
```

---

**Bonne chance ! 🎉**

Si tu as des questions ou des problèmes, consulte les logs dans `logs/` ou envoie-moi les messages d'erreur !
