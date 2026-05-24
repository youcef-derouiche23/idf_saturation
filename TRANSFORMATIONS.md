# 🔄 Transformations Données - Documentation Détaillée

Ce document explique toutes les transformations dans la couche Silver.

---

## 📊 Pipeline Complet

```
CSV (Raw)
   ↓
FEEDER : Ingest CSV → Parquet /raw/hdfs
   ↓
PROCESSOR : 
   - Load /raw/parquet
   - JOINTURES
   - AGRÉGATIONS
   - WINDOW FUNCTIONS
   - Write Hive Silver
   ↓
HIVE TABLE : silver.validations_enrichies
   ↓
DATAMART :
   - Read silver
   - Create 4 Gold datamarts
   - Write PostgreSQL
   ↓
4 DATAMARTS PostgreSQL
   ↓
API REST + Streamlit Dashboard
```

---

## 🔗 Jointures (Processor)

### Jointure 1 : Validations ↔ Stations

**Objectif :** Enrichir chaque validation avec infos station (nom, zone, géolocalisation)

**Clé :** `id_station`

```python
df_joined = df_validations.join(
    df_stations,
    on="id_station",
    how="left"
)
```

**Before :**
```
validations :
| date       | heure | id_station | ligne | nb_validations |
| 2025-01-01 | 7     | 101        | M1    | 1200           |

stations :
| id_station | nom_station  | ligne | zone_tarifaire | latitude | longitude |
| 101        | Châtelet    | M1    | 1              | 48.8606  | 2.3469    |
```

**After :**
```
| date       | heure | id_station | ligne | nb_validations | nom_station  | zone_tarifaire | latitude | longitude |
| 2025-01-01 | 7     | 101        | M1    | 1200           | Châtelet    | 1              | 48.8606  | 2.3469    |
```

**SQL Équivalent :**
```sql
SELECT 
    v.date, v.heure, v.id_station, v.ligne, v.nb_validations,
    s.nom_station, s.zone_tarifaire, s.latitude, s.longitude
FROM validations v
LEFT JOIN stations s ON v.id_station = s.id_station;
```

### Jointure 2 : Result ↔ Régularité

**Objectif :** Ajouter taux ponctualité et retards

**Clés :** `date + ligne`

```python
df_joined = df_joined.join(
    df_regularite,
    on=["date", "ligne"],
    how="left"
)
```

**Before (résultat jointure 1) :**
```
| date       | heure | id_station | ligne | nom_station | nb_validations |
| 2025-01-01 | 7     | 101        | M1    | Châtelet   | 1200           |

regularite :
| date       | ligne | taux_ponctualite | nb_retards | delai_moyen_minutes |
| 2025-01-01 | M1    | 97.5             | 12         | 5.2                 |
```

**After :**
```
| date       | heure | id_station | ligne | nom_station | nb_validations | taux_ponctualite | nb_retards | delai_moyen_minutes |
| 2025-01-01 | 7     | 101        | M1    | Châtelet   | 1200           | 97.5             | 12         | 5.2                 |
```

**SQL Équivalent :**
```sql
SELECT 
    v.date, v.heure, v.id_station, v.ligne, v.nb_validations,
    s.nom_station, s.zone_tarifaire,
    r.taux_ponctualite, r.nb_retards, r.delai_moyen_minutes
FROM validations v
LEFT JOIN stations s ON v.id_station = s.id_station
LEFT JOIN regularite r ON v.date = r.date AND v.ligne = r.ligne;
```

---

## 📈 Agrégations (Enrichissement)

### Agrégation 1 : Jour de la Semaine

**Code Spark :**
```python
df_joined = df_joined.withColumn(
    "jour_semaine", 
    F.dayofweek(F.col("date"))  # 1=Sun, 2=Mon, ..., 7=Sat
)

df_joined = df_joined.withColumn(
    "jour_nom",
    F.when(F.col("jour_semaine") == 1, "Dimanche")
     .when(F.col("jour_semaine") == 2, "Lundi")
     ...
)
```

**Résultat :**
```
| date       | jour_semaine | jour_nom |
| 2025-01-01 | 4            | Mercredi |
| 2025-01-02 | 5            | Jeudi    |
```

### Agrégation 2 : Détection Vacances

