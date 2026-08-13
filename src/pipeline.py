"""Orquestrador do pipeline: extract() -> transform() -> load(), com logging."""

import logging
import os
import sys

# Garante que a raiz do projeto esteja no sys.path, para que "src" e
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.carga import load_mongo_derived, load_postgres
from src.extracao import extract, save_raw
from src.transformacao import transform

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


logging.getLogger("pymongo").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main() -> None:
    """Executa o pipeline completo de ponta a ponta."""
    logger.info("=== Início do pipeline de cotações ===")
    raw_data = extract()
    save_raw(raw_data)
    df = transform(raw_data)
    load_postgres(df)
    load_mongo_derived(df)
    logger.info("=== Pipeline concluído com sucesso ===")


if __name__ == "__main__":
    main()
