from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from src.data.schema import validate_schema
from src.data.split import assign_split_segment
from src.data.split_v3 import build_v3_splits


def _ownership_frame() -> pd.DataFrame:
    midnight = pd.Timestamp("2017-01-02 00:00").value / 1_000_000_000
    attack_times = midnight + np.arange(20, dtype=np.float64) * 60
    benign_times = midnight + np.arange(30, 60, dtype=np.float64) * 60
    timestamps = np.concatenate((attack_times, benign_times))
    labels = ["Attack"] * len(attack_times) + ["BENIGN"] * len(benign_times)
    return pd.DataFrame(
        {
            "day": ["Monday"] * len(timestamps),
            "ts_end": timestamps,
            "label_multi": labels,
        }
    )


def test_official_window_changes_only_benign_ownership() -> None:
    frame = _ownership_frame()
    ratios = {"train": 0.60, "validation": 0.15, "test": 0.25}
    class_range, _ = assign_split_segment(frame, ratios, gap_minutes=0)
    official, _ = assign_split_segment(
        frame,
        ratios,
        gap_minutes=0,
        benign_ownership="official_window",
        official_windows={"Monday": {"Attack": [["00:00", "01:00"]]}},
    )

    attack_mask = frame["label_multi"].eq("Attack")
    benign_mask = frame["label_multi"].eq("BENIGN")
    assert official.loc[attack_mask].tolist() == class_range.loc[attack_mask].tolist()
    assert class_range.loc[benign_mask].iloc[0] == "train"
    assert official.loc[benign_mask].iloc[0] == "test"


def test_v3_builder_writes_isolated_valid_splits(tmp_path: Path) -> None:
    frame = _ownership_frame()
    frame["flow_id"] = [f"flow-{index:04d}" for index in range(len(frame))]
    frame["orig_flow_id"] = frame["flow_id"]
    frame["source_file"] = "Monday.csv"
    frame["src_ip"] = "192.0.2.1"
    frame["dst_ip"] = "198.51.100.1"
    frame["src_port"] = np.full(len(frame), 1234, dtype=np.int32)
    frame["dst_port"] = np.full(len(frame), 443, dtype=np.int32)
    frame["Flow Duration"] = np.zeros(len(frame), dtype=np.float32)
    frame["feature_a"] = np.arange(len(frame), dtype=np.float32)
    frame["label_bin"] = frame["label_multi"].ne("BENIGN").astype(np.int8)
    source_path = tmp_path / "clean.parquet"
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), source_path)
    processed_v2 = tmp_path / "processed"
    processed_v2.mkdir()
    marker = processed_v2 / "unchanged.txt"
    marker.write_text("protected", encoding="utf-8")
    windows_path = tmp_path / "attack_windows.yaml"
    windows_path.write_text(
        yaml.safe_dump(
            {
                "tolerance_minutes": 0,
                "windows": {"Monday": {"Attack": [["00:00", "01:00"]]}},
            }
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "processed_v3"
    config = {
        "paths": {
            "processed": processed_v2,
            "processed_v3": output_dir,
            "interim": tmp_path,
            "attack_windows": windows_path,
        },
        "split": {
            "train": 0.60,
            "validation": 0.15,
            "test": 0.25,
            "final": {
                "variant": "segment",
                "gap_minutes": 0,
                "benign_ownership": "official_window",
            },
        },
    }

    result = build_v3_splits(config, input_path=source_path, batch_size=10)

    assert result["source_rows"] == len(frame)
    assert result["gap_count"] == 0
    assert marker.read_text(encoding="utf-8") == "protected"
    ids_by_split = []
    for split in ("train", "val", "test"):
        output = pd.read_parquet(output_dir / f"{split}.parquet")
        validate_schema(output, stage="final")
        assert output["split"].astype(str).eq(split).all()
        ids_by_split.append(set(output["flow_id"]))
    assert all(
        not ids_by_split[left].intersection(ids_by_split[right])
        for left in range(3)
        for right in range(left + 1, 3)
    )
    meta = pd.read_parquet(output_dir / "meta.parquet")
    assert meta["flow_id"].is_unique
