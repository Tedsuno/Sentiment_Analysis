import time
import numpy as np
import pandas as pd
import streamlit as st
from pymongo import MongoClient
import plotly.express as px
import plotly.graph_objects as go

# config globale
st.set_page_config(
    page_title="sentiment streaming monitor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

np.seterr(all="ignore")

# connexion mongodb
@st.cache_resource
def init_connection():
    try:
        client = MongoClient("mongodb://localhost:27017/")
        return client
    except:
        return None

client = init_connection()

# couleurs par sentiment
COLOR_MAP = {
    "POSITIF": "#00CC96",
    "NEGATIF": "#EF553B",
    "NEUTRE": "#636EFA",
}

# titre
st.title("analyse de sentiment en temps reel")
st.markdown("")
st.markdown("---")

placeholder = st.empty()
REFRESH_EVERY_SEC = 3  # frequence de refresh

# boucle principale
while True:
    refresh_id = str(time.time())

    if client is None:
        with placeholder.container():
            st.error(
                "impossible de se connecter a mongodb (localhost:27017). lance le service docker mongo."
            )
        time.sleep(REFRESH_EVERY_SEC)
        continue

    # lecture des donnees
    try:
        collection = client["twitter_db"]["sentiments"]
        data = list(collection.find().sort("_id", -1).limit(2000))
        df = pd.DataFrame(data)
    except Exception as e:
        with placeholder.container():
            st.error(f"erreur de lecture mongodb : {e}")
        time.sleep(REFRESH_EVERY_SEC)
        continue

    # preparation du temps
    has_time = False
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_numeric(df["timestamp"], errors="coerce")
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="s", errors="coerce")
        df = df.dropna(subset=["datetime"])
        if not df.empty:
            df = df.sort_values(by="datetime")
            has_time = True

    # affichage dashboard
    with placeholder.container():
        if df.empty:
            st.info("en attente de donnees kafka / spark...")
        else:
            total = len(df)

            sentiment_counts = df["sentiment"].value_counts()
            pos_pct = (
                sentiment_counts.get("POSITIF", 0) / total * 100 if total > 0 else 0
            )
            neg_pct = (
                sentiment_counts.get("NEGATIF", 0) / total * 100 if total > 0 else 0
            )
            neu_pct = (
                sentiment_counts.get("NEUTRE", 0) / total * 100 if total > 0 else 0
            )

            # kpi
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("positifs (%)", f"{pos_pct:0.1f}")
            c2.metric("negatifs (%)", f"{neg_pct:0.1f}")
            c3.metric("neutres (%)", f"{neu_pct:0.1f}")
            c4.metric("nb messages (fenetre)", total)

            st.markdown("---")

            # onglets
            tab1, tab2, tab3, tab4 = st.tabs(
                ["vue globale", "par topic", "chronologie", "donnees brutes"]
            )

            # onglet 1 : vue globale
            with tab1:
                # ligne 1
                col_a, col_b = st.columns(2)

                # graphique 1 : camembert sentiments
                with col_a:
                    fig_pie = px.pie(
                        df,
                        names="sentiment",
                        title="repartition globale des sentiments",
                        color="sentiment",
                        color_discrete_map=COLOR_MAP,
                        hole=0.4,
                    )
                    fig_pie.update_layout(
                        legend_title_text="sentiment",
                        margin=dict(t=40, b=0, l=0, r=0),
                    )
                    st.plotly_chart(
                        fig_pie, use_container_width=True, key=f"pie_{refresh_id}"
                    )

                # graphique 2 : histogramme topics
                with col_b:
                    fig_topic_count = px.histogram(
                        df,
                        x="topic",
                        title="nb messages par topic (brut)",
                        text_auto=True,
                    )
                    fig_topic_count.update_layout(
                        margin=dict(t=40, b=0, l=0, r=0),
                        yaxis_title="nb messages",
                    )
                    st.plotly_chart(
                        fig_topic_count,
                        use_container_width=True,
                        key=f"topic_count_{refresh_id}",
                    )

                # ligne 2
                col_c, col_d = st.columns(2)

                # graphique 3 : nb messages par sentiment
                with col_c:
                    df_sent_cnt = (
                        df.groupby("sentiment")
                        .size()
                        .reset_index(name="nb_messages")
                        .sort_values("nb_messages", ascending=False)
                    )
                    fig_bar_sent = px.bar(
                        df_sent_cnt,
                        x="sentiment",
                        y="nb_messages",
                        title="nb messages par sentiment",
                        text_auto=True,
                        color="sentiment",
                        color_discrete_map=COLOR_MAP,
                    )
                    fig_bar_sent.update_layout(
                        yaxis_title="nb messages",
                        margin=dict(t=40, b=0, l=0, r=0),
                    )
                    st.plotly_chart(
                        fig_bar_sent,
                        use_container_width=True,
                        key=f"bar_sent_{refresh_id}",
                    )

                # graphique 4 : nb messages par topic et sentiment (groupes)
                with col_d:
                    if "topic" in df.columns:
                        df_topic_sent = (
                            df.groupby(["topic", "sentiment"])
                            .size()
                            .reset_index(name="nb_messages")
                        )
                        fig_group = px.bar(
                            df_topic_sent,
                            x="topic",
                            y="nb_messages",
                            color="sentiment",
                            color_discrete_map=COLOR_MAP,
                            barmode="group",
                            title="nb messages par topic et sentiment",
                            text_auto=True,
                        )
                        fig_group.update_layout(
                            yaxis_title="nb messages",
                            margin=dict(t=40, b=0, l=0, r=0),
                        )
                        st.plotly_chart(
                            fig_group,
                            use_container_width=True,
                            key=f"group_{refresh_id}",
                        )
                    else:
                        st.warning("pas de colonne topic dans les donnees.")

            # onglet 2 : par topic
            with tab2:
                if "topic" in df.columns:
                    grouped = (
                        df.groupby(["topic", "sentiment"])
                        .size()
                        .reset_index(name="count")
                    )
                    grouped["pct"] = grouped["count"] / grouped.groupby(
                        "topic"
                    )["count"].transform("sum") * 100

                    fig_stack = px.bar(
                        grouped,
                        x="topic",
                        y="pct",
                        color="sentiment",
                        color_discrete_map=COLOR_MAP,
                        title="repartition (%) des sentiments par topic",
                        text_auto=".1f",
                    )
                    fig_stack.update_layout(
                        yaxis_title="pct",
                        margin=dict(t=40, b=0, l=0, r=0),
                        barmode="stack",
                    )
                    st.plotly_chart(
                        fig_stack,
                        use_container_width=True,
                        key=f"stack_{refresh_id}",
                    )

                    pivot = (
                        grouped.pivot(
                            index="topic", columns="sentiment", values="count"
                        )
                        .fillna(0)
                        .astype(int)
                    )
                    fig_heat = px.imshow(
                        pivot,
                        text_auto=True,
                        aspect="auto",
                        title="heatmap topic x sentiment (nb messages)",
                    )
                    st.plotly_chart(
                        fig_heat,
                        use_container_width=True,
                        key=f"heat_{refresh_id}",
                    )
                else:
                    st.warning("pas de colonne topic dans les donnees.")

            # onglet 3 : chronologie
            with tab3:
                if has_time:
                    df_time = df.set_index("datetime")

                    vol = df_time.resample("1Min").size().reset_index(name="count")
                    fig_vol = px.area(
                        vol,
                        x="datetime",
                        y="count",
                        title="nb messages par minute",
                    )
                    fig_vol.update_layout(
                        xaxis_title="temps",
                        yaxis_title="nb messages",
                        margin=dict(t=40, b=0, l=0, r=0),
                    )
                    st.plotly_chart(
                        fig_vol,
                        use_container_width=True,
                        key=f"vol_{refresh_id}",
                    )

                    pos = (
                        df_time[df_time["sentiment"] == "POSITIF"]
                        .resample("5Min")
                        .size()
                    )
                    total_t = df_time.resample("5Min").size()
                    ratio = (pos / total_t * 100).fillna(0).reset_index(name="pos_pct")

                    fig_pos = px.line(
                        ratio,
                        x="datetime",
                        y="pos_pct",
                        title="part de messages positifs (%) dans le temps (fenetre 5 min)",
                    )
                    fig_pos.update_layout(
                        xaxis_title="temps",
                        yaxis_title="positifs (%)",
                        margin=dict(t=40, b=0, l=0, r=0),
                    )
                    st.plotly_chart(
                        fig_pos,
                        use_container_width=True,
                        key=f"pos_{refresh_id}",
                    )
                else:
                    st.warning(
                        "les timestamps ne sont pas encore exploitables. attendre quelques secondes."
                    )

            # onglet 4 : donnees brutes
            with tab4:
                st.subheader("derniers messages")

                cols_to_show = ["topic", "sentiment", "text"]
                if has_time:
                    cols_to_show.insert(0, "datetime")

                st.dataframe(
                    df[cols_to_show]
                    .sort_values(by=cols_to_show[0], ascending=False)
                    .head(50),
                    use_container_width=True,
                    hide_index=True,
                    key=f"table_{refresh_id}",
                )

    time.sleep(REFRESH_EVERY_SEC)
