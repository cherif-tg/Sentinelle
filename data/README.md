# data/

Aucune donnée n'est versionnée (voir `.gitignore`). Zones attendues :

- `raw/` : exports bruts (GeoTIFF Sentinel-1, CSV bâtiments, pluie).
- `bronze/` : tables Parquet brutes.
- `silver/` : cellules, variables, pluie quotidienne, étiquettes.
- `gold/` : sorties de modèle (`risque_cellules.parquet`).

Tenir un fichier `manifest.csv` (source, URL, date de téléchargement, version, licence) pour chaque jeu ajouté.
