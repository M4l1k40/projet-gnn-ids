"""Construction isolée du split V3 et de ses artefacts de contrôle."""

import json
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from src.data.final_split import (
    _BATCH_SIZE,
    _KEY_COLUMNS,
    _META_COLUMNS,
    _SPLITS,
    _enforce_class_gaps,
    _final_columns,
)
from src.data.folds import build_cv_folds
from src.data.leakage import (
    _feature_columns,
    _read_split,
    _seen_in_train,
    _train_hashes,
    _write_seen_flags_to_meta,
)
from src.data.normalize import normalize_final_data
from src.data.schema import validate_schema
from src.data.split import assign_split_segment
from src.utils.config import load_config

_GAP_TOLERANCE_SECONDS = 1e-5
_MIRROR_IPS = ("192.168.10.50", "172.16.0.1")


def _project_root(config: dict[str, Any]) -> Path:
    return Path(config["paths"]["processed"]).resolve().parent.parent


def _configured_path(config: dict[str, Any], key: str) -> Path:
    value = config["paths"].get(key)
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(f"Chemin de configuration manquant : paths.{key}.")
    path = Path(value)
    return path.resolve() if path.is_absolute() else (_project_root(config) / path).resolve()


def _official_window_config(config: dict[str, Any]) -> dict[str, Any]:
    path = _configured_path(config, "attack_windows")
    if not path.exists():
        raise FileNotFoundError(f"Configuration des fenêtres introuvable : {path}.")
    windows = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(windows, dict) or not isinstance(windows.get("windows"), dict):
        raise ValueError(f"Configuration de fenêtres invalide : {path}.")
    return windows


