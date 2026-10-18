# ADR 001 — HDFS + Parquet en zones raw / bronze / silver / gold

- **Statut** : proposé
- **Contexte** : le projet doit démontrer une chaîne Big Data (Hadoop, Spark) avec des tables cellule × date potentiellement très volumineuses.
- **Décision** : stocker sur HDFS, convertir en Parquet partitionné, organiser en zones raw, bronze, silver, gold.
- **Conséquences** : lecture colonnaire efficace sous Spark ; reproductibilité par zone. En nœud unique, HDFS apporte surtout la démonstration de l'architecture, pas le gain de performance : à dire dans le rapport.
- **Alternative écartée** : fichiers locaux seuls (plus simples, mais ne montrent pas la chaîne Hadoop).
