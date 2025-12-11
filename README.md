# 🐦 Real-Time Social Media Sentiment Analysis

Ce projet est une pipeline Big Data complète capable d'ingérer, traiter et visualiser des sentiments (Positif / Négatif / Neutre) sur des flux de données de réseaux sociaux en temps réel.

---

##  Architecture

Le projet suit une architecture de streaming (type Lambda simplifiée) :

1. **Ingestion** : script Python simulant un flux Twitter via `Faker` (simulation de l’API Twitter).
2. **Messaging** : **Apache Kafka** sert de tampon (buffer) haute performance pour transporter le flux.
3. **Processing** : **Spark Structured Streaming** lit Kafka, nettoie la donnée et applique un modèle NLP (`TextBlob`) pour calculer le sentiment.
4. **Storage** : **MongoDB** stocke les résultats traités.
5. **Visualization** : **Streamlit** + **Plotly** affichent les KPIs et l'évolution temporelle en direct.

---

##  Prérequis

- **Docker** & Docker Compose installés et fonctionnels
- **Python 3.8+**
- **Java 11** (requis pour Spark)
- Les dépendances Python listées dans `requirements.txt`

###  Note importante pour Windows

Le projet inclut un dossier `hadoop/bin` contenant `winutils.exe` et `hadoop.dll`.  
Ces fichiers sont indispensables pour faire tourner Spark sur Windows sans erreur.  
Le script `spark_processor.py` configure automatiquement les variables d'environnement pour utiliser ce dossier.

---

##  Installation

1. Cloner le dépôt :

```bash
git clone https://github.com/Tedsuno/Sentiment_Analysis.git
cd Projet_BigData
```

2. Installer les dépendances Python :

```bash
pip install -r requirements.txt
```

---

## ▶ Démarrage 

Pour faire tourner tout le projet (Kafka + Spark + TextBlob + MongoDB + Dashboard Streamlit), il faut lancer plusieurs scripts **en parallèle** dans différents terminaux.

Voici les **4 étapes** à suivre dans l’ordre :

---

###  Étape 1 : Lancer l’infrastructure (Terminal 1)

Dans un **Terminal 1**, placez-vous à la racine du projet puis lancez :

```bash
docker-compose up -d
```

Cette commande démarre les services suivants :

- Zookeeper  
- Kafka  
- MongoDB  

Les conteneurs tournent en arrière-plan et doivent rester actifs pendant toute la durée du projet.

Vous pouvez vérifier avec :

```bash
docker ps
```

---

###  Étape 2 : Lancer le traitement temps réel Spark + TextBlob (Terminal 1)

Toujours dans le **même Terminal 1**, une fois les conteneurs démarrés, lancez le job Spark Streaming :

```bash
python spark_processor.py
```

Ce script :

- lit en continu le topic Kafka `twitter_stream`
- applique le modèle NLP `TextBlob` pour calculer un sentiment (positif / Négatif / Neutre)
- écrit les messages enrichis dans MongoDB (`twitter_db.sentiments`)

> Important : laissez ce terminal ouvert, sinon le traitement temps réel s’arrête.

---

###  Étape 3 : Lancer le producer Kafka (Terminal 3)

Ouvrez un **Terminal 2**, placez-vous dans le dossier du projet, puis lancez :

```bash
python producer.py
```

Ce script :

- génère de faux tweets (texte, auteur, topic, timestamp) via `Faker`
- envoie environ **un message par seconde** dans le topic Kafka `twitter_stream`

Vous verrez défiler des lignes du type :

```text
Envoyé : {'text': '...', 'author': '...', 'topic': 'tech', 'timestamp': 173...}
```

> Ce terminal doit aussi rester ouvert pour que le flux de données continue.

---

###  Étape 4 : Lancer le dashboard Streamlit (Terminal 3)

Ouvrez un **Terminal 3**, placez-vous dans le dossier du projet, puis lancez :

```bash
streamlit run dashboard.py
```

Cela ouvre l’interface Streamlit (en général sur :  
`http://localhost:8501`).

Le dashboard :

- lit les données dans MongoDB
- affiche les pourcentages de sentiments
- montre plusieurs graphiques :
  - répartition globale des sentiments
  - répartition par topic
  - séries temporelles
  - heatmap topic × sentiment
- liste les derniers messages dans un tableau qui se met à jour en temps réel

> Tant que Spark (Terminal 1) et le producer (Terminal 2) tournent, le dashboard se met à jour automatiquement.


##  Arrêt propre du système

1. Dans les Terminaux 1, 2 et 3, stoppez les scripts Python avec `Ctrl + C`.
2. Dans n’importe quel terminal, arrêtez les conteneurs Docker :

```bash
docker-compose down
```

Tous les services (Kafka, Zookeeper, MongoDB) sont alors arrêtés.

---
