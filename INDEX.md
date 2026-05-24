# 🚇 Projet Big Data IDFM - Index Principal

**Analyse de la Fréquentation et Régularité du Réseau Ferré Île-de-France**

> Métro/RER 2025 • Architecture Médaillon • Spark + Hive + PostgreSQL + FastAPI + Streamlit

---

## 🎯 Au Démarrage

**Je veux lancer rapidement le projet :**
→ **Voir : [GUIDE_DEMARRAGE.md](GUIDE_DEMARRAGE.md)**

**Je veux comprendre l'architecture :**
→ **Voir : [README.md](README.md)** (sections Architecture + Stack)

**Je veux voir la structure fichiers :**
→ **Voir : [STRUCTURE_COMPLETE.md](STRUCTURE_COMPLETE.md)**

---

## 📚 Documentation Complète

### 1. 🚀 [README.md](README.md)
**La bible du projet** (~500 lignes)

Sections principales :
- ✅ Contexte + Problématique métier (3 sous-questions)
- ✅ Architecture médaillon (Raw → Silver → Gold)
- ✅ Stack technique (9 technologies)
- ✅ Structure fichiers (18 fichiers/dossiers)
- ✅ Données sources (3 CSV)
- ✅ Transformations (jointures + agrégations + window functions)
- ✅ Datamarts détaillés (4 tables PostgreSQL)
- ✅ Lancement étape par étape (6 étapes)
- ✅ API endpoints (6 routes)
- ✅ Configuration + Troubleshooting

**Quand lire :** Première approche du projet

---

### 2. ⚡ [GUIDE_DEMARRAGE.md](GUIDE_DEMARRAGE.md)
**Quick-start** (~300 lignes)

Sections principales :
- ✅ 5 minutes pour démarrer
- ✅ Format CSV attendu (exemples)
- ✅ Test API avec curl
- ✅ Vérification logs
- ✅ Problèmes courants + solutions
- ✅ Pipeline automatisé (script shell)
- ✅ SQL utiles
- ✅ Prochaines étapes ML

**Quand lire :** Tu as 15 minutes et tu veux tout lancer

---

### 3. 🔄 [TRANSFORMATIONS.md](TRANSFORMATIONS.md)
**Données brutes → Silver → Gold** (~400 lignes)

Sections principales :
- ✅ Pipeline complet (diagramme)
- ✅ Jointure 1 : validations ↔ stations
- ✅ Jointure 2 : validations ↔ régularité
- ✅ Agrégations : jour semaine, vacances
- ✅ Window functions : RANK, LAG, ROW_NUMBER
- ✅ Table Silver finale (colonnes)
- ✅ Agrégations datamarts
- ✅ Diagramme relationnel
- ✅ Vérification transformations (requêtes SQL)
- ✅ Performance

**Quand lire :** Tu veux comprendre les jointures/agrégations

---

### 4. 📊 [WINDOW_FUNCTIONS.md](WINDOW_FUNCTIONS.md)
**Window Functions expliquées** (~350 lignes)

Sections principales :
- ✅ Vue d'ensemble (syntaxe générale)
- ✅ RANK() : classement stations par fréquentation
- ✅ LAG() : évolution vs semaine précédente
- ✅ ROW_NUMBER() : numérotation chronologique
- ✅ DENSE_RANK() : ranking régularité
- ✅ AVG() mobile : moyennes glissantes
- ✅ Exemples pratiques SQL (10 exemples)
- ✅ Comparaisons RANK vs ROW_NUMBER vs DENSE_RANK
- ✅ Performance + optimisations

**Quand lire :** Tu veux maîtriser les window functions Spark SQL

---

### 5. 📁 [STRUCTURE_COMPLETE.md](STRUCTURE_COMPLETE.md)
**Vue d'ensemble fichiers + responsabilités** (~350 lignes)

Sections principales :
- ✅ Organisation répertoires (tree)
- ✅ Description chaque fichier
- ✅ Fichiers Python principaux (feeder, processor, datamart)
- ✅ Fichiers API (auth, models, database, app)
- ✅ Dashboard Streamlit
- ✅ Configuration centralisée
- ✅ Flux données complet (diagramme)
- ✅ Responsabilités par fichier (tableau)
- ✅ Dépendances entre fichiers
- ✅ Extensibilité

**Quand lire :** Tu veux naviguer le code source

---

### 6. 📄 [INDEX.md](INDEX.md)
**Ce fichier** - Vue d'ensemble de toute la doc

---

## 🗂️ Fichiers Principaux

### Ingestion (Raw)
```python
feeder.py
├── Charge CSV sources
├── Ingest vers HDFS Parquet
└── ~7 Ko, 240 lignes
```

