"""Construction en flux des Parquets finaux et de leurs métadonnées."""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.schema import ID_COLS, META_COLS, TARGET_COLS, validate_schema
from src.data.split import assign_split_segment
from src.utils.config import load_config

_KEY_COLUMNS = ("day", "ts_end", "label_multi")
_META_COLUMNS = ("flow_id", "orig_flow_id", "source_file")
_BATCH_SIZE = 50_000
_SPLITS = ("train", "val", "test")
_GAP_TOLERANCE_SECONDS = 1e-5


def _final_columns(source_schema: pa.Schema) -> tuple[list[str], list[str]]:
    source_columns = set(source_schema.names)
    required = set(ID_COLS + TARGET_COLS + ["day", "orig_flow_id", "source_file"])
    missing = required - source_columns
    if missing:
        raise ValueError(
            "Colonnes absentes de clean.parquet : " + ", ".join(sorted(missing)) + "."
        )

    excluded = set(ID_COLS + TARGET_COLS + META_COLS + list(_META_COLUMNS[1:]))
    excluded.add("split")
    feature_columns = [
        column for column in source_schema.names if column not in excluded
    ]
    unknown_non_features = [
        column
        for column in feature_columns
        if not pa.types.is_float32(source_schema.field(column).type)
    ]
    if unknown_non_features:
        raise ValueError(
            "Features source non float32 : " + ", ".join(unknown_non_features) + "."
        )
    final_columns = ID_COLS + feature_columns + TARGET_COLS + ["split", "day"]
    return final_columns, feature_columns


def _enforce_class_gaps(
    frame: pd.DataFrame,
    assignments: pd.Series,
    gap_seconds: float,
) -> tuple[pd.Series, dict[str, int]]:
    """Retire les lignes autour des transitions qui restent trop proches."""
    result = assignments.copy()
    if gap_seconds > 0:
        for _, group in frame.groupby(
            ["day", "label_multi"],
            sort=False,
            observed=True,
        ):
            ordered = group.assign(
                _split_timestamp=pd.to_numeric(group["ts_end"], errors="coerce")
            ).sort_values("_split_timestamp", kind="stable")
            indexes = ordered.index
            timestamps = ordered["_split_timestamp"].to_numpy(dtype=np.float64)
            labels = result.loc[indexes].astype(str).to_numpy()
            while True:
                kept = np.flatnonzero(labels != "gap")
                if len(kept) < 2:
                    break
                differences = np.diff(timestamps[kept])
                transitions = labels[kept[1:]] != labels[kept[:-1]]
                violations = np.flatnonzero(
                    transitions
                    & (differences + _GAP_TOLERANCE_SECONDS < gap_seconds)
                )
                if not len(violations):
                    break
                changed = False
                for violation in violations:
                    left = timestamps[kept[violation]]
                    right = timestamps[kept[violation + 1]]
                    midpoint = (left + right) / 2
                    in_gap = (
                        (timestamps >= midpoint - gap_seconds / 2)
                        & (timestamps <= midpoint + gap_seconds / 2)
                        & (labels != "gap")
                    )
                    if in_gap.any():
                        labels[in_gap] = "gap"
                        changed = True
                if not changed:
                    raise ValueError("Impossible d’appliquer le gap par classe.")
            result.loc[indexes] = labels

    gaps_by_day = result.eq("gap").groupby(
        frame["day"],
        sort=True,
        observed=True,
    ).sum()
    return result, {str(day): int(count) for day, count in gaps_by_day.items()}


