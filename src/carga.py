"""Etapa de carga (load): grava os dados tratados no PostgreSQL e uma
coleção derivada (ranking de variação) no MongoDB Atlas."""

import logging

import pandas as pd
from pymongo import MongoClient
from sqlalchemy import create_engine

from config import get_mongo_uri, get_postgres_url, MONGO_DB_NAME

logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)



TABLE_NAME = "cotacoes"
COLLECTION_NAME = "ranking_variacao"


def load_postgres(df: pd.DataFrame, table_name: str = TABLE_NAME) -> None:
    """Carrega o DataFrame no PostgreSQL de forma idempotente.

    Decisão de design: if_exists="replace". Cada execução do pipeline
    coleta um "retrato" (snapshot) completo das cotações no momento da
    coleta, então substituir a tabela a cada carga evita duplicar linhas
    quando o pipeline roda mais de uma vez — sem precisar de upsert
    manual ou chave única. O histórico de cada coleta continua
    preservado na camada raw (JSON com timestamp em raw/).
    """
    engine = create_engine(get_postgres_url())
    try:
        df.to_sql(table_name, engine, if_exists="replace", index=False)
        logger.info("Carga no PostgreSQL concluída: %d linha(s) em '%s'", len(df), table_name)
    except Exception:
        logger.exception("Falha ao carregar dados no PostgreSQL")
        raise
    finally:
        engine.dispose()


def load_mongo_derived(df: pd.DataFrame, collection_name: str = COLLECTION_NAME) -> None:
    """Grava no MongoDB Atlas uma coleção DERIVADA: um ranking das moedas
    ordenado pela variação percentual absoluta, com a cotação de venda e
    o horário da coleta. Não é cópia da tabela do Postgres — é um recorte
    resumido e reordenado dos dados tratados.
    """
    colunas_disponiveis = [
        col
        for col in ["moeda_origem", "moeda_destino", "venda", "variacao_percentual", "coletado_em"]
        if col in df.columns
    ]
    derivado = (
        df.assign(variacao_abs=df["variacao_percentual"].abs())
        .sort_values("variacao_abs", ascending=False)[colunas_disponiveis]
        .reset_index(drop=True)
    )
    derivado["ranking"] = derivado.index + 1
    registros = derivado.to_dict(orient="records")

    client = MongoClient(get_mongo_uri())
    try:
        database = client[MONGO_DB_NAME]
        collection = database[collection_name]
        collection.delete_many({})  # idempotência: recomeça o ranking a cada execução
        if registros:
            collection.insert_many(registros)
        logger.info(
            "Carga no MongoDB Atlas concluída: %d documento(s) em '%s'",
            len(registros),
            collection_name,
        )
    except Exception:
        logger.exception("Falha ao carregar dados no MongoDB Atlas")
        raise
    finally:
        client.close()
