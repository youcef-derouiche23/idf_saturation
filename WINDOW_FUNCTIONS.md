# 📊 Window Functions - Documentation Détaillée

Ce document explique les window functions utilisées dans le projet IDFM.

---

## 🎯 Vue d'ensemble

Les Window Functions permettent de :
- Analyser des données par partition (sous-groupes)
- Accéder à des lignes voisines (LAG, LEAD)
- Calculer des rankings, numérotations
- Maintenir le contexte ligne par ligne

### Syntaxe générale

```sql
FUNCTION() OVER (
    [PARTITION BY col1, col2]
    [ORDER BY col3 [ASC|DESC]]
    [ROWS BETWEEN ... AND ...]
)
```

---

## 1️⃣ RANK() - Classement par Fréquentation

### Cas d'usage
Identifier les 3 stations les plus fréquentées **par ligne** et **par heure**.

### Code Spark (processor.py)
```python
w_rank = Window.partitionBy("ligne", "heure").orderBy(F.desc("nb_validations"))
df_enriched = df_enriched.withColumn(
    "rank_station_par_ligne",
    F.rank().over(w_rank)
)
```

### Résultat
```
| ligne | heure | id_station | nom_station | nb_validations | rank_station_par_ligne |
|-------|-------|------------|-------------|----------------|----------------------|
| M1    | 7     | 101        | Châtelet   | 2800           | 1                    |
| M1    | 7     | 102        | La Défense | 2600           | 2                    |
| M1    | 7     | 103        | Palais Royal | 2400         | 3                    |
| M1    | 8     | 101        | Châtelet   | 3200           | 1                    |
```

### SQL équivalent
```sql
SELECT 
    ligne, heure, id_station, nom_station, nb_validations,
    RANK() OVER (PARTITION BY ligne, heure ORDER BY nb_validations DESC) AS rank_station_par_ligne
FROM validations_enrichies;
```

### Différence RANK vs ROW_NUMBER vs DENSE_RANK

```
Nb Validations : 2800, 2600, 2600, 2400

RANK()        : 1, 2, 2, 4   (saute si égalité)
ROW_NUMBER()  : 1, 2, 3, 4   (numérotation simple)
DENSE_RANK()  : 1, 2, 2, 3   (dense, pas de saut)
```

---

## 2️⃣ LAG() - Évolution vs Semaine Précédente

### Cas d'usage
Comparer la fréquentation d'une heure/station avec **la même heure de la semaine précédente** (7 jours avant).

### Code Spark
```python
w_lag = Window.partitionBy("id_station", "heure").orderBy(F.col("date"))
df_enriched = df_enriched.withColumn(
    "nb_validations_semaine_precedente",
    F.lag(F.col("nb_validations"), 7).over(w_lag)  # 7 jours = 1 semaine
)

# Calcul du pourcentage d'évolution
df_enriched = df_enriched.withColumn(
    "evolution_pct",
    F.when(
        F.col("nb_validations_semaine_precedente") != 0,
        ((F.col("nb_validations") - F.col("nb_validations_semaine_precedente")) /
         F.col("nb_validations_semaine_precedente") * 100)
    ).otherwise(0)
)
```

### Résultat
```
| date       | heure | id_station | nb_validations | nb_validations_semaine_prev | evolution_pct |
|------------|-------|------------|----------------|----------------------------|---------------|
| 2025-01-01 | 7     | 101        | 1200           | NULL                       | 0             |
| 2025-01-08 | 7     | 101        | 1350           | 1200                       | +12.5%        |
| 2025-01-15 | 7     | 101        | 1280           | 1350                       | -5.2%         |
```

### SQL équivalent
```sql
SELECT 
    date, heure, id_station, nb_validations,
    LAG(nb_validations, 7) OVER (
        PARTITION BY id_station, heure 
        ORDER BY date
    ) AS nb_validations_semaine_prev,
    
    ROUND(100.0 * (
        nb_validations - LAG(nb_validations, 7) OVER (...)
    ) / LAG(nb_validations, 7) OVER (...), 2) AS evolution_pct
FROM validations_enrichies;
```

### Variantes utiles
```python
# LEAD : voir la ligne SUIVANTE (prédiction)
F.lead(F.col("nb_validations"), 1).over(w_lag)  # Demain

# LEAD multi-jour
F.lead(F.col("nb_validations"), 30).over(w_lag)  # 1 mois

# Différence simple (vs jour précédent)
F.lag(F.col("nb_validations"), 1).over(w_lag)  # Hier
```

---

## 3️⃣ ROW_NUMBER() - Numérotation Chronologique

### Cas d'usage
Numéroter les observations **chronologiquement par station**.
Utile pour pagination, détection anomalies temporelles.

### Code Spark
```python
w_row = Window.partitionBy("ligne", "id_station").orderBy(F.col("date"), F.col("heure"))
df_enriched = df_enriched.withColumn(
    "row_num_temps",
    F.row_number().over(w_row)
)
```

### Résultat
```
| ligne | id_station | nom_station | date       | heure | row_num_temps |
|-------|------------|-------------|------------|-------|---------------|
| M1    | 101        | Châtelet   | 2025-01-01 | 0     | 1             |
| M1    | 101        | Châtelet   | 2025-01-01 | 1     | 2             |
| M1    | 101        | Châtelet   | 2025-01-01 | 2     | 3             |
| M1    | 101        | Châtelet   | 2025-01-02 | 0     | 4             |
```

