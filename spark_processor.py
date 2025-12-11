import os
import sys

# config windows
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable
hadoop_path = os.getcwd() + "\\hadoop"
os.environ["HADOOP_HOME"] = hadoop_path
os.environ["hadoop.home.dir"] = hadoop_path
os.environ["PATH"] += os.pathsep + hadoop_path + "\\bin"
# fin config windows

from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, udf
from pyspark.sql.types import StringType, StructType, DoubleType
from textblob import TextBlob
from pymongo import MongoClient

# connexion mongo
try:
    mongo_client = MongoClient("mongodb://localhost:27017/")
    db = mongo_client["twitter_db"]
    collection = db["sentiments"]
    print("connexion mongodb ok")
except Exception as e:
    print(f"erreur mongo: {e}")

# init spark
spark = (
    SparkSession.builder.appName("TwitterSentimentAnalysis")
    .config(
        "spark.jars.packages",
        "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.0",
    )
    .config("spark.sql.warehouse.dir", "file:///C:/tmp")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

# fonction sentiment
def get_sentiment(text):
    if not text:
        return "NEUTRE"
    try:
        analysis = TextBlob(text)
        if analysis.sentiment.polarity > 0:
            return "POSITIF"
        elif analysis.sentiment.polarity < 0:
            return "NEGATIF"
        else:
            return "NEUTRE"
    except Exception:
        return "NEUTRE"


sentiment_udf = udf(get_sentiment, StringType())

# lecture kafka
df = (
    spark.readStream.format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "twitter_stream")
    .option("startingOffsets", "latest")
    .load()
)

# schema messages
schema = (
    StructType()
    .add("text", StringType())
    .add("topic", StringType())
    .add("timestamp", DoubleType())
)

# extraction donnees
data_df = (
    df.selectExpr("CAST(value AS STRING)")
    .select(from_json(col("value"), schema).alias("data"))
    .select("data.*")
    .filter(col("text").isNotNull())
)

# ajout sentiment
sentiment_df = data_df.withColumn("sentiment", sentiment_udf(col("text")))

# ecriture vers mongo
def write_to_mongo_python(batch_df, batch_id):
    try:
        data = batch_df.toPandas().to_dict("records")
        if data:
            collection.insert_many(data)
            print(f"batch {batch_id}: {len(data)} tweets sauvegardes")
    except Exception:
        pass


print("spark lance (version doubletype)")
query = sentiment_df.writeStream.foreachBatch(write_to_mongo_python).start()

query.awaitTermination()