def build_v3_splits(
    config: dict[str, Any] | None = None,
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path | None = None,
    batch_size: int = _BATCH_SIZE,
) -> dict[str, Any]:
    """Écrit les splits V3 dans leur dossier dédié sans remplacer aucun artefact."""
    project_config = load_config() if config is None else config
    split_config = project_config["split"]
    final_config = split_config["final"]
    ownership = final_config.get("benign_ownership", "class_range")
    if ownership != "official_window":
        raise ValueError(
            "La construction V3 exige split.final.benign_ownership='official_window'."
        )
    gap_minutes = float(final_config["gap_minutes"])
    if not np.isfinite(gap_minutes) or gap_minutes < 0:
        raise ValueError("split.final.gap_minutes doit être positif ou nul et fini.")
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")

    source_path = (
        Path(input_path)
        if input_path is not None
        else Path(project_config["paths"]["interim"]) / "clean.parquet"
    )
    destination_dir = (
        Path(output_dir)
        if output_dir is not None
        else _configured_path(project_config, "processed_v3")
    ).resolve()
    v2_dir = Path(project_config["paths"]["processed"]).resolve()
    if destination_dir == v2_dir:
        raise ValueError("Le dossier V3 doit être distinct du dossier processed V2.")
    if not source_path.exists():
        raise FileNotFoundError(f"Parquet source introuvable : {source_path}.")
    targets = [destination_dir / f"{name}.parquet" for name in (*_SPLITS, "meta")]
    existing = [path for path in targets if path.exists()]
    if existing:
        raise FileExistsError(
            "Refus d’écraser des sorties V3 existantes : "
            + ", ".join(str(path) for path in existing)
            + "."
        )

    source = pq.ParquetFile(source_path)
    final_columns, _ = _final_columns(source.schema_arrow)
    key_batches = [
        batch.to_pandas()
        for batch in source.iter_batches(
            columns=list(dict.fromkeys((*_KEY_COLUMNS, "flow_id"))),
            batch_size=batch_size,
        )
    ]
    if not key_batches:
        raise ValueError(f"Parquet source vide : {source_path}.")
    keys = pd.concat(key_batches, ignore_index=True)
    del key_batches
    if len(keys) != source.metadata.num_rows:
        raise ValueError("Le nombre de clés lues ne correspond pas au Parquet source.")
    if keys["flow_id"].duplicated().any():
        raise ValueError("clean.parquet contient des flow_id dupliqués.")
    if not pd.to_numeric(keys["ts_end"], errors="coerce").is_monotonic_increasing:
        raise ValueError("clean.parquet doit être trié par ts_end croissant.")

    window_config = _official_window_config(project_config)
    assignments, _ = assign_split_segment(
        keys,
        ratios=split_config,
        gap_minutes=gap_minutes,
        benign_ownership=ownership,
        official_windows=window_config["windows"],
        tolerance_minutes=float(window_config.get("tolerance_minutes", 0)),
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
        raise ValueError("Le split V3 doit contenir au moins une ligne par bloc.")

    destination_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".split-v3-", dir=destination_dir) as temporary:
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
                split_values = assignments.iloc[row_offset:row_end].astype(str).to_numpy()
                if len(split_values) != len(frame):
                    raise ValueError("Les affectations V3 ne correspondent pas aux lignes source.")
                frame["split"] = pd.Categorical(
                    split_values,
                    categories=list(_SPLITS),
                )
                kept = split_values != "gap"
                meta = frame.loc[kept, list(_META_COLUMNS)]
                if not meta.empty:
                    table = pa.Table.from_pandas(meta, preserve_index=False)
                    if meta_writer is None:
                        meta_writer = pq.ParquetWriter(staged_paths["meta"], table.schema)
                    else:
                        table = table.cast(meta_writer.schema)
                    meta_writer.write_table(table, row_group_size=batch_size)
                for split in _SPLITS:
                    selected = split_values == split
                    if not selected.any():
                        continue
                    table = pa.Table.from_pandas(
                        frame.loc[selected, final_columns],
                        preserve_index=False,
                    )
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
            raise ValueError("Un ou plusieurs Parquets V3 n’ont pas été écrits.")
        for split in _SPLITS:
            frame = pd.read_parquet(staged_paths[split])
            if list(frame.columns) != final_columns:
                raise ValueError(f"Colonnes V3 finales inattendues dans {split}.")
            validate_schema(frame, stage="final")
            if not frame["ts_end"].is_monotonic_increasing:
                raise ValueError(f"{split}.parquet V3 n’est pas trié par ts_end.")
        if sum(assignment_counts.values()) + gap_count != source.metadata.num_rows:
            raise ValueError("La conservation des lignes du split V3 est invalide.")
        if pq.ParquetFile(staged_paths["meta"]).metadata.num_rows != sum(
            assignment_counts.values()
        ):
            raise ValueError("Le nombre de lignes de meta.parquet V3 est invalide.")
        for name in (*_SPLITS, "meta"):
            staged_paths[name].replace(destination_dir / f"{name}.parquet")

    return {
        "processed_dir": destination_dir,
        "assignments": assignments.astype(str).to_numpy(),
        "gaps_by_day": gaps_by_day,
        "block_counts": dict(assignment_counts),
        "gap_count": gap_count,
        "source_rows": source.metadata.num_rows,
    }


def _populate_seen_flags(processed_dir: Path) -> None:
    train_path = processed_dir / "train.parquet"
    train_schema = pq.ParquetFile(train_path).schema_arrow
    features = _feature_columns(train_schema)
    train = _read_split(train_path, features)
    hashes, _ = _train_hashes(train, features)
    del train
    seen_by_flow_id: dict[str, bool] = {}
    for split in ("val", "test"):
        frame = _read_split(processed_dir / f"{split}.parquet", features)
        seen = _seen_in_train(frame, hashes, features)
        seen_by_flow_id.update(
            {
                str(flow_id): bool(value)
                for flow_id, value in zip(
                    seen["flow_id"],
                    seen["seen_in_train"],
                )
            }
        )
        del frame, seen
    _write_seen_flags_to_meta(processed_dir / "meta.parquet", seen_by_flow_id)


