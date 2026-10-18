"""Session Spark (avec Sedona en option). NON TESTÉ dans l'environnement de génération."""
from __future__ import annotations

import os


def creer_session(nom: str = "sentinelle-lome", master: str | None = None, avec_sedona: bool = True):
    from pyspark.sql import SparkSession

    builder = SparkSession.builder.appName(nom)
    if master:
        builder = builder.master(master)
    if avec_sedona:
        builder = builder.config("spark.serializer", "org.apache.spark.serializer.KryoSerializer").config(
            "spark.kryo.registrator", "org.apache.sedona.core.serde.SedonaKryoRegistrator"
        )
        paquets = os.getenv("SL_SEDONA_PACKAGES", "")  # coordonnées Maven à épingler (voir docs/03)
        if paquets:
            builder = builder.config("spark.jars.packages", paquets)
    spark = builder.getOrCreate()
    if avec_sedona:
        from sedona.spark import SedonaContext

        spark = SedonaContext.create(spark)
    return spark
