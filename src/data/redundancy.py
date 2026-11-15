"""Flags de redondance des features entre les splits finaux."""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.schema import ID_COLS, META_COLS, TARGET_COLS
from src.utils.config import load_config

_SPLITS = ("train", "val", "test")
_BATCH_SIZE = 50_000
_EXPECTED_TEST_SAME_CLASS = 200_648


def _feature_columns(schema: pa.Schema) -> list[str]:
    excluded = set(ID_COLS + META_COLS + TARGET_COLS)
    features = [name for name in schema.names if name not in excluded]
    invalid = [
        name for name in features if not pa.types.is_float32(schema.field(name).type)
    ]
    if invalid:
        raise ValueError(
            "Features attendues en float32 : " + ", ".join(invalid) + "."
        )
    if not features:
        raise ValueError("Aucune feature disponible pour le diagnostic.")
    return features


def _rounded_hashes(
    batch: pd.DataFrame,
    features: list[str],
) -> list[bytes]:
    values = np.round(
        batch[features].to_numpy(dtype=np.float64),
        decimals=6,
    )
    values[values == 0] = 0.0
    return [row.tobytes() for row in np.ascontiguousarray(values)]


def _train_vector_index(
    train_path: Path,
    features: list[str],
    batch_size: int,
) -> tuple[dict[bytes, tuple[int, set[str]]], int]:
    train_file = pq.ParquetFile(train_path)
    vector_index: dict[bytes, tuple[int, set[str]]] = {}
    rows_seen = 0
    for batch in train_file.iter_batches(
        columns=features + ["label_multi"],
        batch_size=batch_size,
    ):
        frame = batch.to_pandas()
        if frame["label_multi"].isna().any():
            raise ValueError(f"{train_path} contient des label_multi manquants.")
        if not np.isfinite(frame[features].to_numpy(dtype=np.float64)).all():
            raise ValueError(f"{train_path} contient des features non finies.")
        labels = frame["label_multi"].astype(str).to_numpy()
        for vector, label in zip(_rounded_hashes(frame, features), labels):
            previous = vector_index.get(vector)
            if previous is None:
                vector_index[vector] = (1, {label})
            else:
                previous[1].add(label)
                vector_index[vector] = (previous[0] + 1, previous[1])
        rows_seen += len(frame)
    if rows_seen != train_file.metadata.num_rows:
        raise ValueError(f"{train_path} : lecture incomplète du split train.")
    return vector_index, rows_seen


