# -*- coding: utf-8 -*-
"""
app.py - Dashboard Streamlit pour l'analyse du réseau ferré IDFM

Le dashboard ne touche PAS PostgreSQL directement : il consomme l'API REST
sécurisée (couche au-dessus des datamarts).

Lancement (depuis la racine du projet) :
    streamlit run dashboard/app.py

Pré-requis : l'API doit être lancée (uvicorn api.app:app).
"""

import configparser
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

st.title("🚇 Tableau de Bord IDFM - Analyse du Réseau Ferré")
st.markdown("**Où et quand le réseau souffre-t-il le plus ? Réponses basées sur les données 2025**")

# Section "Comment lire ce dashboard" en prominent
with st.expander("📖 **GUIDE - Comment utiliser ce tableau de bord**", expanded=False):
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 Objectif
        Comprendre où et quand le réseau métro/RER souffre le plus
        en termes de :
        - 👥 **Surcharge** (fréquentation extrême)
        - 🕐 **Retards** (ponctualité insuffisante)
        - 📉 **Variations** (écarts par rapport à la normal)
        """)
    
    with col2:
        st.markdown("""
        ### 📊 Comment lire les chiffres
        - Les chiffres rouges 🔴 = situation critique
        - Les chiffres orange � = attention requise
        - Les chiffres verts 🟢 = situation normale
        
        ### ⏱️ Jours types
        - **DIJFP** = Jour ouvrable (lun-ven, hors fériés)
        - **SAMEDI** = Samedi
        - **DIMANCHE** = Dimanche
        """)
    
    st.markdown("""
    ### 📍 Structure du tableau de bord
    1. **Fréquentation** : Quelles stations saturent ?
    2. **Régularité** : Quelles lignes prennent du retard ?
    3. **Évolution** : Comment ça change dans le temps ?
    4. **IA/Saturation** : Dataset pour prédire les pics
    """)

# =====================================================
# ACCES A L'API
# =====================================================

@st.cache_data(ttl=3000, show_spinner=False)
def get_token():
    """Authentifie le dashboard auprès de l'API et récupère un token JWT."""
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


@st.cache_data(ttl=600, show_spinner="Chargement des données depuis l'API...")
def fetch_datamart(endpoint, page_size=5000):
    """
    Récupère l'intégralité d'un datamart en parcourant toutes les pages
    de l'API.
    """
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
                timeout=30,
            )
            resp.raise_for_status()
            payload = resp.json()

            rows.extend(payload["data"])

            if page >= payload["total_pages"]:
                break

            page += 1

        return pd.DataFrame(rows)

    except Exception as e:
        st.error(f"❌ Erreur lors du chargement du datamart {endpoint} : {e}")
        return pd.DataFrame()


# =====================================================
# CONTENU PRINCIPAL
# =====================================================

# Vérifier la connexion API
try:
    resp = requests.get(f"{API_URL}/", timeout=5)
    resp.raise_for_status()
    st.success("✅ Connexion API établie")
except:
    st.error("❌ API non accessible. Assurez-vous que l'API est lancée (uvicorn api.app:app)")
    st.stop()

# Sélection du datamart à visualiser
st.markdown("---")
st.subheader("📊 Sélectionnez un datamart")

datamart_choice = st.radio(
    "Datamarts disponibles :",
    [
        "frequentation-stations",
        "regularite-lignes",
        "evolution-temporelle",
        "saturation-ml"
    ],
    format_func=lambda x: {
        "frequentation-stations": "1️⃣ Fréquentation par Station/Ligne",
        "regularite-lignes": "2️⃣ Régularité des Lignes",
        "evolution-temporelle": "3️⃣ Évolution Temporelle",
        "saturation-ml": "4️⃣ Saturation (ML)"
    }.get(x, x)
)

# =====================================================
# DATAMART 1 : FREQUENTATION PAR STATION/LIGNE
# =====================================================

