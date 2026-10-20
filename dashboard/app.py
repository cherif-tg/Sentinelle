"""Tableau de bord Streamlit — carte de risque, seuils d'alerte et mode d'emploi.

Lit le Parquet produit par `sentinelle_lome.pipeline.gold` (variable `SL_RISQUE_PARQUET`) et son
`.meta.json` voisin. Les niveaux d'alerte sont **recalculés à la volée** à partir du ratio de coûts
choisi dans la barre latérale : le fichier source n'est jamais modifié.
"""
from __future__ import annotations

import json
import os

import altair as alt
import pandas as pd
import pydeck as pdk
import streamlit as st

from sentinelle_lome.serving.tableau_de_bord import (
    agregat_par_quartier,
    courbe_sensibilite,
    niveaux_recalcules,
    part_au_dessus,
    resume_global,
    seuil_depuis_couts,
)

CHEMIN = os.getenv("SL_RISQUE_PARQUET", "data/gold/risque_cellules.parquet")
COULEURS = {
    "rouge": [214, 40, 40, 180],
    "orange": [255, 152, 0, 180],
    "vert": [46, 160, 67, 150],
}
LIBELLES = {"rouge": "🟥 rouge", "orange": "🟧 orange", "vert": "🟩 vert"}


def espace_milliers(n: int) -> str:
    """Sépare les milliers par une espace, convention française (1 234 au lieu de 1,234)."""
    return f"{n:,}".replace(",", "\u202f")

st.set_page_config(page_title="Sentinelle Lomé — tableau de bord", page_icon="🌧️", layout="wide")


# --------------------------------------------------------------------------------------
# Chargement
# --------------------------------------------------------------------------------------
def charger_meta(chemin: str) -> dict:
    """Métadonnées voisines du Parquet, ou dictionnaire vide si absentes."""
    chemin_meta = f"{chemin}.meta.json"
    if not os.path.exists(chemin_meta):
        return {}
    try:
        with open(chemin_meta, encoding="utf-8") as fichier:
            return json.load(fichier)
    except (OSError, json.JSONDecodeError):
        return {}


if not os.path.exists(CHEMIN):
    st.title("Sentinelle Lomé — risque d'inondation")
    st.error(
        "Aucune donnée de risque trouvée. Le fichier attendu est :\n\n"
        f"`{CHEMIN}`\n\n"
        "Générez-le avec :\n\n"
        "```\npython -m sentinelle_lome.pipeline.gold\n```"
    )
    st.stop()

df = pd.read_parquet(CHEMIN)
meta = charger_meta(CHEMIN)
synthetique = meta.get("source") == "synthetique"


# --------------------------------------------------------------------------------------
# En-tête et mode d'emploi
# --------------------------------------------------------------------------------------
st.title("Sentinelle Lomé — risque d'inondation")
st.caption(
    "Prototype de cartographie du risque par cellule. Les niveaux d'alerte se recalculent en direct "
    "selon le ratio de coûts choisi dans la barre latérale."
)

if synthetique:
    st.warning(meta.get("avertissement", "Données de démonstration, non validées."), icon="⚠️")
else:
    st.info("Données de provenance déclarée : " + str(meta.get("source", "inconnue")), icon="ℹ️")

with st.expander("Comment utiliser ce tableau de bord", expanded=True):
    st.markdown(
        """
**En trois étapes**

1. **Réglez le ratio de coûts** dans la barre latérale : combien coûte une fausse alerte face à une
   inondation manquée. Le seuil rouge en découle automatiquement, et tous les chiffres de la page
   sont recalculés. Vous pouvez aussi forcer un seuil manuel pour explorer.
2. **Filtrez par quartier** si vous voulez isoler une zone ; « (tous) » conserve l'emprise entière.
3. **Parcourez les quatre onglets** : *Carte*, *Seuils*, *Quartiers*, *Données et méthode*.

**Définitions**

| Terme | Sens exact |
|---|---|
| `proba_inondation` | Probabilité qu'une cellule soit inondée, **dans le monde synthétique** de ce prototype |
| Seuil rouge | Probabilité au-delà de laquelle la cellule est en alerte maximale |
| Seuil orange | Moitié du seuil rouge (convention du prototype), pour une alerte intermédiaire |
| `niveau_alerte` du fichier | Niveau calculé à la génération ; **il peut différer** de celui affiché ici |

**À retenir :** aucun chiffre de cette page n'est une prévision sur Lomé. Les valeurs servent à
valider la chaîne technique et la façon de raisonner, pas à décider d'une évacuation.
"""
    )


