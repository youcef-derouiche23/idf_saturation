# 🚀 GUIDE D'EXÉCUTION - PIPELINE SPARK COMPLET

## 📋 Résumé

Ce guide t'explique comment lancer le **pipeline Big Data complet** avec **Spark** :
```
feeder.py → processor.py → datamart.py → API → Dashboard
```

---

## ✅ Vérifications Préalables

### 1️⃣ Vérifier que Spark est installé

```bash
spark-submit --version
# Devrait afficher: Spark 3.x.x
```

### 2️⃣ Vérifier que les CSV sont valides

```bash
python3 test_csv_files.py

# Résultat attendu:
# ✅ arrets.csv
# ✅ validations-reseau-ferre-...csv
# ✅ ponctualite-mensuelle-transilien.csv
# ✅ histo-validations-reseau-ferre.csv
```

### 3️⃣ Vérifier la configuration

```bash
cat config/config.ini | grep -A 10 "\[local\]"

# Vérifier les chemins des CSV
```

---

## 🔥 Lancer le Pipeline Spark

### Option 1 : Pipeline Complet (feeder → processor → datamart)

```bash
# Configurer l'environnement Spark
source setup_spark_env.sh

# Lancer le pipeline
bash run_spark_pipeline.sh

# Cela lancera:
# ✅ feeder.py      : Ingestion CSV → Parquet/HDFS (/raw)
# ✅ processor.py   : Transformation → Hive (/silver)
# ✅ datamart.py    : 4 datamarts → PostgreSQL (gold)
```

**Durée estimée** : 5-10 minutes selon ton système

### Option 2 : Lancer chaque étape individuellement

#### Étape 1️⃣ : FEEDER (Ingestion)

```bash
spark-submit --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  feeder.py --config config/config.ini
```

**Résultat** : Fichiers Parquet dans `/raw` (HDFS local)
- `/raw/validations`
- `/raw/stations`
- `/raw/regularite`

#### Étape 2️⃣ : PROCESSOR (Transformation)

```bash
spark-submit --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  processor.py --config config/config.ini
```

**Résultat** : Table Hive Silver
- `silver.validations_enrichies` (avec jointures + agrégations + window functions)

#### Étape 3️⃣ : DATAMART (Création des tables Gold)

```bash
spark-submit --master local[*] \
  --driver-memory 4g \
  --executor-memory 4g \
  datamart.py --config config/config.ini
```

**Résultat** : 4 tables PostgreSQL
- `dm_frequentation_par_station_ligne`
- `dm_regularite_par_ligne`
- `dm_evolution_frequentation`
- `dm_saturation_ml`

### Option 3 : Sauter certaines étapes

```bash
# Relancer processor et datamart (skip feeder)
bash run_spark_pipeline.sh --skip-feeder

# Relancer uniquement datamart (skip feeder et processor)
bash run_spark_pipeline.sh --skip-feeder --skip-processor
```

---

## 📊 Architecture du Pipeline

```
┌─────────────────────────────────────────────────────┐
│  FEEDER.PY - Ingestion (feeder.py)                  │
│  ▼                                                   │
│  Lit CSV → Spark DataFrame → Parquet HDFS           │
│  Sortie: /raw/validations, /raw/stations, /raw/regularite
└─────────────────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  PROCESSOR.PY - Transformation (processor.py)       │
│  ▼                                                   │
│  Jointures: validations ↔ stations ↔ régularité     │
│  Agrégations: SUM, AVG, COUNT                        │
│  Window Functions: RANK, LAG, ROW_NUMBER            │
│  Sortie: Hive Silver (validations_enrichies)        │
└─────────────────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  DATAMART.PY - Datamarts (datamart.py)              │
│  ▼                                                   │
│  Crée 4 tables PostgreSQL:                          │
│  1. dm_frequentation_par_station_ligne              │
│  2. dm_regularite_par_ligne                         │
│  3. dm_evolution_frequentation                      │
│  4. dm_saturation_ml (pour ML)                      │
└─────────────────────────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────┐
│  API REST + DASHBOARD                               │
│  ▼                                                   │
│  API: http://localhost:8000/docs                    │
│  Dashboard: http://localhost:8501                   │
└─────────────────────────────────────────────────────┘
```

---

## 📝 Outputs et Logs

