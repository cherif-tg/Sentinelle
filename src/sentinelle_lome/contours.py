"""Contours administratifs : chargement, masquage de grille et superficie.

Le contour est un GeoJSON produit par `sentinelle_lome.ingestion.gee_contours` (GAUL 2025,
préfectures Golfe et Agoè-Nyivé). Il sert à deux choses : restreindre la grille au territoire réel
et calculer une superficie comparable à celle d'Earth Engine.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from shapely import contains_xy
from shapely import transform as shapely_transform
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

KM_PAR_DEGRE = 111.195  # 2πR/360 avec R = 6371,0088 km : cohérent avec dimensionnement.surface_emprise_km2


def charger_contour(chemin: str | Path | None) -> BaseGeometry | None:
    """Charge un GeoJSON de contours et renvoie l'union de ses entités.

    Renvoie `None` si le chemin est vide ou si le fichier n'existe pas : l'appelant décide alors
    de continuer avec la seule emprise rectangulaire (et doit le signaler).
    """
    if not chemin:
        return None
    fichier = Path(chemin)
    if not fichier.exists():
        return None
    contenu = json.loads(fichier.read_text(encoding="utf-8"))
    entites = contenu.get("features") if contenu.get("type") == "FeatureCollection" else [contenu]
    geometries = [shape(entite["geometry"]) for entite in entites]
    if not geometries:
        return None
    return unary_union(geometries)


def masque_points(geometrie: BaseGeometry, lon, lat) -> np.ndarray:
    """Masque booléen des points situés à l'intérieur du contour (bord exclu)."""
    lon_arr = np.asarray(lon, dtype=float).ravel()
    lat_arr = np.asarray(lat, dtype=float).ravel()
    if lon_arr.shape != lat_arr.shape:
        raise ValueError("lon et lat doivent avoir la même longueur")
    return contains_xy(geometrie, lon_arr, lat_arr)


def surface_km2(geometrie: BaseGeometry) -> float:
    """Superficie approchée en km², par projection équirectangulaire locale.

    La latitude de référence est celle du centre de l'emprise : l'erreur reste inférieure à
    quelques dixièmes de pour cent sur une zone de la taille du Grand Lomé. Earth Engine reste la
    référence géodésique ; cette valeur sert au contrôle de cohérence local.
    """
    if geometrie is None or geometrie.is_empty:
        return 0.0
    _, lat_min, _, lat_max = geometrie.bounds
    facteur_lon = KM_PAR_DEGRE * math.cos(math.radians((lat_min + lat_max) / 2.0))

    def projeter(coords):
        coordonnees = np.asarray(coords, dtype=float)
        sortie = coordonnees.copy()
        sortie[:, 0] = coordonnees[:, 0] * facteur_lon
        sortie[:, 1] = coordonnees[:, 1] * KM_PAR_DEGRE
        return sortie

    return float(shapely_transform(geometrie, projeter).area)


def emprise_rectangulaire(geometrie: BaseGeometry) -> list[float]:
    """Emprise [lon_min, lat_min, lon_max, lat_max] du contour, arrondie à 6 décimales."""
    lon_min, lat_min, lon_max, lat_max = geometrie.bounds
    return [round(float(v), 6) for v in (lon_min, lat_min, lon_max, lat_max)]


def charger_quartiers(chemin: str | Path | None) -> list[tuple[str, BaseGeometry]]:
    """Liste (nom, géométrie) des quartiers d'un GeoJSON ; liste vide si le fichier manque.

    Un fichier absent n'est pas une erreur : l'appelant retombe alors sur l'affectation par
    centroïdes, et doit le signaler dans ses métadonnées.
    """
    if not chemin:
        return []
    fichier = Path(chemin)
    if not fichier.exists():
        return []
    contenu = json.loads(fichier.read_text(encoding="utf-8"))
    quartiers: list[tuple[str, BaseGeometry]] = []
    for entite in contenu.get("features", []):
        nom = (entite.get("properties") or {}).get("nom")
        if nom and entite.get("geometry"):
            quartiers.append((str(nom), shape(entite["geometry"])))
    return quartiers


def affecter_par_polygones(
    quartiers: list[tuple[str, BaseGeometry]], lon, lat, defaut: str = "non cartographié"
) -> np.ndarray:
    """Nom du quartier contenant chaque point ; `defaut` si aucun polygone ne le couvre.

    Les points situés exactement sur une frontière ne sont contenus par aucun polygone et tombent
    donc dans `defaut` : cas marginal, assumé pour éviter un double rattachement arbitraire.
    """
    lon_arr = np.asarray(lon, dtype=float).ravel()
    lat_arr = np.asarray(lat, dtype=float).ravel()
    if lon_arr.shape != lat_arr.shape:
        raise ValueError("lon et lat doivent avoir la même longueur")
    noms = np.full(lon_arr.shape, defaut, dtype=object)
    for nom, geometrie in quartiers:
        noms[contains_xy(geometrie, lon_arr, lat_arr)] = nom
    return noms
