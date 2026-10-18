# 09 — Planning (10 semaines) [PROPOSITION]

| Semaine | Objectif | Livrable |
|---|---|---|
| 1 | Vérifications (`11_...`), emprise, grille, dépôt ; notebooks 01 et 03 (mesures réelles) | Checklist remplie, emprise fixée, `verifications_ee.json` |
| 2-3 | Ingestion Earth Engine → HDFS ; étiquettes radar (notebook 02, partie réelle) | `raw/` et `silver/labels_inondation` |
| 4 | Variables Spark/Sedona, tables silver | `silver/cellules_features`, `pluie_quotidienne` |
| 5-6 | Modèles A et B, références simples | Notebooks et rapports d'évaluation |
| 7 | Modèle C, test hors temps (juin 2026) | Résultats d'exposition |
| 8 | MLflow, API, Docker Compose | Services démarrables |
| 9 | Dashboard | Application complète |
| 10 | Rapport, démo, prototype d'alertes | Dépôt final |

**Jalon de décision (fin semaine 1)** : si les contours d'inondation et la pluie ne sont pas exploitables, basculer sur une version 100 % open data avec étiquettes radar seules.
