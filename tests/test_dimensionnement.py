import pytest

from sentinelle_lome.dimensionnement import n_cellules, n_lignes_cellule_date, taille_estimee_go


def test_n_cellules_exemple_500km2_10m():
    assert n_cellules(500, 10) == 5_000_000


def test_n_cellules_30m():
    assert n_cellules(900, 30) == 1_000_000


def test_lignes_et_taille():
    assert n_lignes_cellule_date(500, 10, 300) == 1_500_000_000
    assert taille_estimee_go(1_500_000_000, 64) == pytest.approx(96.0)


def test_entrees_invalides():
    with pytest.raises(ValueError):
        n_cellules(0, 10)


def test_surface_emprise_degre_equateur():
    from sentinelle_lome.dimensionnement import surface_emprise_km2

    assert surface_emprise_km2(0, 0, 1, 1) == pytest.approx(12364, abs=2)
    with pytest.raises(ValueError):
        surface_emprise_km2(1, 0, 0, 1)
