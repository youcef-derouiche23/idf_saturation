import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
from datetime import datetime
import os

# Configuration de la page Streamlit
st.set_page_config(
    page_title="Dashboard Saturation Île-de-France Mobilités",
    page_icon="🚇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configuration de l'URL de l'API
API_URL = os.getenv("API_URL", "http://localhost:8000")
SATURATION_THRESHOLD = 7.0  # Seuil de saturation par défaut en %

# -----------------------------------------------------------------------------
# CONSTANTES ET MAPPINGS (Placés au début pour éviter les NameError)
# -----------------------------------------------------------------------------

# Dictionnaire de correspondance des IDs de stations aux noms lisibles
STATION_MAPPING = {
    "Porte Maillot": [71379],
    "Gare de Lyon": [71510, 71511],
    "Gare du Nord": [71410, 71411],
    "Châtelet": [71470, 71471],
    "La Défense": [71520]
}

# Mapping des codes de jour-type techniques vers des libellés lisibles
JOUR_TYPE_MAPPING = {
    "DIJFP": "Lundi-Vendredi (Hors Vacances)",
    "JOHV": "Jour Ouvrable Hors Vacances",
    "JOVS": "Jour Ouvrable Vacances Scolaires",
    "SAHV": "Samedi Hors Vacances",
    "SAVS": "Samedi Vacances Scolaires",
    "SAMEDI": "Samedi",
    "DIMANCHE": "Dimanche"
}

def map_ligne_code_to_name(code):
    """Convertit un code technique de ligne en nom lisible."""
    if pd.isna(code):
        return "Inconnue"
    code_str = str(code).strip().upper()
    if code_str.startswith("C"):
        return f"Tram {code_str[1:]}"
    return f"Ligne {code_str}"

def map_jour_type(jour_code):
    """Convertit un code jour technique en libellé propre."""
    if pd.isna(jour_code):
        return "Inconnu"
    jour_str = str(jour_code).strip().upper()
    return JOUR_TYPE_MAPPING.get(jour_str, jour_str)

# Inverser le mapping pour les recherches rapides d'identifiants
_REVERSE_STATION_MAPPING = {}
for station_name, ids in STATION_MAPPING.items():
    for sid in ids:
        _REVERSE_STATION_MAPPING[sid] = station_name
        _REVERSE_STATION_MAPPING[str(sid)] = station_name
        try:
            _REVERSE_STATION_MAPPING[int(sid)] = station_name
        except (ValueError, TypeError):
            pass

def get_station_name(df, station_id):
    """Retourne le nom de la station à partir de son ID ou des métadonnées du DataFrame."""
    if pd.isna(station_id):
        return "Station Inconnue"
        
    # 1. Vérification dans le dictionnaire hardcodé
    if station_id in _REVERSE_STATION_MAPPING:
        return _REVERSE_STATION_MAPPING[station_id]
    if str(station_id) in _REVERSE_STATION_MAPPING:
        return _REVERSE_STATION_MAPPING[str(station_id)]
        
    # 2. Vérification dynamique dans le dataframe si les colonnes de nom existent
    if df is not None and not df.empty:
        for col in ["nom_station", "station_nom", "station", "nom"]:
            if col in df.columns:
                match = df[df["id_station"] == station_id]
                if not match.empty and pd.notna(match[col].iloc[0]):
                    return str(match[col].iloc[0])
                    
    return f"Station {station_id}"

# -----------------------------------------------------------------------------
# FONCTIONS UTILITAIRES ET ACCÈS API
# -----------------------------------------------------------------------------

@st.cache_data(ttl=300)
def fetch_datamart(endpoint: str) -> pd.DataFrame:
    """Récupère les données d'un datamart spécifique via l'API FastAPI."""
    try:
        response = requests.get(f"{API_URL}/api/datamarts/{endpoint}", timeout=15)
        if response.status_code == 200:
            res_json = response.json()
            if isinstance(res_json, list):
                return pd.DataFrame(res_json)
            elif isinstance(res_json, dict) and "data" in res_json:
                return pd.DataFrame(res_json["data"])
            return pd.DataFrame()
        else:
            st.sidebar.error(f"Erreur API ({response.status_code}) sur {endpoint}")
            return pd.DataFrame()
    except Exception as e:
        st.sidebar.error(f"Erreur de connexion à l'API : {str(e)}")
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# INTERFACE GRAPHIQUE PRINCIPALE (SIDEBAR & TITRE)
# -----------------------------------------------------------------------------

st.sidebar.title("🚇 IDFM Pipeline & Saturation")
st.sidebar.markdown("Analyse Big Data du trafic et de la charge du réseau Île-de-France Mobilités.")

datamart_choice = st.sidebar.selectbox(
    "Sélectionnez le module d'analyse :",
    [
        "frequentation-stations",
        "saturation-ml",
        "regularite-lignes",
        "ponctualite-transilien"
    ],
    format_func=lambda x: {
        "frequentation-stations": "📈 Fréquentation & Saturation",
        "saturation-ml": "🤖 Prédictions Modèles ML",
        "regularite-lignes": "⏱️ Régularité Métro / RER",
        "ponctualite-transilien": "📊 Ponctualité Transilien"
    }.get(x, x)
)

# -----------------------------------------------------------------------------
# MODULE 1 : FRÉQUENTATION ET SATURATION DES STATIONS
# -----------------------------------------------------------------------------
if datamart_choice == "frequentation-stations":
    st.title("📈 Analyse de Fréquentation et Profils de Saturation")
    
    df = fetch_datamart("frequentation-stations")
    
    if df.empty:
        st.warning("⚠️ Aucune donnée disponible pour le datamart de fréquentation.")
        st.info("Veuillez vous assurer que la base PostgreSQL est bien alimentée et que l'API s'exécute correctement.")
    else:
        # Harmonisation robuste et globale des colonnes de l'API locale pour éviter les KeyError
        if "pct_validations" in df.columns:
            df = df.rename(columns={"pct_validations": "pourcentage_validations"})
        elif "nb_validations" in df.columns and "pourcentage_validations" not in df.columns:
            df["pourcentage_validations"] = df["nb_validations"]
            
        if "pourcentage_validations" not in df.columns:
            df["pourcentage_validations"] = 1.0  # Sécurité ultime contre le crash
            
        if "jour_type" not in df.columns and "date" in df.columns:
            df = df.rename(columns={"date": "jour_type"})
        if "jour_type" not in df.columns:
            df["jour_type"] = "DIJFP"

        # Section KPIs généraux
        kpi1, kpi2, kpi3 = st.columns(3)
        with kpi1:
            st.metric("Lignes Analysées", df["ligne"].nunique() if "ligne" in df.columns else 0)
        with kpi2:
            st.metric("Stations Uniques", df["id_station"].nunique() if "id_station" in df.columns else 0)
        with kpi3:
            sat_points = len(df[df["pourcentage_validations"] > SATURATION_THRESHOLD])
            st.metric("Pics de Saturation (> Seuil)", sat_points)

        st.markdown(f"**Indicateur Contractuel** : Un point de mesure est jugé critique si sa charge excède `{SATURATION_THRESHOLD}%` du trafic quotidien global de la ligne.")

        # Création des onglets graphiques
        tab1, tab2, tab3 = st.tabs(["📊 Vue par Ligne", "🏢 Vue par Station", "📋 Vue Détaillée & Brute"])
        
        with tab1:
            st.markdown("#### Top 10 des Lignes par Charge Moyenne")
            top_lines = df.groupby("ligne")["pourcentage_validations"].mean().nlargest(10).reset_index()
            top_lines = top_lines.sort_values("pourcentage_validations")
            top_lines["ligne_nom"] = top_lines["ligne"].apply(map_ligne_code_to_name)
            
            fig_lines = px.bar(
                top_lines,
                y="ligne_nom",
                x="pourcentage_validations",
                title="Fréquentation Moyenne par Ligne (% du Trafic Global)",
                orientation="h",
                color="pourcentage_validations",
                color_continuous_scale="Reds"
            )
            fig_lines.update_layout(yaxis_title="Ligne", xaxis_title="% Moyen de validations")
            fig_lines.add_vline(x=SATURATION_THRESHOLD, line_dash="dash", line_color="darkred", annotation_text="Seuil Alerte")
            
            # Utilisation de clés uniques pour éviter les conflits d'ID Streamlit
            st.plotly_chart(fig_lines, use_container_width=True, key="unique_chart_lignes_freq")

            st.markdown("##### Détail des charges moyennes et maximales par Jour Type")
            line_detail = df.groupby(["ligne", "jour_type"])["pourcentage_validations"].agg(["mean", "max"]).reset_index()
            line_detail.columns = ["Ligne Code", "Jour Type", "% Moyen", "% Max"]
            line_detail["Ligne"] = line_detail["Ligne Code"].apply(map_ligne_code_to_name)
            line_detail["Jour"] = line_detail["Jour Type"].apply(map_jour_type)
            line_detail = line_detail[["Ligne", "Jour", "% Moyen", "% Max"]].sort_values("% Moyen", ascending=False)
            st.dataframe(line_detail.head(25), use_container_width=True, hide_index=True)

        with tab2:
            st.markdown("#### Top 10 des Stations les Plus Chargées du Réseau")
            top_stations = df.groupby("id_station")["pourcentage_validations"].mean().nlargest(10).reset_index()
            
            # Correction de l'erreur d'argument manquant en passant le dataframe via une lambda
            top_stations["station_nom"] = top_stations["id_station"].apply(lambda x: get_station_name(df, x))
            top_stations = top_stations.sort_values("pourcentage_validations")
            
            fig_stations = px.bar(
                top_stations,
                y="station_nom",
                x="pourcentage_validations",
                title="Top 10 Stations par Volume Moyen de Validations",
                orientation="h",
                color="pourcentage_validations",
                color_continuous_scale="Oranges"
            )
            fig_stations.update_layout(yaxis_title="Station", xaxis_title="% Moyen du trafic quotidien")
            st.plotly_chart(fig_stations, use_container_width=True, key="unique_chart_stations_freq")

            st.markdown("##### Alertes de Saturation constatées par Station")
            saturated_df = df[df["pourcentage_validations"] > SATURATION_THRESHOLD].copy()
            if not saturated_df.empty:
                saturated_df["Station"] = saturated_df["id_station"].apply(lambda x: get_station_name(df, x))
                saturated_df["Ligne Nom"] = saturated_df["ligne"].apply(map_ligne_code_to_name)
                saturated_df["Jour"] = saturated_df["jour_type"].apply(map_jour_type)
                
                display_sat = saturated_df[["Station", "Ligne Nom", "heure", "Jour", "pourcentage_validations"]].rename(
                    columns={"heure": "Heure", "pourcentage_validations": "% Trafic"}
                ).sort_values("% Trafic", ascending=False)
                st.dataframe(display_sat.head(30), use_container_width=True, hide_index=True)
            else:
                st.success("✅ Félicitations ! Aucun point de saturation critique ne dépasse actuellement le seuil.")

        with tab3:
            st.markdown("##### Aperçu Complet du Datamart Récupéré (50 premières lignes)")
            raw_display = df.head(50).copy()
            raw_display["Station"] = raw_display["id_station"].apply(lambda x: get_station_name(df, x))
            raw_display["Ligne Nom"] = raw_display["ligne"].apply(map_ligne_code_to_name)
            raw_display["Jour"] = raw_display["jour_type"].apply(map_jour_type)
            st.dataframe(
                raw_display[["Station", "Ligne Nom", "heure", "Jour", "pourcentage_validations"]],
                use_container_width=True
            )

# -----------------------------------------------------------------------------
# MODULE 2 : DATASET SATURATION POUR MACHINE LEARNING
# -----------------------------------------------------------------------------
elif datamart_choice == "saturation-ml":
    st.title("🤖 Analyse des Features & Prédictions de Saturation ML")
    
    df = fetch_datamart("saturation-ml")
    
    if df.empty:
        st.info("💡 Le datamart Machine Learning n'est pas encore alimenté. Exécutez votre pipeline d'ingestion Spark.")
    else:
        if "pct_validations" in df.columns:
            df = df.rename(columns={"pct_validations": "pourcentage_validations"})
        if "is_saturated" not in df.columns and "pourcentage_validations" in df.columns:
            df["is_saturated"] = df["pourcentage_validations"] > SATURATION_THRESHOLD

        st.markdown("Ce module expose l'état de préparation du dataset destiné à l'apprentissage de modèles supervisés (Random Forest / GBT).")
        
        if "is_saturated" in df.columns:
            st.markdown("#### Équilibre de la variable cible (Target : is_saturated)")
            sat_dist = df["is_saturated"].value_counts().reset_index()
            sat_dist.columns = ["Statut", "Nombre"]
            sat_dist["Statut"] = sat_dist["Statut"].map({True: "🔴 Saturation Critique", False: "🟢 Trafic Fluide"})
            
            fig_pie = px.pie(sat_dist, values="Nombre", names="Statut", title="Distribution Target", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True, key="unique_chart_ml_pie")
            
        st.markdown("##### Échantillon de données préparées (Features & Vector)")
        st.dataframe(df.head(30), use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 3 : RÉGULARITÉ DES LIGNES (DONNÉES HIVE/SPARK)
# -----------------------------------------------------------------------------
elif datamart_choice == "regularite-lignes":
    st.title("⏱️ Suivi de la Régularité et des Retards (Métro / RER)")
    
    df = fetch_datamart("regularite-lignes")
    
    if df.empty:
        st.info("💡 Aucun historique de régularité disponible. Vérifiez la table correspondante en base de données.")
    else:
        st.markdown("Visualisation comparative du taux de ponctualité contractuel par ligne de transport.")
        
        rate_col = None
        for col in ["taux_regularite", "regularite", "ponctualite", "taux"]:
            if col in df.columns:
                rate_col = col
                break
                
        if rate_col:
            df_sorted = df.sort_values(rate_col, ascending=True)
            if "ligne" in df_sorted.columns:
                df_sorted["ligne_nom"] = df_sorted["ligne"].apply(map_ligne_code_to_name)
                
                fig_reg = px.bar(
                    df_sorted.head(15),
                    x=rate_col,
                    y="ligne_nom",
                    orientation="h",
                    title="Top 15 des Lignes avec les Taux de Régularité les Plus Faibles",
                    color=rate_col,
                    color_continuous_scale="Reds_r"
                )
                st.plotly_chart(fig_reg, use_container_width=True, key="unique_chart_regularite")
        
        st.markdown("##### Tableau Général de Synthèse de la Régularité")
        st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# MODULE 4 : PONCTUALITÉ TRANSILIEN (SNCF)
# -----------------------------------------------------------------------------
elif datamart_choice == "ponctualite-transilien":
    st.title("📊 Ponctualité Mensuelle Contractuelle Transilien")
    
    df = fetch_datamart("ponctualite-transilien")
    
    if df.empty:
        st.info("💡 Les données de ponctualité historique Transilien ne sont pas chargées.")
    else:
        st.markdown("Historique mensuel des indicateurs de ponctualité comparés aux objectifs fixés par Île-de-France Mobilités.")
        st.dataframe(df, use_container_width=True)

# -----------------------------------------------------------------------------
# PIED DE PAGE DYNAMIQUE
# -----------------------------------------------------------------------------
st.markdown("---")
st.caption(f"Dernière synchronisation locale de l'interface : {datetime.now().strftime('%d/%m/%Y à %H:%M:%S')}")