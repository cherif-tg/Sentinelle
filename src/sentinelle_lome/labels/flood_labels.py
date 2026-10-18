"""Détection d'eau d'inondation par changement radar (Sentinel-1, échelle dB).

Les seuils par défaut sont des POINTS DE DÉPART à calibrer sur Lomé
(voir docs/04_methodologie_labels.md) ; ce ne sont pas des valeurs validées.
"""
from __future__ import annotations

import numpy as np


def vers_db(intensite: np.ndarray) -> np.ndarray:
    """Convertit une intensité linéaire en décibels (valeurs <= 0 -> NaN)."""
    return 10.0 * np.log10(np.where(intensite > 0, intensite, np.nan))


def detecter_eau(
    pre_db: np.ndarray,
    post_db: np.ndarray,
    seuil_delta_db: float = -3.0,
    seuil_post_db: float = -15.0,
    hand: np.ndarray | None = None,
    hand_max_m: float = 15.0,
) -> np.ndarray:
    """Masque booléen : forte baisse de rétrodiffusion ET valeur post-événement basse.

    Si `hand` est fourni, les pixels trop hauts au-dessus du drainage sont écartés.
    """
    with np.errstate(invalid="ignore"):
        delta = post_db - pre_db
        masque = (delta <= seuil_delta_db) & (post_db <= seuil_post_db)
    masque = masque & ~np.isnan(delta) & ~np.isnan(post_db)
    if hand is not None:
        masque = masque & (hand <= hand_max_m)
    return masque.astype(bool)


def concordance_passes(masque_asc: np.ndarray, masque_desc: np.ndarray) -> np.ndarray:
    """Étiquette « haute confiance » : eau détectée par les deux passes."""
    return np.logical_and(masque_asc, masque_desc)


def metriques_masques(pred: np.ndarray, ref: np.ndarray) -> dict[str, float]:
    """Précision, rappel, F1 et IoU d'un masque prédit contre un masque de référence."""
    pred, ref = np.asarray(pred, dtype=bool), np.asarray(ref, dtype=bool)
    tp = float(np.sum(pred & ref))
    fp = float(np.sum(pred & ~ref))
    fn = float(np.sum(~pred & ref))

    def _div(a: float, b: float) -> float:
        return a / b if b > 0 else float("nan")

    precision, rappel = _div(tp, tp + fp), _div(tp, tp + fn)
    return {
        "precision": precision,
        "rappel": rappel,
        "f1": _div(2 * tp, 2 * tp + fp + fn),
        "iou": _div(tp, tp + fp + fn),
    }