# --------------------------------------------------------------------------------------
# Barre latérale
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.header("Paramètres")

    st.subheader("Coûts d'alerte")
    st.caption("Valeurs arbitraires de travail : l'ANPC n'a pas encore fourni de barème.")
    cout_fausse_alerte = st.number_input(
        "Coût d'une fausse alerte",
        min_value=0.1,
        max_value=1000.0,
        value=1.0,
        step=0.5,
        help="Coût relatif d'une alerte déclenchée sans inondation (évacuation inutile, crédibilité).",
    )
    cout_inondation_manquee = st.number_input(
        "Coût d'une inondation manquée",
        min_value=0.1,
        max_value=10000.0,
        value=10.0,
        step=1.0,
        help="Coût relatif d'une inondation non annoncée (dommages, victimes).",
    )
    seuil_calcule = seuil_depuis_couts(cout_fausse_alerte, cout_inondation_manquee)
    st.metric("Seuil rouge calculé", f"{seuil_calcule:.3f}")
    st.caption(
        f"Formule : {cout_fausse_alerte:g} / ({cout_fausse_alerte:g} + {cout_inondation_manquee:g}) "
        f"= {seuil_calcule:.3f}"
    )

    seuil_manuel = st.checkbox(
        "Forcer un seuil manuel",
        value=False,
        help="Ignore le calcul par les coûts, pour explorer la sensibilité du découpage.",
    )
    if seuil_manuel:
        seuil_rouge = st.slider(
            "Seuil rouge imposé",
            min_value=0.0,
            max_value=1.0,
            value=float(round(seuil_calcule, 2)),
            step=0.005,
            help="Toute cellule dont la probabilité atteint ce seuil est en rouge.",
        )
    else:
        seuil_rouge = seuil_calcule
    seuil_orange = seuil_rouge / 2.0
    st.caption(f"Seuil orange = moitié du seuil rouge = {seuil_orange:.3f}")

    st.divider()
    st.subheader("Filtre")
    quartiers_disponibles = sorted(df["quartier"].astype(str).unique().tolist())
    choix_quartier = st.selectbox(
        "Quartier",
        ["(tous)"] + quartiers_disponibles,
        help="Restreint les indicateurs, la carte et les graphiques au quartier choisi.",
    )

    st.divider()
    st.caption(
        "Emprise et quartiers : centroïdes approximatifs, en attendant des contours administratifs. "
        "Les cellules situées sur l'eau ne sont pas masquées."
    )


# --------------------------------------------------------------------------------------
# Vue filtrée et indicateurs
# --------------------------------------------------------------------------------------
vue = df if choix_quartier == "(tous)" else df[df["quartier"].astype(str) == choix_quartier].copy()
if vue.empty:
    st.warning("Aucune cellule pour ce filtre.")
    st.stop()

vue = vue.assign(
    niveau=niveaux_recalcules(vue["proba_inondation"], seuil_rouge, seuil_orange),
)
vue["couleur"] = vue["niveau"].map(COULEURS).tolist()

resume = resume_global(vue, seuil_rouge, seuil_orange)

col1, col2, col3, col4 = st.columns(4)
col1.metric(
    "Cellules au-dessus du seuil rouge",
    espace_milliers(resume["n_au_dessus"]),
    delta=f"{resume['part_au_dessus']:.1%} de la vue",
    delta_color="off",
    help="Nombre de cellules dont la probabilité atteint le seuil rouge, et leur part dans la vue.",
)
col2.metric(
    "Probabilité moyenne",
    f"{resume['proba_moyenne']:.3f}",
    help="Moyenne de proba_inondation sur la vue courante. Sensible aux valeurs extrêmes.",
)
col3.metric(
    "Probabilité maximale",
    f"{resume['proba_max']:.3f}",
    help="Cellule la plus exposée de la vue. Utile pour repérer un point chaud localisé.",
)
col4.metric(
    "Quartiers avec au moins une cellule rouge",
    f"{resume['n_quartiers_rouge']} / {resume['n_quartiers']}",
    help="Un quartier est compté dès qu'une seule de ses cellules atteint le seuil rouge.",
)

if choice_note := ("Vue filtrée sur **" + choix_quartier + "**." if choix_quartier != "(tous)" else None):
    st.caption(choice_note)

onglet_carte, onglet_seuils, onglet_quartiers, onglet_donnees = st.tabs(
    ["🗺️ Carte", "🎚️ Seuils d'alerte", "🏘️ Quartiers", "📄 Données et méthode"]
)


