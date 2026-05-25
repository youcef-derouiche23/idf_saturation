-- =====================================================
-- VUE API POUR FRÉQUENTATION PAR STATION
-- =====================================================

DROP VIEW IF EXISTS api_frequentation_stations CASCADE;

CREATE VIEW api_frequentation_stations AS
SELECT 
    ligne AS "Ligne",
    nom_station AS "Station",
    heure AS "Plage Horaire",
    ROUND(nb_validations_avg::numeric, 1) AS "Validations Moyennes (%)",
    ROUND(nb_validations_max::numeric, 1) AS "Validations Max (%)",
    ROUND(nb_validations_min::numeric, 1) AS "Validations Min (%)",
    nb_observations AS "Nombre Observations",
    DATE(load_timestamp) AS "Date Chargement"
FROM public.dm_frequentation_par_station_ligne
ORDER BY ligne, nom_station, heure;

-- =====================================================
-- VUE API POUR SATURATION ML
-- =====================================================

DROP VIEW IF EXISTS api_saturation_ml CASCADE;

CREATE VIEW api_saturation_ml AS
SELECT 
    ligne AS "Ligne",
    nom_station AS "Station",
    heure AS "Plage Horaire",
    jour_nom AS "Type de Jour",
    ROUND(pourcentage_validations::numeric, 1) AS "Taux d'Occupation (%)",
    CASE 
        WHEN est_saturation = 1 THEN 'ℹ️ SATURÉ'
        ELSE '✅ Normal'
    END AS "Statut Saturation",
    DATE(load_timestamp) AS "Date Chargement"
FROM public.dm_saturation_ml
WHERE pourcentage_validations IS NOT NULL
ORDER BY ligne, nom_station, heure;

-- =====================================================
-- VUE API POUR RÉGULARITÉ PAR LIGNE
-- =====================================================

DROP VIEW IF EXISTS api_regularite_lignes CASCADE;

CREATE VIEW api_regularite_lignes AS
SELECT 
    DATE(date) AS "Date",
    ligne AS "Ligne",
    ROUND((taux_ponctualite * 100)::numeric, 1) AS "Ponctualité (%)",
    nb_retards AS "Nombre de Retards",
    ROUND(delai_moyen::numeric, 2) AS "Délai Moyen (min)",
    CASE 
        WHEN taux_ponctualite >= 0.95 THEN '🟢 Excellent'
        WHEN taux_ponctualite >= 0.90 THEN '🟡 Bon'
        WHEN taux_ponctualite >= 0.85 THEN '🟠 Acceptable'
        ELSE '🔴 Dégradé'
    END AS "Qualité Service",
    DATE(load_timestamp) AS "Date Chargement"
FROM public.dm_regularite_par_ligne
WHERE ligne IS NOT NULL AND ligne != ''
ORDER BY date DESC, ligne;

-- =====================================================
-- VUE API POUR PONCTUALITÉ TRANSILIEN
-- =====================================================

DROP VIEW IF EXISTS api_ponctualite_transilien CASCADE;

CREATE VIEW api_ponctualite_transilien AS
SELECT 
    DATE(date) AS "Date",
    ligne AS "Ligne RER/Transilien",
    ROUND((taux_ponctualite * 100)::numeric, 1) AS "Taux Ponctualité (%)",
    nb_retards AS "Retards Enregistrés",
    ROUND(delai_moyen::numeric, 2) AS "Retard Moyen (minutes)",
    CASE 
        WHEN taux_ponctualite >= 0.95 THEN '🟢 Excellente'
        WHEN taux_ponctualite >= 0.90 THEN '🟡 Bonne'
        WHEN taux_ponctualite >= 0.85 THEN '🟠 Dégradée'
        ELSE '🔴 Très dégradée'
    END AS "Niveau Service",
    DATE(load_timestamp) AS "Mise à jour"
FROM public.dm_regularite_par_ligne
WHERE ligne IN ('100', '760', '800')  -- Filtrer sur lignes RER/Transilien
ORDER BY date DESC, ligne;

-- =====================================================
-- VUE API POUR ÉVOLUTION TEMPORELLE
-- =====================================================

DROP VIEW IF EXISTS api_evolution_frequentation CASCADE;

CREATE VIEW api_evolution_frequentation AS
SELECT 
    ligne AS "Ligne",
    nom_station AS "Station",
    heure AS "Plage Horaire",
    jour_nom AS "Type de Jour",
    ROUND(nb_validations_avg::numeric, 1) AS "Évolution Validations (%)",
    DATE(load_timestamp) AS "Date Analyse"
FROM public.dm_frequentation_par_station_ligne
ORDER BY load_timestamp DESC, ligne, nom_station, heure;

-- =====================================================
-- VUE API POUR STATIONS (RÉFÉRENTIEL)
-- =====================================================

DROP VIEW IF EXISTS api_stations CASCADE;

CREATE VIEW api_stations AS
SELECT DISTINCT
    code_stif AS "Code Station",
    name AS "Nom Station",
    line_ids AS "Lignes Desservies",
    DATE(load_timestamp) AS "Date Chargement"
FROM public.stations
ORDER BY name;

-- =====================================================
-- VUE API POUR VALIDATION (DONNÉES BRUTES SAMPLE)
-- =====================================================

DROP VIEW IF EXISTS api_validations_sample CASCADE;

CREATE VIEW api_validations_sample AS
SELECT 
    code_stif_trns AS "Ligne",
    libelle_arret AS "Station",
    trnc_horr_60 AS "Plage Horaire",
    cat_jour AS "Type de Jour",
    ROUND(pourcentage_validations::numeric, 1) AS "Taux Validations (%)",
    DATE(load_timestamp) AS "Date Enregistrement"
FROM public.validations
WHERE load_timestamp IS NOT NULL
ORDER BY load_timestamp DESC, code_stif_trns, libelle_arret
LIMIT 5000;

-- =====================================================
-- VUE STATISTIQUES GLOBALES
-- =====================================================

DROP VIEW IF EXISTS api_stats_globales CASCADE;

CREATE VIEW api_stats_globales AS
SELECT 
    COUNT(DISTINCT ligne) AS "Nombre Lignes",
    COUNT(DISTINCT nom_station) AS "Nombre Stations",
    ROUND(AVG(nb_validations_avg)::numeric, 1) AS "Occupation Moyenne (%)",
    ROUND(MAX(nb_validations_max)::numeric, 1) AS "Pic Occupation (%)",
    COUNT(*) AS "Nombre Observations"
FROM public.dm_frequentation_par_station_ligne;

GRANT SELECT ON api_frequentation_stations TO youcef;
GRANT SELECT ON api_saturation_ml TO youcef;
GRANT SELECT ON api_regularite_lignes TO youcef;
GRANT SELECT ON api_ponctualite_transilien TO youcef;
GRANT SELECT ON api_evolution_frequentation TO youcef;
GRANT SELECT ON api_stations TO youcef;
GRANT SELECT ON api_validations_sample TO youcef;
GRANT SELECT ON api_stats_globales TO youcef;
