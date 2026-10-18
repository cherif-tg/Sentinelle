# 05 — Modélisation

## Modèle A — susceptibilité (statique) [PROPOSITION]

- **Cible** : cellule inondée (haute confiance) ou fréquence d'eau observée.
- **Variables** : `hand_m, pente_deg, altitude_m, dist_drain_m, densite_bati` ; extensions possibles : occupation du sol, indice de surface imperméable.
- **Modèle** : gradient boosting (`HistGradientBoostingClassifier` ; LightGBM possible).
- **Références** : seuil HAND simple, régression logistique, carte multicritère existante (réf. 3).
- Code : `sentinelle_lome/models/susceptibilite.py`.

## Modèle B — déclenchement par la pluie [PROPOSITION]

- **Variables** : cumuls 1, 3, 7 jours (`processing/features.py`), indice de pluie antérieure `API_t = k·API_{t-1} + P_t`.
- **Cible** : quartier ou bassin inondé lors de l'épisode.
- **Contrainte de monotonie** : plus de pluie ne peut pas diminuer la probabilité.
- **Seuil d'alerte** : pour des probabilités calibrées, alerter si `p > c_fa / (c_fa + c_manque)` (`models/declenchement.py`). Les coûts relatifs se fixent **avec l'ANPC**.
- **Limite** : peu d'événements, donc peu de positifs. L'annoncer.

## Modèle C — exposition [PROPOSITION]

- Jointure bâtiments (Open Buildings, filtrés par confiance) × probabilité de la cellule.
- Sorties par quartier : bâtiments au-dessus du seuil, nombre attendu (somme des probabilités), population exposée via les grilles HDX.
- Open Buildings ne fournit pas le type de bâtiment [VÉRIFIÉ, réf. 6] : on s'en tient à des comptes et des surfaces, sans indice de vulnérabilité inventé.
- Code : `models/exposition.py`.

## Protocole d'évaluation

| Élément | Choix |
|---|---|
| Découpage | Validation croisée **spatiale** par blocs de `taille_bloc_m` (`models/spatial_cv.py`, `GroupKFold`) |
| Test hors temps | Entraînement sur ≤ 2025, test sur l'épisode de juin 2026 |
| Métriques | PR-AUC (classes déséquilibrées), rappel à précision fixée, IoU sur l'emprise, Brier / calibration, erreur sur le nombre de bâtiments exposés |
| Références | Seuil HAND, carte multicritère, logistique |
| Rapport | Résultats bruts, y compris défavorables ; intervalles par pli |

## Pièges à éviter

- Fuite spatiale (cellules voisines entre entraînement et test) : d'où les blocs.
- Fuite temporelle (pluie future dans les variables).
- Optimiser sur la même crue que le test.
- Présenter une probabilité non calibrée comme un risque.