### Utilité
```sql
-- Détecter données manquantes
SELECT * FROM validations
WHERE row_num_temps != EXTRACT(DAY FROM date) * 24 + EXTRACT(HOUR FROM date);

-- Garder top 10 observations récentes
SELECT * FROM validations
WHERE row_num_temps <= 10;
```

---

## 4️⃣ DENSE_RANK() - Ranking Lignes par Régularité

### Cas d'usage
Classer les **lignes par taux de ponctualité** du jour.
Moins bonne régularité = rang 1, meilleure = rang N.

### Code Spark (dans datamart.py)
```python
w_rank_reg = Window.partitionBy("date").orderBy(F.asc("taux_ponctualite_avg"))
df_regularite = df_regularite.withColumn(
    "rang_regularite",
    F.dense_rank().over(w_rank_reg)  # Dense = pas de saut
)
```

### Résultat
```
| date       | ligne | taux_ponctualite_avg | rang_regularite |
|------------|-------|----------------------|-----------------|
| 2025-01-01 | M2    | 92.1%                | 1 (pire)        |
| 2025-01-01 | M4    | 93.5%                | 2               |
| 2025-01-01 | RER B | 96.8%                | 3               |
| 2025-01-01 | M1    | 97.5%                | 4 (meilleur)    |
```

### SQL
```sql
SELECT 
    date, ligne, taux_ponctualite_avg,
    DENSE_RANK() OVER (PARTITION BY date ORDER BY taux_ponctualite_avg ASC) AS rang_regularite
FROM dm_regularite_par_ligne;
```

---

## 5️⃣ AVG() + OVER() - Moyennes Mobiles

### Cas d'usage (bonus)
Calculer la fréquentation **moyenne sur 3 heures** (fenêtre glissante).

### Code Spark
```python
w_moving = Window.partitionBy("id_station").orderBy(F.col("date"), F.col("heure")) \
    .rangeBetween(-3600*3, 0)  # 3 heures en secondes

df_enriched = df_enriched.withColumn(
    "freq_moving_avg_3h",
    F.avg("nb_validations").over(w_moving)
)
```

### Résultat
```
| date | heure | nb_validations | freq_moving_avg_3h |
|------|-------|----------------|--------------------|
| 01-01| 7     | 1200           | 1200 (seule donnée)|
| 01-01| 8     | 1400           | 1300 (moyenne 7-8)|
| 01-01| 9     | 1500           | 1367 (moyenne 7-9)|
| 01-01| 10    | 1300           | 1400 (moyenne 8-10)|
```

---

## 🔬 Exemples Pratiques dans Hive/Spark SQL

### Exemple 1 : Top 3 stations par ligne/heure

```sql
WITH ranked_stations AS (
    SELECT 
        ligne, heure, id_station, nom_station, nb_validations,
        RANK() OVER (PARTITION BY ligne, heure ORDER BY nb_validations DESC) AS rank
    FROM dm_frequentation_par_station_ligne
)
SELECT * FROM ranked_stations WHERE rank <= 3;
```

### Exemple 2 : Déterminer si fréquentation a baissé

```sql
SELECT 
    date, id_station, nom_station,
    nb_validations,
    nb_validations_semaine_prev,
    evolution_pct,
    CASE 
        WHEN evolution_pct < -10 THEN '🔴 Forte baisse'
        WHEN evolution_pct < 0 THEN '🟡 Baisse légère'
        WHEN evolution_pct = 0 THEN '🟢 Stable'
        ELSE '🟢 Augmentation'
    END AS trend
FROM dm_evolution_frequentation
ORDER BY evolution_pct ASC;
```

### Exemple 3 : Lignes problématiques (régularité + fréquentation)

```sql
SELECT 
    d1.date,
    d1.ligne,
    d1.taux_ponctualite_avg,
    d1.rang_regularite,
    COUNT(DISTINCT d2.id_station) AS nb_stations_saturees
FROM dm_regularite_par_ligne d1
LEFT JOIN dm_frequentation_par_station_ligne d2 
    ON d1.ligne = d2.ligne AND d1.date = d2.date AND d2.rank_station_par_ligne <= 3
WHERE d1.rang_regularite <= 3  -- Top 3 lignes moins régulières
GROUP BY d1.date, d1.ligne, d1.taux_ponctualite_avg, d1.rang_regularite
ORDER BY d1.rang_regularite;
```

---

## 📈 Performance

Les window functions peuvent être lourdes. Optimisations :

```python
# ❌ Mauvais : recalcul de window à chaque fois
df = df.withColumn("rank1", F.rank().over(w))
df = df.withColumn("rank2", F.rank().over(w))

# ✅ Bon : définir une fois et réutiliser
df = df.withColumn("rank", F.rank().over(w))
df = df.withColumn("rank1", F.col("rank"))
df = df.withColumn("rank2", F.col("rank"))

# ✅ Meilleur : calculer en une passe
w1 = Window.partitionBy("ligne", "heure").orderBy(F.desc("nb_validations"))
w2 = Window.partitionBy("date").orderBy(F.asc("taux_ponctualite"))

df = df \
    .withColumn("rank_freq", F.rank().over(w1)) \
    .withColumn("rank_reg", F.rank().over(w2))
```

---

## 📚 Ressources

- **Spark Docs :** https://spark.apache.org/docs/latest/sql-ref-window-functions.html
- **PySpark API :** https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql.html#window
- **SQL Window Functions :** https://www.postgresql.org/docs/current/functions-window.html

