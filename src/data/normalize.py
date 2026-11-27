"""Normalisation des features finaux avec ajustement limité au train."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import joblib
from sklearn.preprocessing import StandardScaler

from src.data.schema import ID_COLS, META_COLS, TARGET_COLS, validate_schema
from src.utils.config import load_config

_SPLITS = ("train", "val", "test")
_BATCH_SIZE = 50_000


def _feature_columns(schema: pa.Schema) -> list[str]:
    excluded = set(ID_COLS + TARGET_COLS + META_COLS)
    features = [name for name in schema.names if name not in excluded]
    invalid = [
        name for name in features if not pa.types.is_float32(schema.field(name).type)
    ]
    if invalid:
        raise ValueError(
            "Features attendues en float32 : " + ", ".join(invalid) + "."
        )
    if not features:
        raise ValueError("Aucune feature numérique à normaliser.")
    return features


def _prepare_features(values: np.ndarray, method: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ValueError("Les features contiennent des NaN ou des valeurs infinies.")
    if method == "log1p_standard":
        if (matrix < 0).any():
            raise ValueError(
                "La méthode log1p_standard exige des features non négatives."
            )
        return np.log1p(matrix)
    return matrix


def _feature_batches(
    parquet_path: Path,
    features: list[str],
    batch_size: int,
):
    parquet_file = pq.ParquetFile(parquet_path)
    for batch in parquet_file.iter_batches(
        columns=features,
        batch_size=batch_size,
    ):
        frame = batch.to_pandas()
        yield frame.to_numpy(dtype=np.float64, copy=False)


def _dataset_moments(
    totals: np.ndarray,
    squared_totals: np.ndarray,
    row_count: int,
) -> tuple[np.ndarray, np.ndarray]:
    mean = totals / row_count
    variance = np.maximum(squared_totals / row_count - mean * mean, 0)
    return mean, np.sqrt(variance)


def normalize_final_data(
    config: dict[str, Any] | None = None,
    *,
    processed_dir: str | Path | None = None,
    models_dir: str | Path | None = None,
    scaler_path: str | Path | None = None,
    write_features: bool = True,
    report_path: str | Path | None = None,
    batch_size: int = _BATCH_SIZE,
) -> tuple[Path, Path, Path, dict[str, Any]]:
    """Ajuste le scaler sur train, transforme les trois splits et écrit les artefacts."""
    project_config = load_config() if config is None else config
    method = str(project_config["normalization"]["method"])
    if method not in {"standard", "log1p_standard"}:
        raise ValueError(
            "normalization.method doit être 'standard' ou 'log1p_standard'."
        )
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")

    data_dir = (
        Path(processed_dir)
        if processed_dir is not None
        else Path(project_config["paths"]["processed"])
    )
    project_root = Path(__file__).resolve().parents[2]
    model_dir = Path(models_dir) if models_dir is not None else project_root / "models"
    scaler_output = (
        Path(scaler_path) if scaler_path is not None else model_dir / "scaler.joblib"
    )
    if scaler_path is not None and scaler_output.exists():
        raise FileExistsError(f"Refus d’écraser le scaler existant : {scaler_output}.")
    report_file = (
        Path(report_path)
        if report_path is not None
        else project_root / "reports" / "normalization_report.md"
    )
    source_paths = {split: data_dir / f"{split}.parquet" for split in _SPLITS}
    for split, path in source_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Split final introuvable ({split}) : {path}.")

    features = _feature_columns(pq.ParquetFile(source_paths["train"]).schema_arrow)
    scaler = StandardScaler()
    train_rows = 0
    for values in _feature_batches(source_paths["train"], features, batch_size):
        prepared = _prepare_features(values, method)
        scaler.partial_fit(prepared)
        train_rows += len(prepared)
    if train_rows == 0:
        raise ValueError("Le split train est vide ; le scaler ne peut pas être ajusté.")
    if int(np.asarray(scaler.n_samples_seen_).max()) != train_rows:
        raise ValueError("Le scaler n’a pas été ajusté sur toutes les lignes train.")

    zero_variance = [
        feature for feature, variance in zip(features, scaler.var_) if variance == 0
    ]
    dataset_moments: dict[str, tuple[np.ndarray, np.ndarray, int]] = {}
    with TemporaryDirectory(prefix=".normalization-", dir=data_dir) as temporary:
        temporary_dir = Path(temporary)
        staged_paths = {
            split: temporary_dir / f"{split}.parquet" for split in _SPLITS
        }
        for split, source_path in source_paths.items():
            writer: pq.ParquetWriter | None = None
            totals = np.zeros(len(features), dtype=np.float64)
            squared_totals = np.zeros(len(features), dtype=np.float64)
            row_count = 0
            try:
                for batch in pq.ParquetFile(source_path).iter_batches(
                    batch_size=batch_size
                ):
                    frame = batch.to_pandas()
                    prepared = _prepare_features(
                        frame[features].to_numpy(dtype=np.float64, copy=False),
                        method,
                    )
                    transformed = scaler.transform(prepared).astype(np.float32)
                    if not np.isfinite(transformed).all():
                        raise ValueError(
                            f"Normalisation de {split} produite des valeurs non finies."
                        )
                    for index, feature in enumerate(features):
                        frame[feature] = transformed[:, index]
                    totals += transformed.sum(axis=0, dtype=np.float64)
                    squared_totals += np.square(transformed).sum(
                        axis=0, dtype=np.float64
                    )
                    row_count += len(frame)
                    table = pa.Table.from_pandas(frame, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(staged_paths[split], table.schema)
                    else:
                        table = table.cast(writer.schema)
                    writer.write_table(table, row_group_size=batch_size)
            finally:
                if writer is not None:
                    writer.close()
            if row_count != pq.ParquetFile(source_path).metadata.num_rows:
                raise ValueError(f"Nombre de lignes modifié pendant le traitement de {split}.")
            if row_count == 0:
                raise ValueError(f"Le split {split} est vide.")
            mean, standard_deviation = _dataset_moments(
                totals,
                squared_totals,
                row_count,
            )
            dataset_moments[split] = (mean, standard_deviation, row_count)

            frame = pd.read_parquet(staged_paths[split])
            validate_schema(frame, stage="final")
            if list(frame.columns) != list(pq.ParquetFile(source_path).schema_arrow.names):
                raise ValueError(f"Les colonnes de {split} ont changé.")
            if not frame["ts_end"].is_monotonic_increasing:
                raise ValueError(f"Le tri ts_end de {split} a été modifié.")

        train_mean, train_std, _ = dataset_moments["train"]
        nonconstant = np.asarray(scaler.var_) > 0
        if not np.allclose(train_mean[nonconstant], 0, atol=2e-5):
            raise ValueError("Les features train ne sont pas centrées après normalisation.")
        if not np.allclose(train_std[nonconstant], 1, atol=2e-5):
            raise ValueError("L’écart-type des features train normalisées n’est pas 1.")

        model_dir.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(prefix=".scaler-", dir=model_dir) as model_temporary:
            staged_model_dir = Path(model_temporary)
            staged_scaler = staged_model_dir / "scaler.joblib"
            staged_features = staged_model_dir / "features.json"
            joblib.dump(scaler, staged_scaler)
            if write_features:
                staged_features.write_text(
                    json.dumps(features, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            for split in _SPLITS:
                staged_paths[split].replace(source_paths[split])
            staged_scaler.replace(scaler_output)
            if write_features:
                staged_features.replace(model_dir / "features.json")

    report_lines = [
        "# Rapport de normalisation",
        "",
        f"- Méthode : `{method}`.",
        f"- Scaler ajusté uniquement sur train : {train_rows} lignes.",
        f"- Nombre de features : {len(features)}.",
        f"- Features à variance nulle dans train : {len(zero_variance)}.",
        "",
        "| Split | Lignes | Moyenne min | Moyenne max | Écart-type min | Écart-type max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for split in _SPLITS:
        mean, standard_deviation, count = dataset_moments[split]
        report_lines.append(
            f"| {split} | {count} | {mean.min():.8g} | {mean.max():.8g} | "
            f"{standard_deviation.min():.8g} | {standard_deviation.max():.8g} |"
        )
    report_lines.extend(["", "## Features à variance nulle", ""])
    report_lines.extend(
        [f"- `{feature}` (scale=1, non divisée par zéro)" for feature in zero_variance]
        or ["Aucune."]
    )
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    features_path = model_dir / "features.json"
    print(
        f"Scaler ajusté sur {train_rows} lignes train ; "
        f"{len(features)} features, {len(zero_variance)} à variance nulle."
    )
    print(f"Scaler : {scaler_output}")
    if write_features:
        print(f"Features : {features_path}")
    print(f"Rapport : {report_file}")
    return scaler_output, features_path, report_file, dataset_moments