### Transformation (Silver)
```python
processor.py
├── Charge Parquet bruts
├── Jointures (validations ↔ stations ↔ régularité)
├── Agrégations (jour semaine, vacances)
├── Window functions (RANK, LAG, ROW_NUMBER)
├── Écriture Hive silver
└── ~10 Ko, 365 lignes
```

### Datamarts (Gold)
```python
datamart.py
├── Charge table silver
├── Crée 4 datamarts
│  ├── DM1 : Fréquentation stations/ligne
│  ├── DM2 : Régularité lignes
│  ├── DM3 : Évolution temporelle
│  └── DM4 : Saturation ML
├── Écriture PostgreSQL
└── ~12 Ko, 329 lignes
```

### API REST
```python
api/
├── __init__.py              # Package
├── auth.py                  # JWT auth (~90 lignes)
├── models.py                # Pydantic (~60 lignes)
├── database.py              # PostgreSQL (~120 lignes)
└── app.py                   # FastAPI (6 endpoints, ~250 lignes)
```

### Dashboard
```python
dashboard/
└── app.py                   # Streamlit (4 pages, ~400 lignes)
```

### Configuration
```ini
config/
└── config.ini               # Tout ce qui change (~50 lignes)
```

### Démarrage
```bash
start_api_dashboard.sh       # Unix/Mac
start_api_dashboard.bat      # Windows
```

---

## 🎓 Parcours d'Apprentissage

### Niveau 1 : Débutant (1-2h)
1. Lis [README.md](README.md) - Contexte + Architecture
2. Lance [GUIDE_DEMARRAGE.md](GUIDE_DEMARRAGE.md) - Quick-start
3. Explore le dashboard Streamlit

### Niveau 2 : Intermédiaire (3-4h)
1. Lis [TRANSFORMATIONS.md](TRANSFORMATIONS.md) - Jointures + Agrégations
2. Lis [WINDOW_FUNCTIONS.md](WINDOW_FUNCTIONS.md) - Window functions
3. Inspecte `processor.py` - Comprendre les transformations

### Niveau 3 : Avancé (5-6h)
1. Lis [STRUCTURE_COMPLETE.md](STRUCTURE_COMPLETE.md) - Ensemble projet
2. Étudie `datamart.py` - Création datamarts
3. Étudie `api/app.py` - Endpoints REST
4. Modifie code pour ajouter une transformation

---

## 🔍 Cheat Sheet Commandes

### Démarrage
```bash
# Cluster Hadoop/Spark
cd ../docker-hadoop-spark
docker-compose up -d

# Pipeline complet
docker exec spark-master spark-submit --master local[*] feeder.py --config config/config.ini
docker exec spark-master spark-submit --master local[*] processor.py --config config/config.ini
docker exec spark-master spark-submit --master local[*] datamart.py --config config/config.ini

# API + Dashboard
bash start_api_dashboard.sh
```

### Test API
```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -d "username=admin&password=admin"

# Requête
curl -H "Authorization: Bearer TOKEN" \
  http://localhost:8000/datamarts/frequentation-stations?page=1&page_size=10
```

### Vérification Données
```bash
# PostgreSQL
docker exec -it postgres psql -U idfm_user -d idfm_datamarts
SELECT COUNT(*) FROM dm_frequentation_par_station_ligne;

# Logs Spark
docker logs spark-master | grep -E "feeder|processor|datamart"
cat logs/feeder.txt  # Ou processor.txt, datamart.txt
```

---

## 📊 Les 4 Datamarts Expliqués Vite

| N° | Nom | Colonnes clés | Cas d'usage |
|----|----|---------------|-----------|
| 1 | `dm_frequentation_par_station_ligne` | ligne, heure, jour_semaine, nb_validations_avg/max/min, rank_station | Stations pics par ligne/créneau |
| 2 | `dm_regularite_par_ligne` | ligne, date, taux_ponctualite_avg, nb_retards_total, rang_regularite | Lignes problématiques |
| 3 | `dm_evolution_frequentation` | date, jour_semaine, est_vacances, nb_validations_cumul, evolution_pct | Tendances, impact vacances |
| 4 | `dm_saturation_ml` | date, heure, nb_validations, taux_ponctualite, jour_semaine, est_vacances, **est_saturation** | Features ML + label |

---

## 🎯 Problématiques Répondues

### Q1 : Stations fréquentées par ligne/créneau ?
**→ Datamart 1 + Dashboard page 1**
```
Top 3 stations ligne M1 à 8h : Châtelet (3200), La Défense (3100), Palais Royal (2900)
```

### Q2 : Lignes moins régulières ?
**→ Datamart 2 + Dashboard page 2**
```
Ranking régularité jour X :
1️⃣ M2 (92.1%) ← Pire
2️⃣ M4 (93.5%)
3️⃣ RER B (96.8%)
4️⃣ M1 (97.5%) ← Meilleur
```

