# notebooks/

Installation : `pip install -e ".[notebooks]"` (ajoute `jupyterlab`, `matplotlib`, `rasterio`). Ré-exécution complète : `make notebooks`.

| # | Notebook | Statut | Ferme dans `docs/11` |
|---|---|---|---|
| 01 | `01_exploration_zone.ipynb` | Exécuté ; la section Earth Engine est désactivée (`UTILISER_EE = False`) | Taille de l'emprise, nombre de bâtiments, passes Sentinel-1 |
| 02 | `02_etiquettes_radar.ipynb` | Exécuté sur scène **fictive** ; partie réelle activée si `data/raw/s1_*.tif` existent | Calibration des seuils (après référence réelle) |
| 03 | `03_variables_pluie.ipynb` | Exécuté sur pluie **fictive** ; extraction réelle désactivée par défaut | Choix CHIRPS / IMERG |

## Ordre de travail recommandé

1. Notebook 01 avec `UTILISER_EE = True` : produit `data/raw/verifications_ee.json`.
2. Notebook 03 avec `UTILISER_EE = True` : produit `data/raw/pluie_chirps.csv` et `pluie_imerg.csv`, puis la comparaison.
3. Lancer `python -m sentinelle_lome.ingestion.gee_export --projet-gee VOTRE_PROJET`, puis notebook 02, partie 2.

## À venir (voir `docs/09_planning.md`)

04 variables de terrain (HAND, pente) · 05 tables silver avec Spark et Sedona · 06 modèles A et B · 07 exposition · 08 évaluation sur juin 2026.
