"""Filtrage des empreintes de bâtiments (Open Buildings v3).

Les noms de colonnes attendus sont ceux des exports CSV d'Open Buildings ;
à VÉRIFIER sur la fiche officielle du jeu de données avant le premier chargement.
"""
from __future__ import annotations

import pandas as pd

COLONNES_ATTENDUES = {"latitude", "longitude", "area_in_meters", "confidence"}


def filtrer_batiments(df: pd.DataFrame, seuil_confiance: float, surface_min_m2: float) -> pd.DataFrame:
    manquantes = COLONNES_ATTENDUES - set(df.columns)
    if manquantes:
        raise ValueError(f"colonnes manquantes : {sorted(manquantes)}")
    masque = (df["confidence"] >= seuil_confiance) & (df["area_in_meters"] >= surface_min_m2)
    return df.loc[masque].reset_index(drop=True)
