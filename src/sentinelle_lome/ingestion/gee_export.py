"""Exports Google Earth Engine (Sentinel-1) pour les événements d'inondation.

Usage :
    python -m sentinelle_lome.ingestion.gee_export --dry-run
    python -m sentinelle_lome.ingestion.gee_export --projet-gee MON_PROJET

--dry-run n'appelle pas Earth Engine : il affiche le plan d'export.
L'authentification (`earthengine authenticate`) est à faire une fois.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta

from sentinelle_lome.config import charger_config, charger_evenements


def fenetres_evenement(date_pic: date, avant_jours: int, apres_jours: int) -> dict[str, tuple[str, str]]:
    """Fenêtres (début inclus, fin exclue) avant/après l'événement, au format ISO."""
    return {
        "avant": ((date_pic - timedelta(days=avant_jours)).isoformat(), date_pic.isoformat()),
        "apres": (date_pic.isoformat(), (date_pic + timedelta(days=apres_jours + 1)).isoformat()),
    }


def plan_exports(config: dict, evenements: list[dict]) -> list[dict]:
    radar = config["radar"]
    plan = []
    for e in evenements:
        if e["date_pic"] is None:
            print(f"[avertissement] événement {e['id']} sans date_pic : ignoré")
            continue
        fen = fenetres_evenement(e["date_pic"], radar["fenetre_avant_jours"], radar["fenetre_apres_jours"])
        for passe in radar["passes"]:
            for nom_fen, (debut, fin) in fen.items():
                plan.append(
                    {
                        "description": f"s1_{e['id']}_{passe[:3].lower()}_{nom_fen}",
                        "passe": passe,
                        "debut": debut,
                        "fin": fin,
                    }
                )
    return plan


def composite_s1(ee, aoi, debut: str, fin: str, passe: str):
    """Composite médian Sentinel-1 GRD (mode IW, VV+VH) pour une passe donnée."""
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(debut, fin)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.eq("orbitProperties_pass", passe))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(["VV", "VH"])
        .median()
        .clip(aoi)
    )


def executer(config: dict, evenements: list[dict], projet_gee: str, dossier_drive: str) -> None:
    import ee  # import tardif : dépendance optionnelle (extra "gee")

    ee.Initialize(project=projet_gee)
    lon_min, lat_min, lon_max, lat_max = config["zone_etude"]["emprise_provisoire"]
    aoi = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])
    for t in plan_exports(config, evenements):
        image = composite_s1(ee, aoi, t["debut"], t["fin"], t["passe"])
        tache = ee.batch.Export.image.toDrive(
            image=image,
            description=t["description"],
            folder=dossier_drive,
            region=aoi,
            scale=config["grille"]["resolution_radar_m"],
            crs=config["zone_etude"]["crs_projete"],
            maxPixels=int(1e10),
        )
        tache.start()
        print(f"[lancé] {t['description']} ({t['debut']} -> {t['fin']})")


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true", help="affiche le plan sans appeler Earth Engine")
    p.add_argument("--projet-gee", default=None, help="identifiant du projet Google Cloud / Earth Engine")
    p.add_argument("--dossier-drive", default="sentinelle_lome_s1")
    a = p.parse_args(argv)
    cfg, evts = charger_config(), charger_evenements()
    if a.dry_run:
        for t in plan_exports(cfg, evts):
            print(t)
        return
    if not a.projet_gee:
        p.error("--projet-gee est requis hors --dry-run")
    executer(cfg, evts, a.projet_gee, a.dossier_drive)


if __name__ == "__main__":
    main()
