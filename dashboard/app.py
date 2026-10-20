"""Dashboard Streamlit — carte de risque et synthèse par quartier.

Lit le Parquet produit par `sentinelle_lome.pipeline.gold` et affiche, s'il existe, le
bandeau d'avertissement de son `.meta.json`.
"""
import json
import os

import pandas as pd
import pydeck as pdk
import streamlit as st

st.set_page_config(page_title="Sentinelle Lomé", layout="wide")
st.title("Sentinelle Lomé — risque d'inondation")

chemin = os.getenv("SL_RISQUE_PARQUET", "data/gold/risque_cellules.parquet")
if not os.path.exists(chemin):
    st.warning("Aucune donnée de risque trouvée. Exécutez d'abord le lot de calcul.")
    st.stop()

df = pd.read_parquet(chemin)

# Bandeau de provenance : les niveaux affichés dépendent d'un ratio de coûts encore provisoire.
_meta_path = f"{chemin}.meta.json"
if os.path.exists(_meta_path):
    with open(_meta_path, encoding="utf-8") as _f:
        _meta = json.load(_f)
    st.warning(_meta.get("avertissement", "Données de démonstration, non validées."))
    _seuils = _meta.get("seuils_alerte") or {}
    if _seuils:
        st.caption(
            "Niveaux d'alerte dérivés d'un ratio de coûts PROVISOIRE "
            f"(seuil rouge = {_seuils['rouge']:.3f}, orange = {_seuils['orange']:.3f}) : "
            "une large part de rouge est attendue et ne constitue pas une prévision."
        )

seuil = st.sidebar.slider("Seuil de probabilité", 0.0, 1.0, 0.5, 0.05)
quartiers = ["(tous)"] + sorted(df["quartier"].unique().tolist())
choix = st.sidebar.selectbox("Quartier", quartiers)
vue = df if choix == "(tous)" else df[df["quartier"] == choix]
vue = vue.assign(au_dessus=vue["proba_inondation"] >= seuil)

c1, c2 = st.columns(2)
c1.metric("Cellules au-dessus du seuil", int(vue["au_dessus"].sum()))
c2.metric("Probabilité moyenne", f"{vue['proba_inondation'].mean():.2f}")

st.pydeck_chart(
    pdk.Deck(
        map_style=None,
        initial_view_state=pdk.ViewState(latitude=float(vue["lat"].mean()), longitude=float(vue["lon"].mean()), zoom=11),
        layers=[
            pdk.Layer(
                "ScatterplotLayer",
                data=vue,
                get_position="[lon, lat]",
                get_radius=30,
                get_fill_color="[255 * proba_inondation, 80, 255 * (1 - proba_inondation), 160]",
                pickable=True,
            )
        ],
    )
)
st.caption("Prototype : les probabilités sont indicatives et doivent être validées par l'ANPC avant toute diffusion.")