def _block_assignments(
    source_ids: pd.Series,
    processed_dir: Path,
) -> np.ndarray:
    result = np.full(len(source_ids), "gap", dtype=object)
    id_index = pd.Index(source_ids)
    for split in _SPLITS:
        split_ids = pd.read_parquet(
            processed_dir / f"{split}.parquet",
            columns=["flow_id"],
        )["flow_id"]
        positions = id_index.get_indexer(split_ids)
        if np.any(positions < 0):
            raise ValueError(f"Un flux de {split} est absent de clean.parquet.")
        if np.any(result[positions] != "gap"):
            raise ValueError("Un flow_id apparaît dans plusieurs blocs.")
        result[positions] = split
    return result


def _mirror_distribution(
    frame: pd.DataFrame,
    candidate_mask: np.ndarray,
    block_values: np.ndarray,
) -> tuple[int, dict[str, int], int]:
    candidates = np.flatnonzero(candidate_mask)
    endpoint_mask = (
        frame["src_ip"].isin(_MIRROR_IPS)
        & frame["dst_ip"].isin(_MIRROR_IPS)
        & frame["src_ip"].ne(frame["dst_ip"])
    )
    pool = frame.loc[
        endpoint_mask,
        ["src_ip", "dst_ip", "src_port", "dst_port", "ts_end"],
    ].copy()
    pool["block"] = block_values[np.flatnonzero(endpoint_mask.to_numpy())]
    groups: dict[tuple[Any, ...], tuple[np.ndarray, np.ndarray]] = {}
    for key, group in pool.groupby(
        ["src_ip", "dst_ip", "src_port", "dst_port"],
        sort=False,
        observed=True,
    ):
        ordered = group.sort_values("ts_end", kind="stable")
        groups[key] = (
            ordered["ts_end"].to_numpy(dtype=np.float64),
            ordered["block"].to_numpy(dtype=object),
        )

    counts: Counter[str] = Counter()
    for index in candidates:
        row = frame.iloc[index]
        reverse = (
            row["dst_ip"],
            row["src_ip"],
            row["dst_port"],
            row["src_port"],
        )
        match = groups.get(reverse)
        if match is None:
            counts["introuvable"] += 1
            continue
        times, blocks = match
        timestamp = float(row["ts_end"])
        insertion = int(np.searchsorted(times, timestamp))
        nearby = [
            position
            for position in (insertion - 1, insertion)
            if 0 <= position < len(times) and abs(times[position] - timestamp) <= 130
        ]
        if not nearby:
            counts["introuvable"] += 1
            continue
        nearest = min(nearby, key=lambda position: abs(times[position] - timestamp))
        counts[str(blocks[nearest])] += 1
    distribution = {
        block: int(counts[block])
        for block in ("train", "val", "test", "gap", "introuvable")
    }
    cross_block = sum(
        distribution[block] for block in ("train", "val", "gap")
    )
    return len(candidates), distribution, cross_block


def _mirror_report(
    config: dict[str, Any],
    current_blocks: np.ndarray,
    v3_blocks: np.ndarray,
) -> list[str]:
    processed = Path(config["paths"]["processed"])
    clean_path = Path(config["paths"]["interim"]) / "clean.parquet"
    frame = pd.read_parquet(
        clean_path,
        columns=[
            "flow_id",
            "src_ip",
            "dst_ip",
            "src_port",
            "dst_port",
            "ts_end",
        ],
    )
    if len(frame) != len(current_blocks) or len(frame) != len(v3_blocks):
        raise ValueError("Les vecteurs de blocs ne sont pas alignés sur clean.parquet.")
    audit = pd.read_parquet(
        processed / "label_audit.parquet",
        columns=["flow_id", "label_rule"],
    )
    labels = pd.read_parquet(
        processed / "labels_v2.parquet",
        columns=["flow_id", "v2_family"],
    )
    if not labels["flow_id"].is_unique or not audit["flow_id"].is_unique:
        raise ValueError("Les clés d’audit ou de labels v2 ne sont pas uniques.")
    frame = frame.merge(audit, on="flow_id", how="left", validate="one_to_one")
    frame = frame.merge(labels, on="flow_id", how="left", validate="one_to_one")
    hulk = frame["label_rule"].isin(["DoS Hulk", "DoS Hulk - Attempted"]).to_numpy()
    server = frame["v2_family"].eq("server_response").to_numpy()
    lines: list[str] = []
    for label, candidate in (
        ("server_response", server),
        ("DoS Hulk (+ Attempted)", hulk),
    ):
        current_test = candidate & (current_blocks == "test")
        v3_test = candidate & (v3_blocks == "test")
        current = _mirror_distribution(frame, current_test, current_blocks)
        v3 = _mirror_distribution(frame, v3_test, v3_blocks)
        lines.append(
            f"| {label} | {current[0]} | "
            f"{current[1]['train']}/{current[1]['val']}/{current[1]['test']}/"
            f"{current[1]['gap']}/{current[1]['introuvable']} | {current[2]} | "
            f"{v3[0]} | {v3[1]['train']}/{v3[1]['val']}/{v3[1]['test']}/"
            f"{v3[1]['gap']}/{v3[1]['introuvable']} | {v3[2]} |"
        )
    return lines


