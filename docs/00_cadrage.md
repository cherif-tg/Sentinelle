# 00 — Cadrage du projet

**Légende des statuts utilisée dans tous les documents**
- **[VÉRIFIÉ]** : fait confirmé par une source citée dans `12_references.md`.
- **[À CONFIRMER]** : information plausible mais non vérifiée ; à traiter dans `11_verifications_semaine1.md`.
- **[PROPOSITION]** : choix de conception de l'équipe, pas un fait.

## 1. Problème

Chaque saison des pluies, des quartiers du Grand Lomé sont inondés. Les cartes de danger existantes reposent surtout sur une approche SIG multicritère [VÉRIFIÉ, réf. 3]. Il manque un outil **entraîné sur des observations**, qui relie la pluie au risque par quartier et chiffre l'exposition du bâti.

## 2. Question métier

> Pour une pluie donnée, quels quartiers du Grand Lomé sont inondés, combien de bâtiments et de personnes sont exposés, et à partir de quel seuil faut-il alerter ?

## 3. Utilisateurs et parties prenantes

| Acteur | Rôle dans le projet | Statut |
|---|---|---|
| ANPC (Agence nationale de la protection civile) | Utilisateur cible ; a déjà demandé l'activation de la Charte internationale pour Lomé (activation n°1037) | [VÉRIFIÉ, réf. 1] |
| Togo Flying Labs | Cartographie par drone de 17 sites inondés avec l'ANPC ; source possible de validation terrain | [VÉRIFIÉ, réf. 4] |
| Mairies du Grand Lomé | Relais d'alerte et de prévention | [PROPOSITION] |
| Population des quartiers exposés | Destinataire final des alertes | [PROPOSITION] |

## 4. Livrables

1. Pipeline Big Data reproductible (Earth Engine → HDFS → Spark/Sedona → Parquet).
2. Catalogue d'événements et jeu d'étiquettes avec niveau de confiance.
3. Trois modèles : susceptibilité, déclenchement par la pluie, exposition.
4. API de risque et tableau de bord interactif.
5. Chaîne d'alertes multilingue avec validation humaine.
6. Rapport, démo et dépôt documenté.

## 5. Hors périmètre (version 1)

- Prévision hydrodynamique physique (modèle hydraulique de réseau de drainage).
- Alerte automatique sans validation de l'ANPC.
- Estimation de dommages monétaires.

## 6. Critères de réussite

Les valeurs cibles ne sont **pas** fixées à l'avance : elles le seront après la mesure des références simples (seuil HAND, carte multicritère existante).

- Le modèle A dépasse nettement la référence HAND en validation croisée spatiale.
- Le test hors temps sur juin 2026 est reporté tel quel, y compris s'il est mauvais.
- Le pipeline se relance de bout en bout avec `make` sur un échantillon.
- Chaque affirmation du rapport renvoie à une source ou à une mesure.
