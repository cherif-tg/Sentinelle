"""Chargement de la configuration du projet (YAML)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parents[2]
CONFIG_DEFAUT = RACINE / "configs" / "projet.yaml"
EVENEMENTS_DEFAUT = RACINE / "configs" / "evenements.yaml"


def charger_config(chemin: str | Path | None = None) -> dict:
    with open(chemin or CONFIG_DEFAUT, encoding="utf-8") as f:
        return yaml.safe_load(f)


def charger_evenements(chemin: str | Path | None = None) -> list[dict]:
    with open(chemin or EVENEMENTS_DEFAUT, encoding="utf-8") as f:
        evts = yaml.safe_load(f)["evenements"]
    for e in evts:
        d = e.get("date_pic")
        e["date_pic"] = date.fromisoformat(str(d)) if d else None
    return evts