if datamart_choice == "frequentation-stations":
    st.markdown("### 1️⃣ Fréquentation par Station et Ligne")
    st.markdown("""
    **Qu'est-ce que c'est ?**
    
    La fréquentation mesure le nombre de validations (passages) par heure et par ligne.
    Elle varie selon l'heure du jour (heures de pointe le matin et soir) et le type de jour (semaine/weekend).
    
    **Comment ça marche :**
    - **Ligne** : Numéro de la ligne de métro/RER (ex: 1, 2, 4, A, B)
    - **Heure** : Créneau horaire (ex: 7H-8H = entre 7h et 8h du matin)
    - **Jour-type** : DIJFP = jour normal, SAMEDI = samedi, DIMANCHE = dimanche
    - **% Validations** : Pourcentage du trafic total de la ligne à cette heure
    - **Fréquentation Max** : Nombre maximum de passagers observés
    """)

    df_freq = fetch_datamart("frequentation-stations")

    if not df_freq.empty:
        # SEUIL DE SATURATION (configuration)
        SATURATION_THRESHOLD = 5000
        
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "📊 Stations analysées",
                df_freq["id_station"].nunique(),
                "arrêts"
            )

        with col2:
            st.metric(
                "🚇 Lignes couvertes",
                df_freq["ligne"].nunique(),
                "lignes"
            )

        with col3:
            st.metric(
                "⏰ Créneaux horaires",
                df_freq["heure"].nunique(),
                "heures"
            )

        # Contexte métier
        st.markdown("""
        ### 📈 Qu'est-ce que la fréquentation ?
        C'est le **nombre de personnes validant leur titre** (badgeage) par station, ligne et heure.
        
        **Seuils clés :**
        - 🟢 < 1 000 = Faible charge
        - 🟠 1 000-5 000 = Normal à chargé
        - 🔴 > 5 000 = **SATURATION** (action requise)
        """)

        # Sélection de ligne
        ligne_selected = st.selectbox(
            "🔍 **Filtrer par ligne** (optionnel) :",
            ["Toutes les lignes"] + sorted(df_freq["ligne"].unique().tolist()),
            help="Sélectionnez une ligne spécifique ou 'Toutes' pour voir l'ensemble du réseau"
        )

        if ligne_selected != "Toutes les lignes":
            df_filtered = df_freq[df_freq["ligne"] == ligne_selected]
            st.info(f"📍 Affichage des données pour la ligne **{ligne_selected}**")
        else:
            df_filtered = df_freq

        # Graphique 1 : Top 10 lignes par fréquentation moyenne
        top_lignes = df_filtered.groupby("ligne")["nb_validations"].mean() \
            .nlargest(10).reset_index()
        top_lignes = top_lignes.sort_values("nb_validations")

        fig1 = px.bar(
            top_lignes,
            y="ligne",
            x="nb_validations",
            title="🏆 Top 10 Lignes par Fréquentation Moyenne",
            labels={"ligne": "Ligne", "nb_validations": "Fréquentation Moyenne (validations/h)"},
            color="nb_validations",
            color_continuous_scale="Reds",
            orientation="h"
        )
        fig1.update_layout(showlegend=False, hovermode='closest')
        fig1.add_vline(x=SATURATION_THRESHOLD, line_dash="dash", line_color="red",
                      annotation_text="Seuil saturation", annotation_position="top right")
        st.plotly_chart(fig1, use_container_width=True)
        
        st.caption("""
        💡 **Lecture** : Ces lignes dépassent régulièrement le seuil de saturation (5 000 validations/heure).
        Les barres rouges sombre = priorité absolue. Les lignes au-delà du trait rouge = saturées en moyenne.
        """)
        st.caption("💡 **Lecture** : Les lignes à droite sont les plus fréquentées. C'est une moyenne sur tous les créneaux horaires.")

        # Graphique 2 : Fréquentation par heure
        hourly_data = df_filtered.groupby("heure")["nb_validations"].mean().reset_index()
        
        fig2 = px.line(
            hourly_data,
            x="heure",
            y="nb_validations",
            title="📈 Fréquentation Moyenne par Heure de la Journée",
            labels={"heure": "Heure", "nb_validations": "Fréquentation Moyenne"},
            markers=True
        )
        fig2.update_traces(line=dict(color='#FF6B6B', width=3), marker=dict(size=8))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("💡 **Lecture** : Les pics du matin (7-9h) et du soir (17-19h) sont visibles. C'est normal !")

        # Tableau détaillé avec explications
        st.markdown("#### 📋 Détails des données")
        st.markdown("""
        Le tableau ci-dessous montre les détails complets de la fréquentation.
        Vous pouvez le trier en cliquant sur les en-têtes de colonne.
        """)
        
        display_df = df_filtered[["ligne", "heure", "jour_type", "pourcentage_validations", "nb_validations", "rang_frequentation"]].copy()
        display_df.columns = ["Ligne", "Heure", "Jour-type", "% du trafic", "Fréquentation", "Rang"]
        display_df["Fréquentation"] = display_df["Fréquentation"].round(0).astype(int)
        display_df["% du trafic"] = display_df["% du trafic"].round(2)
        
        st.dataframe(display_df.head(100), use_container_width=True)
        st.caption(f"Affichage : 100 premières lignes sur {len(display_df)} total")

