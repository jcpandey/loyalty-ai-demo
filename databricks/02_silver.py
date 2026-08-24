from pyspark.sql import functions as F
from pyspark.sql.window import Window

bronze_table = "loyalty_demo.bronze.loyalty_events"
silver_table = "loyalty_demo.silver.loyalty_events"
quarantine_table = "loyalty_demo.silver.loyalty_events_quarantine"

bronze = spark.table(bronze_table)

prepared = (
    bronze.withColumn("event_ts", F.to_timestamp("event_timestamp"))
    .withColumn("points", F.col("points").cast("long"))
    .withColumn("amount_aud", F.col("amount_aud").cast("decimal(18,2)"))
    .withColumn("event_date", F.to_date("event_ts"))
    .withColumn(
        "is_valid",
        F.col("event_id").isNotNull()
        & F.col("member_id").isNotNull()
        & F.col("event_ts").isNotNull()
        & F.col("event_type").isin(
            "POINTS_EARNED", "POINTS_REDEEMED", "POINTS_ADJUSTED"
        )
        & F.col("points").isNotNull(),
    )
)

valid = prepared.filter("is_valid = true")
invalid = prepared.filter("is_valid = false")

window = Window.partitionBy("event_id").orderBy(F.col("_bronze_loaded_at").desc())

deduplicated = (
    valid.withColumn("_row_number", F.row_number().over(window))
    .filter("_row_number = 1")
    .drop("_row_number", "is_valid")
)

(
    deduplicated.write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(silver_table)
)

(
    invalid.drop("is_valid").write.format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(quarantine_table)
)
