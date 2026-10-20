"""Calculs du tableau de bord : seuils d'alerte, sensibilité, agrégation par quartier.

Ces fonctions sont pures et séparées de l'interface Streamlit : elles se testent sans navigateur.
Elles servent à recalculer les niveaux d'alerte **à la volée** quand l'utilisateur change le ratio
de coûts, sans jamais réécrire le fichier « gold ».
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from sentinelle_lome.models.declenchement import niveau_alerte, seuil_decision

NIVEAUX = ("vert", "orange", "rouge")


def seuil_depuis_couts(cout_fausse_alerte: float, cout_inondation_manquee: float) -> float:
    """Seuil de probabilité au-delà duquel on alerte, pour un couple de coûts donné.

    Rappel de la règle : on alerte si p·c_manquée > (1−p)·c_fausse_alerte, soit
    p > c_fausse_alerte / (c_fausse_alerte + c_manquée). Le résultat n'a de sens que sur des
    probabilités calibrées ; dans ce prototype, la calibration est relative au monde synthétique.
    """
    return seuil_decision(cout_fausse_alerte, cout_inondation_manquee)


def part_au_dessus(proba, seuil: float) -> float:
    """Part des cellules dont la probabilité atteint le seuil (comparaison `>=`, seuil inclus)."""
    if not 0.0 <= seuil <= 1.0:
        raise ValueError("le seuil doit être dans [0, 1]")
    valeurs = np.asarray(proba, dtype=float)
    if valeurs.size == 0:
        return 0.0
    return float(np.mean(valeurs >= seuil))


def courbe_sensibilite(proba, n_points: int = 101) -> pd.DataFrame:
    """Part de cellules au-dessus du seuil, pour des seuils réguliers de 0 à 1.

    Sert à montrer la sensibilité du nombre d'alertes au réglage des coûts : la courbe décroît
    forcément, et sa pente dit si le territoire est proche ou loin du seuil.
    """
    if n_points < 2:
        raise ValueError("n_points doit être >= 2")
    valeurs = np.asarray(proba, dtype=float)
    seuils = np.linspace(0.0, 1.0, n_points)
    return pd.DataFrame(
        {"seuil": seuils, "part_au_dessus": [part_au_dessus(valeurs, s) for s in seuils]}
    )


def agregat_par_quartier(df: pd.DataFrame, seuil_rouge: float, seuil_orange: float) -> pd.DataFrame:
    """Statistiques par quartier pour un couple de seuils donné, triées par part de rouge.

    La colonne `niveau_alerte` du fichier « gold » correspond aux seuils en vigueur lors de sa
    génération ; ici les niveaux sont recalculés, donc cohérents avec les coûts affichés.
    """
    for colonne in ("quartier", "proba_inondation"):
        if colonne not in df.columns:
            raise KeyError(f"colonne absente du fichier de risque : {colonne!r}")
    if not 0.0 <= seuil_orange <= seuil_rouge <= 1.0:
        raise ValueError("exiger 0 <= seuil_orange <= seuil_rouge <= 1")

    tmp = df.assign(
        _rouge=df["proba_inondation"] >= seuil_rouge,
        _alerte=df["proba_inondation"] >= seuil_orange,
    )
    agrege = (
        tmp.groupby("quartier")
        .agg(
            n_cellules=("proba_inondation", "size"),
            proba_moyenne=("proba_inondation", "mean"),
            proba_max=("proba_inondation", "max"),
            part_rouge=("_rouge", "mean"),
            part_alerte=("_alerte", "mean"),
        )
        .reset_index()
    )
    return agrege.sort_values(["part_rouge", "proba_moyenne"], ascending=False).reset_index(drop=True)


def resume_global(df: pd.DataFrame, seuil_rouge: float, seuil_orange: float, exclure: list[str] | None = None) -> dict:
    """Indicateurs de synthèse affichés en tête du tableau de bord.

    `exclure` retire certaines valeurs de quartier (par exemple « non cartographié ») du décompte
    des quartiers touchés : un trou de cartographie n'est pas un quartier.
    """
    if "proba_inondation" not in df.columns:
        raise KeyError("colonne absente du fichier de risque : 'proba_inondation'")
    proba = df["proba_inondation"].to_numpy(dtype=float)
    base = df[~df["quartier"].isin(exclure)] if (exclure and "quartier" in df.columns) else df
    par_quartier = agregat_par_quartier(base, seuil_rouge, seuil_orange) if "quartier" in df.columns else None
    return {
        "n_cellules": int(proba.size),
        "n_au_dessus": int(np.sum(proba >= seuil_rouge)),
        "part_au_dessus": part_au_dessus(proba, seuil_rouge),
        "proba_moyenne": float(np.mean(proba)) if proba.size else 0.0,
        "proba_max": float(np.max(proba)) if proba.size else 0.0,
        "n_quartiers": len(par_quartier) if par_quartier is not None else 0,
        "n_quartiers_rouge": int((par_quartier["part_rouge"] > 0).sum()) if par_quartier is not None else 0,
        "n_quartiers_majorite_rouge": int((par_quartier["part_rouge"] >= 0.5).sum())
        if par_quartier is not None
        else 0,
    }


def niveaux_recalcules(proba, seuil_rouge: float, seuil_orange: float) -> np.ndarray:
    """Niveaux d'alerte recalculés pour les seuils courants (vert / orange / rouge)."""
    return niveau_alerte(np.asarray(proba, dtype=float), seuil_orange, seuil_rouge)
