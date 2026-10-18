"""Validation croisée spatiale : les cellules voisines doivent rester dans le même pli."""
from __future__ import annotations

import numpy as np


def blocs_spatiaux(x_m: np.ndarray, y_m: np.ndarray, taille_bloc_m: float) -> np.ndarray:
    """Identifiant de bloc carré (en coordonnées projetées, en mètres) pour chaque point."""
    if taille_bloc_m <= 0:
        raise ValueError("taille_bloc_m doit être > 0")
    bx = np.floor(np.asarray(x_m) / taille_bloc_m).astype(np.int64)
    by = np.floor(np.asarray(y_m) / taille_bloc_m).astype(np.int64)
    # appariement de Cantor après décalage positif -> identifiant entier unique
    bx -= bx.min()
    by -= by.min()
    return (bx + by) * (bx + by + 1) // 2 + by
