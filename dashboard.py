import streamlit as st
import pandas as pd
import numpy as np # Ajouté pour gérer les erreurs maths
from pymongo import MongoClient
import time
import plotly.express as px
import plotly.graph_objects as go

# --- FIX : IGNORER LES ERREURS DE CALCUL (Overflow) ---
np.seterr(all='ignore')
# ------------------------------------------------------

# --- CONFIG ---
st.set_page_config(page_title="Big Data Monitor", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

# --- CSS ---
st.markdown("""
    <style>
        .main { background-color: #0E1117; }
        .metric-card { background-color: #1a1c24; border: 1px solid #333; padding: 20px; border-radius: 12px; text-align: center; }
        h1, h2, h3 { color: #00acee !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { height: 50px; background-color: #1a1c24; border-radius: 5px; color: #888; }
        .stTabs [aria-selected="true"] { background-color: #00acee !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

# --- MONGO ---
@st.cache_resource
def init_connection():
    try: return MongoClient("mongodb://localhost:27017/")
    except: return None
client = init_connection()

COLOR_MAP = {'POSITIF':'#00CC96', 'NEGATIF':'#EF553B', 'NEUTRE':'#636EFA'}

st.title("📡 Kafka Streaming Analytics")
st.markdown("---")
placeholder = st.empty()

while True:
    refresh_id = str(time.time())
    if client is None:
        st.error("MongoDB off"); time.sleep(5); continue

    try:
        db = client["twitter_db"]
        collection = db["sentiments"]
        data = list(collection.find().sort("_id", -1).limit(1000))
        df = pd.DataFrame(data)
        
        # --- GESTION ROBUSTE DU TEMPS ---
        has_time = False
        if not df.empty and 'timestamp' in df.columns:
            # On force la conversion en numérique d'abord pour éviter les bugs
            df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
            df['datetime'] = pd.to_datetime(df['timestamp'], unit='s', errors='coerce')
            df = df.dropna(subset=['datetime'])
            if not df.empty:
                df = df.sort_values(by='datetime')
                has_time = True
        # -------------------------------

    except Exception as e:
        time.sleep(2); continue

    with placeholder.container():
        if df.empty:
            st.info("⏳ En attente de données Kafka...")
        else:
            total = len(df)
            pos_pct = (len(df[df['sentiment']=='POSITIF'])/total*100)
            neg_pct = (len(df[df['sentiment']=='NEGATIF'])/total*100)
            
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Flux (Window)", total)
            k2.metric("Positif", f"{pos_pct:.1f}%")
            k3.metric("Négatif", f"{neg_pct:.1f}%")
            k4.metric("Status", "🟢 LIVE")

            tab1, tab2, tab3 = st.tabs(["Vue Globale", "Time Series", "Data"])

            with tab1:
                c1, c2 = st.columns(2)
                with c1:
                    fig_sun = px.sunburst(df, path=['topic', 'sentiment'], color='sentiment', color_discrete_map=COLOR_MAP)
                    fig_sun.update_layout(margin=dict(t=0,b=0,l=0,r=0), paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_sun, use_container_width=True, key=f"sun_{refresh_id}")
                with c2:
                    counts = df['sentiment'].value_counts().reset_index()
                    counts.columns = ['sentiment', 'count']
                    fig_bar = px.bar(counts, x='sentiment', y='count', color='sentiment', color_discrete_map=COLOR_MAP)
                    fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_bar, use_container_width=True, key=f"bar_{refresh_id}")

            with tab2:
                if has_time:
                    df_time = df.set_index('datetime')
                    df_trend = df_time.groupby([pd.Grouper(freq='1Min'), 'sentiment']).size().reset_index(name='count')
                    fig_line = px.line(df_trend, x='datetime', y='count', color='sentiment', color_discrete_map=COLOR_MAP, markers=True)
                    fig_line.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_line, use_container_width=True, key=f"line_{refresh_id}")
                    
                    df_vol = df_time.resample('1Min').size().reset_index(name='count')
                    fig_area = px.area(df_vol, x='datetime', y='count')
                    fig_area.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_area, use_container_width=True, key=f"area_{refresh_id}")
                else:
                    st.warning("⚠️ Les timestamps arrivent... (Attendez quelques secondes)")

            with tab3:
                cols_to_show = ['topic', 'sentiment', 'text']
                if has_time: cols_to_show.insert(0, 'datetime')
                st.dataframe(df[cols_to_show].sort_index(ascending=False).head(20), use_container_width=True, hide_index=True)

    time.sleep(2)