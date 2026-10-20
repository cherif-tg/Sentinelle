# 14 — Plan des prochaines étapes

Rédigé le 20 octobre 2026, après la livraison du MVP technique (`docs/13_mvp_demo.md`).

## Où en est le projet

| Acquis | Preuve |
|---|---|
| Chaîne `production → API → dashboard` exécutable | 6 644 cellules générées, API interrogée en HTTP réel, dashboard exécuté sans exception |
| Emprise réelle du Grand Lomé | GAUL 2025 (Golfe + Agoè-Nyivé) : 414,9 km², grille masquée sur le contour |
| Quartiers géoréférencés | 69 polygones OSM (admin_level=10), couvrant 21,3 % du district |
| 55 tests, lint propre | exécutés fichier par fichier ; CI GitHub Actions en place (Python 3.11) |

**État de la branche :** `phase-2-dashboard` fusionnée dans `main` le 20 octobre 2026
(fusion `0a2f264`), après passage des 55 tests et du lint sur `main`.

## Avancement des lots

| Lot | État | Reste à faire |
|---|---|---|
| 0 — Vérifications | partiel | Contours de la Charte : tranché (inaccessibles → open data). Restent CHIRPS/IMERG, passes S1, contact ANPC |
| 1 — Données réelles | partiel | Contours et quartiers faits. Restent exports Sentinel-1, pluie, MNT, bâti |
| 2 à 6 | non commencés | — |
| Modèles A et B entraînables et évaluables | tests unitaires sur données synthétiques uniquement |

**Ce que le MVP ne prouve pas : rien sur Lomé.** Aucune donnée réelle n'a été traitée, aucun score de
modèle n'a de valeur. Le MVP a sécurisé la plomberie, pas la science.

**Le vrai goulot n'est pas le code.** Les 16 vérifications de `docs/11_verifications_semaine1.md`
sont toujours décochées : accès aux contours de la Charte, passes Sentinel-1 réellement
disponibles, choix CHIRPS/IMERG, contours administratifs, contacts ANPC. Tant qu'elles ne sont pas
faites, tout développement supplémentaire tourne à vide.

## Trois décisions bloquantes (avant d'écrire du code)

| Décision | Qui décide | Conséquence si non tranchée |
|---|---|---|
| Ratio de coûts d'alerte (`cout_fausse_alerte` / `cout_inondation_manquee`) | ANPC | Les niveaux restent à 61 % de rouge : inutilisables |
| Emprise officielle du Grand Lomé + polygones de quartiers | ANPC / OSM | Les quartiers restent des centroïdes approximatifs |
| Accès aux contours d'inondation (Charte n°1037 et septembre 2020) + produit de pluie retenu | Vous + ANPC / HOT | Sans étiquettes réelles, les modèles A et B restent des démonstrations |

## Séquence proposée

| Lot | Objectif | Durée | Dépend de |
|---|---|---|---|
| 0 | Boucler les vérifications de `docs/11` | 3-4 j | — |
| 1 | Données réelles minimales (S1, pluie, MNT, bâti) | 1,5 sem | Lot 0 |
| 2 | Étiquettes radar + modèle A sur données réelles | 2,5 sem | Lot 1 |
| 3 | Modèle B + calibration réelle | 2 sem | Lot 2 |
| 4 | Modèle C + service à 30 m sur contours réels | 2 sem | Lots 1-3 |
| 5 | MLOps et infrastructure (conditionnel) | 1 sem | Lot 4 |
| 6 | Alertes multilingues | hors périmètre actuel | Validation ANPC |

Total ≈ 9 à 10 semaines, cohérent avec `docs/09_planning.md`, mais **re-basé** : le MVP occupe la
place des semaines 8-9 (API, Docker), tandis que les semaines 1 à 3 restent entièrement à faire.

### Lot 0 — Vérifications (3-4 jours)

Cocher et dater chaque ligne de `docs/11_verifications_semaine1.md`. Points rédhibitoires :

- Passes Sentinel-1 réellement disponibles à Lomé aux dates des événements (notebook 01, section 3).
- Contours de la Charte téléchargeables, avec licence.
- CHIRPS ou IMERG : trancher sur la latence et la résolution, pas sur la préférence.

**Critère de sortie :** checklist remplie, emprise fixée dans `configs/projet.yaml`.

### Lot 1 — Données réelles minimales (1,5 semaine)

Exports S1 aux dates d'événements, MNT GLO-30, pluie quotidienne, bâtiments Open Buildings filtrés
(`seuil_confiance` 0,7, `surface_min_m2` 10).

