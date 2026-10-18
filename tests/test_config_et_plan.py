from datetime import date

from sentinelle_lome.config import charger_config, charger_evenements
from sentinelle_lome.ingestion.gee_export import fenetres_evenement, plan_exports


def test_fenetres():
    f = fenetres_evenement(date(2026, 6, 29), 30, 6)
    assert f["avant"] == ("2026-05-30", "2026-06-29")
    assert f["apres"] == ("2026-06-29", "2026-07-06")


def test_config_et_evenements():
    cfg, evts = charger_config(), charger_evenements()
    assert cfg["zone_etude"]["crs_projete"] == "EPSG:32631"
    assert {e["id"] for e in evts} >= {"2026-06-pluies", "2020-10-charte"}


def test_plan_ignore_evenement_sans_date(capsys):
    cfg, evts = charger_config(), charger_evenements()
    plan = plan_exports(cfg, evts)
    assert "2020-09-inondation" in capsys.readouterr().out
    # 2 événements datés x 2 passes x 2 fenêtres
    assert len(plan) == 8
    assert all(t["description"].startswith("s1_") for t in plan)
