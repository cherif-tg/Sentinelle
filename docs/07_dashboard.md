# 07 — Spécification du tableau de bord

| Page | Contenu | Données |
|---|---|---|
| Carte de risque | Probabilité par cellule, couche bâtiments, filtre par quartier | `gold/risque_cellules` |
| Scénarios de pluie | Curseur en mm : bâtiments et population exposés par quartier | Modèles B et C |
| Historique | Emprise observée contre emprise prédite (2020, 2026) | `silver/labels_inondation` + prédictions |
| Qualité et limites | Incertitude, étiquettes écartées, biais de sous-détection urbaine | Rapports d'évaluation |

## Règles de conception [PROPOSITION]

- Toujours afficher l'incertitude et la date de calcul.
- Aucune couleur seule pour porter l'information (ajouter libellés et légendes).
- Libellés en français ; options éwé et kabiyè pour les messages d'alerte.
- Mention visible : « Prototype, à valider par l'ANPC avant toute diffusion ».
