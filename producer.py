import time
import json
import random
from kafka import KafkaProducer
from faker import Faker # pip install faker kafka-python

fake = Faker()
producer = KafkaProducer(bootstrap_servers='localhost:9092',
                         value_serializer=lambda v: json.dumps(v).encode('utf-8'))

topics = ["tech", "politics", "sport", "music"]

print("--- Démarrage du générateur de faux tweets ---")

while True:
    # On crée un faux tweet
    data = {
        'text': fake.sentence(),
        'author': fake.user_name(),
        'topic': random.choice(topics),
        'timestamp': time.time()
    }
    
    # On l'envoie dans le topic 'twitter_stream'
    producer.send('twitter_stream', data)
    print(f"Envoyé : {data}")
    
    time.sleep(1) # Un tweet par seconde