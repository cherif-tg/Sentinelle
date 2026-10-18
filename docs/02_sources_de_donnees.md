# 02 — Catalogue des sources de données

| Source | Contenu | Accès | Licence | Statut |
|---|---|---|---|---|
| Sentinel-1 GRD | Radar C-band VV/VH, 10 m, tout temps | Earth Engine, collection `COPERNICUS/S1_GRD` | À vérifier | Collection confirmée, réf. 8 |
| Sentinel-2 | Optique 10-20 m (occupation du sol, indices) | Earth Engine, collection `COPERNICUS/S2_SR_HARMONIZED` | À vérifier | Collection standard Earth Engine ; référence d'usage sur le Togo à ajouter (réf. 9) |
| Open Buildings v3 | 1,8 milliard de détections, polygones avec score de confiance ; pas de type de bâtiment | Earth Engine et buckets GCS (partition par cellule S2 niveau 4) | À vérifier | [VÉRIFIÉ, réf. 6] |
| OpenStreetMap (HOT) | Points d'intérêt, routes, bâti | Export HDX | Selon l'export (à vérifier) | [VÉRIFIÉ pour l'existence, réf. 10 ; URL à confirmer] |
| Grilles de population | Densité et estimations démographiques | HDX | Millésime et licence à vérifier | [VÉRIFIÉ pour l'existence, réf. 11 ; URL à confirmer] |
| Pluie satellitaire | CHIRPS (`UCSB-CHG/CHIRPS/DAILY`) et/ou IMERG (`NASA/GPM_L3/IMERG_V07`) | Earth Engine | À vérifier | [À CONFIRMER] : latence et résolution à tester sur Lomé |
| MNT 30 m | Altitude ; dérivés : pente, HAND, distance au drain | Copernicus GLO-30 (`COPERNICUS/DEM/GLO30`) ou autre | À vérifier | [À CONFIRMER] : choix et qualité sur zone plate |
| Contours d'inondation Charte | Emprises observées 2020 et 2026 | Charte, HOT | À obtenir | [À CONFIRMER] : accès public non établi |
| Drones ANPC / Togo Flying Labs | Cartes d'inondation à haute résolution | Contact institutionnel | À négocier | [À CONFIRMER] |
| Limites administratives (quartiers) | Polygones des quartiers du Grand Lomé | HDX ou ANPC | À vérifier | [À CONFIRMER] |

## Règles de gestion des données

- Aucune donnée brute dans Git : tout va dans `data/` (ignoré), avec un `manifest` de provenance (URL, date de téléchargement, version).
- Chaque jeu conserve sa licence et sa citation dans `12_references.md`.
- Toute donnée personnelle (adresses, numéros de téléphone d'abonnés aux alertes) est stockée séparément et jamais versionnée.
