"""API de risque (FastAPI). Lit un Parquet « gold » produit par le lot nocturne.

Colonnes attendues : cellule_id, quartier, lon, lat, proba_inondation, niveau_alerte.
Variable d'environnement : SL_RISQUE_PARQUET (chemin du fichier).
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Sentinelle Lomé — API de risque", version="0.1.0")

_cache: dict = {"mtime": None, "df": None}


def _donnees() -> pd.DataFrame:
    chemin = Path(os.getenv("SL_RISQUE_PARQUET", "data/gold/risque_cellules.parquet"))
    if not chemin.exists():
        raise HTTPException(status_code=503, detail="Données de risque indisponibles (lot nocturne non exécuté).")
    mtime = chemin.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["df"], _cache["mtime"] = pd.read_parquet(chemin), mtime
    return _cache["df"]


@app.get("/sante")
def sante() -> dict:
    return {"statut": "ok"}


@app.get("/risque/point")
def risque_point(lat: float, lon: float) -> dict:
    """Cellule la plus proche (distance euclidienne en degrés : approximation de prototype)."""
    df = _donnees()
    i = ((df["lat"] - lat) ** 2 + (df["lon"] - lon) ** 2).idxmin()
    r = df.loc[i]
    return {
        "cellule_id": str(r["cellule_id"]),
        "quartier": str(r["quartier"]),
        "proba_inondation": float(r["proba_inondation"]),
        "niveau_alerte": str(r["niveau_alerte"]),
    }


@app.get("/risque/quartier/{nom}")
def risque_quartier(nom: str) -> dict:
    df = _donnees()
    sel = df[df["quartier"].str.lower() == nom.lower()]
    if sel.empty:
        raise HTTPException(status_code=404, detail="Quartier inconnu")
    return {
        "quartier": nom,
        "n_cellules": len(sel),
        "proba_moyenne": float(sel["proba_inondation"].mean()),
        "part_rouge": float((sel["niveau_alerte"] == "rouge").mean()),
    }
