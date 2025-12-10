import os
import sys
import json

# --- CONFIG WINDOWS ---
os.environ['PYSPARK_PYTHON'] = sys.executable
os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable
hadoop_path = os.getcwd() + "\\hadoop"
os.environ['HADOOP_HOME'] = hadoop_path
os.environ['hadoop.home.dir'] = hadoop_path
os.environ['PATH'] += os.pathsep + hadoop_path + "\\bin"
# ----------------------

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
# IMPORT DE DoubleType (C'est la clé du fix)
from pyspark.sql.types import StringType, StructType, DoubleType 
from textblob import TextBlob
from pymongo import MongoClient

# 1. Connexion Mongo
try:
    mongo_client = MongoClient("mongodb://localhost:27017/")
    db = mongo_client["twitter_db"]
    collection = db["sentiments"]
    print("--- Connexion MongoDB OK ---")
except Exception as e:
    print(f"--- Erreur Mongo: {e} ---")

# 2. Init Spark
spark = SparkSession.builder \
    .appName("TwitterSentimentAnalysis") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0") \
    .config("spark.sql.warehouse.dir", "file:///C:/tmp") \
    .getOrCreate()
spark.sparkContext.setLogLevel("WARN")

# 3. Fonction Sentiment
def get_sentiment(text):
    if not text: return "NEUTRE"
    try:
        analysis = TextBlob(text)
        if analysis.sentiment.polarity > 0: return "POSITIF"
        elif analysis.sentiment.polarity < 0: return "NEGATIF"
        else: return "NEUTRE"
    except: return "NEUTRE"

sentiment_udf = udf(get_sentiment, StringType())

# 4. Lecture Kafka
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "twitter_stream") \
    .option("startingOffsets", "latest") \
    .load()

# 5. Traitement
# ICI : On utilise DoubleType() pour le timestamp (plus précis que Float)
schema = StructType() \
    .add("text", StringType()) \
    .add("topic", StringType()) \
    .add("timestamp", DoubleType()) 

data_df = df.selectExpr("CAST(value AS STRING)") \
    .select(from_json(col("value"), schema).alias("data")) \
    .select("data.*") \
    .filter(col("text").isNotNull())

sentiment_df = data_df.withColumn("sentiment", sentiment_udf(col("text")))

# 6. Écriture
def write_to_mongo_python(batch_df, batch_id):
    try:
        data = batch_df.toPandas().to_dict("records")
        if data:
            collection.insert_many(data)
            print(f"--- Batch {batch_id}: {len(data)} tweets sauvegardés ---")
    except Exception as e:
        pass

print("--- Spark Lancé (Version DoubleType) ---")
query = sentiment_df.writeStream \
    .foreachBatch(write_to_mongo_python) \
    .start()

query.awaitTermination()