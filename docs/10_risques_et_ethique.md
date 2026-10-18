# 10 — Risques et éthique

## Risques techniques

| Risque | Probabilité / impact | Parade |
|---|---|---|
| Étiquettes radar bruitées en ville | Élevé | Masque HAND, concordance des passes, validation drone |
| Peu d'événements étiquetés | Élevé | Test hors temps, intervalles, pas de promesse de précision |
| Pluie disponible trop tard | Moyen | Comparer CHIRPS et IMERG, documenter la latence |
| Accès institutionnel retardé | Moyen | Version open data seule |
| Infrastructure locale insuffisante | Moyen | Échantillons, nœud unique, calculs raster dans Earth Engine |

## Éthique et responsabilité

- **Fausses alertes et alertes manquées** ont des coûts différents : les rendre explicites et fixer le seuil avec l'ANPC.
- **Pas de ciblage individuel** : résultats agrégés par cellule et quartier, sans adresse.
- **Communication de l'incertitude** : probabilités calibrées, limites affichées.
- **Données personnelles** (abonnés aux alertes) : stockage séparé, minimisation, accord de consentement.
- **Équité** : vérifier que la détection n'est pas moins bonne dans les quartiers denses (biais radar urbain) et le dire.
- **Licences** des données : vérifier et citer avant publication.
