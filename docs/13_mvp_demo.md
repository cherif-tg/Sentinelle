# MVP — chaîne de bout en bout (données synthétiques)

**Statut : vérifié le 20 octobre 2026.** Aucune donnée réelle n'est utilisée : le fichier produit
porte un avertissement explicite et l'API comme le dashboard l'affichent.

## Ce qui tourne

| Étape | Commande | Sortie |
|---|---|---|
| 1. Production des données | `python -m sentinelle_lome.pipeline.gold` (ou `make demo`) | `data/gold/risque_cellules.parquet` + `.meta.json` |
| 2. API | `make api` | `http://127.0.0.1:8000` |
| 3. Dashboard | `make dashboard` | `http://localhost:8501` |

Producteur : `src/sentinelle_lome/pipeline/gold.py`. Options : `--sortie`, `--resolution-m`
(défaut 250), `--graine`, `--scenario {moderee,extreme}`.

À 250 m sur le périmètre GAUL 2025 du Grand Lomé (414,9 km²), la commande écrit **6 644 cellules**
en une trentaine de secondes. Le contour est exporté depuis Earth Engine par
`python -m sentinelle_lome.ingestion.gee_contours` et n'est pas versionné (`data/` est ignoré) :
sans lui, la grille retombe sur le rectangle de la configuration, et le `.meta.json` l'indique
(`contour.masque = false`).

## Contrat de données

`data/gold/risque_cellules.parquet`, six colonnes, consommées telles quelles par `serving/api.py`
et `dashboard/app.py` :

- `cellule_id`, `quartier`, `lon`, `lat`, `proba_inondation`, `niveau_alerte`

`<parquet>.meta.json` documente la provenance : `source`, `avertissement`, `date_generation`,
`n_cellules`, `graine`, `resolution_m`, `scenario`, `scenario_pluie_mm`, `seuils_alerte`,
`calibration` (méthode, taille du jeu, taux de positifs observé, portée).

## Contours administratifs

L'emprise n'est plus un rectangle arbitraire : c'est le périmètre du **District autonome du Grand
Lomé**, obtenu depuis Earth Engine.

```bash
python -m sentinelle_lome.ingestion.gee_contours --dry-run          # plan, sans réseau
python -m sentinelle_lome.ingestion.gee_contours --projet-gee <id>   # export réel
```

- Source : `FAO/GAUL/2025/level2`, union des préfectures **Golfe** et **Agoè-Nyivé**.
- Sortie : `data/raw/contours/grand_lome_gaul2025.geojson` (non versionné) + `.meta.json`.
- Superficie : **414,9 km²**, calculée par Earth Engine ; le calcul local (Shapely) retrouve la même
  valeur, ce qui sert de contrôle croisé.
- La grille ne conserve que les cellules dont le centre est **à l'intérieur** du contour : 6 644
  cellules à 250 m, soit 1,001 par maille théorique.

**Limite de la source :** GAUL s'arrête au niveau 2 (préfectures). Les 13 communes du DAGL et les
quartiers n'y figurent pas — d'où le maintien de centroïdes pour les quartiers.

## Ce que valent les chiffres

- Modèle A (susceptibilité) et modèle B (déclenchement) sont entraînés sur des données
  synthétiques distinctes ; leur produit est un **indice**, pas une probabilité.
- Cet indice est ensuite **calibré** (régression isotone) sur une vérité terrain synthétique jointe
  — logit terrain de `models.susceptibilite.donnees_synthetiques` plus un terme de pluie. La valeur
  publiée est donc une probabilité **dans ce monde synthétique**, sans aucune validité sur Lomé.
- `niveau_alerte` applique `seuil_decision(cout_fausse_alerte, cout_inondation_manquee)` du YAML :
  avec le ratio provisoire 1:10, le seuil rouge vaut **0,0909** et l'orange 0,045.

**Conséquence à assumer :** un seuil à 9 % met mécaniquement une grande partie de l'emprise en
rouge — **61 % en scénario `moderee`, 76 % en `extreme`**. Ce n'est pas un défaut de calcul mais
l'effet du ratio de coûts provisoire ; il ne doit pas être lu comme une prévision.

## Vérifications réellement effectuées

- **50 tests** passent, exécutés fichier par fichier : `test_api` 7, `test_pipeline_gold` 7,
  `test_contours` 7, `test_tableau_de_bord` 9, `test_config_et_plan` 3, `test_dimensionnement` 5,
  `test_labels_et_features` 7, `test_modeles` 5.
- `ruff check src tests dashboard` : propre.
- Contour : superficie locale (414,9 km²) identique à celle d'Earth Engine ; toutes les cellules du
  fichier gold sont à l'intérieur du polygone.
- API interrogée en serveur HTTP réel (uvicorn) : `/sante` 200, `/meta` 200, `/risque/point` dans
  l'emprise 200, hors emprise (Paris) 422, `/risque/quartier/Bè` 200, quartier inconnu 404.
- Dashboard exécuté via `streamlit.testing.v1.AppTest` : zéro exception, titre, bandeau
  d'avertissement et métriques rendus.

## Limites connues

1. **Ratio de coûts provisoire** : les niveaux d'alerte ne sont pas exploitables avant arbitrage
   avec l'ANPC. C'est la première décision à prendre.
2. **Quartiers par centroïdes approximatifs** : l'emprise est désormais le vrai périmètre, mais les
   quartiers n'ont pas de polygones ; une cellule limitrophe peut être rattachée au mauvais quartier.
3. **Aucun masque eau / lagune** : des cellules situées sur l'océan ou la lagune sont comptées
   comme des quartiers.
4. **Pluie uniforme** sur l'emprise et terrain **sans autocorrélation spatiale** : le modèle B ne
   produit aucune variation spatiale, il ne fait que rééchelonner le modèle A.
5. **Modèle C (exposition) non branché** : ni bâtiments ni population dans la chaîne.
6. **Hors périmètre** : Spark/Sedona, HDFS, MLflow, docker-compose ; les exports Sentinel-1 réels
   n'ont toujours pas été lancés.
7. `make test` lance toute la suite en un appel ; sur ce poste cet appel fait échouer le harnais
   d'exécution (arbre de processus). Lancer les fichiers de test séparément.

## Prochain lot recommandé

1. Faire arbitrer `cout_fausse_alerte` / `cout_inondation_manquee` par l'ANPC, puis recalculer.
2. Remplacer les centroïdes de quartiers par une jointure sur des polygones (OSM ou données ANPC) :
   l'emprise, elle, est déjà réelle.
3. Masquer l'eau (hydrographie) avant agrégation par quartier.
4. Brancher le modèle C et la page « scénarios de pluie » du dashboard.
5. Donner au modèle B une dimension spatiale (pluie par zone) pour qu'il cesse d'être décoratif.
