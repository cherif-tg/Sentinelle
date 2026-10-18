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
