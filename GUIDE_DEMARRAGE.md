# 🚀 Guide de Démarrage Rapide

## Quick Start (5 minutes)

### Prérequis
- ✅ Docker Desktop lancé (6-8 Go RAM)
- ✅ Python 3.8+
- ✅ Cluster `docker-hadoop-spark/` accessible

### 1. Démarrer le Cluster

```bash
cd ../docker-hadoop-spark/
docker-compose up -d

# Vérifier
docker-compose ps
```

Attend 30-60 secondes le temps que tous les services démarrent.

### 2. Préparer les Données

```bash
cd ../Projet_IDFM_Frequentation

# Ajouter vos CSV dans data/
cp /chemin/vers/validations_2025.csv data/
cp /chemin/vers/stations_referentiel.csv data/
cp /chemin/vers/regularite_lignes.csv data/
```

### 3. Exécuter le Pipeline

```bash
# Option A : Manuellement (chaque étape)
docker exec spark-master spark-submit --master local[*] feeder.py --config config/config.ini
docker exec spark-master spark-submit --master local[*] processor.py --config config/config.ini
docker exec spark-master spark-submit --master local[*] datamart.py --config config/config.ini

# Option B : Script automatisé (à créer)
bash run_pipeline.sh  # (voir exemple ci-dessous)
```

### 4. Lancer l'API + Dashboard

```bash
# Option A : Automatisé
bash start_api_dashboard.sh

# Option B : Manuel
pip install -r requirements.txt
uvicorn api.app:app --reload &
streamlit run dashboard/app.py
```

### 5. Accéder aux Services

| Service | URL | Login |
|---------|-----|-------|
| 🌐 Dashboard | http://localhost:8501 | - |
| 📡 API Docs | http://localhost:8000/docs | admin/admin |
| 📡 API REST | http://localhost:8000 | admin/admin |
| �� Spark Master | http://localhost:8080 | - |

---

## 📥 Format des Données (CSV)

### validations_2025.csv
```csv
date,heure,id_station,ligne,nb_validations
2025-01-01,07,101,M1,1200
2025-01-01,07,102,M1,950
2025-01-01,08,101,M1,2800
```

### stations_referentiel.csv
```csv
id_station,nom_station,ligne,zone_tarifaire,zone_geographique,latitude,longitude
101,Châtelet,M1,1,Centre,48.8606,2.3469
102,La Défense,RER A,2,Ouest,48.8936,2.2458
```

### regularite_lignes.csv
```csv
date,ligne,taux_ponctualite,nb_retards,delai_moyen_minutes
2025-01-01,M1,97.5,12,5.2
2025-01-01,M2,96.1,18,6.8
```

---

## 🧪 Tester l'API

### 1. Obtenir un Token

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

**Réponse :**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Requête Protégée

```bash
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

curl -X GET "http://localhost:8000/datamarts/frequentation-stations?page=1&page_size=10" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"
```

**Réponse :**
```json
{
  "data": [
    {
      "ligne": "M1",
      "id_station": 101,
      "nom_station": "Châtelet",
      "heure": 7,
      "jour_semaine": 2,
      "jour_nom": "Lundi",
      "nb_validations_avg": 1500.5,
      "nb_validations_max": 2800,
      "nb_validations_min": 1200,
      "nb_observations": 20
    }
  ],
  "total": 1500,
  "page": 1,
  "page_size": 10,
  "total_pages": 150
}
```

### 3. Exporter en CSV

```bash
TOKEN="..."

curl -s -X GET "http://localhost:8000/datamarts/saturation-ml?page_size=50000" \
  -H "Authorization: Bearer $TOKEN" | \
  jq '.data' > ml_features.json

# Convertir en CSV avec pandas
python -c "
import pandas as pd
import json
with open('ml_features.json') as f:
    df = pd.DataFrame(json.load(f))
df.to_csv('ml_features.csv', index=False)
"
```

---

## 🔍 Vérifier les Logs

### Logs Feeder
```bash
docker logs spark-master | grep feeder
# ou
cat logs/feeder.txt
```

### Logs Processor
```bash
docker logs spark-master | grep processor
# ou
cat logs/processor.txt
```

### Logs Datamart
```bash
docker logs spark-master | grep datamart
# ou
cat logs/datamart.txt
```

### Logs API
```bash
# Affichés en console uvicorn
# Chercher les GET/POST /datamarts/*
```

---

## 🐛 Problèmes Courants

### ❌ "Connection refused" API
```bash
# Vérifier que l'API est lancée
ps aux | grep uvicorn

# Relancer
uvicorn api.app:app --reload --host 0.0.0.0 --port 8000
```

