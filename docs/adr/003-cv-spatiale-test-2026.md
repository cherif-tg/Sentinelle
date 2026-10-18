# ADR 003 — Validation croisée spatiale et test hors temps sur juin 2026

- **Statut** : proposé
- **Contexte** : les cellules voisines sont fortement corrélées ; une validation aléatoire surestimerait les performances.
- **Décision** : validation croisée par blocs spatiaux (`GroupKFold`) et test hors temps sur l'épisode de juin 2026, jamais utilisé pour l'entraînement ni le réglage.
- **Conséquences** : estimations plus honnêtes, mais peu de positifs par pli ; les plis sans positif sont ignorés et leur nombre est rapporté.
