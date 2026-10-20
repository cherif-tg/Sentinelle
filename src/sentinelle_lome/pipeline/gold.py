"""Production du fichier « gold » de risque par cellule — DONNÉES SYNTHÉTIQUES.

Ce module est le producteur manquant entre les modèles (A : susceptibilité, B : déclenchement)
et la couche de service (`serving/api.py`, `dashboard/app.py`). Il écrit un Parquet à six
colonnes (cellule_id, quartier, lon, lat, proba_inondation, niveau_alerte) et, à côté, un
fichier `<sortie>.meta.json` qui documente la provenance synthétique des valeurs.

Usage :
    python -m sentinelle_lome.pipeline.gold
    python -m sentinelle_lome.pipeline.gold --sortie data/gold/risque_cellules.parquet \
        --resolution-m 250 --graine 0

AVERTISSEMENT : aucune donnée réelle n'est utilisée. Les probabilités produites ne décrivent
pas le risque d'inondation réel à Lomé et ne doivent pas être diffusées comme telles.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from sentinelle_lome.config import charger_config
from sentinelle_lome.contours import (
    affecter_par_polygones,
    charger_contour,
    charger_quartiers,
    masque_points,
    surface_km2,
)
from sentinelle_lome.models.declenchement import entrainer_declenchement, niveau_alerte, seuil_decision
from sentinelle_lome.models.susceptibilite import VARIABLES_PAR_DEFAUT, donnees_synthetiques, entrainer

COLONNES = ["cellule_id", "quartier", "lon", "lat", "proba_inondation", "niveau_alerte"]

# Quartiers du Grand Lomé et centroïdes APPROXIMATIFS (latitude, longitude, degrés décimaux).
# Valeurs arrondies « à la main » pour le prototype : ce ne sont pas des centroïdes calculés
# sur des contours administratifs.
QUARTIERS: dict[str, tuple[float, float]] = {
    "Adidogomé": (6.175, 1.180),
    "Bè": (6.128, 1.248),
    "Tokoin": (6.158, 1.215),
    "Agoè-Nyivé": (6.215, 1.175),
    "Kodjoviakopé": (6.122, 1.208),
    "Baguida": (6.105, 1.315),
    "Hédzranawoé": (6.163, 1.250),
    "Nyékonakpoè": (6.128, 1.220),
}

VARIABLES_PLUIE = ["pluie_cumul_1j", "pluie_cumul_3j", "pluie_cumul_7j"]

# Scénarios pluvieux SYNTHÉTIQUES (cumuls en mm sur 1, 3 et 7 jours), uniformes sur l'emprise.
# « moderee » ≈ fort épisode de saison des pluies ; « extreme » ≈ épisode exceptionnel.
# Le choix du scénario change la part de cellules au-dessus du seuil d'alerte : ce sont des
# fixtures de démonstration, pas des prévisions.
SCENARIOS: dict[str, dict[str, float]] = {
    "moderee": {"pluie_cumul_1j": 60.0, "pluie_cumul_3j": 110.0, "pluie_cumul_7j": 160.0},
    "extreme": {"pluie_cumul_1j": 120.0, "pluie_cumul_3j": 180.0, "pluie_cumul_7j": 260.0},
}
SCENARIO_DEFAUT = "moderee"


def scenario_pluie(nom: str) -> dict[str, float]:
    """Cumuls du scénario demandé ; `ValueError` explicite si le nom est inconnu."""
    if nom not in SCENARIOS:
        raise ValueError(f"scénario inconnu : {nom!r} (connus : {sorted(SCENARIOS)})")
    return SCENARIOS[nom]

AVERTISSEMENT = (
    "Valeurs SYNTHÉTIQUES produites par un prototype : elles ne décrivent pas le risque "
    "d'inondation réel à Lomé et ne doivent pas servir à une décision opérationnelle ni à une "
    "diffusion au public."
)

# Jeu de calibration : taille et décalage de graine (disjoint des tirages d'entraînement).
N_CALIBRATION = 10_000
DECALAGE_GRAINE_CALIBRATION = 1000

# Terme de pluie de la vérité terrain : +1,5 de logit par tranche de 100 mm au-dessus de 100 mm.
PLUIE_REF_MM = 100.0
EFFET_PLUIE_PAR_TRANCHE = 1.5

M_PAR_DEGRE_LAT = 111_320.0


def _pas_degres(resolution_m: float, lat_moyenne: float) -> tuple[float, float]:
    """Pas de grille (lat, lon) en degrés pour une résolution métrique donnée."""
    pas_lat = resolution_m / M_PAR_DEGRE_LAT
    pas_lon = resolution_m / (M_PAR_DEGRE_LAT * np.cos(np.radians(lat_moyenne)))
    return pas_lat, pas_lon


def grille_emprise(emprise: list[float], resolution_m: float, graine: int, contour=None) -> pd.DataFrame:
    """Grille régulière centrée sur les mailles de `emprise` = [lon_min, lat_min, lon_max, lat_max].

    Le pas est converti en degrés (approximation sphérique, sans pyproj) et le nombre de mailles
    est arrondi vers le bas pour ne pas sortir de l'emprise. Si un `contour` est fourni, seules
    les cellules dont le centre est à l'intérieur du polygone sont conservées, et les identifiants
    sont renumérotés dans l'ordre. Les variables terrain sont tirées de façon déterministe :
    même graine + même résolution ⇒ même grille.
    """
    if resolution_m <= 0:
        raise ValueError("resolution_m doit être > 0")
    lon_min, lat_min, lon_max, lat_max = (float(v) for v in emprise)
    pas_lat, pas_lon = _pas_degres(resolution_m, (lat_min + lat_max) / 2)
    n_lat = max(1, int(np.floor((lat_max - lat_min) / pas_lat)))
    n_lon = max(1, int(np.floor((lon_max - lon_min) / pas_lon)))
    lats = lat_min + pas_lat * (np.arange(n_lat) + 0.5)
    lons = lon_min + pas_lon * (np.arange(n_lon) + 0.5)
    grille_lon, grille_lat = np.meshgrid(lons, lats)
    df = pd.DataFrame({"lon": grille_lon.ravel(), "lat": grille_lat.ravel()})
    if contour is not None:
        df = df.loc[masque_points(contour, df["lon"], df["lat"])].reset_index(drop=True)
        if df.empty:
            raise ValueError("aucune cellule dans le contour : vérifier l'emprise et le GeoJSON")
    df.insert(0, "cellule_id", np.arange(len(df), dtype=int))
    return pd.concat([df, variables_terrain(len(df), graine)], axis=1)


def variables_terrain(n: int, graine: int) -> pd.DataFrame:
    """Variables terrain synthétiques, mêmes lois que `models.susceptibilite.donnees_synthetiques`.

    Les tirages sont indépendants d'une cellule à l'autre : aucune autocorrélation spatiale
    n'est simulée. L'altitude est bornée à 0 pour éviter des valeurs non physiques.
    """
    rng = np.random.default_rng(graine)
    return pd.DataFrame(
        {
            "hand_m": rng.gamma(2.0, 3.0, n),
            "pente_deg": rng.gamma(1.5, 1.0, n),
            "altitude_m": np.clip(rng.normal(15.0, 6.0, n), 0.0, None),
            "dist_drain_m": rng.gamma(2.0, 200.0, n),
            "densite_bati": rng.uniform(0.0, 1.0, n),
        }
    )


def donnees_pluie_synthetiques(n: int, graine: int) -> pd.DataFrame:
    """Cumuls de pluie synthétiques cohérents (1 j ≤ 3 j ≤ 7 j) et cible d'inondation.

    La cible suit une loi logistique des cumuls, ce qui rend la contrainte de monotonie du
    modèle B pertinente. Aucune valeur observée : simple support d'entraînement.
    """
    rng = np.random.default_rng(graine + 1)
    cumul_1j = rng.gamma(2.0, 25.0, n)
    cumul_3j = cumul_1j + rng.gamma(2.0, 30.0, n)
    cumul_7j = cumul_3j + rng.gamma(2.0, 45.0, n)
    df = pd.DataFrame({"pluie_cumul_1j": cumul_1j, "pluie_cumul_3j": cumul_3j, "pluie_cumul_7j": cumul_7j})
    logit = -8.0 + 0.04 * cumul_1j + 0.02 * cumul_3j + 0.008 * cumul_7j
    df["inonde"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df


def probabilite_susceptibilite(grille: pd.DataFrame, graine: int, n_entrainement: int = 6000) -> np.ndarray:
    """Modèle A : entraîné sur un échantillon synthétique, appliqué à chaque cellule de la grille."""
    echantillon = donnees_synthetiques(n_entrainement, graine)
    modele = entrainer(echantillon, VARIABLES_PAR_DEFAUT, "inonde", graine)
    return modele.predict_proba(grille[VARIABLES_PAR_DEFAUT].to_numpy())[:, 1]


def probabilite_declenchement(grille: pd.DataFrame, graine: int, n_entrainement: int = 6000) -> np.ndarray:
    """Modèle B : entraîné sur des pluies synthétiques, appliqué au scénario pluvieux de la grille."""
    echantillon = donnees_pluie_synthetiques(n_entrainement, graine)
    modele = entrainer_declenchement(echantillon, VARIABLES_PLUIE, "inonde", graine)
    return modele.predict_proba(grille[VARIABLES_PLUIE].to_numpy())[:, 1]


def combiner_proba(susceptibilite: np.ndarray, declenchement: np.ndarray) -> np.ndarray:
    """INDICE de risque avant calibration, borné dans [0, 1] : susceptibilité (A) × déclenchement (B).

    Les deux modèles sont entraînés séparément, sur des cibles synthétiques distinctes et sans
    apprentissage conjoint ; leur produit suppose l'indépendance conditionnelle de la
    susceptibilité et du déclenchement, ce qui est faux physiquement. Le résultat n'est donc pas
    une probabilité : c'est un simple indice d'ordonnancement, que `ajuster_calibration` transforme
    ensuite en probabilité calibrée sur la vérité terrain synthétique.
    """
    return np.clip(np.asarray(susceptibilite) * np.asarray(declenchement), 0.0, 1.0)


def logit_verite(terrain: pd.DataFrame, pluie_cumul_3j: np.ndarray) -> np.ndarray:
    """Logit de la vérité terrain SYNTHÉTIQUE et JOINTE (terrain + pluie).

    Le terme terrain reprend à l'identique le logit de
    `models.susceptibilite.donnees_synthetiques` : mêmes coefficients et mêmes variables actives
    (hand_m, pente_deg, dist_drain_m, densite_bati ; altitude_m n'y figure pas). Le terme de pluie
    ajoute +1,5 par tranche de 100 mm de cumul 3 j au-dessus de 100 mm.

    C'est cette vérité terrain qui définit ce que « probabilité » veut dire dans le monde
    synthétique : une probabilité calibrée n'a de sens que relativement à elle, et ne dit rien du
    risque d'inondation réel à Lomé.
    """
    return (
        1.5
        - 0.5 * terrain["hand_m"].to_numpy()
        - 0.4 * terrain["pente_deg"].to_numpy()
        - 0.002 * terrain["dist_drain_m"].to_numpy()
        + 1.0 * terrain["densite_bati"].to_numpy()
        + EFFET_PLUIE_PAR_TRANCHE * (np.asarray(pluie_cumul_3j, dtype=float) - PLUIE_REF_MM) / 100.0
    )


def jeu_calibration(
    n: int = N_CALIBRATION,
    graine: int = 0,
    n_entrainement: int = 6000,
    scenario: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """(score A×B, étiquettes) d'un jeu de calibration synthétique disjoint de l'entraînement.

    Les variables terrain suivent les mêmes lois que `variables_terrain`, avec une graine décalée
    pour ne pas retomber sur les tirages d'entraînement ; le scénario pluvieux est celui appliqué
    à la grille (par défaut `SCENARIO_DEFAUT`). Les étiquettes sont tirées au sort (binomial) selon
    `logit_verite`, donc selon la vérité terrain jointe et non selon le score : c'est ce qui rend
    la calibration informative.
    """
    terrain = variables_terrain(n, graine + DECALAGE_GRAINE_CALIBRATION)
    df = terrain.assign(**(scenario if scenario is not None else SCENARIOS[SCENARIO_DEFAUT]))
    probabilite_vraie = 1.0 / (1.0 + np.exp(-logit_verite(df, df["pluie_cumul_3j"].to_numpy())))
    rng = np.random.default_rng(graine + DECALAGE_GRAINE_CALIBRATION + 1)
    etiquettes = (rng.uniform(size=n) < probabilite_vraie).astype(int)
    score = combiner_proba(
        probabilite_susceptibilite(df, graine, n_entrainement),
        probabilite_declenchement(df, graine, n_entrainement),
    )
    return score, etiquettes


def ajuster_calibration(score: np.ndarray, etiquettes: np.ndarray) -> IsotonicRegression:
    """Régression isotone score → probabilité, bornée dans [0, 1], valeurs hors bornes écrêtées."""
    return IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(
        np.asarray(score, dtype=float), np.asarray(etiquettes, dtype=int)
    )


def affecter_quartiers(lon: np.ndarray, lat: np.ndarray, quartiers=None) -> np.ndarray:
    """Quartier de chaque cellule : polygones OSM si fournis, sinon centroïdes provisoires.

    Avec des polygones, une cellule hors de toute zone cartographiée est marquée « non
    cartographié » plutôt que rattachée de force : l'absence de donnée est une information.
    Sans polygones (fichier absent), on retombe sur les centroïdes APPROXIMATIFS décrits plus bas.
    """
    if quartiers:
        return affecter_par_polygones(quartiers, lon, lat)
    noms = list(QUARTIERS)
    centres = np.array([QUARTIERS[n] for n in noms], dtype=float)  # lignes : (lat, lon)
    facteur_lon = np.cos(np.radians(np.mean(lat)))
    distances = (lat[:, None] - centres[None, :, 0]) ** 2 + ((lon[:, None] - centres[None, :, 1]) * facteur_lon) ** 2
    return np.array(noms, dtype=object)[np.argmin(distances, axis=1)]


def seuils_alerte(config: dict) -> tuple[float, float]:
    """(seuil_orange, seuil_rouge) : seuil rouge = seuil de coût du YAML, orange = sa moitié."""
    modelisation = config["modelisation"]
    rouge = seuil_decision(modelisation["cout_fausse_alerte"], modelisation["cout_inondation_manquee"])
    return rouge / 2.0, rouge


def generer_gold(
    sortie: str | Path = "data/gold/risque_cellules.parquet",
    resolution_m: float = 250.0,
    graine: int = 0,
    config: dict | None = None,
    n_entrainement: int = 6000,
    n_calibration: int = N_CALIBRATION,
    scenario: str = SCENARIO_DEFAUT,
    contour: str | None = None,
) -> pd.DataFrame:
    """Génère le Parquet de risque et son `<sortie>.meta.json`, puis retourne le DataFrame écrit.

    Toutes les valeurs sont synthétiques. Le fichier respecte le contrat de `serving/api.py` :
    six colonnes, `proba_inondation` dans [0, 1], `niveau_alerte` dans {vert, orange, rouge}.
    `proba_inondation` est une probabilité calibrée par régression isotone (score A×B → issue
    observée sur un jeu synthétique disjoint), ce qui rend l'application de `seuil_decision`
    légitime — dans les limites du monde synthétique, pas du risque réel.

    Si `contour` désigne un GeoJSON existant, la grille est restreinte à ce territoire ; sinon
    l'emprise rectangulaire de la configuration est utilisée telle quelle (et le signalement
    apparaît dans les métadonnées sous `contour.masque`).
    """
    cfg = config if config is not None else charger_config()
    pluie = scenario_pluie(scenario)
    geometry = charger_contour(contour if contour is not None else cfg["zone_etude"].get("contour"))
    liste_quartiers = charger_quartiers(cfg["zone_etude"].get("quartiers"))
    grille = grille_emprise(cfg["zone_etude"]["emprise"], resolution_m, graine, geometry)
    grille = grille.assign(**pluie)

    score = combiner_proba(
        probabilite_susceptibilite(grille, graine, n_entrainement),
        probabilite_declenchement(grille, graine, n_entrainement),
    )
    score_calibration, etiquettes_calibration = jeu_calibration(n_calibration, graine, n_entrainement, pluie)
    proba = np.clip(ajuster_calibration(score_calibration, etiquettes_calibration).predict(score), 0.0, 1.0)
    taux_positifs = float(np.mean(etiquettes_calibration))
    seuil_orange, seuil_rouge = seuils_alerte(cfg)

    quartiers = affecter_quartiers(grille["lon"].to_numpy(), grille["lat"].to_numpy(), liste_quartiers)

    df = pd.DataFrame(
        {
            "cellule_id": grille["cellule_id"].to_numpy(),
            "quartier": quartiers,
            "lon": grille["lon"].to_numpy(),
            "lat": grille["lat"].to_numpy(),
            "proba_inondation": proba,
            "niveau_alerte": niveau_alerte(proba, seuil_orange, seuil_rouge),
        }
    )[COLONNES]

    chemin = Path(sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(chemin, index=False)

    meta = {
        "source": "synthetique",
        "graine": graine,
        "resolution_m": resolution_m,
        "n_cellules": len(df),
        "date_generation": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "avertissement": AVERTISSEMENT,
        "scenario": scenario,
        "scenario_pluie_mm": pluie,
        "seuils_alerte": {"orange": seuil_orange, "rouge": seuil_rouge},
        "calibration": {
            "methode": "regression isotone (sklearn.isotonic.IsotonicRegression, out_of_bounds=clip, y_min=0, y_max=1)",
            "n_calibration": int(n_calibration),
            "taux_positifs_observe": taux_positifs,
            "portee": (
                "probabilites calibrees relativement a la verite terrain synthetique "
                "(logit terrain de donnees_synthetiques + terme de pluie) ; aucune validite "
                "sur le risque d'inondation reel a Lome"
            ),
        },
        "affectation_quartiers": (
            "polygones OpenStreetMap (admin_level=10)"
            if liste_quartiers
            else "centroides approximatifs, plus proche voisin (provisoire)"
        ),
        "quartiers": {
            "fichier": cfg["zone_etude"].get("quartiers"),
            "n_polygones": len(liste_quartiers),
            "part_non_cartographiee": round(float(np.mean(quartiers == "non cartographié")), 4),
            "attribution": "© OpenStreetMap contributors (ODbL 1.0)" if liste_quartiers else None,
        },
        "contour": {
            "fichier": contour if contour is not None else cfg["zone_etude"].get("contour"),
            "masque": geometry is not None,
            "superficie_km2": round(surface_km2(geometry), 1) if geometry is not None else None,
        },
    }
    Path(f"{chemin}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return df


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sortie", default="data/gold/risque_cellules.parquet", help="chemin du Parquet de sortie")
    p.add_argument("--resolution-m", type=float, default=250.0, help="pas de la grille en mètres (défaut : 250)")
    p.add_argument("--graine", type=int, default=0, help="graine aléatoire (défaut : 0)")
    p.add_argument("--contour", default=None, help="GeoJSON de contour (défaut : celui de la configuration)")
    p.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default=SCENARIO_DEFAUT,
        help=f"scénario pluvieux synthétique (défaut : {SCENARIO_DEFAUT})",
    )
    a = p.parse_args(argv)
    if a.resolution_m <= 0:
        p.error("--resolution-m doit être > 0")
    df = generer_gold(a.sortie, a.resolution_m, a.graine, scenario=a.scenario, contour=a.contour)
    print(f"[gold] {len(df)} cellules écrites dans {a.sortie} (+ {a.sortie}.meta.json)")
    print(f"[gold] proba_inondation moyenne : {df['proba_inondation'].mean():.4f}")
    print(f"[gold] niveaux d'alerte : {df['niveau_alerte'].value_counts().to_dict()}")
    print("[gold] DONNÉES SYNTHÉTIQUES — ne décrivent pas le risque réel à Lomé.")


if __name__ == "__main__":
    main()
