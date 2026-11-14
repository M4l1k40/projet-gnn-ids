import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.data import build as data_build
from src.data.final_split import _enforce_class_gaps
from src.data.split import assign_split_segment
from src.data.schema import validate_schema
from src.utils.config import load_config

_SPLITS = ("train", "val", "test")


def test_force_build_recreates_seen_flag_after_final_split(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root = tmp_path / "project"
    module_path = project_root / "src" / "data" / "build.py"
    module_path.parent.mkdir(parents=True)
    monkeypatch.setattr(data_build, "__file__", str(module_path))
    interim = project_root / "data" / "interim"
    processed = project_root / "data" / "processed"
    reports = project_root / "reports"
    models = project_root / "models"
    configs = project_root / "configs"
    calls: list[str] = []

    def clean_raw(_config) -> None:
        calls.append("clean")
        interim.mkdir(parents=True, exist_ok=True)
        reports.mkdir(parents=True, exist_ok=True)
        (interim / "clean_raw.parquet").touch()
        (reports / "cleaning_report.md").touch()

    def build_timestamps(_config) -> None:
        calls.append("timestamps")
        (interim / "clean.parquet").touch()
        (interim / "clean_sample.parquet").touch()
        (reports / "timestamps_check.md").touch()

    def build_splits(_config) -> None:
        calls.append("split")
        processed.mkdir(parents=True, exist_ok=True)
        for split in ("train", "val", "test"):
            (processed / f"{split}.parquet").write_bytes(b"placeholder")
        meta = pa.table(
            {
                "flow_id": ["train-1", "test-1"],
                "orig_flow_id": ["original-1", "original-2"],
                "source_file": ["train.csv", "test.csv"],
            }
        )
        pq.write_table(meta, processed / "meta.parquet")

    def generate_classes(_config) -> None:
        calls.append("classes")
        configs.mkdir(parents=True, exist_ok=True)
        (configs / "classes.yaml").touch()

    def normalize(_config) -> None:
        calls.append("normalize")
        models.mkdir(parents=True, exist_ok=True)
        reports.mkdir(parents=True, exist_ok=True)
        (models / "scaler.joblib").touch()
        (models / "features.json").touch()
        (reports / "normalization_report.md").touch()

    def leakage(_config) -> None:
        calls.append("leakage")
        meta_path = processed / "meta.parquet"
        meta = pq.read_table(meta_path)
        assert "seen_in_train" not in meta.column_names
        meta = meta.append_column(
            "seen_in_train",
            pa.array([None, True], type=pa.bool_()),
        )
        pq.write_table(meta, meta_path)
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "leakage_report.md").touch()
        (reports / "leakage_report.csv").touch()
        (reports / "leakage_histogram.png").touch()

    def build_card(_config) -> Path:
        calls.append("data_card")
        card = reports / "data_card.md"
        card.parent.mkdir(parents=True, exist_ok=True)
        card.touch()
        return card

    monkeypatch.setattr(data_build, "clean_raw", clean_raw)
    monkeypatch.setattr(data_build, "build_clean_dataset", build_timestamps)
    monkeypatch.setattr(data_build, "build_final_splits", build_splits)
    monkeypatch.setattr(data_build, "generate_classes_config", generate_classes)
    monkeypatch.setattr(data_build, "normalize_final_data", normalize)
    monkeypatch.setattr(data_build, "run_leakage_diagnostics", leakage)
    monkeypatch.setattr(data_build, "build_data_card", build_card)

    data_build.build_pipeline(
        {"paths": {"interim": interim, "processed": processed}},
        force=True,
    )

    assert calls == [
        "clean",
        "timestamps",
        "split",
        "classes",
        "normalize",
        "leakage",
        "data_card",
    ]
    assert "seen_in_train" in pq.read_table(processed / "meta.parquet").column_names


