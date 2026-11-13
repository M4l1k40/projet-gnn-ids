"""Schéma commun des flux réseau préparés."""

from collections.abc import Sequence

import numpy as np
import pandas as pd
ID_COLS = ["flow_id", "src_ip", "dst_ip", "src_port", "dst_port", "ts_end"]
TARGET_COLS = ["label_bin", "label_multi"]
META_COLS = ["split", "day"]
PREDICTION_COLUMNS = [
    "flow_id",
    "y_true",
    "y_pred",
    "score",
    "recon_error",
    "seed",
]

_REQUIRED_DTYPES = {
    "flow_id": "string",
    "src_port": "int32",
    "dst_port": "int32",
    "ts_end": "float64",
    "label_bin": "int8",
    "label_multi": "string",
    "day": "string",
}
_SPLIT_VALUES = {"train", "val", "test"}


def _feature_columns(columns: Sequence[str], stage: str) -> list[str]:
    excluded = set(ID_COLS + TARGET_COLS + META_COLS)
    if stage == "clean":
        excluded.discard("split")
    return [column for column in columns if column not in excluded]


def validate_schema(df: pd.DataFrame, stage: str = "final") -> None:
    """Valide les colonnes, types et contraintes du schéma des flux."""
    if stage not in {"final", "clean"}:
        raise ValueError("stage doit être 'final' ou 'clean'.")
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df doit être un pandas.DataFrame.")

    required_columns = ID_COLS + TARGET_COLS + ["day"]
    if stage == "final" or "split" in df.columns:
        required_columns.append("split")
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Colonnes manquantes : {', '.join(missing_columns)}.")

    errors: list[str] = []
    row_count = len(df)

    for column, expected_dtype in _REQUIRED_DTYPES.items():
        if column not in df.columns:
            continue
        series = df[column]
        if expected_dtype == "string":
            invalid_count = int(
                (~series.map(lambda value: isinstance(value, str))).sum()
            )
            if invalid_count:
                errors.append(
                    f"{column} : type attendu {expected_dtype}, type reçu "
                    f"{series.dtype} ({invalid_count} ligne(s) concernée(s))."
                )
        elif str(series.dtype) != expected_dtype:
            errors.append(
                f"{column} : type attendu {expected_dtype}, type reçu "
                f"{series.dtype} ({row_count} ligne(s) concernée(s))."
            )

    if "split" in df.columns:
        split = df["split"]
        if not isinstance(split.dtype, pd.CategoricalDtype):
            errors.append(
                f"split : type attendu category, type reçu {split.dtype} "
                f"({row_count} ligne(s) concernée(s))."
            )
        invalid_split = split.isna() | ~split.isin(_SPLIT_VALUES)
        invalid_split_count = int(invalid_split.sum())
        if invalid_split_count:
            errors.append(
                "split : valeurs hors de train/val/test ou manquantes "
                f"({invalid_split_count} ligne(s) concernée(s))."
            )

    if "flow_id" in df.columns:
        duplicated = df["flow_id"].duplicated(keep=False)
        duplicate_count = int(duplicated.sum())
        if duplicate_count:
            errors.append(
                f"flow_id : valeurs non uniques ({duplicate_count} ligne(s) "
                "concernée(s))."
            )

    features = _feature_columns(df.columns, stage)
    for column in features:
        series = df[column]
        if not pd.api.types.is_numeric_dtype(series.dtype):
            continue
        if str(series.dtype) != "float32":
            errors.append(
                f"{column} : type attendu float32 pour une feature, type reçu "
                f"{series.dtype} ({row_count} ligne(s) concernée(s))."
            )
        non_finite_count = int(
            (~np.isfinite(series.to_numpy(dtype=np.float64, na_value=np.nan))).sum()
        )
        if non_finite_count:
            errors.append(
                f"{column} : NaN ou infini ({non_finite_count} ligne(s) concernée(s))."
            )

    if "label_bin" in df.columns and "label_multi" in df.columns:
        label_bin = df["label_bin"]
        label_multi = df["label_multi"]
        invalid_binary = ~label_bin.isin([0, 1])
        inconsistent = (label_bin.eq(0) != label_multi.eq("BENIGN")) | invalid_binary
        inconsistent_count = int(inconsistent.sum())
        if inconsistent_count:
            errors.append(
                "label_bin/label_multi : incohérence (label_bin=0 doit "
                "correspondre exactement à BENIGN) "
                f"({inconsistent_count} ligne(s) concernée(s))."
            )

    if errors:
        raise ValueError("Schéma invalide :\n- " + "\n- ".join(errors))