### Q3 : Évolution fréquentation selon jour/vacances ?
**→ Datamart 3 + Dashboard page 3**
```
Lundi-Vendredi : 2500 validations/heure (moyen)
Samedi-Dimanche : 1200 validations/heure (-52%)
Vacances été : 800 validations/heure (-68%)
```

### Q4 (ML) : Prédire saturation ?
**→ Datamart 4 + Exporter ML**
```
Features : nb_validations, taux_ponctualite, jour_semaine, est_vacances, jour_ferie, rank_station
Label : est_saturation (0/1)
→ Entraîner modèle Random Forest / XGBoost
```

---

## 🚀 Prochaines Étapes

1. **Entraîner Modèle ML**
   - Exporter dm_saturation_ml
   - Random Forest / XGBoost
   - Cross-validation + GridSearchCV

2. **Endpoint Prédictif**
   - POST /predict/{ligne}/{station}/{heure}
   - Retourne prob(saturation)

3. **Monitoring Temps Réel**
   - MLflow pour suivi modèles
   - Alertes saturation (webhook)
   - Retraining automatique

4. **Orchestration**
   - Apache Airflow pour pipeline
   - Scheduling quotidien
   - Notifications Slack

---

## ❓ FAQ Rapide

**Q: Où modifier la config ?**
→ `config/config.ini`

**Q: Où voir les logs ?**
→ `logs/` (feeder.txt, processor.txt, datamart.txt)

**Q: Comment ajouter un endpoint API ?**
→ Modifier `api/app.py` (ajouter fonction avec `@app.get()`)

**Q: Comment ajouter un graphique dashboard ?**
→ Modifier `dashboard/app.py` (ajouter avec `plotly`)

**Q: Seuil saturation (5000) me convient pas ?**
→ Modifier `config/config.ini` [thresholds] saturation_threshold

**Q: Mes données arrivent où ?**
→ `/raw` (HDFS) → `/silver` (Hive) → PostgreSQL

---

## 📖 Ressources Externes

- **Spark SQL** : https://spark.apache.org/docs/latest/sql-programming-guide.html
- **PySpark API** : https://spark.apache.org/docs/latest/api/python/
- **Window Functions** : https://spark.apache.org/docs/latest/sql-ref-window-functions.html
- **FastAPI** : https://fastapi.tiangolo.com/
- **Streamlit** : https://docs.streamlit.io/
- **PostgreSQL** : https://www.postgresql.org/docs/

---

## 📞 Support

| Besoin | Fichier | Section |
|--------|---------|---------|
| Démarrage rapide | GUIDE_DEMARRAGE.md | Tout |
| Architecture | README.md | Architecture (Médaillon) |
| Jointures/Agrégations | TRANSFORMATIONS.md | Jointures + Agrégations |
| Window Functions | WINDOW_FUNCTIONS.md | Tout |
| Structure code | STRUCTURE_COMPLETE.md | Fichiers Détaillés |
| Configuration | README.md | Configuration |
| API | README.md | API REST |
| Dashboard | README.md | Dashboard Streamlit |
| Erreurs | GUIDE_DEMARRAGE.md | Problèmes Courants |

---

## 📋 Fichiers à Personaliser

```
[ ] Noms auteurs dans README.md
[ ] Données sources CSV dans data/
[ ] Secret key config.ini [api] secret_key
[ ] Identifiants PostgreSQL si changés
[ ] Seuils config.ini [thresholds]
```

---

## ✅ Checklist Avant Production

```
[ ] Requirements.txt installé (pip install -r requirements.txt)
[ ] Cluster Hadoop/Spark stable
[ ] PostgreSQL accessible et vide
[ ] CSV sources valides et chargés
[ ] Config.ini adapté à l'environnement
[ ] Logs feeder.txt sans erreurs
[ ] Logs processor.txt sans erreurs
[ ] Logs datamart.txt sans erreurs
[ ] PostgreSQL datamarts remplis
[ ] API endpoints accessibles
[ ] Dashboard affiche données
[ ] JWT token valide
[ ] Pagination fonctionne
```

---

## 🎓 Version du Projet

- **Date** : 24 mai 2026
- **Thème** : Analyse Fréquentation Réseau Ferré IDFM
- **Stack** : Spark + Hive + PostgreSQL + FastAPI + Streamlit
- **Fichiers** : 18 fichiers + 5 docs
- **Lignes code** : ~1900 lignes Python
- **Lignes doc** : ~2000 lignes Markdown
- **Taille** : 156 KB

---

**Bienvenue dans le projet ! 🚇 Bon data engineering ! 📊**

