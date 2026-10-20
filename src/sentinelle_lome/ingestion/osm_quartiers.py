"""Extraction des quartiers du Grand Lomé depuis OpenStreetMap.

Les quartiers de Lomé sont cartographiés dans OSM comme relations `boundary=administrative`
de niveau 10. Une relation est composée de tronçons (`ways`) qu'il faut recoudre pour former des
anneaux, puis des polygones.

Données © OpenStreetMap contributors, licence ODbL 1.0 : l'attribution est obligatoire et reportée
dans les métadonnées produites ici.

Usage :
    python -m sentinelle_lome.ingestion.osm_quartiers --dry-run
    python -m sentinelle_lome.ingestion.osm_quartiers

L'API OSM est sollicitée une fois par relation, avec une pause entre les appels : c'est volontaire,
pour rester dans les limites d'usage.
"""
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from shapely.geometry import MultiPolygon, Polygon, mapping
from shapely.ops import unary_union

from sentinelle_lome.config import charger_config
from sentinelle_lome.contours import charger_contour

OVERPASS = "https://overpass-api.de/api/interpreter"
API_OSM = "https://api.openstreetmap.org/api/0.6"
AGENT = "sentinelle-lome/0.1 (prototype; contact: projet Sentinelle Lomé)"
NIVEAU_QUARTIER = "10"
SORTIE_DEFAUT = "data/raw/contours/quartiers_osm.geojson"
PAUSE_S = 0.2
TENTATIVES = 3


def _get(url: str, donnees: bytes | None = None, timeout: int = 120) -> dict:
    """GET avec quelques reprises : Overpass répond parfois 429 ou 502 sous charge."""
    derniere: Exception | None = None
    for essai in range(TENTATIVES):
        try:
            requete = urllib.request.Request(url, data=donnees, headers={"User-Agent": AGENT})
            return json.loads(urllib.request.urlopen(requete, timeout=timeout).read().decode())
        except Exception as exc:  # noqa: BLE001 - on veut reessayer sur toute erreur reseau
            derniere = exc
            time.sleep(2 * (essai + 1))
    raise RuntimeError(f"échec après {TENTATIVES} tentatives : {url}") from derniere


def lister_quartiers(emprise: list[float], timeout: int = 180) -> list[dict]:
    """Relations `admin_level=10` dont l'emprise intersecte le rectangle donné."""
    lon_min, lat_min, lon_max, lat_max = emprise
    requete = f"""
[out:json][timeout:{timeout}];
relation["boundary"="administrative"]["admin_level"="{NIVEAU_QUARTIER}"]
        ({lat_min},{lon_min},{lat_max},{lon_max});
out tags center;
"""
    reponse = _get(OVERPASS, urllib.parse.urlencode({"data": requete}).encode(), timeout=timeout + 60)
    return [
        {"osm_id": e["id"], "nom": e["tags"].get("name"), "lat": e.get("center", {}).get("lat"), "lon": e.get("center", {}).get("lon")}
        for e in reponse.get("elements", [])
        if e.get("type") == "relation" and e.get("tags", {}).get("name")
    ]


def geometrie_relation(osm_id: int) -> tuple[Polygon | MultiPolygon | None, dict]:
    """Reconstruit la géométrie d'une relation OSM à partir de ses tronçons.

    Retourne (géométrie, diagnostic). Une relation dont un anneau ne se referme pas est rejetée
    plutôt que complétée arbitrairement.
    """
    contenu = _get(f"{API_OSM}/relation/{osm_id}/full.json")
    elements = contenu.get("elements", [])
    relation = next((e for e in elements if e["type"] == "relation"), None)
    if relation is None:
        return None, {"motif": "relation absente"}

    coordonnees = {
        e["id"]: (float(e["lon"]), float(e["lat"])) for e in elements if e["type"] == "node"
    }
    ways = {e["id"]: e["nodes"] for e in elements if e["type"] == "way"}

    exterieurs: list[list[int]] = []
    interieurs: list[list[int]] = []
    manquants = 0
    for membre in relation.get("members", []):
        if membre.get("type") != "way":
            continue
        noeuds = ways.get(membre.get("ref"))
        if not noeuds:
            manquants += 1
            continue
        (interieurs if membre.get("role") == "inner" else exterieurs).append(list(noeuds))

    anneaux_ext = _recoudre(exterieurs)
    anneaux_int = _recoudre(interieurs)
    if not anneaux_ext:
        return None, {"motif": "aucun anneau extérieur refermé", "tronçons": len(exterieurs)}

    def polygone(anneau: list[int]) -> Polygon | None:
        if any(i not in coordonnees for i in anneau):
            return None
        return Polygon([coordonnees[i] for i in anneau])

    enveloppes = [p for p in (polygone(a) for a in anneaux_ext) if p is not None]
    if not enveloppes:
        return None, {"motif": "coordonnées de nœuds manquantes"}
    trous = [p for p in (polygone(a) for a in anneaux_int) if p is not None]

    finaux = []
    for enveloppe in enveloppes:
        dedans = [t.exterior.coords for t in trous if enveloppe.contains(t)]
        poly = Polygon(enveloppe.exterior.coords, dedans)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if not poly.is_empty:
            finaux.append(poly)

    geometrie = unary_union(finaux)
    diagnostic = {
        "tronçons": len(exterieurs),
        "anneaux": len(anneaux_ext),
        "trous": len(trous),
        "tronçons_manquants": manquants,
    }
    return geometrie, diagnostic


