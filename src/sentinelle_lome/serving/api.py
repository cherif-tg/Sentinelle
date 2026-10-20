"""API de risque (FastAPI). Lit un Parquet « gold » produit par le lot nocturne.

Colonnes attendues : cellule_id, quartier, lon, lat, proba_inondation, niveau_alerte.
Variable d'environnement : SL_RISQUE_PARQUET (chemin du fichier).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Sentinelle Lomé — API de risque", version="0.1.0")

_cache: dict = {"mtime": None, "df": None}


def _chemin_parquet() -> Path:
    return Path(os.getenv("SL_RISQUE_PARQUET", "data/gold/risque_cellules.parquet"))


def _lire_meta() -> dict | None:
    """Contenu du `<parquet>.meta.json` voisin, ou None s'il est absent ou illisible."""
    chemin = Path(f"{_chemin_parquet()}.meta.json")
    if not chemin.exists():
        return None
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _source() -> str:
    """Provenance déclarée dans les métadonnées, « inconnue » à défaut."""
    meta = _lire_meta()
    return str(meta.get("source", "inconnue")) if meta else "inconnue"


def _emprise(df: pd.DataFrame) -> tuple[float, float, float, float]:
    """(lon_min, lat_min, lon_max, lat_max) de l'emprise effectivement couverte par les données."""
    return (float(df["lon"].min()), float(df["lat"].min()), float(df["lon"].max()), float(df["lat"].max()))


def _donnees() -> pd.DataFrame:
    chemin = _chemin_parquet()
    if not chemin.exists():
        raise HTTPException(status_code=503, detail="Données de risque indisponibles (lot nocturne non exécuté).")
    mtime = chemin.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["df"], _cache["mtime"] = pd.read_parquet(chemin), mtime
    return _cache["df"]


@app.get("/sante")
def sante() -> dict:
    return {"statut": "ok"}


@app.get("/meta")
def meta_risque() -> dict:
    """Métadonnées du fichier de risque : provenance synthétique, date de génération, volumétrie."""
    contenu = _lire_meta()
    if contenu is None:
        raise HTTPException(status_code=503, detail="Métadonnées de risque indisponibles (lot nocturne non exécuté).")
    for cle, defaut in (
        ("source", "inconnue"),
        ("avertissement", None),
        ("date_generation", None),
        ("n_cellules", None),
    ):
        contenu.setdefault(cle, defaut)
    return contenu


@app.get("/risque/point")
def risque_point(lat: float, lon: float) -> dict:
    """Cellule la plus proche (distance euclidienne en degrés : approximation de prototype).

    Un point hors de l'emprise des données est refusé (422) : le plus proche voisin y serait
    arbitrairement éloigné et renverrait une cellule sans rapport avec le point demandé.
    """
    df = _donnees()
    lon_min, lat_min, lon_max, lat_max = _emprise(df)
    if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
        raise HTTPException(
            status_code=422,
            detail=(
                "Point hors de l'emprise des données de risque : "
                f"lon doit être dans [{lon_min:.4f}, {lon_max:.4f}] et "
                f"lat dans [{lat_min:.4f}, {lat_max:.4f}]."
            ),
        )
    i = ((df["lat"] - lat) ** 2 + (df["lon"] - lon) ** 2).idxmin()
    r = df.loc[i]
    return {
        "cellule_id": str(r["cellule_id"]),
        "quartier": str(r["quartier"]),
        "proba_inondation": float(r["proba_inondation"]),
        "niveau_alerte": str(r["niveau_alerte"]),
        "source": _source(),
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
        "source": _source(),
    }