def _robust_window_rows(
    frame: pd.DataFrame,
    windows_config: dict[str, Any],
) -> list[str]:
    official: dict[tuple[str, str], list[list[str]]] = {}
    for day, classes in windows_config["windows"].items():
        for label, spans in classes.items():
            official[(str(day), str(label).casefold())] = spans
    tolerance = float(windows_config.get("tolerance_minutes", 0))
    rows: list[str] = []
    attacks = frame.loc[frame["label_multi"].ne("BENIGN")]
    for (day, label), group in attacks.groupby(
        ["day", "label_multi"],
        sort=True,
        observed=True,
    ):
        spans = official.get((str(day), str(label).casefold()))
        if not spans:
            rows.append(f"| {day} | {label} | non configurée | — | — | — |")
            continue
        local_date = pd.to_datetime(group["ts_end"].iloc[0], unit="s").normalize()
        official_starts: list[pd.Timestamp] = []
        official_ends: list[pd.Timestamp] = []
        for start, end in spans:
            official_starts.append(
                pd.Timestamp(f"{local_date.date()} {start}")
                - pd.Timedelta(minutes=tolerance)
            )
            official_ends.append(
                pd.Timestamp(f"{local_date.date()} {end}")
                + pd.Timedelta(minutes=tolerance)
            )
        robust = pd.to_datetime(group["ts_end"], unit="s")
        q005 = robust.quantile(0.005)
        q995 = robust.quantile(0.995)
        official_start = min(official_starts)
        official_end = max(official_ends)
        early = max(0.0, (official_start - q005).total_seconds() / 60)
        late = max(0.0, (q995 - official_end).total_seconds() / 60)
        deviation = max(early, late)
        note = "ALERTE >5 min" if deviation > 5 else "OK"
        rows.append(
            f"| {day} | {label} | {q005:%H:%M:%S}–{q995:%H:%M:%S} | "
            f"{official_start:%H:%M}–{official_end:%H:%M} | "
            f"{early:.2f}/{late:.2f} | {note} |"
        )
    return rows


