from pathlib import Path

import pandas as pd
import pytest

from src.data.schema import validate_schema
from src.utils.config import load_config


def test_schema_de_l_echantillon_reel() -> None:
    chemin = Path(load_config()["paths"]["interim"]) / "clean_sample.parquet"
    if not chemin.exists():
        pytest.skip(
            f"Échantillon réel absent : {chemin}; test exécuté seulement s'il existe."
        )

    flux = pd.read_parquet(chemin)
    validate_schema(flux, stage="clean")
