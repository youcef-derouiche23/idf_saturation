# 📊 RÉSUMÉ DU DASHBOARD IDFM

## Vue d'ensemble
Dashboard Streamlit d'analyse du réseau ferré Île-de-France affichant **4 pages** avec 85,768 observations de fréquentation et 2,009 enregistrements de ponctualité.

---

## PAGE 1 : 📈 Fréquentation par Stations/Lignes

### Métriques (haut de page)
| Métrique | Valeur | Description |
|----------|--------|-------------|
| 📊 Stations | 782 | Nombre d'arrêts distincts du réseau ferré |
| 🚇 Lignes | 6 | RER A, B, C, D, E + Transilien H |
| ⏰ Créneaux | 25 | Heures horaires (0H-1H à 23H-0H) |

### Graphiques et Tableaux

#### Onglet 1 : "📊 Par Ligne"
- **Graphique** : Bar chart horizontal - Top 10 lignes par fréquentation moyenne
  - X = Fréquentation moyenne (validations/heure)
  - Y = Nom de ligne (RER A, RER B, etc.)
  - Couleur = dégradé rouge (plus chargé = plus rouge)
- **Tableau** : Détail par ligne et jour-type
  - Colonnes : Ligne | Jour Type | Validations Moyennes | Validations Max | Stations

#### Onglet 2 : "🏢 Par Station"
- **Graphique** : Bar chart horizontal - Top 10 stations par fréquentation
  - X = Fréquentation moyenne
  - Y = Station ID
- **Tableau** : Stations saturées (validations > 5,000/heure)
  - Colonnes : Station ID | Validations Moyennes | Validations Max | Occurrences | Ligne | Jour

#### Onglet 3 : "📋 Détail"
- **Tableau** : Toutes les données (50 premières lignes)
  - Colonnes : Station | Ligne | Heure | Jour Type | Validations

---

## PAGE 2 : 📋 Régularité et Ponctualité

### Métriques (haut de page)
| Métrique | Valeur | Description |
|----------|--------|-------------|
| ✅ Ponctualité Moyenne | 89.66% | Moyenne sur toute la période |
| 🚇 Lignes | 13 | Toutes lignes RER + Transilien |
| 📅 Périodes | 2,009 | Enregistrements mensuels |

### Graphiques et Tableaux

#### Graphique 1 : "Ponctualité par Ligne"
- **Type** : Bar chart horizontal avec code couleur
  - 🟢 Vert (>95%) = Excellent
  - 🟠 Orange (80-95%) = À surveiller
  - 🔴 Rouge (<80%) = Critique
- **Lignes verticales** : Seuil objectif IDFM à 95%
- Trié du moins ponctuel au plus ponctuel

#### Tableau : "Détails par Ligne"
- Colonnes : Ligne | Nom Complet | Ponctualité (%) | Période
- Trié par ponctualité croissante

---

## PAGE 3 : 📈 Évolution Temporelle

### Métriques (haut de page)
| Métrique | Valeur | Description |
|----------|--------|-------------|
| 📊 Fréquentation Totale | ~13.5M | Total cumulé sur tous jours-types |
| 📅 Jours Type | 5 | DIJFP, JOHV, JOVS, SAHV, etc. |
| 📈 Variation Moyenne | 0.0% | Variation moyenne semaine précédente |

### Graphiques et Tableaux

#### Graphique 1 : "Fréquentation par Jour-Type"
- **Type** : Bar chart horizontal
  - X = Fréquentation cumulée
  - Y = Jour-type en français (Lundi-Vendredi, Samedi, Dimanche)
  - Couleur = dégradé bleu

#### Tableau : "Détail par Ligne et Jour-Type"
- Colonnes : Jour Type | Ligne | Fréquentation | Stations
- Trié par jour-type puis fréquentation décroissante
- Hauteur : 400px (scrollable)

---

## PAGE 4 : 🤖 Dataset Saturation (ML)

### Métriques (haut de page)
| Métrique | Valeur | Description |
|----------|--------|-------------|
| 🔴 Situations Saturées | 15,450 | Créneaux > 5,000 validations/heure |
| 📊 Total Observations | 85,768 | Ensemble complet du dataset |
| 📈 % Saturation | 18.1% | Proportion de saturation |

### Graphiques et Tableaux

#### Onglet 1 : "📊 Distribution"
- **Donut chart** : Répartition Normal vs Saturé
  - 🟢 Normal (82,318)
  - 🔴 Saturé (15,450)
- **Bar chart** : Saturation par ligne
  - Y = Nom de ligne
  - X = Nombre de saturations
  - Trié du plus saturé au moins saturé

#### Onglet 2 : "⚠️ Pics de Saturation"
- **Tableau** : 100 premiers pics
  - Colonnes : Ligne | Heure | Jour Type | Validations | Ponctualité (%)
  - Trié par validations décroissantes

#### Onglet 3 : "📋 Détail"
- **Tableau** : Toutes les données ML (100 premières lignes)
  - Colonnes : Ligne | Heure | Jour Type | Validations | Ponctualité (%) | Saturé
  - Colonne "Saturé" : 🟢 Non ou 🔴 Oui

---

## 🎯 SEUILS ET INDICATEURS

| Indicateur | Seuil | Signification |
|-----------|-------|---------------|
| **Saturation** | > 5,000 validations/heure | 🔴 Critique |
| **Ponctualité Objectif** | > 95% | 🟢 Excellent |
| **Ponctualité Acceptable** | 80-95% | 🟠 À surveiller |
| **Ponctualité Critique** | < 80% | 🔴 Critique |

---

## 🔧 SOURCES DE DONNÉES

| Source | Récurrence | Lignes | Colonnes Clés |
|--------|-----------|--------|---------------|
| validations-reseau-ferre-profils-... | Trimestriel | 85,768 | code_stif_trns, trnc_horr_60, pourcentage_validations |
| ponctualite-mensuelle-transilien.csv | Mensuel | 2,009 | Ligne, Taux de ponctualité, Date |
| arrets.csv | Statique | 782 | ArRId, ArRName, ZdAId |

---

## 📱 ACCÈS

- **URL** : http://localhost:8501
- **Authentification** : Aucune (dashboard public)
- **Mise à jour** : En temps réel depuis l'API (cache 600s)
- **Format** : Streamlit (Python)

---

**Dernière mise à jour** : 24 mai 2026
**Version** : 2.0 (Refactorisée - Sans codes, vraies valeurs uniquement)
