# -*- coding: utf-8 -*-
"""
app.py - API REST FastAPI pour les datamarts IDFM

Lancement (depuis la racine du projet) :
    uvicorn api.app:app --reload

Documentation interactive : http://localhost:8000/docs

Endpoints :
    GET  /                                          -> santé de l'API (public)
    POST /auth/login                                -> retourne un token JWT
    GET  /datamarts/frequentation-stations          (JWT) paginé
    GET  /datamarts/regularite-lignes               (JWT) paginé
    GET  /datamarts/evolution-temporelle            (JWT) paginé
    GET  /datamarts/saturation-ml                   (JWT) paginé
"""

import logging
import math
import os

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from .auth import authenticate_user, create_access_token, get_current_user
from .database import Database
from .database_cache import DatabaseCache
from .models import PaginatedResponse, Token

# --- Configuration ---
CONFIG_PATH = os.environ.get(
    "API_CONFIG",
    os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", "config", "config.ini")
    ),
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Essayer PostgreSQL, sinon utiliser le cache en mémoire
DB_MODE = None
db = None

try:
    logger.info(f"🔍 Tentative connexion PostgreSQL...")
    logger.info(f"   CONFIG_PATH = {CONFIG_PATH}")
    db = Database(CONFIG_PATH)
    logger.info(f"   Host: {db.host}, Port: {db.port}, DB: {db.dbname}, User: {db.user}")
    db.connect()
    logger.info("✅ PostgreSQL disponible - mode production")
    DB_MODE = "postgres"
except Exception as e:
    logger.warning(f"⚠️ PostgreSQL indisponible: {e}")
    logger.info("📦 Initialisation du mode cache (chargement des CSV en arrière-plan)...")
    # Ne pas charger les CSV ici - le faire au premier appel
    db = None
    DB_MODE = "cache"

# Map des endpoints vers (table SQL, colonnes de tri)
DATAMARTS = {
    "frequentation-stations": (
        "dm_frequentation_par_station_ligne",
        "ligne, id_station, heure"
    ),
    "regularite-lignes": (
        "dm_regularite_par_ligne",
        "date DESC, rang_regularite"
    ),
    "evolution-temporelle": (
        "dm_evolution_frequentation",
        "date DESC, ligne"
    ),
    "saturation-ml": (
        "dm_saturation_ml",
        "date DESC, heure DESC, est_saturation DESC"
    ),
}

app = FastAPI(
    title="API Fréquentation Réseau Ferré IDFM",
    description=(
        "Expose les 4 datamarts de la data platform (couche Gold). "
        "Analyse de la saturation et régularité du réseau métro/RER Île-de-France. "
        "Authentification JWT obligatoire sur les endpoints /datamarts."
    ),
    version="1.0.0",
)

# CORS ouvert : pratique pour tester depuis un navigateur ou un autre outil
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# ENDPOINT PUBLIC : SANTE DE L'API
# =====================================================

def ensure_db_initialized():
    """Initialise le DB en lazy-loading au premier appel"""
    global db, DB_MODE
    if db is None and DB_MODE == "cache":
        logger.info("🔨 Chargement des datamarts en cache (premier appel)...")
        db = DatabaseCache(CONFIG_PATH)
        logger.info("✅ Cache chargé et prêt")
    return db

@app.get("/", tags=["Santé"])
def health():
    """Vérifie que l'API répond et liste les datamarts disponibles."""
    ensure_db_initialized()
    return {
        "status": "ok",
        "service": "IDFM Fréquentation & Régularité",
        "datamarts": list(DATAMARTS.keys()),
        "database_mode": DB_MODE,
        "message": "🎉 API opérationnelle" if DB_MODE == "cache" else "✅ PostgreSQL connecté"
    }


# =====================================================
# AUTHENTIFICATION : OBTENTION DU TOKEN JWT
# =====================================================