# --------------------------------------------------------------------------------------
# Onglet carte
# --------------------------------------------------------------------------------------
with onglet_carte:
    st.markdown(
        "Chaque point est une cellule. La couleur suit le **seuil courant** ; "
        "survolez un point pour lire son quartier et sa probabilité."
    )
    etiquette = f"Seuil rouge {seuil_rouge:.3f} · orange {seuil_orange:.3f}"
    st.caption(
        f"{LIBELLES['rouge']} ≥ {seuil_rouge:.3f} · {LIBELLES['orange']} ≥ {seuil_orange:.3f} · "
        f"{LIBELLES['vert']} < {seuil_orange:.3f} ({etiquette})"
    )

    couche = pdk.Layer(
        "ScatterplotLayer",
        data=vue,
        get_position="[lon, lat]",
        get_radius=90,
        radius_min_pixels=2,
        radius_max_pixels=8,
        get_fill_color="couleur",
        pickable=True,
        opacity=0.85,
    )
    st.pydeck_chart(
        pdk.Deck(
            map_style=None,
            initial_view_state=pdk.ViewState(
                latitude=float(vue["lat"].mean()),
                longitude=float(vue["lon"].mean()),
                zoom=10.5,
            ),
            layers=[couche],
            tooltip={
                "html": "<b>{quartier}</b><br/>probabilité : {proba_inondation}<br/>niveau : {niveau}",
                "style": {"backgroundColor": "#1f2937", "color": "white"},
            },
        ),
        height=480,
    )

    repartition = (
        vue["niveau"].value_counts().rename_axis("niveau").reset_index(name="n_cellules")
    )
    repartition["part"] = repartition["n_cellules"] / len(vue)
    st.dataframe(
        repartition.assign(niveau=repartition["niveau"].map(LIBELLES)),
        hide_index=True,
        column_config={
            "niveau": "Niveau",
            "n_cellules": st.column_config.NumberColumn("Cellules", format="%d"),
            "part": st.column_config.ProgressColumn("Part", format="percent", min_value=0, max_value=1),
        },
        width="stretch",
    )


# --------------------------------------------------------------------------------------
# Onglet seuils
# --------------------------------------------------------------------------------------
with onglet_seuils:
    st.markdown(
        "Ces deux graphiques répondent à la même question : **combien de cellules alerter, et à "
        "partir de quel seuil ?** Déplacez les coûts dans la barre latérale pour voir la réponse "
        "changer."
    )

    gauche, droite = st.columns(2)

    with gauche:
        st.subheader("Distribution des probabilités")
        st.caption("La ligne verticale est le seuil rouge courant. Tout ce qui est à droite alerte.")
        histogramme = (
            alt.Chart(vue)
            .mark_bar(color="#4C78A8")
            .encode(
                x=alt.X("proba_inondation:Q", bin=alt.Bin(maxbins=50), title="Probabilité d'inondation"),
                y=alt.Y("count():Q", title="Nombre de cellules"),
                tooltip=[alt.Tooltip("count():Q", title="Cellules")],
            )
            .properties(height=320)
            .interactive()
        )
        regle = (
            alt.Chart(pd.DataFrame({"seuil": [seuil_rouge]}))
            .mark_rule(color="#D62828", strokeDash=[6, 4], size=2)
            .encode(x="seuil:Q")
        )
        st.altair_chart(histogramme + regle, width="stretch")

    with droite:
        st.subheader("Sensibilité au seuil")
        st.caption(
            "Part de cellules en alerte selon le seuil choisi. Le point rouge rappelle la position "
            "actuelle ; une courbe plate signifie que le réglage ne change presque rien."
        )
        courbe = courbe_sensibilite(vue["proba_inondation"], n_points=101)
        ligne = (
            alt.Chart(courbe)
            .mark_line(color="#4C78A8", strokeWidth=2)
            .encode(
                x=alt.X("seuil:Q", title="Seuil de probabilité", scale=alt.Scale(zero=True, domain=[0, 1])),
                y=alt.Y(
                    "part_au_dessus:Q",
                    title="Part des cellules en alerte",
                    axis=alt.Axis(format="%"),
                    scale=alt.Scale(zero=True, domain=[0, 1]),
                ),
                tooltip=[
                    alt.Tooltip("seuil:Q", title="Seuil", format=".3f"),
                    alt.Tooltip("part_au_dessus:Q", title="Part", format=".1%"),
                ],
            )
            .properties(height=320)
            .interactive()
        )
        point = (
            alt.Chart(pd.DataFrame({"seuil": [seuil_rouge], "part": [part_au_dessus(vue["proba_inondation"], seuil_rouge)]}))
            .mark_circle(size=140, color="#D62828")
            .encode(x="seuil:Q", y="part:Q", tooltip=["seuil:Q", "part:Q"])
        )
        st.altair_chart(ligne + point, width="stretch")

    st.divider()
    st.markdown(
        f"""
**Lecture immédiate.** Avec un ratio de coûts de {cout_fausse_alerte:g} contre
{cout_inondation_manquee:g}, le seuil rouge vaut **{seuil_rouge:.3f}** : dans la vue courante,
**{espace_milliers(resume['n_au_dessus'])} cellules** sur {espace_milliers(resume['n_cellules'])} alertent,
soit **{resume['part_au_dessus']:.1%}**.

Le ratio traduit une politique, pas une mesure physique : alerter peu coûte des vies, alerter trop
coûte de la crédibilité. Tant que l'ANPC n'a pas arbitré, ces valeurs restent des hypothèses de
travail.
"""
    )


