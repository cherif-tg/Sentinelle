"""Modèle B — déclenchement par la pluie, avec contrainte de monotonie, et seuils d'alerte."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier


def entrainer_declenchement(df: pd.DataFrame, variables_pluie: list[str], cible: str, graine: int = 0) -> HistGradientBoostingClassifier:
    """Plus de pluie ne peut pas réduire la probabilité d'inondation (contrainte +1)."""
    m = HistGradientBoostingClassifier(monotonic_cst=[1] * len(variables_pluie), random_state=graine)
    return m.fit(df[variables_pluie].to_numpy(), df[cible].to_numpy())


def seuil_decision(cout_fausse_alerte: float, cout_inondation_manquee: float) -> float:
    """Seuil de probabilité minimisant le coût attendu, pour des probabilités CALIBRÉES.

    On alerte si p * c_manque > (1 - p) * c_fausse_alerte, soit p > c_fa / (c_fa + c_manque).
    """
    if cout_fausse_alerte <= 0 or cout_inondation_manquee <= 0:
        raise ValueError("les coûts doivent être > 0")
    return cout_fausse_alerte / (cout_fausse_alerte + cout_inondation_manquee)


def niveau_alerte(proba: np.ndarray, seuil_orange: float, seuil_rouge: float) -> np.ndarray:
    if not 0 <= seuil_orange <= seuil_rouge <= 1:
        raise ValueError("exiger 0 <= seuil_orange <= seuil_rouge <= 1")
    return np.where(proba >= seuil_rouge, "rouge", np.where(proba >= seuil_orange, "orange", "vert"))
