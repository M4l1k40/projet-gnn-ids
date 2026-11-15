"""K-fold chronologique par segments, avec purge temporelle."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.config import load_config

_KEY_COLUMNS = ("flow_id", "day", "label_multi", "ts_end")
_BATCH_SIZE = 50_000
_TIME_TOLERANCE_SECONDS = 1e-5


def _assign_folds(
    keys: pd.DataFrame,
    k: int,
    purge_minutes: float,
) -> tuple[np.ndarray, np.ndarray]:
    if keys[list(_KEY_COLUMNS)].isna().any().any():
        raise ValueError("Le train contient des clés de pli manquantes.")
    timestamps = pd.to_numeric(keys["ts_end"], errors="coerce").to_numpy(
        dtype=np.float64
    )
    if not np.isfinite(timestamps).all():
        raise ValueError("ts_end du train contient des valeurs non finies.")
    day_values = keys["day"].astype(str).to_numpy()
    fold_ids = np.full(len(keys), -1, dtype=np.int8)

    for indexes in keys.groupby(
        ["day", "label_multi"],
        sort=False,
        observed=True,
    ).indices.values():
        indexes = np.asarray(indexes, dtype=np.int64)
        ordered = indexes[np.argsort(timestamps[indexes], kind="stable")]
        for fold, chunk in enumerate(np.array_split(ordered, k)):
            fold_ids[chunk] = fold
    if np.any(fold_ids < 0):
        raise ValueError("Un ou plusieurs flux n’ont reçu aucun pli.")

    purge_seconds = purge_minutes * 60
    purged = np.zeros((k, len(keys)), dtype=bool)
    if purge_seconds == 0:
        return fold_ids, purged

    for day in pd.unique(day_values):
        day_indexes = np.flatnonzero(day_values == day)
        day_folds = fold_ids[day_indexes]
        for fold in range(k):
            validation_indexes = day_indexes[day_folds == fold]
            training_candidates = day_indexes[day_folds != fold]
            if not len(validation_indexes) or not len(training_candidates):
                continue
            validation_times = np.sort(timestamps[validation_indexes])
            candidate_times = timestamps[training_candidates]
            positions = np.searchsorted(validation_times, candidate_times)
            nearest = np.full(len(candidate_times), np.inf, dtype=np.float64)
            has_left = positions > 0
            if has_left.any():
                nearest[has_left] = np.minimum(
                    nearest[has_left],
                    candidate_times[has_left]
                    - validation_times[positions[has_left] - 1],
                )
            has_right = positions < len(validation_times)
            if has_right.any():
                nearest[has_right] = np.minimum(
                    nearest[has_right],
                    validation_times[positions[has_right]]
                    - candidate_times[has_right],
                )
            purged[fold, training_candidates] = (
                nearest + _TIME_TOLERANCE_SECONDS < purge_seconds
            )
    return fold_ids, purged


def _fold_report(
    labels: np.ndarray,
    fold_ids: np.ndarray,
    purged: np.ndarray,
    k: int,
    report_path: Path,
) -> list[dict[str, Any]]:
    all_classes = sorted(set(labels))
    missing_by_fold: list[dict[str, Any]] = []
    lines = [
        "# Validation croisée purgée sur train",
        "",
        f"- Plis : {k}.",
        "- Les segments sont `(day, label_multi)` (BENIGN est segmenté par jour), triés "
        "par `ts_end` puis divisés en morceaux contigus de taille aussi égale que possible.",
        "- Pour chaque pli, les lignes de son morceau sont la validation; les flux d’autres "
        "classes du même jour à moins de la purge temporelle sont exclus du train.",
        "- Les lignes de validation ne sont jamais marquées purgées dans leur pli.",
        "",
        "| Pli | Classe | Train | Validation | Purgés |",
        "|---:|---|---:|---:|---:|",
    ]
    for fold in range(k):
        validation = fold_ids == fold
        excluded = purged[fold]
        training = ~validation & ~excluded
        present_validation = set(labels[validation])
        missing = sorted(set(all_classes) - present_validation)
        missing_by_fold.append({"fold": fold, "classes_absentes": missing})
        for label in all_classes:
            class_rows = labels == label
            lines.append(
                f"| {fold} | {label} | "
                f"{int(np.count_nonzero(training & class_rows))} | "
                f"{int(np.count_nonzero(validation & class_rows))} | "
                f"{int(np.count_nonzero(excluded & class_rows))} |"
            )
        lines.append("")
        lines.append(
            f"- Pli {fold}, classes absentes de la validation : "
            + (", ".join(missing) if missing else "aucune")
            + "."
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return missing_by_fold


def build_cv_folds(
    config: dict[str, Any] | None = None,
    *,
    train_path: str | Path | None = None,
    output_path: str | Path | None = None,
    report_path: str | Path | None = None,
    batch_size: int = _BATCH_SIZE,
) -> tuple[Path, Path, list[dict[str, Any]]]:
    """Create fold and purge columns aligned to train.parquet row order."""
    project_config = load_config() if config is None else config
    processed_dir = Path(project_config["paths"]["processed"])
    project_root = processed_dir.parent.parent
    cv_config = project_config["cv"]
    k = int(cv_config["k"])
    purge_minutes = float(cv_config["purge_minutes"])
    if k < 2:
        raise ValueError("cv.k doit être au moins égal à 2.")
    if not np.isfinite(purge_minutes) or purge_minutes < 0:
        raise ValueError("cv.purge_minutes doit être positif ou nul et fini.")
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")
    source_path = (
        Path(train_path) if train_path is not None else processed_dir / "train.parquet"
    )
    folds_path = (
        Path(output_path) if output_path is not None else processed_dir / "folds.parquet"
    )
    report = (
        Path(report_path)
        if report_path is not None
        else project_root / "reports" / "cv_folds.md"
    )
    if not source_path.exists():
        raise FileNotFoundError(f"train.parquet introuvable : {source_path}.")

    source = pq.ParquetFile(source_path)
    key_batches = [
        batch.to_pandas()
        for batch in source.iter_batches(
            columns=list(_KEY_COLUMNS),
            batch_size=batch_size,
        )
    ]
    if not key_batches:
        raise ValueError(f"{source_path} est vide.")
    keys = pd.concat(key_batches, ignore_index=True)
    del key_batches
    if len(keys) != source.metadata.num_rows:
        raise ValueError("Lecture incomplète des clés de train.")
    fold_ids, purged = _assign_folds(keys, k, purge_minutes)
    labels = keys["label_multi"].astype(str).to_numpy()
    missing_by_fold = _fold_report(labels, fold_ids, purged, k, report)

    folds_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".cv-folds-", dir=folds_path.parent) as temp_dir:
        staged_path = Path(temp_dir) / folds_path.name
        writer: pq.ParquetWriter | None = None
        row_offset = 0
        try:
            for batch in source.iter_batches(
                columns=["flow_id"],
                batch_size=batch_size,
            ):
                flow_ids = batch.column(0).to_pylist()
                row_end = row_offset + len(flow_ids)
                frame_data: dict[str, Any] = {
                    "flow_id": pd.Series(flow_ids, dtype="string"),
                    "fold": fold_ids[row_offset:row_end],
                }
                for fold in range(k):
                    frame_data[f"purged_{fold}"] = purged[fold, row_offset:row_end]
                table = pa.Table.from_pandas(
                    pd.DataFrame(frame_data),
                    preserve_index=False,
                )
                if writer is None:
                    writer = pq.ParquetWriter(staged_path, table.schema)
                else:
                    table = table.cast(writer.schema)
                writer.write_table(table, row_group_size=batch_size)
                row_offset = row_end
        finally:
            if writer is not None:
                writer.close()

        if writer is None or row_offset != source.metadata.num_rows:
            raise ValueError(
                f"Nombre de lignes folds incorrect : {row_offset} au lieu de "
                f"{source.metadata.num_rows}."
            )
        staged_path.replace(folds_path)

    missing_count = sum(len(item["classes_absentes"]) for item in missing_by_fold)
    print(
        f"Écrit {source.metadata.num_rows} lignes et {k} plis; "
        f"{missing_count} absence(s) de classe validation cumulées."
    )
    return folds_path, report, missing_by_fold


def get_fold(
    k: int,
    config: dict[str, Any] | None = None,
    *,
    folds_path: str | Path | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Return row positions for train and validation in fold k.

    Positions are aligned with the row order of train.parquet. A row is excluded
    from training when its `purged_k` flag is true, but validation positions are
    never removed by the purge.
    """
    project_config = load_config() if config is None else config
    cv_config = project_config["cv"]
    k_count = int(cv_config["k"])
    if not 0 <= k < k_count:
        raise ValueError(f"k doit être compris entre 0 et {k_count - 1}.")
    configured_processed = Path(project_config["paths"]["processed"])
    source_path = (
        Path(folds_path)
        if folds_path is not None
        else configured_processed / "folds.parquet"
    )
    if not source_path.exists():
        raise FileNotFoundError(f"Fichier de plis introuvable : {source_path}.")
    frame = pd.read_parquet(source_path, columns=["fold", f"purged_{k}"])
    validation_mask = frame["fold"].to_numpy(dtype=np.int8) == k
    purged_mask = frame[f"purged_{k}"].to_numpy(dtype=bool)
    training_mask = ~validation_mask & ~purged_mask
    return np.flatnonzero(training_mask), np.flatnonzero(validation_mask)


if __name__ == "__main__":
    build_cv_folds()