# =====================================================
# DATAMART 2 : REGULARITE PAR LIGNE
# =====================================================

elif datamart_choice == "regularite-lignes":
    st.markdown("### 2️⃣ Quelles lignes sont les moins ponctuelles ?")
    st.markdown("""
    La ponctualité est la **% de trains arrivant à l'heure** (variation ±5 minutes acceptable).
    C'est un indicateur clé de satisfaction des usagers.
    """)

    df_reg = fetch_datamart("regularite-lignes")

    if not df_reg.empty:
        # SEUILS MÉTIER IDFM
        OBJECTIF_PONCTUALITE = 95  # Target IDFM
        SEUIL_CRITIQUE = 80        # Situation dégradée
        
        col1, col2, col3 = st.columns(3)

        avg_ponctualite = df_reg['taux_ponctualite'].mean()
        
        with col1:
            if avg_ponctualite >= OBJECTIF_PONCTUALITE:
                st.success(f"✅ Ponctualité moyenne : **{avg_ponctualite:.1f}%**")
                st.caption("Au-delà de l'objectif IDFM (95%)")
            elif avg_ponctualite >= SEUIL_CRITIQUE:
                st.warning(f"⚠️ Ponctualité moyenne : **{avg_ponctualite:.1f}%**")
                st.caption(f"Sous l'objectif ({OBJECTIF_PONCTUALITE}%), situation acceptable")
            else:
                st.error(f"🔴 Ponctualité moyenne : **{avg_ponctualite:.1f}%**")
                st.caption(f"**Critique** : en dessous de {SEUIL_CRITIQUE}%")

        with col2:
            nb_lignes = df_reg['ligne'].nunique()
            st.metric(
                "🚇 Lignes analysées",
                nb_lignes
            )

        with col3:
            nb_observations = len(df_reg)
            st.metric(
                "📊 Observations",
                nb_observations
            )

        # Contexte métier
        st.markdown(f"""
        ### 📋 Seuils de Ponctualité IDFM
        - 🟢 **> {OBJECTIF_PONCTUALITE}%** = Excellent (objectif atteint)
        - 🟠 **{SEUIL_CRITIQUE}-{OBJECTIF_PONCTUALITE}%** = Acceptable mais à surveiller
        - 🔴 **< {SEUIL_CRITIQUE}%** = **CRITIQUE** - Action immédiate recommandée
        
        **Qu'est-ce qui affecte la ponctualité ?**
        - Problèmes techniques (pannes, signalisation)
        - Surcharge (plus de passagers = plus lent)
        - Aléas externes (incidents, travaux)
        """)

        # Graphique 1 : Régularité par ligne (coloration par seuils)
        line_reg = df_reg.groupby("ligne")["taux_ponctualite"].mean() \
            .sort_values(ascending=True).reset_index()
        
        # Colorer selon les seuils
        def get_color_for_ponctualite(val):
            if val >= OBJECTIF_PONCTUALITE:
                return "green"
            elif val >= SEUIL_CRITIQUE:
                return "orange"
            else:
                return "red"
        
        line_reg["color"] = line_reg["taux_ponctualite"].apply(get_color_for_ponctualite)

        fig1 = px.bar(
            line_reg,
            y="ligne",
            x="taux_ponctualite",
            title="📊 Taux de Ponctualité par Ligne (Vert=Bon, Orange=À surveiller, Rouge=Critique)",
            labels={"ligne": "Ligne", "taux_ponctualite": "Ponctualité (%)"},
            color="color",
            color_discrete_map={"green": "#2ecc71", "orange": "#f39c12", "red": "#e74c3c"},
            orientation="h"
        )
        fig1.add_vline(x=OBJECTIF_PONCTUALITE, line_dash="dash", line_color="darkgreen", 
                      annotation_text=f"Objectif ({OBJECTIF_PONCTUALITE}%)", annotation_position="top right")
        fig1.add_vline(x=SEUIL_CRITIQUE, line_dash="dash", line_color="darkred",
                      annotation_text=f"Seuil critique ({SEUIL_CRITIQUE}%)", annotation_position="top left")
        fig1.update_layout(showlegend=False)
        st.plotly_chart(fig1, use_container_width=True)
        st.caption(f"""
        💡 **Comment lire ce graphique :**
        - Les barres **vertes** ({OBJECTIF_PONCTUALITE}%+) = excellente ponctualité ✅
        - Les barres **orange** ({SEUIL_CRITIQUE}-{OBJECTIF_PONCTUALITE}%) = à surveiller ⚠️
        - Les barres **rouges** (<{SEUIL_CRITIQUE}%) = situation critique 🔴
        """)

        # Graphique 2 : Évolution temporelle régularité
        time_reg = df_reg.groupby("date")["taux_ponctualite"].mean().reset_index()

        fig2 = px.line(
            time_reg,
            x="date",
            y="taux_ponctualite",
            title="📈 Tendance de la Ponctualité - Évolution dans le Temps",
            labels={"date": "Date/Période", "taux_ponctualite": "Taux de Ponctualité (%)"},
            markers=True,
            color_discrete_sequence=['#3498db']
        )
        fig2.add_hline(y=OBJECTIF_PONCTUALITE, line_dash="dash", line_color="green", 
                      annotation_text=f"Objectif: {OBJECTIF_PONCTUALITE}%", annotation_position="right")
        fig2.add_hline(y=SEUIL_CRITIQUE, line_dash="dash", line_color="red",
                      annotation_text=f"Seuil critique: {SEUIL_CRITIQUE}%", annotation_position="left")
        fig2.update_traces(line=dict(width=3), marker=dict(size=8))
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(f"""
        💡 **Interprétation** : 
        - Courbe **au-dessus** de la ligne verte ({OBJECTIF_PONCTUALITE}%) = objectif atteint ✅
        - Courbe **entre** les deux lignes = zone acceptable 🟠
        - Courbe **sous** la ligne rouge ({SEUIL_CRITIQUE}%) = action corrective urgente 🔴
        """)

        # Tableau détaillé avec améliorations et contexte
        st.markdown("#### 📋 Détails par ligne et date")
        st.markdown("""
        **Colonnes :**
        - **Rang (1=pire)** : Position dans le classement (1 = ponctualité la plus faible)
        - **Nom Ligne** : Identifiant complet de la ligne
        """)
        
        display_df = df_reg[["date", "ligne", "nom_ligne", "taux_ponctualite", "rang_regularite"]].copy()
        display_df.columns = ["Période", "Code Ligne", "Nom Ligne", "Ponctualité (%)", "Rang (1=pire)"]
        display_df["Ponctualité (%)"] = display_df["Ponctualité (%)"].round(1)
        
        # Ajouter une colonne de status
        display_df["Status"] = display_df["Ponctualité (%)"].apply(
            lambda x: "🟢 OK" if x >= OBJECTIF_PONCTUALITE else ("🟠 À surveiller" if x >= SEUIL_CRITIQUE else "🔴 CRITIQUE")
        )
        
        st.dataframe(display_df.head(50), use_container_width=True)
        st.caption(f"Affichage : 50 premières lignes sur {len(display_df)} total")

