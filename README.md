# 🐦 Real-Time Social Media Sentiment Analysis

Ce projet est une pipeline Big Data complète capable d'ingérer, traiter et visualiser des sentiments (Positif/Négatif/Neutre) sur des flux de données de réseaux sociaux en temps réel.

## 🏗️ Architecture

Le projet suit une architecture Lambda simplifiée pour le streaming :

1.  **Ingestion :** Script Python simulant un flux Twitter via `Faker` (Simule l'API Twitter).
2.  **Messaging :** **Apache Kafka** sert de tampon (buffer) haute performance.
3.  **Processing :** **Spark Structured Streaming** lit Kafka, nettoie la donnée et applique un modèle NLP (`TextBlob`).
4.  **Storage :** **MongoDB** stocke les résultats traités.
5.  **Visualization :** **Streamlit** + **Plotly** affichent les KPIs et l'évolution temporelle en direct.

---

## 🚀 Prérequis

* **Docker** & Docker Compose (installés et lancés).
* **Python 3.8+**.
* **Java 11** (Requis pour Spark).

## 📦 Installation

1.  Cloner le dépôt :
    ```bash
    git clone <VOTRE_LIEN_GIT>
    cd Projet_BigData
    ```

2.  Installer les dépendances Python :
    ```bash
    pip install -r requirements.txt
    ```

3.  **Note pour Windows :**
    Le projet inclut un dossier `hadoop/bin` avec `winutils.exe` et `hadoop.dll` nécessaires pour faire tourner Spark sur Windows sans erreur. Le script `spark_processor.py` configure automatiquement les variables d'environnement pour utiliser ce dossier.

---

## ▶️ Démarrage (Guide pas à pas)

Il est important de lancer les services dans cet ordre précis en ouvrant **3 terminaux différents**.

### Étape 1 : L'Infrastructure (Terminal 1)
Lancez les conteneurs (Zookeeper, Kafka, MongoDB) :
```bash
docker-compose up -d