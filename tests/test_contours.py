"""Tests des contours administratifs : chargement, masquage et superficie."""
import json

import pytest
from shapely.geometry import box, mapping

from sentinelle_lome.contours import (
    charger_contour,
    emprise_rectangulaire,
    masque_points,
    surface_km2,
)


def _ecrire_geojson(tmp_path, geometrie, nom="contour.geojson"):
    contenu = {
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "properties": {"nom": "test"}, "geometry": mapping(geometrie)}],
    }
    chemin = tmp_path / nom
    chemin.write_text(json.dumps(contenu), encoding="utf-8")
    return chemin


def test_charger_contour_absent_renvoie_none(tmp_path):
    assert charger_contour(None) is None
    assert charger_contour("") is None
    assert charger_contour(tmp_path / "inexistant.geojson") is None


def test_charger_contour_fusionne_les_entites(tmp_path):
    contenu = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": mapping(box(1.0, 6.0, 1.1, 6.1))},
            {"type": "Feature", "properties": {}, "geometry": mapping(box(1.1, 6.0, 1.2, 6.1))},
        ],
    }
    chemin = tmp_path / "deux.geojson"
    chemin.write_text(json.dumps(contenu), encoding="utf-8")
    geometrie = charger_contour(chemin)
    assert geometrie is not None
    assert geometrie.area == pytest.approx(0.02)


def test_masque_points_exclut_le_bord():
    carre = box(1.0, 6.0, 1.2, 6.2)
    masque = masque_points(carre, [1.1, 1.5, 1.0], [6.1, 6.1, 6.0])
    assert masque.tolist() == [True, False, False]


def test_masque_points_refuse_des_entrees_de_taille_differente():
    with pytest.raises(ValueError):
        masque_points(box(0, 0, 1, 1), [0.5, 0.6], [0.5])


def test_surface_km2_un_degre_au_bord_de_l_equateur():
    # 1° x 1° à l'équateur : même ordre de grandeur que dimensionnement.surface_emprise_km2
    assert surface_km2(box(0, 0, 1, 1)) == pytest.approx(12364, abs=5)


def test_surface_km2_geometrie_vide():
    assert surface_km2(box(0, 0, 0, 0)) == 0.0


def test_emprise_rectangulaire_arrondie():
    assert emprise_rectangulaire(box(1.0, 6.0, 1.2, 6.2)) == [1.0, 6.0, 1.2, 6.2]
