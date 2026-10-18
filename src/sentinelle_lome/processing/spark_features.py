"""Variables de pluie (version Spark). NON TESTÉ dans l'environnement de génération."""
from __future__ import annotations


def cumuls_pluie_spark(df, fenetres=(1, 3, 7), col_zone="zone_id", col_date="date", col_mm="pluie_mm"):
    """Cumuls glissants par zone via fenêtres sur plage de temps (jours calendaires)."""
    from pyspark.sql import Window
    from pyspark.sql import functions as F

    df = df.withColumn("_ts", F.col(col_date).cast("timestamp").cast("long"))
    for n in fenetres:
        w = Window.partitionBy(col_zone).orderBy("_ts").rangeBetween(-(n - 1) * 86400, 0)
        df = df.withColumn(f"pluie_cumul_{n}j", F.sum(col_mm).over(w))
    return df.drop("_ts")
