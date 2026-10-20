"""Tests du producteur « gold » : contrat de colonnes, bornes et lecture par l'API."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from sentinelle_lome.config import charger_config
from sentinelle_lome.pipeline.gold import COLONNES, generer_gold


@pytest.fixture(scope="module")
def sortie(tmp_path_factory):
    """Parquet généré une seule fois (résolution grossière pour rester rapide)."""
    chemin = tmp_path_factory.mktemp("gold") / "risque.parquet"
    generer_gold(sortie=chemin, resolution_m=2000.0, graine=3)
    return chemin


def test_colonnes_et_bornes(sortie):
    df = pd.read_parquet(sortie)
    assert list(df.columns) == COLONNES
    assert len(df) > 0 and df["cellule_id"].is_unique
    assert df["proba_inondation"].between(0.0, 1.0).all()
    assert set(df["niveau_alerte"]) <= {"vert", "orange", "rouge"}
    assert df["quartier"].notna().all()
    lon_min, lat_min, lon_max, lat_max = charger_config()["zone_etude"]["emprise"]
    assert df["lon"].between(lon_min, lon_max).all()
    assert df["lat"].between(lat_min, lat_max).all()


def test_meta_json(sortie):
    df = pd.read_parquet(sortie)
    meta = json.loads(Path(f"{sortie}.meta.json").read_text(encoding="utf-8"))
    assert meta["source"] == "synthetique"
    assert meta["resolution_m"] == 2000.0
    assert meta["graine"] == 3
    assert meta["n_cellules"] == len(df)
    assert "date_generation" in meta
    assert "ne décrivent pas le risque" in meta["avertissement"]


def test_api_lit_le_fichier_genere(sortie, monkeypatch):
    from sentinelle_lome.serving import api

    api._cache.update({"mtime": None, "df": None})
    monkeypatch.setenv("SL_RISQUE_PARQUET", str(sortie))
    client = TestClient(api.app)
    df = pd.read_parquet(sortie)
    r = client.get("/risque/point", params={"lat": float(df["lat"].iloc[0]), "lon": float(df["lon"].iloc[0])})
    assert r.status_code == 200 and r.json()["niveau_alerte"] in {"vert", "orange", "rouge"}
    q = client.get(f"/risque/quartier/{df['quartier'].iloc[0]}")
    assert q.status_code == 200 and q.json()["n_cellules"] >= 1


def test_calibration_monotone_et_moyenne():
    """La calibration doit produire une probabilité bornée, croissante avec le score, de moyenne conforme."""
    from sentinelle_lome.pipeline import gold

    score, etiquettes = gold.jeu_calibration(n=1500, graine=4, n_entrainement=1500)
    modele = gold.ajuster_calibration(score, etiquettes)

    grille = np.linspace(0.0, 1.0, 201)
    p = modele.predict(grille)
    assert np.all((p >= 0.0) & (p <= 1.0))
    assert np.all(np.diff(p) >= -1e-12), "la probabilité calibrée ne doit pas décroître avec le score"
    assert abs(modele.predict(score).mean() - float(np.mean(etiquettes))) < 0.05


def test_meta_documente_la_calibration(sortie):
    """Les métadonnées doivent rendre la calibration auditable (méthode, taille, taux observé)."""
    meta = json.loads(Path(f"{sortie}.meta.json").read_text(encoding="utf-8"))
    cal = meta["calibration"]
    assert "isotone" in cal["methode"].lower()
    assert cal["n_calibration"] > 0
    assert 0.0 <= cal["taux_positifs_observe"] <= 1.0
    assert "synthetique" in cal["portee"].lower()


def test_meta_nomme_le_scenario(sortie):
    """Le scénario pluvieux utilisé doit être identifiable dans les métadonnées."""
    meta = json.loads(Path(f"{sortie}.meta.json").read_text(encoding="utf-8"))
    assert meta["scenario"] == "moderee"
    assert set(meta["scenario_pluie_mm"]) == {"pluie_cumul_1j", "pluie_cumul_3j", "pluie_cumul_7j"}


def test_scenario_inconnu_refuse():
    from sentinelle_lome.pipeline import gold

    with pytest.raises(ValueError):
        gold.scenario_pluie("mousson")
