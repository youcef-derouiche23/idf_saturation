-- init_db.sql - Initialiser la base PostgreSQL pour IDFM

-- DATAMART 1 : Fréquentation par station/ligne
CREATE TABLE IF NOT EXISTS dm_frequentation_par_station_ligne (
    id SERIAL PRIMARY KEY,
    ligne VARCHAR(50),
    id_station INTEGER,
    nom_station VARCHAR(255),
    heure VARCHAR(10),
    jour_semaine VARCHAR(20),
    jour_nom VARCHAR(20),
    nb_validations_avg FLOAT,
    nb_validations_max FLOAT,
    nb_validations_min FLOAT,
    nb_observations INTEGER,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DATAMART 2 : Régularité par ligne
CREATE TABLE IF NOT EXISTS dm_regularite_par_ligne (
    id SERIAL PRIMARY KEY,
    date VARCHAR(10),
    ligne VARCHAR(50),
    taux_ponctualite FLOAT,
    nb_retards INTEGER,
    delai_moyen FLOAT,
    rang_regularite INTEGER,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DATAMART 3 : Évolution temporelle
CREATE TABLE IF NOT EXISTS dm_evolution_frequentation (
    id SERIAL PRIMARY KEY,
    date VARCHAR(10),
    ligne VARCHAR(50),
    id_station INTEGER,
    frequentation_cumulee INTEGER,
    frequentation_jour_precedent INTEGER,
    variation_pourcentage FLOAT,
    jour_semaine VARCHAR(20),
    jour_nom VARCHAR(20),
    nb_observations INTEGER,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- DATAMART 4 : Saturation ML (Features pour ML)
CREATE TABLE IF NOT EXISTS dm_saturation_ml (
    id SERIAL PRIMARY KEY,
    date VARCHAR(10),
    heure VARCHAR(10),
    ligne VARCHAR(50),
    id_station INTEGER,
    nom_station VARCHAR(255),
    nb_validations FLOAT,
    pourcentage_validations FLOAT,
    taux_ponctualite FLOAT,
    jour_semaine INTEGER,
    jour_nom VARCHAR(20),
    est_vacances BOOLEAN,
    est_jour_ferie BOOLEAN,
    rank_saturation INTEGER,
    est_saturation INTEGER,
    load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tables auxiliaires
CREATE TABLE IF NOT EXISTS stations (
    id_station INTEGER PRIMARY KEY,
    nom_station VARCHAR(255),
    ville VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS validations (
    id SERIAL PRIMARY KEY,
    date VARCHAR(10),
    heure VARCHAR(10),
    ligne VARCHAR(50),
    id_station INTEGER,
    nb_validations FLOAT,
    pourcentage_validations FLOAT
);

CREATE TABLE IF NOT EXISTS regularite (
    id SERIAL PRIMARY KEY,
    date VARCHAR(10),
    ligne VARCHAR(50),
    taux_ponctualite FLOAT
);

-- Créer les index pour performance
CREATE INDEX IF NOT EXISTS idx_dm1_ligne ON dm_frequentation_par_station_ligne(ligne);
CREATE INDEX IF NOT EXISTS idx_dm2_ligne ON dm_regularite_par_ligne(ligne);
CREATE INDEX IF NOT EXISTS idx_dm3_ligne ON dm_evolution_frequentation(ligne);
CREATE INDEX IF NOT EXISTS idx_dm4_ligne ON dm_saturation_ml(ligne);
