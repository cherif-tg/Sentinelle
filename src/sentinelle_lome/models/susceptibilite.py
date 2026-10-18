"""Modèle A — susceptibilité à l'inondation (statique), validation croisée spatiale."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, brier_score_loss
from sklearn.model_selection import GroupKFold

VARIABLES_PAR_DEFAUT = ["hand_m", "pente_deg", "altitude_m", "dist_drain_m", "densite_bati"]


def evaluer_cv_spatiale(df: pd.DataFrame, variables: list[str], cible: str, groupes: str, n_plis: int = 5, graine: int = 0) -> dict:
    """Retourne PR-AUC et Brier moyens (et par pli) sur des plis spatialement disjoints."""
    X, y, g = df[variables].to_numpy(), df[cible].to_numpy(), df[groupes].to_numpy()
    pr, br = [], []
    for tr, te in GroupKFold(n_splits=n_plis).split(X, y, g):
        if y[te].sum() == 0 or y[tr].sum() == 0:
            continue  # pli sans positif : PR-AUC non définie
        m = HistGradientBoostingClassifier(random_state=graine).fit(X[tr], y[tr])
        p = m.predict_proba(X[te])[:, 1]
        pr.append(average_precision_score(y[te], p))
        br.append(brier_score_loss(y[te], p))
    if not pr:
        raise ValueError("aucun pli exploitable (pas de positifs dans les plis)")
    return {"pr_auc_moy": float(np.mean(pr)), "brier_moy": float(np.mean(br)), "pr_auc_plis": pr, "n_plis_valides": len(pr)}


def entrainer(df: pd.DataFrame, variables: list[str], cible: str, graine: int = 0) -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(random_state=graine).fit(df[variables].to_numpy(), df[cible].to_numpy())


def donnees_synthetiques(n: int = 4000, graine: int = 0) -> pd.DataFrame:
    """Jeu FICTIF pour tester la chaîne de bout en bout. Aucune valeur réelle."""
    rng = np.random.default_rng(graine)
    df = pd.DataFrame(
        {
            "x_m": rng.uniform(0, 20000, n),
            "y_m": rng.uniform(0, 20000, n),
            "hand_m": rng.gamma(2.0, 3.0, n),
            "pente_deg": rng.gamma(1.5, 1.0, n),
            "altitude_m": rng.normal(15, 6, n),
            "dist_drain_m": rng.gamma(2.0, 200.0, n),
            "densite_bati": rng.uniform(0, 1, n),
        }
    )
    logit = 1.5 - 0.5 * df["hand_m"] - 0.4 * df["pente_deg"] - 0.002 * df["dist_drain_m"] + 1.0 * df["densite_bati"]
    df["inonde"] = (rng.uniform(size=n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df
