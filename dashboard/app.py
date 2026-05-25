import configparser
import os
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

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
    page_title="IDFM - Analyse du Réseau Ferre",
    layout="wide",
)

st.title("Tableau de Bord IDFM - Réseau Ferre")
st.markdown("**Ou et quand le reseau souffre-t-il le plus ?**")

STIF_TO_LIGNE = {
    100: "RER A",
    760: "RER B",
    761: "RER C",
    762: "RER D",
    800: "RER E",
    810: "Transilien H",
    820: "Transilien J",
    830: "Transilien K",
    840: "Transilien L",
    850: "Transilien N",
    860: "Transilien P",
    870: "Transilien R",
    880: "Transilien U",
}

JOUR_TYPE_MAPPING = {
    "DIJFP": "Lundi-Vendredi",
    "JOHV": "Samedi",
    "JOVS": "Dimanche",
    "SAHV": "Samedi",
    "SAVS": "Dimanche",
}

def map_ligne_code_to_name(code):
    try:
        code_int = int(code) if not isinstance(code, int) else code
        return STIF_TO_LIGNE.get(code_int, str(code))
    except (ValueError, TypeError):
        return str(code)

def map_jour_type(jour_code):
    return JOUR_TYPE_MAPPING.get(str(jour_code), str(jour_code))

_STATION_CACHE = {}
_STATION_CACHE_LOADED = False

_REVERSE_STATION_MAPPING = {}
for station_name, ids in STATION_MAPPING.items():
    for sid in ids:
        _REVERSE_STATION_MAPPING[sid] = station_name
        _REVERSE_STATION_MAPPING[str(sid)] = station_name
        try:
            _REVERSE_STATION_MAPPING[int(sid)] = station_name
        except (ValueError, TypeError):
            pass

def load_station_cache():
    global _STATION_CACHE, _STATION_CACHE_LOADED
    if _STATION_CACHE_LOADED:
        return
    _STATION_CACHE.update(_REVERSE_STATION_MAPPING)
    try:
        resp = requests.post(
            f"{API_URL}/auth/login",
            data={"username": LOGIN_USER, "password": LOGIN_PASSWORD},
            timeout=10,
        )
        if resp.ok:
            token = resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            page = 1
            while True:
                resp = requests.get(
                    f"{API_URL}/data/stations",
                    headers=headers,
                    params={"page": page, "page_size": 1000},
                    timeout=10,
                )
                if resp.ok:
                    data = resp.json()
                    stations_data = data.get("data", [])
                    if not stations_data:
                        break
                    for station in stations_data:
                        station_id = station.get("id_station")
                        station_name = (
                            station.get("nom_station") or 
                            station.get("ArRName") or 
                            station.get("name") or
                            station.get("station_name")
                        )
                        if station_id is not None and station_name:
                            _STATION_CACHE[station_id] = station_name
                    page += 1
                else:
                    break
    except Exception:
        pass
    _STATION_CACHE_LOADED = True

def get_station_name(df, station_id):
    row = df[df['id_station'] == station_id]
    if not row.empty:
        return row.iloc[0]['nom_station']
    return str(station_id)

def clean_dataframe(df, mapping_config):
    df_copy = df.copy()
    for col, mapper_func in mapping_config.items():
        if col in df_copy.columns:
            df_copy[col] = df_copy[col].apply(lambda x: mapper_func(x) if pd.notna(x) else "N/A")
    return df_copy

@st.cache_data(ttl=600)
def get_token():
    try:
        resp = requests.post(
            f"{API_URL}/auth/login",
            data={"username": LOGIN_USER, "password": LOGIN_PASSWORD},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]
    except Exception as e:
        st.error(f"Erreur d'authentification : {e}")
        return None

@st.cache_data(ttl=600)
def fetch_datamart(endpoint, page_size=5000):
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
        df = pd.DataFrame(rows)
        if df.empty or (endpoint == "regularite-lignes" and df["taux_ponctualite"].sum() == 0):
            st.warning("API retourne des donnees invalides, chargement depuis CSV local...")
            return load_regularite_local() if endpoint == "regularite-lignes" else pd.DataFrame()
        return df
    except Exception as e:
        st.warning(f"Chargement API echoue pour {endpoint}, tentative CSV local...")
        return load_regularite_local() if endpoint == "regularite-lignes" else pd.DataFrame()

