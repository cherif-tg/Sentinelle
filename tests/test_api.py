import json

import pandas as pd
from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch, ecrire=True):
    from sentinelle_lome.serving import api

    api._cache.update({"mtime": None, "df": None})
    chemin = tmp_path / "risque.parquet"
    if ecrire:
        pd.DataFrame(
            {
                "cellule_id": [1, 2, 3],
                "quartier": ["Adidogomé", "Adidogomé", "Bè"],
                "lon": [1.20, 1.21, 1.25],
                "lat": [6.17, 6.18, 6.13],
                "proba_inondation": [0.9, 0.2, 0.5],
                "niveau_alerte": ["rouge", "vert", "orange"],
            }
        ).to_parquet(chemin)
    monkeypatch.setenv("SL_RISQUE_PARQUET", str(chemin))
    return TestClient(api.app)


def test_sante(tmp_path, monkeypatch):
    assert _client(tmp_path, monkeypatch).get("/sante").json() == {"statut": "ok"}


def test_point_et_quartier(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.get("/risque/point", params={"lat": 6.1301, "lon": 1.2499}).json()["quartier"] == "Bè"
    q = c.get("/risque/quartier/adidogomé").json()
    assert q["n_cellules"] == 2 and q["part_rouge"] == 0.5
    assert c.get("/risque/quartier/inconnu").status_code == 404


def test_donnees_absentes(tmp_path, monkeypatch):
    assert _client(tmp_path, monkeypatch, ecrire=False).get("/risque/point", params={"lat": 6, "lon": 1}).status_code == 503


def test_point_hors_emprise(tmp_path, monkeypatch):
    """Un point hors de l'emprise (ici Paris) est refusé au lieu de renvoyer une cellule de Lomé."""
    r = _client(tmp_path, monkeypatch).get("/risque/point", params={"lat": 48.8566, "lon": 2.3522})
    assert r.status_code == 422
    assert "emprise" in r.json()["detail"]


def test_point_dans_emprise_expose_la_source(tmp_path, monkeypatch):
    corps = _client(tmp_path, monkeypatch).get("/risque/point", params={"lat": 6.1301, "lon": 1.2499}).json()
    assert corps["quartier"] == "Bè"
    assert corps["source"] == "inconnue"  # pas de .meta.json à côté de ce Parquet de test


def test_meta_lue_depuis_le_fichier(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    meta = {
        "source": "synthetique",
        "avertissement": "Valeurs synthétiques.",
        "date_generation": "2026-10-20T00:00:00+00:00",
        "n_cellules": 3,
    }
    (tmp_path / "risque.parquet.meta.json").write_text(json.dumps(meta), encoding="utf-8")
    r = client.get("/meta")
    assert r.status_code == 200
    assert {"source", "avertissement", "date_generation", "n_cellules"} <= r.json().keys()
    assert r.json()["n_cellules"] == 3


def test_meta_absente(tmp_path, monkeypatch):
    assert _client(tmp_path, monkeypatch).get("/meta").status_code == 503
