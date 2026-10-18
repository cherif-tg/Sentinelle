"""Calculs d'ordre de grandeur pour justifier (ou non) le recours à Spark.

Arithmétique pure : ne remplace pas une mesure sur les données réelles
(voir docs/03_architecture.md).
"""
from __future__ import annotations

import math


def n_cellules(surface_km2: float, resolution_m: float) -> int:
    """Nombre de cellules carrées de côté `resolution_m` dans `surface_km2`."""
    if surface_km2 <= 0 or resolution_m <= 0:
        raise ValueError("surface et résolution doivent être > 0")
    return round(surface_km2 * 1_000_000 / (resolution_m**2))


def n_lignes_cellule_date(surface_km2: float, resolution_m: float, n_dates: int) -> int:
    return n_cellules(surface_km2, resolution_m) * n_dates


def taille_estimee_go(n_lignes: int, octets_par_ligne: int = 64) -> float:
    """Taille brute (Go) d'une table de `n_lignes`, avant compression Parquet."""
    return n_lignes * octets_par_ligne / 1e9


def surface_emprise_km2(lon_min: float, lat_min: float, lon_max: float, lat_max: float) -> float:
    """Aire d'un rectangle lon/lat sur une sphère (R = 6371,0088 km), en km².

    Approximation sphérique : suffisante pour un ordre de grandeur, pas pour un calcul cadastral.
    """
    if lon_max <= lon_min or lat_max <= lat_min:
        raise ValueError("emprise invalide : exiger lon_max > lon_min et lat_max > lat_min")
    r = 6371.0088
    dlam = math.radians(lon_max - lon_min)
    return r**2 * dlam * abs(math.sin(math.radians(lat_max)) - math.sin(math.radians(lat_min)))