def _recoudre(troncons: list[list[int]]) -> list[list[int]]:
    """Recoud des tronçons en anneaux fermés. Les tronçons non recousables sont abandonnés."""
    restants = [list(t) for t in troncons if len(t) >= 2]
    anneaux: list[list[int]] = []
    while restants:
        courant = restants.pop(0)
        progression = True
        while courant[0] != courant[-1] and progression and restants:
            progression = False
            for i, troncon in enumerate(restants):
                if troncon[0] == courant[-1]:
                    courant.extend(troncon[1:])
                elif troncon[-1] == courant[-1]:
                    courant.extend(list(reversed(troncon))[1:])
                elif troncon[-1] == courant[0]:
                    courant = troncon[:-1] + courant
                elif troncon[0] == courant[0]:
                    courant = list(reversed(troncon))[:-1] + courant
                else:
                    continue
                restants.pop(i)
                progression = True
                break
        if len(courant) >= 4 and courant[0] == courant[-1]:
            anneaux.append(courant)
    return anneaux


def exporter(sortie: str = SORTIE_DEFAUT, emprise: list[float] | None = None, contour: str | None = None) -> dict:
    """Écrit un GeoJSON des quartiers OSM situés dans le contour de travail. Retourne les métadonnées."""
    cfg = charger_config()
    emprise = emprise or cfg["zone_etude"]["emprise"]
    geometrie_zone = charger_contour(contour if contour is not None else cfg["zone_etude"].get("contour"))

    candidats = lister_quartiers(emprise)
    entites, rejetes = [], []
    for candidat in candidats:
        geometrie, diagnostic = geometrie_relation(candidat["osm_id"])
        if geometrie is None or geometrie.is_empty:
            rejetes.append({**candidat, **diagnostic})
            continue
        if geometrie_zone is not None and not geometrie.intersects(geometrie_zone):
            rejetes.append({**candidat, "motif": "hors du contour de travail"})
            continue
        entites.append(
            {
                "type": "Feature",
                "properties": {
                    "nom": candidat["nom"],
                    "osm_id": candidat["osm_id"],
                    "admin_level": NIVEAU_QUARTIER,
                },
                "geometry": mapping(geometrie),
            }
        )
        time.sleep(PAUSE_S)

    collection = {"type": "FeatureCollection", "features": entites}
    chemin = Path(sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(collection, ensure_ascii=False), encoding="utf-8")

    meta = {
        "source": "OpenStreetMap, relations boundary=administrative admin_level=10",
        "licence": "ODbL 1.0 — © OpenStreetMap contributors",
        "attribution": "© OpenStreetMap contributors",
        "date_export": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fichier": str(chemin).replace("\\", "/"),
        "n_quartiers": len(entites),
        "n_candidats": len(candidats),
        "n_rejetes": len(rejetes),
        "rejetes": rejetes[:20],
        "emprise_requete": emprise,
    }
    Path(f"{chemin}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="n'interroge pas le réseau")
    p.add_argument("--sortie", default=SORTIE_DEFAUT)
    a = p.parse_args(argv)
    cfg = charger_config()

    if a.dry_run:
        print(
            json.dumps(
                {
                    "source": OVERPASS,
                    "api": API_OSM,
                    "niveau": NIVEAU_QUARTIER,
                    "emprise": cfg["zone_etude"]["emprise"],
                    "sortie": a.sortie,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    meta = exporter(a.sortie)
    print(f"[quartiers] {meta['n_quartiers']} quartiers exportés vers {meta['fichier']}")
    if meta["n_rejetes"]:
        print(f"[quartiers] {meta['n_rejetes']} candidats rejetés (voir {a.sortie}.meta.json)")


if __name__ == "__main__":
    main()