def _write_report(
    report_path: Path,
    counts: Counter[tuple[str, str, str]],
    expected_test_same_class: int,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Redondance des vecteurs de features",
        "",
        "Les vecteurs sont comparés après arrondi de chaque feature à 6 décimales, "
        "comme dans le diagnostic de fuite. Le même vecteur est défini par ses octets "
        "contigus et les zéros signés sont normalisés.",
        "",
        "- `seen_in_train_any_label` : un vecteur identique existe dans train, quelle que soit sa classe.",
        "- `conflict_in_train` : le vecteur existe dans train sous une classe différente.",
        "- `train_dup_count` : nombre d’occurrences de ce vecteur dans le split train (0 si absent).",
        "",
        f"- Contrôle test/same-class : {expected_test_same_class:,} flux (attendu : "
        f"{_EXPECTED_TEST_SAME_CLASS:,}).",
        "",
        "| Split | Classe | Flux | Vecteur présent train | % présent | Conflit de classe | % conflit | Même classe | Train occurrences cumulées | Lignes avec doublon train |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    grouped: dict[tuple[str, str], dict[str, int]] = {}
    for (split, label, metric), count in counts.items():
        grouped.setdefault((split, label), {})[metric] = count
    for (split, label), values in sorted(grouped.items()):
        total = values.get("flows", 0)
        seen = values.get("seen_any", 0)
        conflict = values.get("conflict", 0)
        same = values.get("same_class", 0)
        duplicates = values.get("duplicate_rows", 0)
        dup_sum = values.get("train_dup_count_sum", 0)
        lines.append(
            f"| {split} | {label} | {total} | {seen} | "
            f"{100 * seen / total if total else 0:.4f} % | {conflict} | "
            f"{100 * conflict / total if total else 0:.4f} % | {same} | "
            f"{dup_sum} | {duplicates} |"
        )
    lines.extend(
        [
            "",
            "Les indicateurs sont des annotations de diagnostic : aucun flux n’est supprimé "
            "ni modifié. `train_dup_count` peut être utilisé pour pondérer ou dédupliquer "
            "l’entraînement au niveau de l’expérience.",
        ]
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_redundancy_flags(
    config: dict[str, Any] | None = None,
    *,
    processed_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    report_path: str | Path | None = None,
    batch_size: int = _BATCH_SIZE,
) -> tuple[Path, Path, dict[str, Any]]:
    """Write per-flow redundancy flags without changing the source splits."""
    project_config = load_config() if config is None else config
    configured_processed = Path(project_config["paths"]["processed"])
    data_dir = Path(processed_dir) if processed_dir is not None else configured_processed
    project_root = configured_processed.parent.parent
    result_path = (
        Path(output_path)
        if output_path is not None
        else data_dir / "redundancy_flags.parquet"
    )
    report = (
        Path(report_path)
        if report_path is not None
        else project_root / "reports" / "redundancy_report.md"
    )
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")
    paths = {split: data_dir / f"{split}.parquet" for split in _SPLITS}
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Splits finaux introuvables : " + ", ".join(missing))

    schema = pq.ParquetFile(paths["train"]).schema_arrow
    features = _feature_columns(schema)
    vector_index, train_rows = _train_vector_index(
        paths["train"],
        features,
        batch_size,
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter[tuple[str, str, str]] = Counter()
    same_class_total = 0
    total_rows = 0

    with TemporaryDirectory(prefix=".redundancy-", dir=result_path.parent) as temp_dir:
        staged_path = Path(temp_dir) / result_path.name
        writer: pq.ParquetWriter | None = None
        try:
            for split in _SPLITS:
                split_file = pq.ParquetFile(paths[split])
                split_schema = split_file.schema_arrow
                missing_columns = set(features + ["flow_id", "label_multi"]) - set(
                    split_schema.names
                )
                if missing_columns:
                    raise ValueError(
                        f"{paths[split]} : colonnes absentes : "
                        + ", ".join(sorted(missing_columns))
                        + "."
                    )
                for batch in split_file.iter_batches(
                    columns=["flow_id", "label_multi"] + features,
                    batch_size=batch_size,
                ):
                    frame = batch.to_pandas()
                    if frame[["flow_id", "label_multi"]].isna().any().any():
                        raise ValueError(
                            f"{paths[split]} contient flow_id ou label_multi manquant."
                        )
                    if not np.isfinite(frame[features].to_numpy(dtype=np.float64)).all():
                        raise ValueError(f"{paths[split]} contient des features non finies.")
                    labels = frame["label_multi"].astype(str).to_numpy()
                    vector_hashes = _rounded_hashes(frame, features)
                    seen = np.zeros(len(frame), dtype=bool)
                    conflict = np.zeros(len(frame), dtype=bool)
                    same_class = np.zeros(len(frame), dtype=bool)
                    duplicate_count = np.zeros(len(frame), dtype=np.int64)
                    for index, (vector_hash, label) in enumerate(
                        zip(vector_hashes, labels)
                    ):
                        indexed = vector_index.get(vector_hash)
                        if indexed is None:
                            continue
                        seen[index] = True
                        duplicate_count[index] = indexed[0]
                        same_class[index] = label in indexed[1]
                        conflict[index] = any(
                            train_label != label for train_label in indexed[1]
                        )
                        if split == "test" and same_class[index]:
                            same_class_total += 1
                    for label in np.unique(labels):
                        class_mask = labels == label
                        counts[(split, str(label), "flows")] += int(class_mask.sum())
                        counts[(split, str(label), "seen_any")] += int(
                            np.count_nonzero(seen & class_mask)
                        )
                        counts[(split, str(label), "conflict")] += int(
                            np.count_nonzero(conflict & class_mask)
                        )
                        counts[(split, str(label), "same_class")] += int(
                            np.count_nonzero(same_class & class_mask)
                        )
                        counts[(split, str(label), "train_dup_count_sum")] += int(
                            duplicate_count[class_mask].sum()
                        )
                        counts[(split, str(label), "duplicate_rows")] += int(
                            np.count_nonzero((duplicate_count > 1) & class_mask)
                        )

                    output = pd.DataFrame(
                        {
                            "flow_id": frame["flow_id"].astype("string"),
                            "split": pd.Series([split] * len(frame), dtype="string"),
                            "seen_in_train_any_label": seen,
                            "conflict_in_train": conflict,
                            "train_dup_count": duplicate_count,
                        }
                    )
                    table = pa.Table.from_pandas(output, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(staged_path, table.schema)
                    else:
                        table = table.cast(writer.schema)
                    writer.write_table(table, row_group_size=batch_size)
                    total_rows += len(frame)
        finally:
            if writer is not None:
                writer.close()

        expected_rows = sum(pq.ParquetFile(path).metadata.num_rows for path in paths.values())
        if writer is None or total_rows != expected_rows:
            raise ValueError(
                f"Nombre de lignes redundancy invalide : {total_rows} au lieu de "
                f"{expected_rows}."
            )
        staged_path.replace(result_path)

    _write_report(report, counts, same_class_total)
    summary = {
        "train_rows": train_rows,
        "output_rows": total_rows,
        "test_seen_same_class": same_class_total,
        "expected_test_seen_same_class": _EXPECTED_TEST_SAME_CLASS,
    }
    if same_class_total != _EXPECTED_TEST_SAME_CLASS and total_rows == 2_550_253:
        raise ValueError(
            "Contrôle de cohérence test/same-class échoué : "
            f"{same_class_total} au lieu de {_EXPECTED_TEST_SAME_CLASS}."
        )
    print(
        "Contrôle test vu dans train, même classe : "
        f"{same_class_total} (attendu : {_EXPECTED_TEST_SAME_CLASS})."
    )
    print(f"Écrit {total_rows} drapeaux dans {result_path}.")
    return result_path, report, summary


if __name__ == "__main__":
    build_redundancy_flags()
