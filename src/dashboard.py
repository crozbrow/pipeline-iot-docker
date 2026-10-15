"""Dashboard interativo de temperaturas IoT."""

from pathlib import Path
import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, URL

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

st.set_page_config(
    page_title="Dashboard IoT | Temperaturas",
    page_icon="🌡️",
    layout="wide",
)

@st.cache_resource
def conectar():
    url = URL.create(
        "postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host="127.0.0.1",
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.environ["POSTGRES_DB"],
    )
    return create_engine(url, pool_pre_ping=True)


@st.cache_data(ttl=60)
def carregar_view(nome):
    views_permitidas = {
        "avg_temp_por_ambiente",
        "leituras_por_hora",
        "temp_max_min_por_dia",
    }
    if nome not in views_permitidas:
        raise ValueError("View não permitida.")

    with conectar().connect() as conexao:
        return pd.read_sql(
            text(f"SELECT * FROM {nome}"),
            conexao,
        )


st.title("🌡️ Dashboard de Temperaturas IoT")
st.caption(
    "Pipeline de Dados com IoT e Docker | "
    "Python • PostgreSQL • Streamlit • Plotly"
)

try:
    df_ambiente = carregar_view("avg_temp_por_ambiente")
    df_hora = carregar_view("leituras_por_hora")
    df_diario = carregar_view("temp_max_min_por_dia")
except Exception as erro:
    st.error(f"Erro ao consultar o banco: {erro}")
    st.stop()

df_diario["data"] = pd.to_datetime(df_diario["data"])

total = int(df_ambiente["total_leituras"].sum())
media_in = df_ambiente.loc[
    df_ambiente["ambiente"] == "In", "temperatura_media"
]
media_out = df_ambiente.loc[
    df_ambiente["ambiente"] == "Out", "temperatura_media"
]

valor_in = float(media_in.iloc[0]) if not media_in.empty else 0
valor_out = float(media_out.iloc[0]) if not media_out.empty else 0

c1, c2, c3, c4 = st.columns(4)

c1.metric("Total de leituras", f"{total:,}".replace(",", "."))
c2.metric("Temperatura média interna", f"{valor_in:.2f} °C")
c3.metric("Temperatura média externa", f"{valor_out:.2f} °C")
c4.metric("Diferença externa - interna", f"{valor_out - valor_in:.2f} °C")

st.divider()

st.subheader("1. Temperatura média por ambiente")

df_ambiente["tipo"] = df_ambiente["ambiente"].map(
    {"In": "Interno", "Out": "Externo"}
)

fig1 = px.bar(
    df_ambiente,
    x="tipo",
    y="temperatura_media",
    color="tipo",
    text="temperatura_media",
    labels={
        "tipo": "Ambiente",
        "temperatura_media": "Temperatura média (°C)",
    },
)
fig1.update_traces(textposition="outside")
fig1.update_layout(showlegend=False)
st.plotly_chart(fig1, use_container_width=True)

st.subheader("2. Quantidade de leituras por hora")

fig2 = px.line(
    df_hora.sort_values("hora"),
    x="hora",
    y="contagem",
    markers=True,
    labels={
        "hora": "Hora do dia",
        "contagem": "Quantidade de leituras",
    },
)
fig2.update_xaxes(dtick=1)
st.plotly_chart(fig2, use_container_width=True)

st.subheader("3. Temperaturas máximas e mínimas por dia")

data_min = df_diario["data"].min().date()
data_max = df_diario["data"].max().date()

intervalo = st.date_input(
    "Selecione o período",
    value=(data_min, data_max),
    min_value=data_min,
    max_value=data_max,
)

df_filtrado = df_diario.copy()

if isinstance(intervalo, (tuple, list)) and len(intervalo) == 2:
    inicio, fim = intervalo
    df_filtrado = df_filtrado[
        (df_filtrado["data"].dt.date >= inicio)
        & (df_filtrado["data"].dt.date <= fim)
    ]

if df_filtrado.empty:
    st.warning("Nenhum dado encontrado para o período.")
else:
    fig3 = px.line(
        df_filtrado.sort_values("data"),
        x="data",
        y=["temp_max", "temp_min", "temp_media"],
        markers=True,
        labels={
            "data": "Data",
            "value": "Temperatura (°C)",
            "variable": "Indicador",
        },
    )
    fig3.update_layout(
        legend_title_text="Temperaturas",
        hovermode="x unified",
    )
    st.plotly_chart(fig3, use_container_width=True)

st.divider()

st.subheader("Dados consultados do PostgreSQL")

with st.expander("Visualizar dados das views SQL"):
    st.write("Temperatura média por ambiente")
    st.dataframe(df_ambiente, use_container_width=True)

    st.write("Leituras por hora")
    st.dataframe(df_hora, use_container_width=True)

    st.write("Temperaturas por dia")
    st.dataframe(df_diario, use_container_width=True)

st.caption(
    "Fonte: Kaggle - Temperature Readings: IoT Devices | "
    "Dados históricos de 2018"
)