@app.post("/auth/login", response_model=Token, tags=["Authentification"])
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    Authentifie l'utilisateur et retourne un token JWT.

    **Identifiants par défaut :**
    - username: admin
    - password: admin
    """
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": form_data.username}
    )

    return {"access_token": access_token, "token_type": "bearer"}


# =====================================================
# ENDPOINTS DATAMARTS (SECURISES)
# =====================================================

@app.get(
    "/datamarts/frequentation-stations",
    response_model=PaginatedResponse,
    tags=["Datamarts"],
    dependencies=[Depends(get_current_user)]
)
def get_frequentation_stations(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000)
):
    """
    Retourne le datamart de fréquentation par station et ligne.

    **Features :**
    - Fréquentation moyenne/max/min par station, ligne, heure
    - Ranking des stations saturées par ligne
    - Agrégées par jour de la semaine
    """
    ensure_db_initialized()
    try:
        table, order_by = DATAMARTS["frequentation-stations"]
        
        if DB_MODE == "cache":
            result = db.query_paginated(table, page=page, page_size=page_size)
        else:
            sql = f"SELECT * FROM {table} ORDER BY {order_by}"
            result = db.query_paginated(sql, page=page, page_size=page_size)

        return PaginatedResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/datamarts/regularite-lignes",
    response_model=PaginatedResponse,
    tags=["Datamarts"],
    dependencies=[Depends(get_current_user)]
)
def get_regularite_lignes(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000)
):
    """
    Retourne le datamart de régularité des lignes.

    **Features :**
    - Taux de ponctualité moyen par ligne et date
    - Total retards et délai moyen
    - Ranking des lignes par régularité (des moins aux plus régulières)
    """
    ensure_db_initialized()
    try:
        table, order_by = DATAMARTS["regularite-lignes"]
        
        if DB_MODE == "cache":
            result = db.query_paginated(table, page=page, page_size=page_size)
        else:
            sql = f"SELECT * FROM {table} ORDER BY {order_by}"
            result = db.query_paginated(sql, page=page, page_size=page_size)

        return PaginatedResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/datamarts/evolution-temporelle",
    response_model=PaginatedResponse,
    tags=["Datamarts"],
    dependencies=[Depends(get_current_user)]
)
def get_evolution_temporelle(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000)
):
    """
    Retourne le datamart d'évolution temporelle de la fréquentation.

    **Features :**
    - Fréquentation cumulée par date, station, ligne
    - Jour de la semaine et détection période de vacances
    - Évolution vs semaine précédente (%)
    """
    ensure_db_initialized()
    try:
        table, order_by = DATAMARTS["evolution-temporelle"]
        
        if DB_MODE == "cache":
            result = db.query_paginated(table, page=page, page_size=page_size)
        else:
            sql = f"SELECT * FROM {table} ORDER BY {order_by}"
            result = db.query_paginated(sql, page=page, page_size=page_size)

        return PaginatedResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/datamarts/saturation-ml",
    response_model=PaginatedResponse,
    tags=["Datamarts"],
    dependencies=[Depends(get_current_user)]
)
def get_saturation_ml(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000)
):
    """
    Retourne le datamart pour modèles ML - Prédiction de saturation.

    **Features (pour entraînement ML) :**
    - Date, heure, ligne, station
    - Fréquentation (nb_validations)
    - Taux de ponctualité
    - Jour de la semaine, vacances, jour férié
    - Rank saturation par station/ligne
    - **Label cible : est_saturation** (0/1 selon seuil configuré)

    **Cas d'usage :** Entraîner un modèle pour prédire si une heure sera saturée
    """
    ensure_db_initialized()
    try:
        table, order_by = DATAMARTS["saturation-ml"]
        
        if DB_MODE == "cache":
            result = db.query_paginated(table, page=page, page_size=page_size)
        else:
            sql = f"SELECT * FROM {table} ORDER BY {order_by}"
            result = db.query_paginated(sql, page=page, page_size=page_size)

        return PaginatedResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =====================================================
# ENDPOINTS SIMPLES : DONNEES BRUTES (SECURISES)
# =====================================================

@app.get(
    "/data/stations",
    response_model=PaginatedResponse,
    tags=["Données Brutes"],
    dependencies=[Depends(get_current_user)]
)
def get_stations(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000)
):
    """Retourne la liste des stations/arrêts"""
    ensure_db_initialized()
    try:
        sql = "SELECT * FROM stations ORDER BY id_station"
        result = db.query_paginated(sql, page=page, page_size=page_size)
        return PaginatedResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/data/validations",
    response_model=PaginatedResponse,
    tags=["Données Brutes"],
    dependencies=[Depends(get_current_user)]
)
def get_validations(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000),
    ligne: str = Query(None)
):
    """Retourne les validations. Filtre optionnel par ligne."""
    ensure_db_initialized()
    try:
        if ligne:
            sql = f"SELECT * FROM validations WHERE ligne = '{ligne}' ORDER BY id_station, heure"
        else:
            sql = "SELECT * FROM validations ORDER BY id_station, heure LIMIT 10000"
        
        result = db.query_paginated(sql, page=page, page_size=page_size)
        return PaginatedResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/data/regularite",
    response_model=PaginatedResponse,
    tags=["Données Brutes"],
    dependencies=[Depends(get_current_user)]
)
def get_regularite(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=10000),
    ligne: str = Query(None)
):
    """Retourne les données de régularité. Filtre optionnel par ligne."""
    ensure_db_initialized()
    try:
        if ligne:
            sql = f"SELECT * FROM regularite WHERE ligne = '{ligne}' ORDER BY date DESC"
        else:
            sql = "SELECT * FROM regularite ORDER BY date DESC"
        
        result = db.query_paginated(sql, page=page, page_size=page_size)
        return PaginatedResponse(
            data=result["data"],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/stats/lignes",
    tags=["Statistiques"],
    dependencies=[Depends(get_current_user)]
)
def get_stats_lignes():
    """Retourne des statistiques par ligne"""
    ensure_db_initialized()
    try:
        sql = """
        SELECT 
            ligne,
            COUNT(*) as nb_validations_records,
            AVG(pct_validations) as avg_pct_validations,
            MAX(pct_validations) as max_pct_validations,
            MIN(pct_validations) as min_pct_validations
        FROM validations
        GROUP BY ligne
        ORDER BY avg_pct_validations DESC
        """
        rows = db.query_raw(sql)
        return {"lines": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/stats/stations",
    tags=["Statistiques"],
    dependencies=[Depends(get_current_user)]
)
def get_stats_stations():
    """Retourne les stations avec le plus de validations"""
    ensure_db_initialized()
    try:
        sql = """
        SELECT 
            s.id_station,
            s.nom_station,
            COUNT(*) as nb_records,
            AVG(v.pct_validations) as avg_pct,
            MAX(v.pct_validations) as max_pct
        FROM validations v
        JOIN stations s ON v.id_station = s.id_station
        GROUP BY s.id_station, s.nom_station
        ORDER BY avg_pct DESC
        LIMIT 50
        """
        rows = db.query_raw(sql)
        return {"stations": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
