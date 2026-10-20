"""Tests des calculs du tableau de bord — fonctions pures, sans navigateur ni Streamlit."""
import numpy as np
import pandas as pd
import pytest

from sentinelle_lome.serving.tableau_de_bord import (
    agregat_par_quartier,
    courbe_sensibilite,
    niveaux_recalcules,
    part_au_dessus,
    resume_global,
    seuil_depuis_couts,
)


def _risque() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "quartier": ["A", "A", "B", "C"],
            "proba_inondation": [0.9, 0.05, 0.5, 0.0],
        }
    )


def test_seuil_depuis_couts_ratio_1_10():
    assert seuil_depuis_couts(1.0, 10.0) == pytest.approx(1.0 / 11.0)


def test_seuil_depuis_couts_refuse_un_cout_nul():
    with pytest.raises(ValueError):
        seuil_depuis_couts(0.0, 10.0)


def test_part_au_dessus_inclut_le_seuil():
    assert part_au_dessus([0.0, 0.1, 0.2], 0.1) == pytest.approx(2.0 / 3.0)


def test_part_au_dessus_refuse_un_seuil_hors_bornes():
    with pytest.raises(ValueError):
        part_au_dessus([0.5], 1.5)


def test_courbe_sensibilite_decroissante_et_bornee():
    rng = np.random.default_rng(0)
    courbe = courbe_sensibilite(rng.uniform(size=500), n_points=21)
    assert courbe["part_au_dessus"].is_monotonic_decreasing
    assert courbe["part_au_dessus"].between(0.0, 1.0).all()
    assert courbe["seuil"].iloc[0] == 0.0
    assert courbe["part_au_dessus"].iloc[0] == pytest.approx(1.0)
    assert courbe["seuil"].iloc[-1] == 1.0


def test_agregat_par_quartier_trie_et_coherent():
    agg = agregat_par_quartier(_risque(), seuil_rouge=0.2, seuil_orange=0.1)
    assert agg["n_cellules"].sum() == 4
    assert list(agg["quartier"]) == ["B", "A", "C"]  # tri par part de rouge décroissante
    ligne_a = agg.set_index("quartier").loc["A"]
    assert ligne_a["part_rouge"] == pytest.approx(0.5)
    assert ligne_a["part_alerte"] == pytest.approx(0.5)  # 0.05 < 0.1 : seule la cellule à 0.9 compte
    assert agg["part_rouge"].between(0.0, 1.0).all()


def test_agregat_par_quartier_refuse_des_seuils_incoherents():
    with pytest.raises(ValueError):
        agregat_par_quartier(_risque(), seuil_rouge=0.1, seuil_orange=0.5)


def test_resume_global_compte_les_quartiers_touches():
    resume = resume_global(_risque(), seuil_rouge=0.2, seuil_orange=0.1)
    assert resume["n_cellules"] == 4
    assert resume["n_au_dessus"] == 2
    assert resume["part_au_dessus"] == pytest.approx(0.5)
    assert resume["n_quartiers"] == 3
    assert resume["n_quartiers_rouge"] == 2  # A et B, pas C


def test_resume_global_exclut_le_non_cartographie_du_decompte():
    df = pd.DataFrame(
        {
            "quartier": ["A", "A", "non cartographié", "non cartographié"],
            "proba_inondation": [0.9, 0.0, 0.9, 0.9],
        }
    )
    resume = resume_global(df, seuil_rouge=0.5, seuil_orange=0.25, exclure=["non cartographié"])
    assert resume["n_cellules"] == 4  # les cellules restent comptées
    assert resume["n_quartiers"] == 1  # un trou de cartographie n'est pas un quartier
    assert resume["n_quartiers_rouge"] == 1


def test_niveaux_recalcules_respecte_les_seuils():
    niveaux = niveaux_recalcules([0.05, 0.3, 0.9], seuil_rouge=0.5, seuil_orange=0.25)
    assert list(niveaux) == ["vert", "orange", "rouge"]
