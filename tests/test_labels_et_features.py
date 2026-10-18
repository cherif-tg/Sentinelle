import numpy as np
import pandas as pd
import pytest

from sentinelle_lome.labels.flood_labels import concordance_passes, detecter_eau, vers_db
from sentinelle_lome.processing.features import cumuls_pluie, indice_pluie_anterieure


def test_vers_db():
    assert vers_db(np.array([1.0]))[0] == pytest.approx(0.0)
    assert vers_db(np.array([0.1]))[0] == pytest.approx(-10.0)
    assert np.isnan(vers_db(np.array([0.0]))[0])


def test_detecter_eau_et_masque_hand():
    pre = np.array([-10.0, -10.0, -10.0, np.nan])
    post = np.array([-20.0, -11.0, -20.0, -20.0])
    hand = np.array([2.0, 2.0, 30.0, 2.0])
    m = detecter_eau(pre, post, hand=hand)
    assert m.tolist() == [True, False, False, False]


def test_concordance():
    a, b = np.array([True, True, False]), np.array([True, False, False])
    assert concordance_passes(a, b).tolist() == [True, False, False]


def test_cumuls_pluie():
    df = pd.DataFrame({"zone_id": ["a"] * 4, "date": pd.date_range("2026-06-01", periods=4), "pluie_mm": [1, 2, 3, 4]})
    out = cumuls_pluie(df, fenetres=(1, 3))
    assert out["pluie_cumul_1j"].tolist() == [1, 2, 3, 4]
    assert out["pluie_cumul_3j"].isna().sum() == 2
    assert out["pluie_cumul_3j"].iloc[3] == 9


def test_api_pluie_anterieure():
    s = pd.Series([10.0, 0.0, 0.0])
    r = indice_pluie_anterieure(s, k=0.5)
    assert r.tolist() == [10.0, 5.0, 2.5]
    with pytest.raises(ValueError):
        indice_pluie_anterieure(s, k=1.5)


def test_metriques_masques():
    from sentinelle_lome.labels.flood_labels import metriques_masques

    ref = np.array([True, True, False, False])
    pred = np.array([True, False, True, False])
    m = metriques_masques(pred, ref)
    assert m["precision"] == 0.5 and m["rappel"] == 0.5
    assert m["iou"] == pytest.approx(1 / 3) and m["f1"] == 0.5
    assert np.isnan(metriques_masques(np.zeros(3, bool), np.zeros(3, bool))["iou"])


def test_evenements_pluvieux_separes():
    from sentinelle_lome.processing.features import evenements_pluvieux

    dates = pd.date_range("2026-06-01", periods=10)
    df = pd.DataFrame({"date": dates, "pluie_mm": [0, 50, 40, 0, 0, 0, 0, 30, 0, 0]})
    r = evenements_pluvieux(df, n=2, separation_jours=3)
    assert r["date"].tolist() == [pd.Timestamp("2026-06-02"), pd.Timestamp("2026-06-08")]
    assert r["cumul_mm"].tolist() == [50.0, 30.0]
