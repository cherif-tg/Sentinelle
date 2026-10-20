"""Export des contours administratifs du Grand Lomé depuis Earth Engine.

Le District autonome du Grand Lomé (DAGL) regroupe deux préfectures — Golfe et Agoè-Nyivé — et
treize communes. FAO/GAUL/2025 s'arrête au niveau 2 (préfectures) : les communes et les quartiers
n'y figurent pas.

Usage :
    python -m sentinelle_lome.ingestion.gee_contours --dry-run
    python -m sentinelle_lome.ingestion.gee_contours --projet-gee sentinelle-512022

`--dry-run` n'appelle pas Earth Engine : il affiche ce qui serait exporté.
L'authentification (`earthengine authenticate`) est à faire une fois.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ASSET = "FAO/GAUL/2025/level2"
PREFECTURES = ["Golfe", "Agoè-Nyivé"]
PAYS = "TGO"
SORTIE_DEFAUT = "data/raw/contours/grand_lome_gaul2025.geojson"


def plan_export(asset: str = ASSET, prefectures: list[str] | None = None, sortie: str = SORTIE_DEFAUT) -> dict:
    """Description de l'export, sans appel réseau : sert au `--dry-run` et aux tests."""
    return {
        "asset": asset,
        "pays": PAYS,
        "unites": list(prefectures if prefectures is not None else PREFECTURES),
        "sortie": sortie,
        "champs": ["GAUL2_NAME", "GAUL1_NAME", "GAUL0_NAME", "GAUL2_CODE"],
    }


def exporter(projet_gee: str, sortie: str = SORTIE_DEFAUT, simplifier_m: float = 0.0) -> dict:
    """Interroge Earth Engine, écrit le GeoJSON et ses métadonnées. Retourne les métadonnées.

    La superficie est celle calculée par Earth Engine (géodésique, sur l'ellipsoïde), pas une
    approximation locale : c'est la référence pour contrôler le masquage de la grille.
    """
    import ee  # import tardif : dépendance optionnelle (extra "gee")

    ee.Initialize(project=projet_gee)
    collection = (
        ee.FeatureCollection(ASSET)
        .filter(ee.Filter.eq("ISO3_CODE", PAYS))
        .filter(ee.Filter.inList("GAUL2_NAME", PREFECTURES))
    )
    noms = collection.aggregate_array("GAUL2_NAME").getInfo()
    if sorted(noms) != sorted(PREFECTURES):
        raise RuntimeError(f"préfectures attendues {PREFECTURES}, obtenues {noms}")

    a_exporter = collection.map(lambda f: f.simplify(simplifier_m)) if simplifier_m else collection
    contenu = a_exporter.getInfo()

    chemin = Path(sortie)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(json.dumps(contenu, ensure_ascii=False), encoding="utf-8")

    geometrie = collection.geometry()
    bornes = geometrie.bounds().coordinates().getInfo()[0]
    meta = {
        "source": ASSET,
        "pays": PAYS,
        "unites": noms,
        "superficie_km2": round(float(geometrie.area(100).divide(1e6).getInfo()), 1),
        "borne_ouest": bornes[0][0],
        "borne_sud": bornes[0][1],
        "borne_est": bornes[2][0],
        "borne_nord": bornes[2][1],
        "simplification_m": simplifier_m,
        "date_export": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fichier": str(chemin).replace("\\", "/"),
        "avertissement": (
            "Contours GAUL 2025 de niveau 2 (préfectures). Les quartiers et les 13 communes du DAGL "
            "ne sont pas couverts par cette source."
        ),
    }
    Path(f"{chemin}.meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="affiche le plan sans appeler Earth Engine")
    p.add_argument("--projet-gee", default=None, help="identifiant du projet Google Cloud / Earth Engine")
    p.add_argument("--sortie", default=SORTIE_DEFAUT, help="chemin du GeoJSON de sortie")
    p.add_argument("--simplifier-m", type=float, default=0.0, help="tolérance de simplification, en mètres")
    a = p.parse_args(argv)

    if a.dry_run:
        print(json.dumps(plan_export(sortie=a.sortie), ensure_ascii=False, indent=2))
        return
    if not a.projet_gee:
        p.error("--projet-gee est requis hors --dry-run")

    meta = exporter(a.projet_gee, a.sortie, a.simplifier_m)
    print(
        f"[contours] {meta['unites']} exportés vers {meta['fichier']} — "
        f"{meta['superficie_km2']} km² (Earth Engine)"
    )


if __name__ == "__main__":
    main()
