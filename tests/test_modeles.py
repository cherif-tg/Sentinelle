import numpy as np
import pandas as pd
import pytest

from sentinelle_lome.models.declenchement import entrainer_declenchement, niveau_alerte, seuil_decision
from sentinelle_lome.models.exposition import exposer_batiments
from sentinelle_lome.models.spatial_cv import blocs_spatiaux
from sentinelle_lome.models.susceptibilite import VARIABLES_PAR_DEFAUT, donnees_synthetiques, evaluer_cv_spatiale


def test_blocs_spatiaux_uniques_et_stables():
    x = np.array([0, 100, 2500, 2600, 0])
    y = np.array([0, 100, 0, 50, 2500])
    b = blocs_spatiaux(x, y, 2000)
    assert b[0] == b[1] and b[2] == b[3]
    assert len({b[0], b[2], b[4]}) == 3


def test_cv_spatiale_sur_donnees_synthetiques():
    df = donnees_synthetiques(3000)
    df["bloc"] = blocs_spatiaux(df["x_m"], df["y_m"], 4000)
    r = evaluer_cv_spatiale(df, VARIABLES_PAR_DEFAUT, "inonde", "bloc", n_plis=4)
    taux = df["inonde"].mean()
    assert r["pr_auc_moy"] > taux  # meilleur que le hasard (PR-AUC du hasard ~ prévalence)


def test_monotonie_pluie():
    rng = np.random.default_rng(0)
    n = 3000
    df = pd.DataFrame({"cumul_24h": rng.gamma(2, 20, n), "cumul_72h": rng.gamma(2, 35, n)})
    p = 1 / (1 + np.exp(-(0.03 * df["cumul_24h"] + 0.02 * df["cumul_72h"] - 4)))
    df["inonde"] = (rng.uniform(size=n) < p).astype(int)
    m = entrainer_declenchement(df, ["cumul_24h", "cumul_72h"], "inonde")
    grille = np.column_stack([np.linspace(0, 300, 50), np.full(50, 100.0)])
    pr = m.predict_proba(grille)[:, 1]
    assert np.all(np.diff(pr) >= -1e-12)


def test_seuil_decision_et_niveaux():
    assert seuil_decision(1.0, 9.0) == pytest.approx(0.1)
    n = niveau_alerte(np.array([0.05, 0.3, 0.9]), 0.1, 0.6)
    assert n.tolist() == ["vert", "orange", "rouge"]
    with pytest.raises(ValueError):
        seuil_decision(0, 1)


def test_exposition():
    bat = pd.DataFrame({"cellule_id": [1, 1, 2, 3], "quartier": ["A", "A", "A", "B"]})
    risque = pd.DataFrame({"cellule_id": [1, 2], "proba_inondation": [0.8, 0.2]})
    r = exposer_batiments(bat, risque, seuil=0.5).set_index("quartier")
    assert r.loc["A", "n_exposes_seuil"] == 2 and r.loc["A", "n_batiments"] == 3
    assert r.loc["A", "n_attendu"] == pytest.approx(1.8)
    assert r.loc["B", "n_attendu"] == 0
