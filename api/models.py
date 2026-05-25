from typing import List, Optional

from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PaginatedResponse(BaseModel):
    data: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


class FrequentationStationResponse(BaseModel):
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
    date: str
    ligne: str
    taux_ponctualite_avg: float
    nb_retards_total: int
    delai_moyen: float
    rang_regularite: int


class EvolutionResponse(BaseModel):
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
