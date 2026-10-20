# 15 — Guide du tableau de bord

Le tableau de bord est fait pour **explorer un raisonnement**, pas pour lire une prévision : il
montre comment le nombre de communes en alerte dépend d'un choix de coûts, sur des données
synthétiques.

## Lancer

```powershell
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py
```

Ou `make dashboard` (voir les équivalents PowerShell dans le README). Le dashboard lit
`data/gold/risque_cellules.parquet` et son `.meta.json` ; sans fichier, il affiche la commande à
lancer (`python -m sentinelle_lome.pipeline.gold`).

## Trois étapes

1. **Régler le ratio de coûts** dans la barre latérale : coût d'une fausse alerte contre coût d'une
   inondation manquée. Le seuil rouge en découle et toute la page se recalcule.
2. **Filtrer par quartier** si nécessaire ; « (tous) » conserve l'emprise entière.
3. **Parcourir les quatre onglets** : Carte, Seuils d'alerte, Quartiers, Données et méthode.

## Le seuil, et pourquoi il change tout

Le seuil rouge n'est pas une constante physique, c'est une décision :

```text
seuil = coût_fausse_alerte / (coût_fausse_alerte + coût_inondation_manquée)
```

Avec 1 contre 10, le seuil vaut 0,091 : une cellule à 10 % de probabilité déclenche l'alerte. Ce
réglage produit **beaucoup** de rouge sur un épisode fort — c'est le comportement attendu d'une
politique qui préfère alerter à tort, pas un défaut d'affichage.

La case **Forcer un seuil manuel** coupe ce calcul pour explorer librement. Elle ne modifie jamais
le fichier de risque.

## Les quatre onglets

| Onglet | Ce qu'il montre | Comment le lire |
|---|---|---|
| Carte | Une cellule par point, colorée selon le seuil courant, sur le tracé du territoire | Survoler pour le quartier et la probabilité ; la répartition chiffrée est sous la carte |
| Seuils d'alerte | Distribution des probabilités et courbe de sensibilité | La ligne verticale est le seuil ; le point rouge rappelle la position actuelle |
| Quartiers | Part de cellules en rouge par quartier, triée | 100 % signifie « toutes les cellules atteignent le seuil », pas « quartier entièrement inondé » |
| Données et méthode | Aperçu des cellules, export CSV, provenance, limites | Le bouton d'export restitue exactement la vue filtrée |

## Indicateurs affichés

| Indicateur | Définition exacte |
|---|---|
| Cellules au-dessus du seuil rouge | Nombre et part des cellules dont `proba_inondation >= seuil_rouge` |
| Probabilité moyenne | Moyenne de `proba_inondation` sur la vue ; sensible aux extrêmes |
| Probabilité maximale | Cellule la plus exposée de la vue |
| Quartiers avec au moins une cellule rouge | Un quartier compte dès qu'une cellule atteint le seuil |

Les niveaux sont **recalculés à l'affichage** : la colonne `niveau_alerte` du fichier correspond aux
seuils utilisés lors de sa génération, et peut donc différer de ce que montre l'écran.

## Ce qu'il ne faut pas conclure

- Les valeurs ne décrivent pas le risque réel à Lomé : elles sont synthétiques.
- Le ratio de coûts est arbitraire, faute de barème ANPC.
- Les quartiers viennent de centroïdes approximatifs, pas de contours administratifs : une cellule
  limitrophe peut changer de quartier.
- Les cellules situées sur la lagune ou l'océan ne sont pas masquées.
- La pluie est uniforme : le modèle de déclenchement ne produit aucune variation spatiale.

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| « Aucune donnée de risque trouvée » | Fichier gold absent | `python -m sentinelle_lome.pipeline.gold` |
| Page blanche / erreur d'import | Dépendances dashboard absentes | `uv pip install --python .venv\Scripts\python.exe -e ".[dashboard]"` |
| Port déjà utilisé | Autre instance Streamlit | `--server.port 8502` |
| Chiffres différents du fichier | Seuil ou filtre modifié | Réinitialiser le ratio (1 contre 10) et le quartier sur « (tous) » |
