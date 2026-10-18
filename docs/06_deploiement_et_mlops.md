# 06 — Déploiement et MLOps

## Chaîne de service [PROPOSITION]

1. **Lot nocturne ou déclenché par la pluie** : recalcul des variables, inférence, écriture de `gold/risque_cellules.parquet`.
2. **API FastAPI** (`serving/api.py`) : `/sante`, `/risque/point`, `/risque/quartier/{nom}`.
3. **Dashboard Streamlit** (`dashboard/app.py`).
4. **MLflow** : suivi des essais et registre des modèles.
5. **Docker Compose** : HDFS, Spark, MLflow, API, dashboard (point de départ, **non testé**).

## Suivi en production

- Santé du flux de pluie (retards, valeurs manquantes).
- Dérive des variables d'entrée.
- Comparaison prévu / observé après chaque événement.
- Journal des alertes émises et des retours terrain.

## Version de démonstration publique

Dashboard avec données agrégées uniquement (pas d'adresses, pas de numéros). Hébergement léger possible (par exemple un Space Hugging Face, déjà utilisé pour d'autres démos) [PROPOSITION].

## Contraintes locales à prendre en compte

- Connexion intermittente : privilégier SMS et WhatsApp pour les alertes, et un tableau de bord léger.
- Ressources limitées : échantillons et mini-cluster pour le développement.
