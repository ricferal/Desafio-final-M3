"""Etapa de extração (extract): coleta defensiva da AwesomeAPI de câmbio
e gravação da camada raw (JSON bruto, intocado, com timestamp no nome)."""

import json
import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

# USD-BRL, EUR-BRL e BTC-BRL: três pares de moedas em uma única chamada.
API_URL = "https://economia.awesomeapi.com.br/json/last/USD-BRL,EUR-BRL,BTC-BRL"

RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw")


def extract(url: str = API_URL, timeout: int = 10) -> dict:
    """Coleta os dados da API de forma defensiva (timeout, status, try/except)."""
    try:
        logger.info("Iniciando coleta em %s", url)
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        logger.info("Coleta concluída com sucesso: %d moedas retornadas", len(data))
        return data
    except requests.exceptions.Timeout:
        logger.error("Timeout ao acessar a API: %s", url)
        raise
    except requests.exceptions.HTTPError as error:
        logger.error("Erro HTTP ao acessar a API: %s", error)
        raise
    except requests.exceptions.RequestException as error:
        logger.error("Erro de requisição ao acessar a API: %s", error)
        raise
    except json.JSONDecodeError as error:
        logger.error("Resposta da API não é um JSON válido: %s", error)
        raise


def save_raw(data: dict, prefix: str = "cotacoes") -> str:
    """Salva o JSON bruto, intocado, em raw/AAAA-MM-DD_HHMM_prefix.json."""
    os.makedirs(RAW_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    filename = f"{timestamp}_{prefix}.json"
    filepath = os.path.join(RAW_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    logger.info("Camada raw salva em %s", filepath)
    return filepath
