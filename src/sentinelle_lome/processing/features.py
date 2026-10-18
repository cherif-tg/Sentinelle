"""Variables de pluie (version pandas, pour tests et prototypage)."""
from __future__ import annotations

import pandas as pd


def cumuls_pluie(df: pd.DataFrame, fenetres=(1, 3, 7), col_zone="zone_id", col_date="date", col_mm="pluie_mm") -> pd.DataFrame:
    """Cumuls glissants par zone. Exige une série quotidienne complète (sans trous)."""
    out = df.sort_values([col_zone, col_date]).copy()
    g = out.groupby(col_zone)[col_mm]
    for n in fenetres:
        out[f"pluie_cumul_{n}j"] = g.transform(lambda s, n=n: s.rolling(n, min_periods=n).sum())
    return out


def indice_pluie_anterieure(serie: pd.Series, k: float = 0.85) -> pd.Series:
    """Indice de pluie antérieure : API_t = k * API_{t-1} + P_t."""
    if not 0 < k < 1:
        raise ValueError("k doit être dans ]0, 1[")
    vals, api = [], 0.0
    for p in serie.fillna(0.0):
        api = k * api + p
        vals.append(api)
    return pd.Series(vals, index=serie.index, name="api")


def evenements_pluvieux(
    df: pd.DataFrame, n: int = 10, separation_jours: int = 3, cumul_jours: int = 1, col_date="date", col_mm="pluie_mm"
) -> pd.DataFrame:
    """Sélectionne les `n` plus fortes pluies (cumul glissant de `cumul_jours`), espacées d'au moins `separation_jours`.

    Sert à choisir les dates d'images radar à étiqueter (docs/04, protocole, étape 1).
    """
    s = df.sort_values(col_date).set_index(col_date)[col_mm]
    cumul = s.rolling(cumul_jours, min_periods=cumul_jours).sum().dropna().sort_values(ascending=False)
    retenus: list[tuple[pd.Timestamp, float]] = []
    for d, v in cumul.items():
        if all(abs((d - r).days) >= separation_jours for r, _ in retenus):
            retenus.append((d, float(v)))
        if len(retenus) == n:
            break
    return pd.DataFrame(retenus, columns=["date", "cumul_mm"])
