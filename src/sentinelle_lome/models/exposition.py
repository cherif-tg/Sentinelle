"""Modèle C — exposition du bâti et de la population."""
from __future__ import annotations

import pandas as pd


def exposer_batiments(batiments: pd.DataFrame, risque: pd.DataFrame, seuil: float, col_cellule: str = "cellule_id") -> pd.DataFrame:
    """Par quartier : nombre de bâtiments au-dessus du seuil et nombre attendu (somme des probabilités)."""
    j = batiments.merge(risque[[col_cellule, "proba_inondation"]], on=col_cellule, how="left")
    j["proba_inondation"] = j["proba_inondation"].fillna(0.0)
    j["expose"] = j["proba_inondation"] >= seuil
    return (
        j.groupby("quartier")
        .agg(
            n_batiments=(col_cellule, "size"),
            n_exposes_seuil=("expose", "sum"),
            n_attendu=("proba_inondation", "sum"),
        )
        .reset_index()
    )