# --------------------------------------------------------------------------------------
# Onglet quartiers
# --------------------------------------------------------------------------------------
with onglet_quartiers:
    agrege = agregat_par_quartier(vue, seuil_rouge, seuil_orange)
    st.markdown(
        "Part des cellules en rouge par quartier, pour le seuil courant. Un quartier à 100 % signifie "
        "que **toutes** ses cellules atteignent le seuil, pas que le quartier est entièrement inondé."
    )

    barres = (
        alt.Chart(agrege)
        .mark_bar()
        .encode(
            x=alt.X("part_rouge:Q", title="Part des cellules en rouge", axis=alt.Axis(format="%")),
            y=alt.Y("quartier:N", sort="-x", title=None),
            color=alt.Color("part_rouge:Q", scale=alt.Scale(scheme="orangered"), legend=None),
            tooltip=[
                alt.Tooltip("quartier:N", title="Quartier"),
                alt.Tooltip("n_cellules:Q", title="Cellules", format=","),
                alt.Tooltip("proba_moyenne:Q", title="Proba moyenne", format=".3f"),
                alt.Tooltip("proba_max:Q", title="Proba max", format=".3f"),
                alt.Tooltip("part_rouge:Q", title="Part rouge", format=".1%"),
            ],
        )
        .properties(height=max(240, 32 * len(agrege)))
        .interactive()
    )
    st.altair_chart(barres, width="stretch")

    tableau = agrege.assign(
        part_rouge=(agrege["part_rouge"] * 100).round(1),
        part_alerte=(agrege["part_alerte"] * 100).round(1),
        proba_moyenne=agrege["proba_moyenne"].round(3),
        proba_max=agrege["proba_max"].round(3),
    )
    tableau.columns = [
        "Quartier",
        "Cellules",
        "Proba moyenne",
        "Proba max",
        "Part rouge (%)",
        "Part en alerte (%)",
    ]
    st.dataframe(tableau, hide_index=True, width="stretch")


# --------------------------------------------------------------------------------------
# Onglet données et méthode
# --------------------------------------------------------------------------------------
with onglet_donnees:
    gauche, droite = st.columns([2, 1])

    with gauche:
        st.subheader("Cellules (aperçu)")
        st.caption("Les 500 premières lignes de la vue courante, niveaux recalculés inclus.")
        st.dataframe(vue.head(500), hide_index=True, width="stretch")
        st.download_button(
            "Télécharger la vue en CSV",
            data=vue.to_csv(index=False).encode("utf-8"),
            file_name="sentinelle_vue.csv",
            mime="text/csv",
            help="Exporte exactement ce qui est affiché, filtres et seuils compris.",
        )

    with droite:
        st.subheader("Provenance")
        if meta:
            st.json(
                {
                    "source": meta.get("source"),
                    "date_generation": meta.get("date_generation"),
                    "scenario": meta.get("scenario"),
                    "resolution_m": meta.get("resolution_m"),
                    "n_cellules": meta.get("n_cellules"),
                    "seuils_alerte": meta.get("seuils_alerte"),
                    "calibration": meta.get("calibration", {}).get("methode"),
                }
            )
        else:
            st.info("Aucun fichier `.meta.json` à côté du Parquet.")

        st.subheader("Colonnes du fichier")
        st.markdown(
            """
| Colonne | Contenu |
|---|---|
| `cellule_id` | Identifiant de la cellule dans la grille |
| `quartier` | Quartier rattaché (centroïde le plus proche, provisoire) |
| `lon`, `lat` | Centre de la cellule, en degrés |
| `proba_inondation` | Probabilité calibrée dans le monde synthétique |
| `niveau_alerte` | Niveau calculé à la génération du fichier |
"""
        )

    st.divider()
    st.subheader("Limites à ne pas masquer")
    st.markdown(
        """
- **Données synthétiques** : aucune valeur ne décrit le risque réel à Lomé.
- **Ratio de coûts arbitraire** : 1 contre 10 par défaut, en attente d'un barème ANPC.
- **Quartiers approximatifs** : centroïdes et non contours administratifs ; une cellule limitrophe
  peut changer de quartier.
- **Pas de masque eau** : des cellules situées sur la lagune ou l'océan sont comptées.
- **Pluie uniforme** : le modèle de déclenchement ne produit aucune variation spatiale.
"""
    )

st.divider()
st.caption(
    f"Source : {meta.get('source', 'inconnue')} · généré le {meta.get('date_generation', 'inconnu')} · "
    f"{espace_milliers(len(df))} cellules au total · seuil rouge courant {seuil_rouge:.3f}"
)