def test_final_data_real_invariants() -> None:
    config = load_config()
    interim = Path(config["paths"]["interim"])
    processed = Path(config["paths"]["processed"])
    split_paths = {
        split: processed / f"{split}.parquet"
        for split in ("train", "val", "test")
    }
    meta_path = processed / "meta.parquet"
    clean_path = interim / "clean.parquet"
    if not all(path.exists() for path in (*split_paths.values(), meta_path, clean_path)):
        pytest.skip(
            "Les Parquets finaux et clean.parquet sont absents ; "
            "lancez `python -m src.data.build` pour les générer."
        )
    features_path = Path(__file__).resolve().parents[1] / "models" / "features.json"
    scaler_path = Path(__file__).resolve().parents[1] / "models" / "scaler.joblib"
    assert features_path.exists()
    assert scaler_path.exists()

    flow_ids: set[str] = set()
    key_frames: list[pd.DataFrame] = []
    split_rows: dict[str, int] = {}
    train_frame: pd.DataFrame | None = None
    for split, path in split_paths.items():
        frame = pd.read_parquet(path)
        validate_schema(frame, stage="final")
        assert frame["ts_end"].is_monotonic_increasing
        current_ids = set(frame["flow_id"].astype(str))
        assert flow_ids.isdisjoint(current_ids)
        flow_ids.update(current_ids)
        split_rows[split] = len(frame)
        key_frames.append(frame[["day", "ts_end", "label_multi", "split"]].copy())
        if split == "train":
            train_frame = frame
        else:
            del frame

    combined = pd.concat(key_frames, ignore_index=True)
    gap_seconds = float(config["split"]["final"]["gap_minutes"]) * 60
    for _, group in combined.groupby(["day", "label_multi"], observed=True):
        ordered = group.sort_values("ts_end", kind="stable")
        times = ordered["ts_end"].to_numpy(dtype=np.float64)
        split_values = ordered["split"].astype(str).to_numpy()
        changes = split_values[1:] != split_values[:-1]
        if changes.any():
            assert (np.diff(times)[changes] + 1e-5 >= gap_seconds).all()

    assert train_frame is not None
    features = json.loads(features_path.read_text(encoding="utf-8"))
    scaler = joblib.load(scaler_path)
    assert int(np.asarray(scaler.n_samples_seen_).max()) == split_rows["train"]
    means = train_frame[features].mean().to_numpy(dtype=np.float64)
    standard_deviations = train_frame[features].std(ddof=0).to_numpy(dtype=np.float64)
    assert np.isfinite(means).all() and np.isfinite(standard_deviations).all()
    nonconstant = np.asarray(scaler.var_) > 0
    assert np.allclose(means[nonconstant], 0, atol=2e-5)
    assert np.allclose(standard_deviations[nonconstant], 1, atol=2e-5)
    del train_frame
    del combined
    del key_frames

    clean_rows = pq.ParquetFile(clean_path).metadata.num_rows
    kept_rows = sum(split_rows.values())
    meta_file = pq.ParquetFile(meta_path)
    meta_rows = meta_file.metadata.num_rows
    assert meta_rows == kept_rows
    assert clean_rows == 2_827_677

    split_ids: dict[str, set[str]] = {}
    for split in ("val", "test"):
        split_ids[split] = {
            str(flow_id)
            for batch in pq.ParquetFile(
                processed / f"{split}.parquet"
            ).iter_batches(columns=["flow_id"], batch_size=50_000)
            for flow_id in batch.column(0).to_pylist()
        }
    test_seen_count = 0
    train_null_count = 0
    for batch in meta_file.iter_batches(
        columns=["flow_id", "seen_in_train"],
        batch_size=50_000,
    ):
        flow_ids = batch.column(0).to_pylist()
        seen_flags = batch.column(1).to_pylist()
        for flow_id, seen in zip(flow_ids, seen_flags):
            key = str(flow_id)
            if key in split_ids["test"]:
                split_ids["test"].remove(key)
                assert seen is not None
                test_seen_count += int(seen)
            elif key in split_ids["val"]:
                split_ids["val"].remove(key)
                assert seen is not None
            else:
                assert seen is None
                train_null_count += 1
    assert not split_ids["val"] and not split_ids["test"]
    assert train_null_count == split_rows["train"]
    assert test_seen_count == 200_648

    source_keys = pd.read_parquet(clean_path, columns=["day", "ts_end", "label_multi"])
    first, _ = assign_split_segment(
        source_keys,
        config["split"],
        float(config["split"]["final"]["gap_minutes"]),
    )
    first, _ = _enforce_class_gaps(
        source_keys,
        first,
        float(config["split"]["final"]["gap_minutes"]) * 60,
    )
    second, _ = assign_split_segment(
        source_keys,
        config["split"],
        float(config["split"]["final"]["gap_minutes"]),
    )
    second, _ = _enforce_class_gaps(
        source_keys,
        second,
        float(config["split"]["final"]["gap_minutes"]) * 60,
    )
    pd.testing.assert_series_equal(first, second)
    expected_counts = first.value_counts()
    assert all(
        int(expected_counts.get(split, 0)) == split_rows[split] for split in _SPLITS
    )
    gap_rows = int(expected_counts.get("gap", 0))
    assert clean_rows == kept_rows + gap_rows
