import time
import json
import random
from kafka import KafkaProducer
from faker import Faker

# config faker et kafka
fake = Faker()
producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

topics = ["tech", "politics", "sport", "music"]

print("demarrage generateur faux tweets")

# boucle generation
while True:
    # creation faux tweet
    data = {
        "text": fake.sentence(),
        "author": fake.user_name(),
        "topic": random.choice(topics),
        "timestamp": time.time(),
    }

    # envoi dans topic kafka
    producer.send("twitter_stream", data)
    print(f"envoye: {data}")

    time.sleep(1)  # 1 tweet par seconde