### ❌ "No such file" config.ini
```bash
# Vérifier le chemin
ls -la config/config.ini

# Ou spécifier via variable d'environnement
export API_CONFIG=/Users/youcef/Downloads/Projet_IDFM_Frequentation/config/config.ini
```

### ❌ PostgreSQL refuse connexion
```bash
# Vérifier que le container postgres est lancé
docker ps | grep postgres

# Ou vérifier les identifiants dans config.ini
cat config/config.ini | grep postgres
```

### ❌ "Table does not exist"
```bash
# Les datamarts n'ont pas été créés
# Relancer : docker exec spark-master spark-submit ... datamart.py
# Et vérifier les logs
cat logs/datamart.txt
```

### ❌ Streamlit "ModuleNotFoundError"
```bash
# Réinstaller dépendances
pip install --upgrade -r requirements.txt

# Ou venv
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate (Windows)
pip install -r requirements.txt
```

---

## 📊 Vérifier les Datamarts PostgreSQL

```bash
# Accéder au container postgres
docker exec -it postgres psql -U idfm_user -d idfm_datamarts

# Requêtes SQL
SELECT COUNT(*) FROM dm_frequentation_par_station_ligne;
SELECT COUNT(*) FROM dm_regularite_par_ligne;
SELECT COUNT(*) FROM dm_evolution_frequentation;
SELECT COUNT(*) FROM dm_saturation_ml;

# Voir la structure
\d dm_frequentation_par_station_ligne;

# Quitter
\q
```

---

## 🔄 Pipeline Automatisé

Créez `run_pipeline.sh` :

```bash
#!/bin/bash

set -e

echo "🚀 Démarrage pipeline complet IDFM"

# Vérifier cluster
if ! docker exec namenode ls / > /dev/null 2>&1; then
    echo "❌ Cluster Hadoop/Spark pas démarré"
    exit 1
fi

echo "✓ Cluster détecté"

# Copier CSVs
echo "📁 Copie des CSV dans le cluster..."
docker cp data/validations_2025.csv spark-master:/ 2>/dev/null || true
docker cp data/stations_referentiel.csv spark-master:/ 2>/dev/null || true
docker cp data/regularite_lignes.csv spark-master:/ 2>/dev/null || true

# Pipeline
echo "1️⃣  Feeder (ingestion)..."
docker exec spark-master spark-submit --master local[*] feeder.py --config config/config.ini

echo "2️⃣  Processor (transformation)..."
docker exec spark-master spark-submit --master local[*] processor.py --config config/config.ini

echo "3️⃣  Datamart (datamarts)..."
docker exec spark-master spark-submit --master local[*] datamart.py --config config/config.ini

echo "✅ Pipeline terminé !"
echo ""
echo "🌐 Services disponibles :"
echo "   - API : http://localhost:8000"
echo "   - Dashboard : http://localhost:8501"
```

Utilisation :
```bash
chmod +x run_pipeline.sh
./run_pipeline.sh
```

---

## 📚 SQL Utiles

### Fréquentation pic
```sql
SELECT ligne, heure, jour_nom, MAX(nb_validations_max)
FROM dm_frequentation_par_station_ligne
GROUP BY ligne, heure, jour_nom
ORDER BY heure DESC;
```

### Lignes les moins régulières
```sql
SELECT ligne, date, taux_ponctualite_avg, nb_retards_total
FROM dm_regularite_par_ligne
WHERE taux_ponctualite_avg < 95
ORDER BY taux_ponctualite_avg ASC;
```

### Evolution vacances
```sql
SELECT est_vacances, jour_nom, AVG(nb_validations_cumul)
FROM dm_evolution_frequentation
GROUP BY est_vacances, jour_nom;
```

### Dataset ML (export)
```sql
SELECT * FROM dm_saturation_ml
WHERE est_saturation = 1
ORDER BY date DESC
LIMIT 10000;
```

---

## 🎯 Prochaines Étapes

1. **Entraîner un modèle ML** (sklearn, XGBoost)
   - Features : dm_saturation_ml
   - Target : est_saturation
   - Cross-validation

2. **Ajouter des visualisations** (Streamlit)
   - Prédictions modèle
   - Confidence scores
   - Feature importance

3. **Pipeline ML** (MLflow, Airflow)
   - Automatiser réentraînement
   - Monitoring drift données

4. **API prédictive**
   - POST /predict/{ligne}/{station}/{heure}
   - Retourner probabilité saturation

---

## 📞 Support

- 📖 Voir README.md pour documentation complète
- 🔗 Issues : Vérifier les logs dans `logs/`
- 🧠 Architecture : Schema médaillon dans README.md

