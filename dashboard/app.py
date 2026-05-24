# -*- coding: utf-8 -*-
"""
app_simple.py - Dashboard Streamlit simplifié pour IDFM
Version allégée pour éviter les problèmes de chargement infini
"""

import configparser
import os
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# =====================================================
# CONFIGURATION
# =====================================================

CONFIG_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "config", "config.ini")
)
_config = configparser.ConfigParser()
_config.read(CONFIG_PATH)
_api = _config["api"]

API_URL = _api.get("api_url", "http://localhost:8000")
LOGIN_USER = _api.get("login_user", "admin")
LOGIN_PASSWORD = _api.get("login_password", "admin")

st.set_page_config(
    page_title="IDFM - Analyse du Réseau Ferré",
    page_icon="🚇",
    layout="wide",
)

st.title("🚇 Tableau de Bord IDFM - Réseau Ferré")
st.markdown("**Où et quand le réseau souffre-t-il le plus ?**")

# =====================================================
# ACCES A L'API
# =====================================================

@st.cache_data(ttl=600)
def get_token():
    """Authentifie auprès de l'API"""
    try:
        resp = requests.post(
            f"{API_URL}/auth/login",
            data={"username": LOGIN_USER, "password": LOGIN_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except Exception as e:
        st.error(f"❌ Erreur d'authentification : {e}")
        return None


@st.cache_data(ttl=600)
def fetch_datamart(endpoint, page_size=5000):
    """Récupère les données du datamart"""
    token = get_token()
    if not token:
        return pd.DataFrame()

    headers = {"Authorization": f"Bearer {token}"}
    rows = []
    page = 1

    try:
        while True:
            resp = requests.get(
                f"{API_URL}/datamarts/{endpoint}",
                headers=headers,
                params={"page": page, "page_size": page_size},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            
            if not data.get("data"):
                break
            
            rows.extend(data["data"])
            page += 1

        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du datamart {endpoint} : {e}")
        return pd.DataFrame()


# =====================================================
# INTERFACE PRINCIPALE
# =====================================================

# Guide d'utilisation
with st.expander("📖 Guide rapide"):
    st.markdown("""
    ### Qu'est-ce que ce dashboard ?
    Analyse des données de fréquentation et régularité du réseau IDFM (Métro + RER).
    
    ### Seuils clés
    - 🔴 **Saturation** : > 5 000 validations/heure
    - 🟠 **Ponctualité critique** : < 80%
    - 🟢 **Objectif IDFM** : > 95% de ponctualité
    """)

# Sélection du datamart
datamart_choice = st.selectbox(
    "📊 Sélectionnez une analyse :",
    ["frequentation-stations", "regularite-lignes", "evolution-temporelle", "saturation-ml"]
)

# =====================================================
# PAGE 1 : FREQUENTATION
# =====================================================

if datamart_choice == "frequentation-stations":
    st.markdown("### 📈 Fréquentation par Stations/Lignes")
    st.markdown("Quelles stations/lignes sont les plus saturées ?")
    
    df = fetch_datamart("frequentation-stations")
    
    if not df.empty:
        SATURATION_THRESHOLD = 5000
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Stations", df["id_station"].nunique())
        with col2:
            st.metric("🚇 Lignes", df["ligne"].nunique())
        with col3:
            st.metric("⏰ Créneaux", df["heure"].nunique())
        
        st.markdown(f"""
        **Seuil de saturation** : {SATURATION_THRESHOLD:,} validations/heure
        - 🟢 < 1 000 = Faible
        - 🟠 1 000-5 000 = Normal
        - 🔴 > 5 000 = Saturé
        """)
        
        # Top 10 lignes
        top_lines = df.groupby("ligne")["nb_validations"].mean().nlargest(10).reset_index()
        top_lines = top_lines.sort_values("nb_validations")
        
        fig = px.bar(
            top_lines,
            y="ligne",
            x="nb_validations",
            title="Top 10 Lignes par Fréquentation Moyenne",
            orientation="h",
            color="nb_validations",
            color_continuous_scale="Reds"
        )
        fig.add_vline(x=SATURATION_THRESHOLD, line_dash="dash", line_color="red")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau
        display_df = df[["ligne", "heure", "jour_type", "nb_validations"]].head(50).copy()
        display_df.columns = ["Ligne", "Heure", "Jour Type", "Validations"]
        st.dataframe(display_df, use_container_width=True)

# =====================================================
# PAGE 2 : REGULARITE
# =====================================================

elif datamart_choice == "regularite-lignes":
    st.markdown("### 📋 Régularité et Ponctualité")
    st.markdown("Quelles lignes sont les moins ponctuelles ?")
    
    df = fetch_datamart("regularite-lignes")
    
    if not df.empty:
        OBJECTIF = 95
        CRITIQUE = 80
        
        avg_ponct = df["taux_ponctualite"].mean()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if avg_ponct >= OBJECTIF:
                st.success(f"✅ Ponctualité : {avg_ponct:.1f}%")
            elif avg_ponct >= CRITIQUE:
                st.warning(f"⚠️ Ponctualité : {avg_ponct:.1f}%")
            else:
                st.error(f"🔴 Ponctualité : {avg_ponct:.1f}%")
        
        with col2:
            st.metric("🚇 Lignes", df["ligne"].nunique())
        with col3:
            st.metric("📅 Périodes", df["date"].nunique())
        
        # Graphique
        line_avg = df.groupby("ligne")["taux_ponctualite"].mean().sort_values().reset_index()
        
        fig = px.bar(
            line_avg,
            y="ligne",
            x="taux_ponctualite",
            title="Ponctualité par Ligne",
            orientation="h",
            color="taux_ponctualite",
            color_continuous_scale="RdYlGn"
        )
        fig.add_vline(x=OBJECTIF, line_dash="dash", line_color="green")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau
        display_df = df[["ligne", "date", "taux_ponctualite", "rang_regularite"]].head(50).copy()
        display_df.columns = ["Ligne", "Date", "Ponctualité (%)", "Rang"]
        st.dataframe(display_df, use_container_width=True)

# =====================================================
# PAGE 3 : EVOLUTION
# =====================================================

elif datamart_choice == "evolution-temporelle":
    st.markdown("### 📈 Évolution Temporelle")
    st.markdown("Comment évolue la fréquentation dans le temps ?")
    
    df = fetch_datamart("evolution-temporelle")
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Fréquentation", f"{df['frequentation_cumulee'].sum():,.0f}")
        with col2:
            st.metric("🚇 Stations", f"{df['nb_stations'].mean():.0f}")
        with col3:
            st.metric("📈 Variation", f"{df['variation_semaine_precedente'].mean():+.1f}%")
        
        # Graphique temporel
        fig = px.line(
            df,
            x="date",
            y="frequentation_cumulee",
            title="Fréquentation Cumulée dans le Temps",
            markers=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau
        display_df = df[["date", "ligne", "frequentation_cumulee", "jour_semaine"]].head(50).copy()
        display_df.columns = ["Date", "Ligne", "Fréquentation", "Jour Semaine"]
        st.dataframe(display_df, use_container_width=True)

# =====================================================
# PAGE 4 : SATURATION ML
# =====================================================

elif datamart_choice == "saturation-ml":
    st.markdown("### 🤖 Dataset Saturation (ML)")
    st.markdown("Données préparées pour prédiction d'IA")
    
    df = fetch_datamart("saturation-ml")
    
    if not df.empty:
        sat_count = (df["est_saturation"] == 1).sum()
        total = len(df)
        sat_pct = sat_count / total * 100 if total > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 Saturés", f"{sat_count:,}")
        with col2:
            st.metric("📊 Total", f"{total:,}")
        with col3:
            st.metric("📈 %", f"{sat_pct:.1f}%")
        
        # Pie chart
        labels = ["Normal", "Saturé"]
        values = [total - sat_count, sat_count]
        fig = px.pie(
            names=labels,
            values=values,
            title="Distribution Saturation",
            color_discrete_map={"Normal": "#2ecc71", "Saturé": "#e74c3c"}
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau
        display_df = df[["ligne", "heure", "jour_type", "nb_validations", "est_saturation"]].head(100).copy()
        display_df.columns = ["Ligne", "Heure", "Jour Type", "Validations", "Saturé"]
        display_df["Saturé"] = display_df["Saturé"].map({0: "🟢 Non", 1: "🔴 Oui"})
        st.dataframe(display_df, use_container_width=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em;'>
📊 Dashboard IDFM — Source : Île-de-France Mobilités
</div>
""", unsafe_allow_html=True)
