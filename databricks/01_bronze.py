from pyspark.sql.functions import current_timestamp
from pyspark.sql.types import (
    DoubleType,
    LongType,
    MapType,
    StringType,
    StructField,
    StructType,
)

source_path = "s3://loyalty-ai-demo-829742257446-ap-southeast-2/landing/events/"
checkpoint_path = "s3://loyalty-ai-demo-829742257446-ap-southeast-2/checkpoints/bronze/loyalty_events/"
schema_path = "s3://loyalty-ai-demo-829742257446-ap-southeast-2/schemas/bronze/loyalty_events/"
target_table = "loyalty_demo.bronze.loyalty_events"

schema = StructType([
    StructField("event_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("event_version", StringType(), True),
    StructField("event_timestamp", StringType(), True),
    StructField("member_id", StringType(), True),
    StructField("partner_id", StringType(), True),
    StructField("transaction_id", StringType(), True),
    StructField("points", LongType(), True),
    StructField("amount_aud", DoubleType(), True),
    StructField("channel", StringType(), True),
    StructField("source_system", StringType(), True),
    StructField("trace_id", StringType(), True),
    StructField("attributes", MapType(StringType(), StringType()), True),
    StructField("_kinesis_sequence_number", StringType(), True),
    StructField("_kinesis_partition_key", StringType(), True),
    StructField("_ingested_at", StringType(), True),
])

bronze_stream = (
    spark.readStream.format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", schema_path)
    .option("cloudFiles.includeExistingFiles", "true")
    .schema(schema)
    .load(source_path)
    .selectExpr("*", "_metadata.file_path as _source_file")
    .withColumn("_bronze_loaded_at", current_timestamp())
)

query = (
    bronze_stream.writeStream.format("delta")
    .option("checkpointLocation", checkpoint_path)
    .option("mergeSchema", "true")
    .trigger(availableNow=True)
    .toTable(target_table)
)

query.awaitTermination()
