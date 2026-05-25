# -*- coding: utf-8 -*-
"""
models.py - Schémas Pydantic pour les réponses API
"""

from typing import Any, List, Optional

from pydantic import BaseModel


# =====================================================
# AUTHENTIFICATION
# =====================================================

class Token(BaseModel):
    """Réponse pour l'obtention d'un token JWT"""
    access_token: str
    token_type: str = "bearer"


# =====================================================
# PAGINATION
# =====================================================

class PaginatedResponse(BaseModel):
    """Response générique paginée pour tous les datamarts"""
    data: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


# =====================================================
# DATAMARTS
# =====================================================

class FrequentationStationResponse(BaseModel):
    """Réponse pour le datamart de fréquentation par station"""
    ligne: str
    id_station: int
    nom_station: str
    heure: int
    jour_semaine: int
    jour_nom: str
    nb_validations_avg: float
    nb_validations_max: int
    nb_validations_min: int
    nb_observations: int


class RegulariteResponse(BaseModel):
    """Réponse pour le datamart de régularité"""
    date: str
    ligne: str
    taux_ponctualite_avg: float
    nb_retards_total: int
    delai_moyen: float
    rang_regularite: int


class EvolutionResponse(BaseModel):
    """Réponse pour le datamart d'évolution temporelle"""
    date: str
    jour_semaine: int
    jour_nom: str
    est_vacances: int
    ligne: str
    id_station: int
    nom_station: str
    nb_validations_cumul: int
    evolution_vs_semaine_precedente_pct: Optional[float]


class SaturationMLResponse(BaseModel):
    """Réponse pour le datamart ML (prédiction saturation)"""
    date: str
    heure: int
    ligne: str
    id_station: int
    nom_station: str
    nb_validations: int
    taux_ponctualite: Optional[float]
    jour_semaine: int
    jour_nom: str
    is_vacances: int
    jour_ferie: int
    rank_station_par_ligne: Optional[int]
    est_saturation: int
