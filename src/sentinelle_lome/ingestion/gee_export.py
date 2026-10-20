"""Exports Google Earth Engine (Sentinel-1) pour les événements d'inondation.

Usage :
    python -m sentinelle_lome.ingestion.gee_export --dry-run
    python -m sentinelle_lome.ingestion.gee_export --projet-gee MON_PROJET
    python -m sentinelle_lome.ingestion.gee_export --projet-gee MON_PROJET --limite 1

--dry-run n'appelle pas Earth Engine : il affiche le plan d'export.
L'authentification (`earthengine authenticate`) est à faire une fois.

L'emprise exportée est le contour administratif s'il existe (voir `sentinelle_lome.contours`),
sinon le rectangle de la configuration. Les fenêtres sans aucune scène sont ignorées : lancer une
tâche sur une collection vide ne produirait qu'un échec.
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


def aoi_ee(ee, config: dict):
    """Emprise de travail : contour administratif s'il existe, sinon rectangle de configuration."""
    from sentinelle_lome.contours import charger_contour

    geometry = charger_contour(config["zone_etude"].get("contour"))
    if geometry is not None:
        return ee.Geometry(geometry.__geo_interface__)
    lon_min, lat_min, lon_max, lat_max = config["zone_etude"]["emprise"]
    return ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])


def collection_s1(ee, aoi, debut: str, fin: str, passe: str):
    """Collection Sentinel-1 GRD filtrée : mode IW, passe demandée, polarisations VV et VH."""
    return (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi)
        .filterDate(debut, fin)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.eq("orbitProperties_pass", passe))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(["VV", "VH"])
    )


def composite_s1(ee, aoi, debut: str, fin: str, passe: str):
    """Composite médian Sentinel-1 GRD (mode IW, VV+VH) pour une passe donnée."""
    return collection_s1(ee, aoi, debut, fin, passe).median().clip(aoi)


def executer(
    config: dict,
    evenements: list[dict],
    projet_gee: str,
    dossier_drive: str,
    limite: int | None = None,
) -> tuple[list[dict], list[dict]]:
    """Lance les exports et retourne (tâches lancées, fenêtres ignorées).

    Une fenêtre sans scène est ignorée plutôt que de lancer une tâche vouée à l'échec : c'est le
    cas des deux fenêtres descendantes de l'événement d'octobre 2020.
    """
    import ee  # import tardif : dépendance optionnelle (extra "gee")

    ee.Initialize(project=projet_gee)
    aoi = aoi_ee(ee, config)
    lancees: list[dict] = []
    ignorees: list[dict] = []
    deja_vues = {
        t.status().get("description")
        for t in ee.batch.Task.list()
        if t.status().get("state") in {"READY", "RUNNING", "COMPLETED"}
    }

    for t in plan_exports(config, evenements):
        if limite is not None and len(lancees) >= limite:
            break
        if t["description"] in deja_vues:
            ignorees.append({**t, "motif": "déjà lancée ou terminée"})
            print(f"[ignoré] {t['description']} : export déjà existant")
            continue
        collection = collection_s1(ee, aoi, t["debut"], t["fin"], t["passe"])
        n_scenes = collection.size().getInfo()
        if n_scenes == 0:
            ignorees.append({**t, "motif": "aucune scène"})
            print(f"[ignoré] {t['description']} : aucune scène sur la fenêtre")
            continue

        tache = ee.batch.Export.image.toDrive(
            image=collection.median().clip(aoi),
            description=t["description"],
            folder=dossier_drive,
            region=aoi,
            scale=config["grille"]["resolution_radar_m"],
            crs=config["zone_etude"]["crs_projete"],
            maxPixels=int(1e10),
        )
        tache.start()
        lancees.append({**t, "n_scenes": n_scenes, "task_id": tache.id})
        print(f"[lancé] {t['description']} ({n_scenes} scènes, {t['debut']} -> {t['fin']})")

    return lancees, ignorees


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dry-run", action="store_true", help="affiche le plan sans appeler Earth Engine")
    p.add_argument("--projet-gee", default=None, help="identifiant du projet Google Cloud / Earth Engine")
    p.add_argument("--dossier-drive", default="sentinelle_lome_s1")
    p.add_argument("--limite", type=int, default=None, help="nombre maximal d'exports lancés")
    a = p.parse_args(argv)
    cfg, evts = charger_config(), charger_evenements()
    if a.dry_run:
        for t in plan_exports(cfg, evts):
            print(t)
        return
    if not a.projet_gee:
        p.error("--projet-gee est requis hors --dry-run")
    lancees, ignorees = executer(cfg, evts, a.projet_gee, a.dossier_drive, a.limite)
    print(f"[bilan] {len(lancees)} tâche(s) lancée(s), {len(ignorees)} fenêtre(s) ignorée(s)")


if __name__ == "__main__":
    main()
