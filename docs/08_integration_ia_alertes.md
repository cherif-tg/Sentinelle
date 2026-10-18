# 08 — Piste d'intégration IA : alertes multilingues

## Principe [PROPOSITION]

Les **décisions** (seuils, niveaux d'alerte) viennent des modèles et des règles. Un LLM ne fait que **rédiger** un message à partir de champs structurés (quartier, niveau, heure, consigne), avec des gabarits où les chiffres sont insérés par le code, jamais générés.

## Chaîne

1. Le modèle B produit `niveau_alerte` par quartier.
2. Un gabarit validé par l'ANPC fixe le contenu minimal (quoi, où, quand, que faire).
3. Le LLM reformule en français simple, puis en éwé et en kabiyè.
4. Relecture par des locuteurs avant toute diffusion.
5. Validation humaine ANPC.
6. Envoi par SMS ou WhatsApp.
7. Un formulaire terrain (ex. KoboToolbox) rapatrie les retours et alimente de nouvelles étiquettes.

## Garde-fous

- Aucune alerte automatique sans validation humaine.
- Évaluation de la qualité des traductions par des locuteurs natifs, avec un échantillon test fixe.
- Journal de toutes les alertes et corrections.
- Gabarit de secours en français si la traduction échoue.