# =====================================================
# DATAMART 3 : EVOLUTION TEMPORELLE
# =====================================================

elif datamart_choice == "evolution-temporelle":
    st.markdown("### 3️⃣ Évolution Temporelle de la Fréquentation")
    st.markdown("""
    **Qu'est-ce que c'est ?**
    
    Cette analyse montre comment la fréquentation change au fil du temps.
    Elle détecte les tendances, les jours de baisse, les variations saisonnières.
    
    **Termes importants :**
    - **Fréquentation cumulée** : Total des validations sur la période
    - **Stations couvertes** : Nombre de stations actives
    - **Jour de la semaine** : Lundi, Mardi, etc. (comportements différents)
    - **Variation semaine précédente** : +5% = 5% plus de monde qu'avant
    
    **Pourquoi c'est utile ?**
    - Prévoir le besoin en personnel et équipements
    - Identifier les événements (vacances, grèves, événements)
    - Planifier les maintenances dans les creux de fréquentation
    """)

    df_evo = fetch_datamart("evolution-temporelle")

    if not df_evo.empty:
        col1, col2, col3 = st.columns(3)

        with col1:
            total_freq = df_evo['frequentation_cumulee'].sum()
            st.metric(
                "📊 Fréquentation totale",
                f"{total_freq:,.0f}",
                "validations"
            )

        with col2:
            avg_stations = df_evo['nb_stations'].mean()
            st.metric(
                "🚇 Stations en moyenne",
                f"{avg_stations:.0f}",
                "stations par période"
            )

        with col3:
            avg_variation = df_evo['variation_semaine_precedente'].mean()
            variation_color = "off" if abs(avg_variation) < 5 else ("inverse" if avg_variation < 0 else "off")
            st.metric(
                "📈 Variation moyenne",
                f"{avg_variation:+.1f}%",
                "vs semaine précédente",
                delta_color=variation_color
            )

        # Filtre par ligne
        ligne_filter = st.selectbox(
            "Sélectionnez une ligne :",
            ["Toutes"] + sorted(df_evo["ligne"].unique().tolist()),
            key="evo_ligne"
        )

        if ligne_filter != "Toutes":
            df_evo_filtered = df_evo[df_evo["ligne"] == ligne_filter]
        else:
            df_evo_filtered = df_evo

        # Graphique 1 : Fréquentation dans le temps
        fig1 = px.line(
            df_evo_filtered,
            x="date",
            y="frequentation_cumulee",
            title="📊 Évolution de la Fréquentation Cumulée",
            labels={"date": "Date/Période", "frequentation_cumulee": "Validations (total)"},
            markers=True,
            color_discrete_sequence=['#3498db']
        )
        fig1.update_traces(line=dict(width=3), marker=dict(size=8))
        st.plotly_chart(fig1, use_container_width=True)
        st.caption("💡 **Lecture** : Les pics = forte fréquentation, les creux = faible fréquentation. Cherchez les tendances (à la hausse ou à la baisse).")

        # Graphique 2 : Répartition par jour de semaine
        day_order = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        freq_by_day = df_evo_filtered.groupby("jour_semaine")["frequentation_cumulee"].mean().reset_index()
        
        # Trier selon l'ordre de la semaine (si les noms sont en français)
        freq_by_day['jour_semaine'] = pd.Categorical(
            freq_by_day['jour_semaine'],
            categories=day_order,
            ordered=True
        )
        freq_by_day = freq_by_day.sort_values("jour_semaine")

        fig2 = px.bar(
            freq_by_day,
            x="jour_semaine",
            y="frequentation_cumulee",
            title="📅 Fréquentation Moyenne par Jour de la Semaine",
            labels={"jour_semaine": "Jour", "frequentation_cumulee": "Validations (moyenne)"},
            color="frequentation_cumulee",
            color_continuous_scale="Viridis"
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("💡 **Lecture** : Les jours de semaine ont plus de passagers que les week-ends (télétravail variable).")

        # Tableau détaillé
        st.markdown("#### 📋 Détails par date et ligne")
        display_df = df_evo_filtered[["date", "ligne", "frequentation_cumulee", "nb_stations", "jour_semaine", "variation_semaine_precedente"]].copy()
        display_df.columns = ["Date/Période", "Ligne", "Fréquentation", "Stations", "Jour Semaine", "Variation (%)"]
        display_df["Fréquentation"] = display_df["Fréquentation"].astype(int)
        display_df["Variation (%)"] = display_df["Variation (%)"].round(1)
        
        st.dataframe(display_df.head(50), use_container_width=True)
        st.caption(f"Affichage : 50 premières lignes sur {len(display_df)} total")

# =====================================================
# DATAMART 4 : SATURATION ML
# =====================================================

elif datamart_choice == "saturation-ml":
    st.markdown("### 4️⃣ Données pour la Prédiction de Saturation (ML)")
    st.markdown("""
    Ce dataset est **préparé pour entraîner une Intelligence Artificielle** qui prédit les pics de saturation.
    
    **Qu'est-ce que "Saturation" ?**
    - **Définition** : Plus de 5 000 validations/heure = la ligne est surchargée
    - **Impact client** : Difficultés à monter en voiture, embarquement ralenti
    - **Impact opérationnel** : Besoin de renforts, personnel supplémentaire
    
    **Utilité de la prédiction ML :**
    - 🔮 Anticiper les pics **1-2 heures à l'avance**
    - 📍 Déployer les ressources **avant la surcharge** (pas après)
    - 💰 Économies : personnel optimisé, moins de crises
    """)

    df_ml = fetch_datamart("saturation-ml")

    if not df_ml.empty:
        # Constantes métier
        SATURATION_THRESHOLD = 5000
        
        # Statistiques saturation
        saturation_count = df_ml[df_ml["est_saturation"] == 1].shape[0]
        total_count = df_ml.shape[0]
        saturation_pct = (saturation_count / total_count * 100) if total_count > 0 else 0

        col1, col2, col3 = st.columns(3)

        with col1:
            if saturation_pct > 20:
                st.warning(f"⚠️ **{saturation_pct:.1f}%** des créneaux saturés")
                st.caption("Plus d'1 créneau sur 5 est critique")
            else:
                st.info(f"📊 **{saturation_pct:.1f}%** des créneaux saturés")
                st.caption("Minorité de créneaux en saturation")

        with col2:
            st.metric(
                "📊 Total créneaux",
                f"{total_count:,}",
                "(lignes × heures × jours)"
            )

        with col3:
            normal_count = total_count - saturation_count
            st.metric(
                "🟢 Créneaux normaux",
                f"{normal_count:,}",
                f"{(100 - saturation_pct):.1f}%"
            )

        st.markdown(f"""
        ### 🎯 Équilibre du Dataset
        - **{saturation_count:,}** créneaux saturés (label=1) 
        - **{normal_count:,}** créneaux normaux (label=0)
        - Ratio : {saturation_pct:.1f}% / {100-saturation_pct:.1f}%
        
        *Note : Un bon équilibre du dataset (pas trop d'un seul label) = modèle ML plus efficace*
        """)

        # Graphique 1 : Distribution saturation (pie chart)
        saturation_labels = {0: f"Normal (< {SATURATION_THRESHOLD:,})", 1: f"Saturé (> {SATURATION_THRESHOLD:,})"}
        saturation_counts = df_ml["est_saturation"].value_counts()

        fig1 = px.pie(
            names=[saturation_labels.get(k, k) for k in saturation_counts.index],
            values=saturation_counts.values,
            title=f"🥧 Distribution : Saturé vs Normal (Seuil = {SATURATION_THRESHOLD:,} validations/h)",
            color_discrete_map={"Normal (< 5000)": "#2ecc71", "Saturé (> 5000)": "#e74c3c"}
        )
        st.plotly_chart(fig1, use_container_width=True)
        st.caption("""
        💡 **Interprétation pour ML** : 
        - Plus la **part rouge est grande** → plus d'exemples de saturation dans les données d'entraînement
        - Une **balance 80/20 ou 70/30** est idéale pour l'apprentissage
        - Une **balance 99/1** serait problématique (le modèle apprendrait mal les cas rares)
        """)

        # Graphique 2 : Saturation par heure - PEAK HOURS
        hourly_sat = df_ml.groupby("heure")["est_saturation"].mean().reset_index()
        hourly_sat["saturation_pct"] = hourly_sat["est_saturation"] * 100

        fig2 = px.bar(
            hourly_sat,
            x="heure",
            y="saturation_pct",
            title="⏰ Heures de Pointe : Probabilité de Saturation par Heure du Jour",
            labels={"heure": "Heure du jour", "saturation_pct": "% de Risque Saturation"},
            color="saturation_pct",
            color_continuous_scale="Reds"
        )
        # Ajouter des annotations pour les pics
        fig2.add_vrect(x0=7, x1=9, fillcolor="red", opacity=0.1, annotation_text="🌅 Pointe matin", annotation_position="top")
        fig2.add_vrect(x0=17, x1=19, fillcolor="red", opacity=0.1, annotation_text="🌆 Pointe soir", annotation_position="top")
        st.plotly_chart(fig2, use_container_width=True)
        st.caption("""
        💡 **Ce que cela signifie** :
        - Les barres **rouges foncées** aux heures 7-9 et 17-19 = pics de saturation (attendus)
        - Les zones **grises** (creux) = opportunités pour maintenances
        - **Stratégie** : Renforcer personnel/rames **avant** ces heures (bleu clair → rouge foncé)
        """)

        # Graphique 3 : Saturation par ligne
        line_sat = df_ml.groupby("ligne")["est_saturation"].agg(['sum', 'count']).reset_index()
        line_sat["saturation_pct"] = (line_sat["sum"] / line_sat["count"] * 100).round(1)
        # Graphique 3 : Saturation par ligne - TOP 15
        line_sat = df_ml.groupby("ligne")["est_saturation"].agg(['sum', 'count']).reset_index()
        line_sat["saturation_pct"] = (line_sat["sum"] / line_sat["count"] * 100).round(1)
        line_sat = line_sat.sort_values("saturation_pct", ascending=False).head(15)

        fig3 = px.bar(
            line_sat,
            x="saturation_pct",
            y="ligne",
            title="� Top 15 Lignes Chroniquement Saturées (Priorité Opérationnelle)",
            labels={"ligne": "Ligne", "saturation_pct": "% de Créneaux Saturés"},
            color="saturation_pct",
            color_continuous_scale="Reds",
            orientation="h"
        )
        st.plotly_chart(fig3, use_container_width=True)
        st.caption("""
        💡 **Stratégie opérationnelle** :
        - Les lignes **en haut à droite** (rouges) = problématiques chroniques
        - Recommandation : Augmenter capacité (plus de rames) ou fréquence (plus de trains)
        - Ces lignes sont les **meilleures candidates** pour l'optimisation
        """)

        # Tableau détaillé avec description des FEATURES pour ML
        st.markdown("""
        #### 📋 Détails du Dataset (Structure pour ML)
        
        **Colonnes expliquées :**
        - **Ligne** : Identifiant de la ligne (la cible pour le déploiement de ressources)
        - **Heure** : Heure du jour (7 = créneau 7h-8h) → pattern temporel clé
        - **Jour-Type** : DIJFP/SAMEDI/DIMANCHE → comportement different selon le jour
        - **Validations** : Nombre de passagers → charge actuelle
        - **Ponctualité** : % de trains à l'heure → qualité de service (peut influencer saturation)
        - **Rang Fréq.** : Position relative vs autres lignes (1 = plus fréquentée)
        - **Saturé** : Label cible (🔴 Oui = dépasse 5 000 validations/h)
        """)
        
        display_cols = ["ligne", "heure", "jour_type", "nb_validations", 
                       "taux_ponctualite", "rang_frequentation", "est_saturation"]
        display_df = df_ml[display_cols].head(100).copy()
        display_df.columns = ["Ligne", "Heure", "Jour Type", "Validations", "Ponctualité (%)", "Rang Fréq.", "Saturé?"]
        display_df["Saturé?"] = display_df["Saturé?"].map({0: "🟢 Non", 1: "🔴 Oui"})
        display_df["Validations"] = display_df["Validations"].astype(int)
        display_df["Ponctualité (%)"] = display_df["Ponctualité (%)"].round(1)
        
        st.dataframe(display_df, use_container_width=True)
        st.caption(f"*Total dataset : {len(df_ml):,} créneaux spatio-temporels prêts pour ML*")


st.markdown("---")

# =====================================================
# GLOSSAIRE & AIDE
# =====================================================

with st.expander("📚 **Glossaire - Termes Importants**"):
    st.markdown("""
    ### Concepts Métier IDFM
    
    **Ligne**
    - Numéro ou lettre identifiant un trajet (ex: 1, 2, 4, A, B, C)
    - Les lignes souterraines = métro, les lignes aériennes/surface = RER
    - Chaque ligne relie plusieurs stations
    
    **Heure / Créneau horaire**
    - Tranche de 1 heure (ex: 7H = entre 7h00 et 7h59)
    - **Heures de pointe** : 7-9h (matin) et 17-19h (soir) = trafic intense
    - **Heures creuses** : 23h-6h (très peu de passagers) = maintenance possible
    
    **Jour-type**
    - **DIJFP** = "Jour Infra Jonction Ferie Paques" = jour ouvrable (lun-ven, hors fériés)
    - **SAMEDI** = samedi (trafic différent : loisirs, shopping)
    - **DIMANCHE** = dimanche (trafic réduit)
    
    **Validations**
    - Nombre de titres badgés (validation du ticket)
    - Proxy du nombre de passagers réels
    - 1 aller simple = 1 validation
    
    **Saturation**
    - **Définition** : > 5 000 validations/heure = capacité dépassée
    - **Impact** : Files, embarquement ralenti, insatisfaction clients
    - **Soluton** : Augmenter rames, fréquence, ou rediriger vers lignes parallèles
    
    **Ponctualité / Régularité**
    - **Ponctualité** : % de trains arrivant à l'heure (±5 min acceptable)
    - **Régularité** : Intervalle régulier entre trains (pas de "trous")
    - **Objectif IDFM** : > 95% de ponctualité
    """)

with st.expander("❓ **FAQ - Questions des Décideurs**"):
    st.markdown("""
    ### Décisions Basées sur les Données
    
    **Q : Comment utiliser ce dashboard pour faire de meilleures décisions ?**
    A : 
    1. **Identifiez les points chauds** (page Fréquentation) : Où saturation > 5 000 ?
    2. **Vérifiez l'impact qualité** (page Régularité) : Ces lignes sur-chargées perdent-elles en ponctualité ?
    3. **Prédisez les pics** (page Saturation ML) : Aux quelles heures ? Quels jours ?
    4. **Décidez des ressources** : Mettre plus de personnel aux heures 7-9 et 17-19 sur lignes saturées
    
    **Q : Quelle est la différence "Fréquentation > 5 000" vs "Ponctualité < 80%" ?**
    A :
    - **Fréquentation** = quantité (trop de monde)
    - **Ponctualité** = qualité (trains en retard)
    - Souvent corrélés : Quand c'est bondé, c'est plus lent
    
    **Q : Pourquoi le Rank/Rang va de 1 à ?**
    A : **Rang = Position dans le classement** :
    - Rang 1 = Ligne/station/heure **la plus problématique** (pire situation)
    - Rang 2 = Deuxième pire
    - Rang 10 = Dixième pire
    - Plus le rang est proche de 1 = plus c'est urgent
    
    **Q : Comment utiliser le dataset ML pour la prédiction ?**
    A :
    - Ce dataset enseigne au modèle : "à cette heure + ce jour + cette ligne = saturation?"
    - Une fois entraîné, le modèle peut anticiper 1-2h avant = temps pour agir
    - Exemple : Si le modèle prédit "Ligne 4 samedi 17h saturée" → mobiliser rames à 16h
    """)

with st.expander("ℹ️ **À Propos - Architecture du Dashboard**"):
    st.markdown("""
    ### Données & Source
    - **Réseau** : Métro + RER Île-de-France
    - **Couverture temporelle** : Données 2025 (heures de pointe + creux)
    - **Granularité** : Heure × Ligne × Jour-type
    - **Total** : 85 000+ créneaux spatio-temporels
    
    ### 4 Perspectives Complémentaires
    1. **Fréquentation** : Charge instantanée (quantité)
    2. **Régularité** : Fiabilité des services (ponctualité %)
    3. **Évolution** : Tendances dans le temps (jours, semaines)
    4. **Saturation ML** : Dataset brut pour prédictions IA
    
    ### Infrastructure Technique
    - 🟢 **API REST** : Données via architecture sécurisée (JWT)
    - 📊 **Dashboard** : Streamlit (Python) = visualisations interactives
    - 💾 **Stockage** : PostgreSQL ou CSV en cache mémoire
    - 🔐 **Accès** : Authentification admin/admin
    
    ### Contact & Améliorations
    - **Questions ?** Consultez l'équipe data IDFM
    - **Bug ?** Reportez au team de dev
    - **Idée** : Suggérez une nouvelle métrique !
    """)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.85em;'>
📊 <b>Tableau de Bord IDFM</b> — Données du Réseau Ferré 2025 — Source : Île-de-France Mobilités<br/>
<i>Dernière mise à jour : données chargées en cache</i><br/>
💡 <b>Conseil :</b> Utilisez les filtres et légendes pour explorer les données. Les couleurs (rouge/orange/vert) indiquent le degré de criticité.
</div>
""", unsafe_allow_html=True)
