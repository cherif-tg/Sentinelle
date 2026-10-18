# 04 — Méthodologie des étiquettes d'inondation

Les étiquettes sont le point le plus fragile du projet : elles viennent d'une détection radar, pas d'un relevé terrain.

## Principe [PROPOSITION]

Détection de changement entre une scène « avant » et une scène « après » l'événement, en dB :
eau si la baisse de rétrodiffusion dépasse un seuil **et** si la valeur post-événement est basse. Implémentation : `sentinelle_lome/labels/flood_labels.py`. Les seuils par défaut (−3 dB de variation, −15 dB en valeur absolue) sont des **points de départ à calibrer** sur Lomé, pas des valeurs validées.

## Limites documentées [VÉRIFIÉ]

- La détection radar est difficile en zone urbaine dense, sur eau agitée par le vent et sous couvert végétal (réf. 8).
- À Dar es Salaam, les inondations sur routes et chaussées n'ont pas pu être détectées avec Sentinel-1 (réf. 12).
- Les surfaces urbaines touchées semblent sous-estimées dans les études urbaines consultées (réf. 13 ; à revérifier dans le texte avant citation).
- Le HAND (hauteur au-dessus du drainage le plus proche) réduit les fausses détections en terrain surélevé (réf. 14).

**Conséquence :** les étiquettes ont un biais de sous-détection en ville dense. Il doit figurer dans les limites du rapport.

## Unités des données Sentinel-1 [À CONFIRMER]

Les valeurs de `COPERNICUS/S1_GRD` sont censées être déjà en **dB** dans Earth Engine : à vérifier sur la fiche de la collection avant tout calcul. Si c'est le cas, ne pas réappliquer `vers_db` aux exports, et noter que le composite médian de `gee_export.py` est calculé sur ces valeurs en dB.

## Illustration et calibration

Le notebook `notebooks/02_etiquettes_radar.ipynb` illustre la méthode sur une scène **fictive** (effet du HAND, sensibilité aux seuils, concordance des passes) et donne la procédure de calibration sur les vraies scènes. Ses scores ne prouvent rien sur Lomé.

## Protocole [PROPOSITION]

1. **Catalogue d'événements** : trois épisodes vérifiés (`configs/evenements.yaml`), complétés par les dates radar suivant les plus fortes pluies détectées.
2. **Deux passes** (ascendante et descendante) : étiquette « haute confiance » si les deux concordent (`concordance_passes`), « moyenne » si une seule détecte.
3. **Masque HAND** : écarter les pixels au-dessus de `hand_max_m`.
4. **Négatifs** : cellules non inondées aux mêmes dates, et dates radar sans épisode pluvieux.
5. **Validation ponctuelle** par les cartes drone de l'ANPC et de Togo Flying Labs si elles sont accessibles, et par les contours de la Charte.
6. **Entraînement sur la haute confiance** ; la confiance moyenne sert à tester la sensibilité.

## À mesurer avant de modéliser

- Nombre d'événements réellement étiquetables et nombre de positifs.
- Fréquence des passes Sentinel-1 sur Lomé aux dates concernées.
- Taux d'accord entre passes ascendante et descendante.