**Code Spark :**
```python
df_joined = df_joined.withColumn(
    "est_vacances",
    F.when(
        (F.month(F.col("date")).isin(7, 8)) |  # Juillet-août
        ((F.month(F.col("date")) == 12) & (F.dayofmonth(F.col("date")) >= 20)) |  # 20 déc - 31 déc
        (F.month(F.col("date")).isin(2, 4)),  # Février, avril
        1
    ).otherwise(0)
)
```

**Résultat :**
```
| date       | est_vacances |
| 2025-07-15 | 1 (été)      |
| 2025-12-25 | 1 (Noël)     |
| 2025-03-10 | 0 (normal)   |
```

---

## 🔢 Window Functions (Enrichissement)

### Window 1 : RANK Stations par Ligne/Heure

**Objectif :** Classer stations par fréquentation

```python
w_rank = Window.partitionBy("ligne", "heure").orderBy(F.desc("nb_validations"))
df_enriched = df_enriched.withColumn(
    "rank_station_par_ligne",
    F.rank().over(w_rank)
)
```

**Résultat :**
```
Ligne M1, Heure 7h :
| nom_station  | nb_validations | rank |
| Châtelet    | 2800           | 1 ← Plus fréquentée à 7h
| La Défense  | 2600           | 2 |
| Palais Royal| 2400           | 3 |

Ligne M1, Heure 8h :
| nom_station  | nb_validations | rank |
| Châtelet    | 3200           | 1 ← Plus fréquentée à 8h
```

### Window 2 : LAG Évolution Semaine

**Objectif :** Comparer vs 7 jours avant

```python
w_lag = Window.partitionBy("id_station", "heure").orderBy(F.col("date"))
df_enriched = df_enriched.withColumn(
    "nb_validations_semaine_precedente",
    F.lag(F.col("nb_validations"), 7).over(w_lag)
)

df_enriched = df_enriched.withColumn(
    "evolution_pct",
    F.when(
        F.col("nb_validations_semaine_precedente") != 0,
        ((F.col("nb_validations") - F.col("nb_validations_semaine_precedente")) /
         F.col("nb_validations_semaine_precedente") * 100)
    ).otherwise(0)
)
```

**Résultat :**
```
Station 101 (Châtelet), Heure 7h :
| date       | nb_val | nb_val_sem_prev | evolution_pct |
| 2025-01-01 | 1200   | NULL            | 0 (1ère semaine) |
| 2025-01-08 | 1350   | 1200            | +12.5% ↑ |
| 2025-01-15 | 1280   | 1350            | -5.2% ↓ |
```

### Window 3 : ROW_NUMBER Chronologie

**Objectif :** Numéroter chronologiquement par station

```python
w_row = Window.partitionBy("ligne", "id_station").orderBy(F.col("date"), F.col("heure"))
df_enriched = df_enriched.withColumn(
    "row_num_temps",
    F.row_number().over(w_row)
)
```

**Résultat :**
```
| date       | heure | row_num | 
| 2025-01-01 | 0     | 1       |
| 2025-01-01 | 1     | 2       |
| 2025-01-01 | 2     | 3       |
| 2025-01-02 | 0     | 4       |
```

---

## 📋 Table Silver Finale

Après toutes les transformations, la table `silver.validations_enrichies` contient :

```
From validations CSV:
├── date
├── heure
├── id_station
├── ligne
├── nb_validations

From stations (join):
├── nom_station
├── zone_tarifaire
├── zone_geographique
├── latitude
├── longitude

From regularite (join):
├── taux_ponctualite
├── nb_retards
├── delai_moyen_minutes

Computed (enrichissements):
├── jour_semaine (1-7)
├── jour_nom (Lundi, Mardi, etc.)
├── est_vacances (0/1)
├── rank_station_par_ligne (window function)
├── nb_validations_semaine_precedente (window function)
├── evolution_pct (computed)
└── row_num_temps (window function)
```

---

## 🎯 Agrégations vers Datamarts

Après Silver, les datamarts effectuent des **agrégations supplémentaires** :

### DM1 : Fréquentation (Agrégation)

```python
dm1 = df.groupBy("ligne", "id_station", "nom_station", "heure", "jour_semaine", "jour_nom") \
    .agg(
        F.avg("nb_validations").alias("nb_validations_avg"),
        F.max("nb_validations").alias("nb_validations_max"),
        F.min("nb_validations").alias("nb_validations_min"),
        F.count("*").alias("nb_observations")
    )
```