def build_final_splits(
    config: dict[str, Any] | None = None,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    batch_size: int = _BATCH_SIZE,
) -> tuple[dict[str, Path], dict[str, int], dict[str, int]]:
    """Construit les splits finaux en deux passes, sans charger les features en entier."""
    project_config = load_config() if config is None else config
    paths = project_config["paths"]
    split_config = project_config["split"]
    final_config = split_config["final"]
    if final_config["variant"] != "segment":
        raise ValueError("La variante split.final.variant doit être 'segment'.")
    gap_minutes = float(final_config["gap_minutes"])
    if not np.isfinite(gap_minutes) or gap_minutes < 0:
        raise ValueError("split.final.gap_minutes doit être positif ou nul et fini.")
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")

    source_path = (
        Path(input_path)
        if input_path is not None
        else Path(paths["interim"]) / "clean.parquet"
    )
    destination_dir = (
        Path(output_dir) if output_dir is not None else Path(paths["processed"])
    )
    if not source_path.exists():
        raise FileNotFoundError(f"Parquet source introuvable : {source_path}.")
    destination_dir.mkdir(parents=True, exist_ok=True)

    source = pq.ParquetFile(source_path)
    final_columns, _ = _final_columns(source.schema_arrow)
    key_batches = [
        batch.to_pandas()
        for batch in source.iter_batches(
            columns=list(_KEY_COLUMNS),
            batch_size=batch_size,
        )
    ]
    if not key_batches:
        raise ValueError(f"Parquet source vide : {source_path}.")
    keys = pd.concat(key_batches, ignore_index=True)
    del key_batches
    if len(keys) != source.metadata.num_rows:
        raise ValueError("Le nombre de clés lues ne correspond pas au Parquet source.")
    if not pd.to_numeric(keys["ts_end"], errors="coerce").is_monotonic_increasing:
        raise ValueError("clean.parquet doit être trié par ts_end croissant.")

    assignments, gaps_by_day = assign_split_segment(
        keys,
        ratios=split_config,
        gap_minutes=gap_minutes,
    )
    assignments, gaps_by_day = _enforce_class_gaps(
        keys,
        assignments,
        gap_seconds=gap_minutes * 60,
    )
    assignment_counts = Counter(assignments.astype(str).tolist())
    gap_count = assignment_counts.pop("gap", 0)
    for split in _SPLITS:
        assignment_counts.setdefault(split, 0)
    if any(assignment_counts[split] == 0 for split in _SPLITS):
        raise ValueError("Le split final doit contenir au moins une ligne par bloc.")

    with TemporaryDirectory(prefix=".final-split-", dir=destination_dir) as temporary:
        temporary_dir = Path(temporary)
        staged_paths = {
            split: temporary_dir / f"{split}.parquet" for split in _SPLITS
        }
        staged_paths["meta"] = temporary_dir / "meta.parquet"
        writers: dict[str, pq.ParquetWriter] = {}
        meta_writer: pq.ParquetWriter | None = None
        row_offset = 0
        try:
            for batch in source.iter_batches(batch_size=batch_size):
                frame = batch.to_pandas()
                row_end = row_offset + len(frame)
                batch_assignments = assignments.iloc[row_offset:row_end].astype(str)
                if len(batch_assignments) != len(frame):
                    raise ValueError("Les affectations ne correspondent pas aux lignes source.")
                split_values = batch_assignments.to_numpy(dtype=object)
                frame["split"] = pd.Categorical(
                    split_values,
                    categories=list(_SPLITS),
                )
                kept = split_values != "gap"
                meta = frame.loc[kept, list(_META_COLUMNS)]
                if not meta.empty:
                    meta_table = pa.Table.from_pandas(meta, preserve_index=False)
                    if meta_writer is None:
                        meta_writer = pq.ParquetWriter(
                            staged_paths["meta"], meta_table.schema
                        )
                    else:
                        meta_table = meta_table.cast(meta_writer.schema)
                    meta_writer.write_table(meta_table, row_group_size=batch_size)

                for split in _SPLITS:
                    selected = split_values == split
                    if not selected.any():
                        continue
                    output_frame = frame.loc[selected, final_columns]
                    table = pa.Table.from_pandas(output_frame, preserve_index=False)
                    if split not in writers:
                        writers[split] = pq.ParquetWriter(staged_paths[split], table.schema)
                    else:
                        table = table.cast(writers[split].schema)
                    writers[split].write_table(table, row_group_size=batch_size)
                row_offset = row_end
        finally:
            for writer in writers.values():
                writer.close()
            if meta_writer is not None:
                meta_writer.close()

        if row_offset != source.metadata.num_rows:
            raise ValueError(
                f"Nombre de lignes lu incorrect : {row_offset} au lieu de "
                f"{source.metadata.num_rows}."
            )
        if set(writers) != set(_SPLITS) or meta_writer is None:
            raise ValueError("Un ou plusieurs Parquets finaux n’ont pas été écrits.")

        for split in _SPLITS:
            frame = pd.read_parquet(staged_paths[split])
            if list(frame.columns) != final_columns:
                raise ValueError(f"Colonnes finales inattendues dans {split}.")
            validate_schema(frame, stage="final")
            if not frame["ts_end"].is_monotonic_increasing:
                raise ValueError(f"{split}.parquet n’est pas trié par ts_end.")
            print(
                f"validate_schema(stage='final') : {split}, "
                f"{len(frame)} lignes, OK."
            )

        kept_count = sum(assignment_counts.values())
        if kept_count + gap_count != source.metadata.num_rows:
            raise ValueError(
                f"Conservation invalide : {kept_count} conservés + {gap_count} gap "
                f"!= {source.metadata.num_rows} lignes source."
            )
        meta_rows = pq.ParquetFile(staged_paths["meta"]).metadata.num_rows
        if meta_rows != kept_count:
            raise ValueError(
                f"meta.parquet contient {meta_rows} lignes au lieu de {kept_count}."
            )

        output_paths: dict[str, Path] = {}
        for split in (*_SPLITS, "meta"):
            destination = destination_dir / f"{split}.parquet"
            staged_paths[split].replace(destination)
            output_paths[split] = destination

    print(
        "Conservation : "
        f"train={assignment_counts['train']}, val={assignment_counts['val']}, "
        f"test={assignment_counts['test']}, gap={gap_count}, "
        f"total={source.metadata.num_rows}."
    )
    print(f"Flux perdus dans les gaps par jour : {gaps_by_day}.")
    return output_paths, dict(assignment_counts), gaps_by_day
