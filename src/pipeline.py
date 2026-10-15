"""Pipeline de ingestão de temperaturas IoT para PostgreSQL."""

from pathlib import Path
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    text,
    URL,
)

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "IOT-temp.csv"

load_dotenv(ROOT / ".env")


def conectar():
    """Cria conexão SQLAlchemy com o PostgreSQL."""

    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host="127.0.0.1",
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.environ["POSTGRES_DB"],
    )

    return create_engine(url, pool_pre_ping=True)


def processar_dados():
    """Lê, valida e transforma os dados do Kaggle."""

    print("Lendo arquivo CSV...")
    df = pd.read_csv(CSV_PATH)

    colunas = {
        "id",
        "room_id/id",
        "noted_date",
        "temp",
        "out/in",
    }

    if set(df.columns) != colunas:
        raise ValueError("Estrutura inesperada do CSV.")

    total_original = len(df)

    df = df.rename(
        columns={
            "id": "reading_id",
            "room_id/id": "room_id",
            "noted_date": "recorded_at",
            "temp": "temperature",
            "out/in": "location_type",
        }
    )

    df["recorded_at"] = pd.to_datetime(
        df["recorded_at"],
        format="%d-%m-%Y %H:%M",
        errors="raise",
    )

    df["temperature"] = pd.to_numeric(
        df["temperature"],
        errors="raise",
    )

    if df.isnull().any().any():
        raise ValueError("Existem valores nulos no dataset.")

    if not df["location_type"].isin(["In", "Out"]).all():
        raise ValueError("Localização inválida encontrada.")

    df = df.drop_duplicates()

    if df["reading_id"].duplicated().any():
        raise ValueError("IDs repetidos com dados diferentes.")

    print(f"Linhas originais: {total_original}")
    print(f"Linhas válidas: {len(df)}")
    print(f"Duplicatas removidas: {total_original - len(df)}")

    return df


def criar_tabela(engine):
    """Cria a tabela com chave primária para evitar duplicações."""

    comando = """
    CREATE TABLE IF NOT EXISTS temperature_readings (
        reading_id TEXT PRIMARY KEY,
        room_id TEXT NOT NULL,
        recorded_at TIMESTAMP NOT NULL,
        temperature NUMERIC(8, 2) NOT NULL,
        location_type VARCHAR(3) NOT NULL
            CHECK (location_type IN ('In', 'Out'))
    );
    """

    with engine.begin() as conexao:
        conexao.execute(text(comando))


def importar_dados(engine, df):
    """Importa apenas registros ainda não existentes."""

    with engine.begin() as conexao:
        existentes = pd.read_sql(
            "SELECT reading_id FROM temperature_readings",
            conexao,
        )

    dados_novos = df[
        ~df["reading_id"].isin(existentes["reading_id"])
    ].copy()

    if not dados_novos.empty:
        dados_novos.to_sql(
            "temperature_readings",
            engine,
            if_exists="append",
            index=False,
            chunksize=2000,
            method="multi",
        )

    with engine.connect() as conexao:
        total = conexao.execute(
            text("SELECT COUNT(*) FROM temperature_readings")
        ).scalar_one()

    print(f"Novas leituras importadas: {len(dados_novos)}")
    print(f"Total no PostgreSQL: {total}")


def main():
    engine = conectar()

    try:
        df = processar_dados()
        criar_tabela(engine)
        importar_dados(engine, df)
        print("Pipeline executado com sucesso!")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