**Livrables :** `data/raw/` + `manifest.csv` (source, URL, date, licence), `silver/cellules_features`,
`silver/pluie_quotidienne`.

**Critère d'acceptation :** une seule commande rejoue l'ingestion ; le manifest est complet ; le
nombre de cellules à 30 m est proche de **461 000** (voir dimensionnement ci-dessous).

### Lot 2 — Étiquettes radar et modèle A (2,5 semaines)

Calibrer `seuil_delta_db`, `seuil_post_db`, `hand_max_m` sur scènes réelles ; mesurer la concordance
ascendant/descendant ; traiter le bruit en ville dense. Entraîner A avec CV spatiale (blocs 2 km,
5 plis) **contre une baseline SIG multicritère** — c'est la comparaison qui justifie le ML.

**Critère d'acceptation :** PR-AUC et Brier par pli, comparaison explicite à la baseline, test
anti-fuite spatiale, et un verdict écrit : le ML apporte-t-il quelque chose ?

### Lot 3 — Modèle B et calibration réelle (2 semaines)

Événements réels (juin 2026, septembre 2020), monotonie conservée, **courbe de fiabilité mesurée**
au lieu de la calibration isotone synthétique actuelle. Le seuil de coût ne s'applique qu'à une
probabilité dont la calibration est établie sur données réelles.

**Critère d'acceptation :** diagramme de fiabilité, Brier, et remplacement de `jeu_calibration`
synthétique par une calibration sur données observées.

### Lot 4 — Modèle C et service à 30 m (2 semaines)

Exposition bâti + population par quartier avec incertitude ; masque eau/lagune ; contours
administratifs réels ; passage de la grille de 250 m à 30 m ; page « scénarios de pluie ».

**Critère d'acceptation :** chiffres d'exposition reproductibles par quartier, API et dashboard
servis sur données réelles, avertissements de provenance adaptés.

### Lot 5 — MLOps et infrastructure (1 semaine, conditionnel)

MLflow et versioning des modèles (les colonnes `date_calcul` et `version_modele` sont déjà prévues
par `docs/03_architecture.md`). Pour Spark et `docker-compose.yml` : décider, ne pas empiler.

### Lot 6 — Alertes (après validation ANPC)

Protocole de diffusion, validation humaine obligatoire, langues (français, éwé, mina). Aucun envoi
automatique sans validation tracée. À n'ouvrir qu'une fois les seuils arbitrés.

## Dimensionnement : ce que le passage à 30 m change

Calculé avec `src/sentinelle_lome/dimensionnement.py` sur le périmètre GAUL 2025 (414,9 km²) :

| Résolution | Cellules | Commentaire |
|---|---|---|
| 250 m | ~6 638 | taille du MVP actuel |
| 30 m | ~461 000 | tient en mémoire pour une date |
| 10 m | ~4 150 000 | résolution radar ; à éviter hors besoin |

Table cellule × jour à 30 m sur un an : **168 millions de lignes, 10,8 Go brut**. C'est seulement à
cette échelle que Spark et Sedona se justifient — pas pour une seule date. Conclusion : garder
pandas pour la table de cellules, et n'ouvrir le chantier Spark qu'au moment de la table temporelle.

## À ne pas commencer maintenant

1. **Spark, HDFS, docker-compose** : aucun volume ne le justifie encore ; l'ADR 001 le dit déjà.
2. **Alertes multilingues** : sans seuils validés, elles diffuseraient du bruit.
3. **Optimisation des modèles** : les régler sur données synthétiques n'apprend rien de Lomé.
4. **Nouvelles fonctionnalités du dashboard** : il y a déjà plus d'interface que de données.

## Quick wins (cette semaine, sans données)

- Vérifier le run CI du commit `fe8df68` dans l'onglet Actions (Python 3.11, `pytest -q`).
- Ajouter un test de reproductibilité : même graine ⇒ même Parquet (aujourd'hui non vérifié).
- Cible `make test-file` qui lance les tests fichier par fichier (la suite complète casse le
  harnais d'exécution sous Windows).
- Ajouter `.gitattributes` pour figer les fins de ligne et faire taire les avertissements CRLF.

## Jalons de décision

| Jalon | Question | Si la réponse est non |
|---|---|---|
| J1 (fin lot 1) | Les contours de la Charte sont-ils exploitables ? | Bascule open data prévue par `docs/09_planning.md` : étiquettes radar seules |
| J2 (fin lot 2) | Le modèle A bat-il la baseline SIG ? | Le dire, publier la baseline, simplifier l'architecture |
| J3 (fin lot 4) | La démo sur données réelles tient-elle ? | Ne pas diffuser ; rester en prototype documenté |