def _write_split_report(
    config: dict[str, Any],
    assignments: np.ndarray,
    gaps_by_day: dict[str, int],
    gap_count: int,
) -> Path:
    processed = Path(config["paths"]["processed"])
    v3_dir = _configured_path(config, "processed_v3")
    report_path = _configured_path(config, "split_v3_report")
    if report_path.exists():
        raise FileExistsError(f"Refus d’écraser le rapport existant : {report_path}.")
    source_path = Path(config["paths"]["interim"]) / "clean.parquet"
    keys = pd.read_parquet(
        source_path,
        columns=["flow_id", "day", "ts_end", "label_multi"],
    )
    current_blocks = _block_assignments(keys["flow_id"], processed)
    v3_blocks = assignments
    if len(keys) != len(v3_blocks):
        raise ValueError("Le split V3 n’est pas aligné sur la source.")

    current_counts = pd.crosstab(keys["label_multi"], current_blocks)
    v3_counts = pd.crosstab(keys["label_multi"], v3_blocks)
    current_counts = current_counts.reindex(columns=[*_SPLITS, "gap"], fill_value=0)
    v3_counts = v3_counts.reindex(columns=[*_SPLITS, "gap"], fill_value=0)
    attack_classes = sorted(keys.loc[keys["label_multi"].ne("BENIGN"), "label_multi"].unique())
    for label in attack_classes:
        if not np.array_equal(
            current_counts.loc[label, list(_SPLITS)].to_numpy(),
            v3_counts.loc[label, list(_SPLITS)].to_numpy(),
        ):
            raise ValueError(
                f"Les effectifs d’attaque de {label} diffèrent entre V2 et V3."
            )

    unique_ids = pd.concat(
        [
            pd.read_parquet(v3_dir / f"{split}.parquet", columns=["flow_id"])["flow_id"]
            for split in _SPLITS
        ],
        ignore_index=True,
    )
    if unique_ids.duplicated().any():
        raise ValueError("Un flow_id V3 apparaît plusieurs fois ou dans plusieurs blocs.")
    source_id_index = pd.Index(keys["flow_id"])
    if (
        len(unique_ids) != int(np.count_nonzero(v3_blocks != "gap"))
        or np.any(source_id_index.get_indexer(unique_ids) < 0)
    ):
        raise ValueError("Les flow_id des Parquets V3 diffèrent des flux non-gap.")
    labels_v2_ids = pd.Index(
        pd.read_parquet(processed / "labels_v2.parquet", columns=["flow_id"])[
            "flow_id"
        ]
    )
    if not labels_v2_ids.is_unique:
        raise ValueError("labels_v2.parquet contient des flow_id dupliqués.")
    missing_labels = ~keys["flow_id"].isin(labels_v2_ids).to_numpy()
    missing_v3_labels = missing_labels & np.isin(v3_blocks, _SPLITS)
    missing_label_counts = (
        pd.DataFrame(
            {
                "block": v3_blocks[missing_v3_labels],
                "label_multi": keys.loc[missing_v3_labels, "label_multi"].to_numpy(),
            }
        )
        .groupby(["block", "label_multi"], observed=True)
        .size()
    )
    missing_labels_by_block = {
        split: int(
            sum(
                count
                for (block, _), count in missing_label_counts.items()
                if block == split
            )
        )
        for split in _SPLITS
    }

    features_file = _configured_path(config, "feature_list")
    if not features_file.exists():
        raise FileNotFoundError(f"Liste des features introuvable : {features_file}.")
    features = json.loads(features_file.read_text(encoding="utf-8"))
    if not isinstance(features, list) or not features:
        raise ValueError("La liste des features existante est invalide.")
    v3_schema = pq.ParquetFile(v3_dir / "train.parquet").schema_arrow
    if _feature_columns(v3_schema) != features:
        raise ValueError("Les features V3 ne correspondent pas à la liste existante.")
    for split in _SPLITS:
        frame = pd.read_parquet(v3_dir / f"{split}.parquet")
        validate_schema(frame, stage="final")
        if frame["flow_id"].duplicated().any():
            raise ValueError(f"flow_id dupliqué dans le bloc V3 {split}.")
        if list(frame["split"].astype(str).unique()) != [split]:
            raise ValueError(f"La colonne split est incohérente dans le bloc V3 {split}.")
        if [column for column in features if column in frame.columns] != features:
            raise ValueError("Les features V3 diffèrent de la liste de features existante.")

    retained = [
        label
        for label in sorted(v3_counts.index)
        if int(v3_counts.loc[label, "train"]) >= 50
        and int(v3_counts.loc[label, "test"]) >= 50
    ]
    missing_retained = set(retained) - set(current_counts.index)
    if missing_retained:
        raise ValueError("Une classe retenue V3 est absente de V2.")

    fold_frame = pd.read_parquet(v3_dir / "folds.parquet")
    train_labels = pd.read_parquet(
        v3_dir / "train.parquet",
        columns=["flow_id", "label_multi"],
    )
    if not np.array_equal(fold_frame["flow_id"].to_numpy(), train_labels["flow_id"].to_numpy()):
        raise ValueError("folds.parquet V3 n’est pas aligné sur train.parquet.")
    fold_counts = pd.crosstab(train_labels["label_multi"], fold_frame["fold"])
    seen_meta = pd.read_parquet(
        v3_dir / "meta.parquet",
        columns=["flow_id", "seen_in_train"],
    )
    if seen_meta["flow_id"].duplicated().any():
        raise ValueError("meta.parquet V3 contient des flow_id dupliqués.")
    v3_lookup = pd.concat(
        [
            pd.read_parquet(
                v3_dir / f"{split}.parquet",
                columns=["flow_id", "label_multi"],
            ).assign(split=split)
            for split in ("val", "test")
        ],
        ignore_index=True,
    ).merge(seen_meta, on="flow_id", how="left", validate="one_to_one")
    if v3_lookup["seen_in_train"].isna().any():
        raise ValueError("seen_in_train manque en val/test dans meta.parquet V3.")
    seen_rates = (
        v3_lookup.groupby(["split", "label_multi"], observed=True)["seen_in_train"]
        .agg(["count", "mean"])
        .sort_index()
    )

    benign_rows = []
    for day in sorted(keys["day"].astype(str).unique()):
        mask = keys["day"].astype(str).eq(day).to_numpy() & keys["label_multi"].eq("BENIGN").to_numpy()
        current_benign = pd.Series(current_blocks[mask]).value_counts()
        v3_benign = pd.Series(v3_blocks[mask]).value_counts()
        benign_rows.append(
            f"| {day} | "
            + "/".join(
                str(int(current_benign.get(block, 0)))
                for block in (*_SPLITS, "gap")
            )
            + " | "
            + "/".join(
                str(int(v3_benign.get(block, 0)))
                for block in (*_SPLITS, "gap")
            )
            + " |"
        )
    benign_current = current_counts.loc["BENIGN", list((*_SPLITS, "gap"))]
    benign_v3 = v3_counts.loc["BENIGN", list((*_SPLITS, "gap"))]
    current_gap_by_day = (
        pd.DataFrame(
            {
                "day": keys["day"].astype(str),
                "gap": current_blocks == "gap",
            }
        )
        .groupby("day", sort=True)["gap"]
        .sum()
        .astype(int)
    )
    mirror_lines = _mirror_report(config, current_blocks, v3_blocks)
    windows_config = _official_window_config(config)
    robust_lines = _robust_window_rows(
        pd.read_parquet(source_path, columns=["day", "ts_end", "label_multi"]),
        windows_config,
    )

    assignment_frame = keys[["day", "label_multi", "ts_end"]].copy()
    assignment_frame["block"] = v3_blocks
    order = {"train": 0, "val": 1, "test": 2, "gap": 3}
    checks = 0
    for (_, label), group in assignment_frame.loc[
        assignment_frame["label_multi"].ne("BENIGN")
    ].groupby(["day", "label_multi"], sort=False, observed=True):
        ordered = group.sort_values("ts_end", kind="stable")
        timestamps = ordered["ts_end"].to_numpy(dtype=np.float64)
        blocks = ordered["block"].to_numpy(dtype=object)
        kept = np.flatnonzero(blocks != "gap")
        if len(kept) > 1:
            transitions = np.flatnonzero(blocks[kept[1:]] != blocks[kept[:-1]])
            for transition in transitions:
                left, right = kept[transition], kept[transition + 1]
                if order[blocks[left]] >= order[blocks[right]]:
                    raise ValueError(f"Ordre temporel invalide pour la classe {label}.")
                if (
                    timestamps[right] - timestamps[left] + _GAP_TOLERANCE_SECONDS
                    < float(config["split"]["final"]["gap_minutes"]) * 60
                ):
                    raise ValueError(f"Gap insuffisant pour la classe {label}.")
                checks += 1

    lines = [
        "# Split alternatif V3",
        "",
        "V3 conserve les coupures de chaque classe d’attaque. Seule la propriété des flux BENIGN change : "
        "ils héritent des coupures de la classe dont la fenêtre officielle, étendue de sa tolérance, "
        "les contient; en cas de chevauchement, la fenêtre la plus précoce gagne. Hors fenêtre, le split "
        "chronologique de référence du jour s’applique.",
        "",
        f"- Paramètre utilisé : `split.final.benign_ownership=official_window`; V2 garde son split d’origine.",
        f"- Lignes source : {len(keys)}; conservées V3 : {len(unique_ids)}; perdues en gap V3 : {gap_count}.",
        f"- Flux en gap V2 : {int((current_blocks == 'gap').sum())}; checks d’ordre/gap d’attaque passés : {checks}.",
        f"- Artefacts V3 : `{v3_dir}`; features inchangées : {len(features)}.",
        "",
        "## Couverture des labels v2",
        "",
        f"labels_v2 couvre {len(unique_ids) - int(missing_v3_labels.sum())} / {len(unique_ids)} "
        "flow_id conservés dans V3. Les identifiants absents sont rapportés ci-dessous; "
        "labels_v2.parquet n’est ni modifié ni complété.",
        "",
        "| Bloc V3 | flow_id absents de labels_v2 | Classes d’origine |",
        "|---|---:|---|",
        *[
            f"| {split} | {missing_labels_by_block[split]} | "
            + ", ".join(
                f"{label} ({int(count)})"
                for (block, label), count in missing_label_counts.items()
                if block == split
            )
            + " |"
            for split in _SPLITS
        ],
        f"| Total | {int(missing_v3_labels.sum())} | "
        + ", ".join(
            f"{label} ({int(count)})"
            for label, count in (
                keys.loc[missing_v3_labels, "label_multi"]
                .value_counts()
                .sort_index()
                .items()
            )
        )
        + " |",
        "",
        "## BENIGN par jour et bloc",
        "",
        "| Jour | V2 train/val/test/gap | V3 train/val/test/gap |",
        "|---|---:|---:|",
        *benign_rows,
        f"| Total | {'/'.join(str(int(benign_current[b])) for b in (*_SPLITS, 'gap'))} | "
        f"{'/'.join(str(int(benign_v3[b])) for b in (*_SPLITS, 'gap'))} |",
        "",
        "## Effectifs par classe et bloc",
        "",
        "| Classe d’origine | V2 train/val/test/gap | V3 train/val/test/gap |",
        "|---|---:|---:|",
    ]
    for label in sorted(v3_counts.index):
        lines.append(
            f"| {label} | "
            + "/".join(str(int(current_counts.loc[label, block])) for block in (*_SPLITS, "gap"))
            + " | "
            + "/".join(str(int(v3_counts.loc[label, block])) for block in (*_SPLITS, "gap"))
            + " |"
        )
    lines.extend(
        [
            "",
            "Classes avec au moins 50 flux train et test : "
            + ", ".join(retained)
            + ".",
            "",
            "## Paires miroir (flux test; blocs du flux aller)",
            "",
            "| Famille/règle | Candidats V2 | V2 train/val/test/gap/introuvable | Paires inter-blocs V2 | "
            "Candidats V3 | V3 train/val/test/gap/introuvable | Paires inter-blocs V3 |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *mirror_lines,
            "",
            "## Attaques par pli de train V3",
            "",
            "| Classe | Pli 0 | Pli 1 | Pli 2 | Pli 3 | Pli 4 | Total |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for label in sorted(
        fold_counts.index[fold_counts.index.to_series().ne("BENIGN")]
    ):
        counts = [
            int(fold_counts.loc[label, fold])
            if fold in fold_counts.columns
            else 0
            for fold in range(int(config["cv"]["k"]))
        ]
        lines.append(
            f"| {label} | "
            + " | ".join(str(count) for count in counts)
            + f" | {sum(counts)} |"
        )
    lines.extend(
        [
            "",
            "## seen_in_train V3 (proportion par classe)",
            "",
            "| Bloc | Classe | Effectif | seen_in_train |",
            "|---|---|---:|---:|",
        ]
    )
    for (split, label), row in seen_rates.iterrows():
        lines.append(
            f"| {split} | {label} | {int(row['count'])} | {100 * row['mean']:.3f} % |"
        )
    lines.extend(
        [
            "",
            "## Fenêtre officielle contre intervalle robuste [p0,5; p99,5]",
            "",
            "| Jour | Classe | Intervalle robuste | Officiel ± tolérance | Écart précoce/tardif (min) | Contrôle |",
            "|---|---|---|---|---:|---|",
            *robust_lines,
            "",
            "## Flux perdus en gap",
            "",
            f"- V2 : {int((current_blocks == 'gap').sum())} flux; V3 : {gap_count} flux.",
            "- Répartition V3 par classe : "
            + "; ".join(
                f"{label}={int(count)}"
                for label, count in pd.Series(
                    keys.loc[v3_blocks == "gap", "label_multi"]
                ).value_counts().sort_index().items()
            )
            + ".",
            "",
            "| Jour | V2 en gap | V3 en gap |",
            "|---|---:|---:|",
            *[
                f"| {day} | {int(current_gap_by_day.get(day, 0))} | "
                f"{int(gaps_by_day.get(day, 0))} |"
                for day in sorted(set(current_gap_by_day.index) | set(gaps_by_day))
            ],
            "",
            "Les prédictions, modèles, labels v2 et artefacts V2 ne sont pas modifiés; "
            "aucun entraînement n’est réalisé.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report_path


def build_split_v3(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Génère les splits, folds, scaler et contrôles V3 dans des chemins dédiés."""
    project_config = load_config() if config is None else config
    processed_v3 = _configured_path(project_config, "processed_v3")
    scaler_v3 = _configured_path(project_config, "scaler_v3")
    report_v3 = _configured_path(project_config, "split_v3_report")
    normalization_report = _configured_path(
        project_config,
        "normalization_v3_report",
    )
    feature_list = _configured_path(project_config, "feature_list")
    labels_v2 = Path(project_config["paths"]["processed"]) / "labels_v2.parquet"
    if not labels_v2.exists():
        raise FileNotFoundError(f"Labels v2 introuvables : {labels_v2}.")
    if scaler_v3.exists():
        raise FileExistsError(f"Refus d’écraser le scaler V3 existant : {scaler_v3}.")
    for path in (report_v3, normalization_report):
        if path.exists():
            raise FileExistsError(f"Refus d’écraser le rapport existant : {path}.")
    if not feature_list.exists():
        raise FileNotFoundError(f"Liste de features introuvable : {feature_list}.")
    original_features = json.loads(feature_list.read_text(encoding="utf-8"))

    built = build_v3_splits(project_config)
    v3_config = dict(project_config)
    v3_config["paths"] = dict(project_config["paths"])
    v3_config["paths"]["processed"] = processed_v3
    v3_config["paths"]["interim"] = Path(project_config["paths"]["interim"])
    scaler_path, _, _, _ = normalize_final_data(
        v3_config,
        processed_dir=processed_v3,
        models_dir=scaler_v3.parent,
        scaler_path=scaler_v3,
        write_features=False,
        report_path=normalization_report,
    )
    current_features = json.loads(feature_list.read_text(encoding="utf-8"))
    if current_features != original_features:
        raise ValueError("La liste de features a changé pendant la normalisation V3.")
    _populate_seen_flags(processed_v3)
    build_cv_folds(
        v3_config,
        train_path=processed_v3 / "train.parquet",
        output_path=processed_v3 / "folds.parquet",
        report_path=processed_v3 / "folds_report.md",
    )
    report_path = _write_split_report(
        project_config,
        built["assignments"],
        built["gaps_by_day"],
        built["gap_count"],
    )
    return {
        "processed_dir": processed_v3,
        "scaler_path": scaler_path,
        "report_path": report_path,
        "normalization_report": normalization_report,
        "block_counts": built["block_counts"],
        "gap_count": built["gap_count"],
    }


if __name__ == "__main__":
    result = build_split_v3()
    print(
        f"Split V3 écrit dans {result['processed_dir']} ; scaler : "
        f"{result['scaler_path']} ; rapport : {result['report_path']}."
    )