def load_regularite_local():
    import configparser
    import os
    try:
        config = configparser.ConfigParser()
        config_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "config", "config.ini")
        )
        config.read(config_path)
        ponctualite_csv = config["local"]["ponctualite_csv_path"]
        df = pd.read_csv(ponctualite_csv, delimiter=';')
        df.columns = df.columns.str.strip()
        column_mapping = {}
        for old_col in df.columns:
            if old_col == 'Date':
                column_mapping[old_col] = 'date'
            elif old_col == 'Ligne':
                column_mapping[old_col] = 'ligne'
            elif old_col == 'Nom de la ligne':
                column_mapping[old_col] = 'nom_ligne'
            elif 'Taux de ponctualite' in old_col:
                column_mapping[old_col] = 'taux_ponctualite'
            elif 'voyageurs' in old_col.lower() or 'retard' in old_col.lower():
                column_mapping[old_col] = 'delai_moyen'
        df = df.rename(columns=column_mapping)
        if 'taux_ponctualite' in df.columns:
            df['taux_ponctualite'] = pd.to_numeric(
                df['taux_ponctualite'].astype(str).str.replace(',', '.'), 
                errors='coerce'
            )
        if 'date' in df.columns and 'taux_ponctualite' in df.columns:
            df['rang_regularite'] = df.groupby('date')['taux_ponctualite'].rank(method='min', ascending=False)
        print(f"CSV regularite charge: {len(df)} lignes, mean taux_ponctualite = {df['taux_ponctualite'].mean():.2f}%")
        return df
    except Exception as e:
        print(f"Erreur chargement CSV regularite: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

load_station_cache()

with st.expander("Guide rapide"):
    st.markdown("""
    ### Qu'est-ce que ce dashboard ?
    Analyse des donnees de frequentation et regularite du reseau IDFM (Metro + RER).
    
    ### Seuils cles
    - Saturation : > 7% du trafic quotidien
    - Ponctualite critique : < 80%
    - Objectif IDFM : > 95% de ponctualite
    """)

datamart_choice = st.selectbox(
    "Selectionnez une analyse :",
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
        # Seuil de saturation : 7.0% du trafic quotidien (spécification IDFM)
        SATURATION_THRESHOLD = 7.0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 Stations", df["id_station"].nunique())
        with col2:
            st.metric("🚇 Lignes", df["ligne"].nunique())
        with col3:
            st.metric("⏰ Créneaux", df["heure"].nunique())
        
        st.markdown(f"""
        **Seuil de saturation** : {SATURATION_THRESHOLD}% du trafic quotidien
        - 🟢 < 3% = Faible
        - 🟠 3-7% = Normal
        - 🔴 > 7% = Saturé
        """)
        
        # Onglets pour les différentes vues
        tab1, tab2, tab3 = st.tabs(["📊 Par Ligne", "🏢 Par Station", "📋 Détail"])
        
        with tab1:
            st.markdown("#### Top 10 Lignes par Fréquentation Moyenne")
            top_lines = df.groupby("ligne")["pourcentage_validations"].mean().nlargest(10).reset_index()
            top_lines = top_lines.sort_values("pourcentage_validations")
            top_lines["ligne_nom"] = top_lines["ligne"].apply(map_ligne_code_to_name)
            
            fig = px.bar(
                top_lines,
                y="ligne_nom",
                x="pourcentage_validations",
                title="Fréquentation Moyenne par Ligne",
                orientation="h",
                color="pourcentage_validations",
                color_continuous_scale="Reds"
            )
            fig.update_layout(yaxis_title="Ligne", xaxis_title="% du Trafic Quotidien")
            fig.add_vline(x=SATURATION_THRESHOLD, line_dash="dash", line_color="darkred", annotation_text=f"Seuil: {SATURATION_THRESHOLD}%")
            st.plotly_chart(fig, use_container_width=True)
            
            # Tableau par ligne et jour
            st.markdown("##### Détail par Ligne et Jour Type")
            line_detail = df.groupby(["ligne", "jour_type"]).agg({
                "pourcentage_validations": ["mean", "max"],
                "id_station": "nunique"
            }).reset_index()
            line_detail.columns = ["Ligne", "Jour", "% Moyen", "% Max", "Stations"]
            line_detail["Ligne"] = line_detail["Ligne"].apply(map_ligne_code_to_name)
            line_detail["Jour"] = line_detail["Jour"].apply(map_jour_type)
            line_detail = line_detail.sort_values("% Moyen", ascending=False)
            st.dataframe(line_detail.head(30), use_container_width=True, hide_index=True)
        
        with tab2:
            st.markdown("#### Top 10 Stations par Fréquentation Moyenne")
            top_stations = df.groupby("id_station")["pourcentage_validations"].mean().nlargest(10).reset_index()
            top_stations = top_stations.sort_values("pourcentage_validations")
            top_stations["station_nom"] = top_stations["id_station"].apply(get_station_name)
            top_stations = top_stations[["station_nom", "pourcentage_validations"]].rename(
                columns={"station_nom": "Station", "pourcentage_validations": "% Trafic"}
            )
            
            fig = px.bar(
                top_stations,
                y="Station",
                x="% Trafic",
                title="Top 10 Stations par Fréquentation",
                orientation="h",
                color="% Trafic",
                color_continuous_scale="Oranges"
            )
            fig.update_layout(yaxis_title="Station", xaxis_title="% du Trafic Quotidien")
            fig.add_vline(x=SATURATION_THRESHOLD, line_dash="dash", line_color="darkred", annotation_text=f"Seuil: {SATURATION_THRESHOLD}%")
            st.plotly_chart(fig, use_container_width=True)
            
            # Tableau stations saturées
            st.markdown("##### Stations les Plus Saturées")
            saturated = df[df["pourcentage_validations"] > SATURATION_THRESHOLD].copy()
            if len(saturated) > 0:
                sat_summary = saturated.groupby("id_station").agg({
                    "pourcentage_validations": ["mean", "max", "count"],
                    "ligne": "first",
                    "jour_type": "first"
                }).reset_index()
                sat_summary.columns = ["Station ID", "% Moyen", "% Max", "Occurrences", "Ligne", "Jour"]
                sat_summary["Station"] = sat_summary["Station ID"].apply(get_station_name)
                sat_summary["Ligne"] = sat_summary["Ligne"].apply(map_ligne_code_to_name)
                sat_summary["Jour"] = sat_summary["Jour"].apply(map_jour_type)
                sat_summary = sat_summary[["Station", "Ligne", "Jour", "% Moyen", "% Max", "Occurrences"]].sort_values("% Max", ascending=False)
                st.dataframe(sat_summary, use_container_width=True, hide_index=True)
            else:
                st.info("✅ Aucune saturation détectée")
        
        with tab3:
            st.markdown("##### Données Détaillées (50 premières lignes)")
            display_df = df[["id_station", "ligne", "heure", "jour_type", "pourcentage_validations"]].head(50).copy()
            display_df["station_nom"] = display_df["id_station"].apply(get_station_name)
            display_df["ligne_nom"] = display_df["ligne"].apply(map_ligne_code_to_name)
            display_df["jour_nom"] = display_df["jour_type"].apply(map_jour_type)
            display_df = display_df[["station_nom", "ligne_nom", "heure", "jour_nom", "pourcentage_validations"]].rename(
                columns={
                    "station_nom": "Station",
                    "ligne_nom": "Ligne",
                    "heure": "Heure",
                    "jour_nom": "Jour Type",
                    "pourcentage_validations": "% Trafic"
                }
            )
            st.dataframe(display_df, use_container_width=True, height=400)

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
        
        # Nettoyer les données
        df['taux_ponctualite'] = pd.to_numeric(df['taux_ponctualite'], errors='coerce')
        df = df.dropna(subset=['taux_ponctualite'])
        
        if len(df) > 0:
            avg_ponct = df["taux_ponctualite"].mean()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if avg_ponct >= OBJECTIF:
                    st.success(f"✅ Ponctualité moyenne : **{avg_ponct:.1f}%**")
                elif avg_ponct >= CRITIQUE:
                    st.warning(f"⚠️ Ponctualité moyenne : **{avg_ponct:.1f}%**")
                else:
                    st.error(f"🔴 Ponctualité moyenne : **{avg_ponct:.1f}%**")
            
            with col2:
                nb_lignes = df['ligne'].nunique()
                st.metric("🚇 Lignes", nb_lignes)
            
            with col3:
                nb_dates = df['date'].nunique()
                st.metric("📅 Périodes", nb_dates)
            
            st.markdown(f"""
            ### 📊 Seuils IDFM
            - 🟢 **> {OBJECTIF}%** = Excellent ✓
            - 🟠 **{CRITIQUE}-{OBJECTIF}%** = À surveiller
            - 🔴 **< {CRITIQUE}%** = Critique 🚨
            """)
            
            # Graphique par ligne avec noms
            line_avg = df.groupby("ligne")["taux_ponctualite"].mean().sort_values().reset_index()
            line_avg["ligne_nom"] = line_avg["ligne"].apply(map_ligne_code_to_name)
            
            if len(line_avg) > 0:
                # Colorier selon les seuils
                def get_color(val):
                    if val >= OBJECTIF:
                        return "#2ecc71"  # Vert
                    elif val >= CRITIQUE:
                        return "#f39c12"  # Orange
                    else:
                        return "#e74c3c"  # Rouge
                
                line_avg["color"] = line_avg["taux_ponctualite"].apply(get_color)
                
                fig = px.bar(
                    line_avg,
                    y="ligne_nom",
                    x="taux_ponctualite",
                    title="📊 Ponctualité par Ligne (Vert=Bon, Orange=À surveiller, Rouge=Critique)",
                    orientation="h",
                    color="color",
                    color_discrete_map={v: v for v in line_avg["color"].unique()}
                )
                fig.update_layout(yaxis_title="Ligne", xaxis_title="Ponctualité (%)")
                fig.add_vline(x=OBJECTIF, line_dash="dash", line_color="darkgreen", 
                             annotation_text=f"Objectif ({OBJECTIF}%)")
                st.plotly_chart(fig, use_container_width=True)
            
            # Tableau détaillé sans codes
            st.markdown("#### 📋 Détails par Ligne")
            display_df = df[["ligne", "nom_ligne", "taux_ponctualite", "date"]].copy()
            display_df["ligne_nom"] = display_df["ligne"].apply(map_ligne_code_to_name)
            display_df = display_df[["ligne_nom", "nom_ligne", "taux_ponctualite", "date"]]
            display_df.columns = ["Ligne", "Nom Complet", "Ponctualité (%)", "Période"]
            display_df["Ponctualité (%)"] = display_df["Ponctualité (%)"].round(1)
            display_df = display_df.sort_values("Ponctualité (%)", ascending=True)
            
            st.dataframe(display_df.drop_duplicates(subset=["Ligne"]), use_container_width=True, hide_index=True)
            st.caption(f"Affichage : {len(display_df)} enregistrements")
        else:
            st.warning("⚠️ Aucune donnée valide de régularité")
    else:
        st.error("❌ Impossible de charger les données de régularité")

# =====================================================
# PAGE 3 : EVOLUTION
# =====================================================

elif datamart_choice == "evolution-temporelle":
    st.markdown("### 📈 Évolution Temporelle")
    st.markdown("Comment évolue la fréquentation selon le jour-type ?")
    
    df = fetch_datamart("evolution-temporelle")
    
    if not df.empty:
        # Aggréger par jour-type
        df_by_jour = df.groupby("date").agg({
            "frequentation_cumulee": "sum",
            "nb_stations": "mean",
            "variation_semaine_precedente": "first"
        }).reset_index()
        
        df_by_jour["jour_nom"] = df_by_jour["date"].apply(map_jour_type)
        
        # Métriques générales
        col1, col2, col3 = st.columns(3)
        with col1:
            total_freq = df_by_jour["frequentation_cumulee"].sum()
            st.metric("📊 Fréquentation Totale", f"{total_freq:,.0f}")
        with col2:
            nb_jours = df_by_jour.shape[0]
            st.metric("📅 Jours Type", f"{nb_jours}")
        with col3:
            avg_variation = df_by_jour["variation_semaine_precedente"].mean()
            st.metric("📈 Variation Moyenne", f"{avg_variation:+.1f}%")
        
        # Graphique par jour-type
        fig = px.bar(
            df_by_jour.sort_values("frequentation_cumulee", ascending=True),
            y="jour_nom",
            x="frequentation_cumulee",
            title="Fréquentation Cumulée par Jour-Type",
            orientation="h",
            color="frequentation_cumulee",
            color_continuous_scale="Blues"
        )
        fig.update_layout(xaxis_title="Fréquentation Cumulée", yaxis_title="Jour Type")
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau détaillé par ligne et jour-type
        st.markdown("#### 📋 Détail par Ligne et Jour-Type")
        display_df = df[["date", "ligne", "frequentation_cumulee", "nb_stations"]].copy()
        display_df["jour_nom"] = display_df["date"].apply(map_jour_type)
        display_df["ligne_nom"] = display_df["ligne"].apply(map_ligne_code_to_name)
        display_df = display_df[["jour_nom", "ligne_nom", "frequentation_cumulee", "nb_stations"]]
        display_df.columns = ["Jour Type", "Ligne", "Fréquentation", "Stations"]
        display_df = display_df.sort_values(["Jour Type", "Fréquentation"], ascending=[True, False])
        st.dataframe(display_df, use_container_width=True, height=400)

# =====================================================
# PAGE 4 : SATURATION ML
# =====================================================

elif datamart_choice == "saturation-ml":
    st.markdown("### 🤖 Dataset Saturation (ML)")
    st.markdown("Analyse des pics de saturation et prédiction d'IA")
    
    df = fetch_datamart("saturation-ml")
    
    if not df.empty:
        # Recalculer est_saturation basé sur le seuil IDFM de 7.0%
        SATURATION_THRESHOLD_ML = 7.0
        df["est_saturation_nouveau"] = (df["pourcentage_validations"] > SATURATION_THRESHOLD_ML).astype(int)
        
        sat_count = (df["est_saturation_nouveau"] == 1).sum()
        total = len(df)
        sat_pct = sat_count / total * 100 if total > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔴 Situations Saturées", f"{sat_count:,}")
        with col2:
            st.metric("📊 Total Observations", f"{total:,}")
        with col3:
            st.metric("📈 % Saturation", f"{sat_pct:.1f}%")
        
        # Onglets
        tab1, tab2, tab3 = st.tabs(["📊 Distribution", "⚠️ Saturées", "📋 Détail"])
        
        with tab1:
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
            
            # Saturation par ligne
            st.markdown("##### Saturation par Ligne")
            line_sat = df[df["est_saturation_nouveau"] == 1].groupby("ligne").size().reset_index(name="Saturations")
            line_sat["Ligne"] = line_sat["ligne"].apply(map_ligne_code_to_name)
            line_sat = line_sat[["Ligne", "Saturations"]].sort_values("Saturations", ascending=True)
            
            fig = px.bar(
                line_sat,
                y="Ligne",
                x="Saturations",
                title="Nombre de Saturations par Ligne",
                orientation="h",
                color="Saturations",
                color_continuous_scale="Reds"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.markdown("##### Pics de Saturation")
            saturated_df = df[df["est_saturation_nouveau"] == 1].copy()
            
            if len(saturated_df) > 0:
                saturated_df["Ligne"] = saturated_df["ligne"].apply(map_ligne_code_to_name)
                saturated_df["Jour"] = saturated_df["jour_type"].apply(map_jour_type)
                display_sat = saturated_df[["Ligne", "heure", "Jour", "pourcentage_validations", "taux_ponctualite"]].head(100)
                display_sat.columns = ["Ligne", "Heure", "Jour Type", "% Trafic", "Ponctualité (%)"]
                display_sat["Ponctualité (%)"] = display_sat["Ponctualité (%)"].round(1)
                display_sat["% Trafic"] = display_sat["% Trafic"].round(2)
                display_sat = display_sat.sort_values("% Trafic", ascending=False)
                st.dataframe(display_sat, use_container_width=True, height=400, hide_index=True)
                st.caption(f"Affichage : {min(100, len(saturated_df))} pics de saturation (> 7% du trafic)")
            else:
                st.info("✅ Aucune saturation détectée")
        
        with tab3:
            st.markdown("##### Toutes les Données ML (100 premières)")
            display_df = df[["ligne", "heure", "jour_type", "pourcentage_validations", "taux_ponctualite", "est_saturation_nouveau"]].head(100).copy()
            display_df["Ligne"] = display_df["ligne"].apply(map_ligne_code_to_name)
            display_df["Jour"] = display_df["jour_type"].apply(map_jour_type)
            display_df["Saturé"] = display_df["est_saturation_nouveau"].map({0: "🟢 Non", 1: "🔴 Oui"})
            display_df = display_df[["Ligne", "heure", "Jour", "pourcentage_validations", "taux_ponctualite", "Saturé"]]
            display_df.columns = ["Ligne", "Heure", "Jour Type", "% Trafic", "Ponctualité (%)", "Saturé"]
            display_df["Ponctualité (%)"] = display_df["Ponctualité (%)"].round(1)
            display_df["% Trafic"] = display_df["% Trafic"].round(2)
            st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em;'>
📊 Dashboard IDFM — Source : Île-de-France Mobilités
</div>
""", unsafe_allow_html=True)