### Fichiers de log

Les logs sont sauvegardés dans `logs/` :

```bash
# Voir tous les logs
ls -lh logs/

# Logs les plus récents
tail -f logs/feeder_*.log
tail -f logs/processor_*.log
tail -f logs/datamart_*.log
```

### Vérifier les données dans Spark

Tu peux inspecter les données via Spark SQL:

```bash
spark-shell --conf "spark.sql.parquet.compression.codec=snappy"

# Spark shell commands:
spark.read.parquet("/raw/validations").show(5)
spark.sql("SELECT * FROM silver.validations_enrichies LIMIT 5").show()
```

---

## 🔍 Dépannage

### Erreur: "No such file or directory" pour les CSV

**Cause** : Les chemins dans `config.ini` sont incorrects

**Solution** :
```bash
# Vérifier que les fichiers existent
ls -la data/
cat config/config.ini | grep csv_path
```

### Erreur: "Connection refused" pour PostgreSQL

**Cause** : PostgreSQL n'est pas en écoute

**Solution** :
```bash
# Vérifier que PostgreSQL est running
psql -h localhost -p 5433 -U idfm_user -d idfm_datamarts

# Ou lancer via Docker:
docker run --name postgres-idfm -e POSTGRES_PASSWORD=idfm_pass \
  -e POSTGRES_USER=idfm_user -e POSTGRES_DB=idfm_datamarts \
  -p 5433:5432 -d postgres:15
```

### Erreur: "Out of memory" dans Spark

**Cause** : Les paramètres `--driver-memory` et `--executor-memory` sont trop bas

**Solution** :
```bash
# Augmenter la mémoire (si ton système le permet)
spark-submit --master local[*] \
  --driver-memory 8g \
  --executor-memory 8g \
  feeder.py --config config/config.ini
```

### Erreur: Hive/HDFS pas accessible

**Cause** : HDFS/Hive n'est pas configuré

**Solution** : 
- Si tu fais du local (pas HDFS), les fichiers seront sauvegardés localement en `/tmp/spark-warehouse`
- Vérifier `config.ini` pour les chemins HDFS

---

## ✅ Checklist de Succès

- [ ] `spark-submit --version` fonctionne
- [ ] `python3 test_csv_files.py` retourne ✅ 4/4 fichiers
- [ ] Les chemins CSV dans `config.ini` existent
- [ ] PostgreSQL est accessible sur `localhost:5433`
- [ ] `bash run_spark_pipeline.sh` s'exécute sans erreur
- [ ] Les logs indiquent "✓ Feeder ingérées", "✓ Silver créée", "✓ Datamarts créés"
- [ ] Les tables PostgreSQL sont créées (voir logs datamart)

---

## 🎯 Prochaines Étapes (Après Pipeline)

### 1️⃣ Lancer l'API REST

```bash
cd api
pip install -r ../requirements.txt
python -m uvicorn app:app --reload --port 8000
```

Accéder à : http://localhost:8000/docs

### 2️⃣ Lancer le Dashboard

```bash
pip install streamlit plotly pandas
streamlit run dashboard/app.py
```

Accéder à : http://localhost:8501

### 3️⃣ Tester les endpoints API

```bash
# Obtenir un token JWT
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin" | jq -r '.access_token')

# Requêter les datamarts
curl http://localhost:8000/datamarts/frequentation-stations \
  -H "Authorization: Bearer $TOKEN" | jq .
```

---

## 📚 Fichiers Importants

| Fichier | Description |
|---------|-------------|
| `feeder.py` | Ingestion CSV → Parquet |
| `processor.py` | Transformation + agrégations |
| `datamart.py` | Création des 4 datamarts |
| `config/config.ini` | Configuration centralisée |
| `run_spark_pipeline.sh` | Script de lancement complet |
| `logs/` | Fichiers de log |

---

## 🎬 Commande Finale Recommandée

```bash
# Setup
source setup_spark_env.sh

# Lancer tout
bash run_spark_pipeline.sh

# Consulter les résultats
tail -f logs/feeder_*.log
tail -f logs/processor_*.log
tail -f logs/datamart_*.log
```

---

**Bonne chance ! 🚀**

Si tu as des erreurs, envoie-moi les logs et je vais t'aider ! 💪