**De :**
```
Silver (1 ligne par date/heure/station) :
| date       | heure | ligne | id_station | nb_validations |
| 2025-01-01 | 7     | M1    | 101        | 1200           |
| 2025-01-02 | 7     | M1    | 101        | 1350           |
| 2025-01-03 | 7     | M1    | 101        | 1280           |
```

**Vers :**
```
DM1 (agrégé par heure/jour) :
| ligne | id_station | heure | jour_semaine | nb_validations_avg | nb_validations_max | nb_observations |
| M1    | 101        | 7     | 2            | 1276.7             | 1350               | 3               |
```

### DM2 : Régularité (Agrégation)

```python
dm2 = df.groupBy("date", "ligne") \
    .agg(
        F.avg("taux_ponctualite").alias("taux_ponctualite_avg"),
        F.sum("nb_retards").alias("nb_retards_total"),
        F.avg("delai_moyen_minutes").alias("delai_moyen")
    )
```

### DM3 : Évolution (Agrégation)

```python
dm3 = df.groupBy("date", "jour_semaine", "est_vacances", "ligne", "id_station") \
    .agg(
        F.sum("nb_validations").alias("nb_validations_cumul"),
        F.avg("evolution_pct").alias("evolution_vs_semaine_precedente_pct")
    )
```

### DM4 : Saturation ML (Pas d'agrégation, juste features)

```python
dm4 = df.select(
    "date", "heure", "ligne", "id_station", "nb_validations",
    "taux_ponctualite", "jour_semaine", "est_vacances", "jour_ferie",
    "rank_station_par_ligne"
).withColumn(
    "est_saturation",
    F.when(F.col("nb_validations") > 5000, 1).otherwise(0)  # Label
)
```

---

## 📊 Diagramme Relationnel

```
validations_enrichies (Silver) [1 ligne par date/heure/station]
    ├─► dm_frequentation_par_station_ligne [Agrégée par heure/jour/station]
    ├─► dm_regularite_par_ligne [Agrégée par date/ligne]
    ├─► dm_evolution_frequentation [Agrégée par date/ligne/station]
    └─► dm_saturation_ml [Non agrégée, features pour ML]
```

---

## 🔍 Vérification des Transformations

### Test Jointures

```sql
-- Vérifier pas de lignes perdues après jointure
SELECT 
    COUNT(*) as total_validations,
    COUNT(DISTINCT id_station) as stations_with_names,
    COUNT(CASE WHEN nom_station IS NOT NULL THEN 1 END) as stations_enriched
FROM silver.validations_enrichies;
-- Devrait avoir stations_enriched ≈ total_validations
```

### Test Agrégations Jour/Vacances

```sql
SELECT DISTINCT jour_semaine, jour_nom FROM silver.validations_enrichies;
-- Devrait avoir 7 jours (1-7)

SELECT DISTINCT est_vacances FROM silver.validations_enrichies;
-- Devrait avoir 0 et 1
```

### Test Window Functions

```sql
SELECT ligne, heure, MAX(rank_station_par_ligne) as max_rank
FROM silver.validations_enrichies
GROUP BY ligne, heure;
-- Devrait avoir max_rank = nombre de stations par ligne/heure

SELECT COUNT(*) FROM silver.validations_enrichies WHERE evolution_pct IS NOT NULL;
-- Devrait avoir 0 pour première semaine, > 0 ensuite
```

---

## 📈 Performance

Optimisations recommandées :

```python
# ❌ Lent : jointures multiples
df = df1.join(df2, "key1").join(df3, "key2").join(df4, "key3")

# ✅ Rapide : réduire colonnes avant jointure
df1_reduced = df1.select("key1", "value1")
df2_reduced = df2.select("key1", "value2")
df = df1_reduced.join(df2_reduced, "key1")

# ✅ Très rapide : broadcast petite table
from pyspark.sql.functions import broadcast
df = large_df.join(broadcast(small_df), "key")
```

---

## 📚 Ressources

- PySpark Transformations : https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/dataframe.html
- Window Functions : https://spark.apache.org/docs/latest/sql-ref-window-functions.html

