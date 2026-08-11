"""Etapa de transformação (transform): achata o JSON, renomeia colunas,
trata nulos e valida os dados antes de seguir para a carga."""

import logging


import pandas as pd

logger = logging.getLogger(__name__)

RENAME_MAP = {
    "code": "moeda_origem",
    "codein": "moeda_destino",
    "name": "nome_par",
    "high": "maxima",
    "low": "minima",
    "varBid": "variacao",
    "pctChange": "variacao_percentual",
    "bid": "compra",
    "ask": "venda",
    "timestamp": "timestamp_unix",
    "create_date": "data_criacao",
}

NUMERIC_COLUMNS = ["maxima", "minima", "variacao", "variacao_percentual", "compra", "venda"]
COLUNAS_OBRIGATORIAS = {"moeda_origem", "moeda_destino", "compra", "venda"}


def transform(raw_data: dict) -> pd.DataFrame:
    """Achata o dict de moedas em um DataFrame tabular e trata os dados."""
    logger.info("Iniciando transformação de %d registros", len(raw_data))

    df = pd.DataFrame(list(raw_data.values()))
    df = df.rename(columns=RENAME_MAP)

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    if "data_criacao" in df.columns:
        df["data_criacao"] = pd.to_datetime(df["data_criacao"], errors="coerce")

    linhas_antes = len(df)
    df = df.dropna(subset=list(COLUNAS_OBRIGATORIAS & set(df.columns)))
    descartadas = linhas_antes - len(df)
    if descartadas:
        logger.warning("%d registro(s) descartado(s) por dados obrigatórios nulos", descartadas)

    if "variacao_percentual" in df.columns:
        df["variacao_percentual"] = df["variacao_percentual"].fillna(0.0)

    _validate(df)

    df["coletado_em"] = pd.Timestamp.now()
    logger.info("Transformação concluída: %d registro(s) válido(s)", len(df))
    return df


def _validate(df: pd.DataFrame) -> None:
    """Valida o DataFrame antes da carga; interrompe o pipeline se algo estiver errado."""
    if df.empty:
        raise ValueError("DataFrame vazio após a transformação — nenhum dado válido para carregar.")

    faltando = COLUNAS_OBRIGATORIAS - set(df.columns)
    if faltando:
        raise ValueError(f"Colunas obrigatórias ausentes após a transformação: {faltando}")

    if (df["compra"] <= 0).any() or (df["venda"] <= 0).any():
        raise ValueError("Valores de compra/venda inválidos (<= 0) encontrados nos dados.")
