import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.data.final_split import _enforce_class_gaps
from src.data.split import assign_split_segment
from src.data.schema import validate_schema
from src.utils.config import load_config

_SPLITS = ("train", "val", "test")


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
    meta_rows = pq.ParquetFile(meta_path).metadata.num_rows
    assert meta_rows == kept_rows
    assert clean_rows == 2_827_677
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
