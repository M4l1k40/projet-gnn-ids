import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.final_split import build_final_splits
from src.data.schema import ID_COLS, TARGET_COLS


def test_build_final_splits_writes_exact_schema_and_meta(tmp_path) -> None:
    rows = 22
    labels = ["BENIGN"] + ["AttackA"] * 20 + ["BENIGN"]
    frame = pd.DataFrame(
        {
            "orig_flow_id": [f"orig-{index}" for index in range(rows)],
            "src_ip": ["192.0.2.1"] * rows,
            "src_port": np.full(rows, 1234, dtype=np.int32),
            "dst_ip": ["198.51.100.1"] * rows,
            "dst_port": np.full(rows, 443, dtype=np.int32),
            "Flow Duration": np.zeros(rows, dtype=np.float32),
            "feature_a": np.arange(rows, dtype=np.float32),
            "label_multi": labels,
            "day": ["Monday"] * rows,
            "source_file": ["Monday.csv"] * rows,
            "flow_id": [f"flow-{index}" for index in range(rows)],
            "label_bin": np.array(
                [0 if label == "BENIGN" else 1 for label in labels],
                dtype=np.int8,
            ),
            "ts_end": np.arange(rows, dtype=np.float64) * 60,
        }
    )
    source_path = tmp_path / "clean.parquet"
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), source_path)
    output_dir = tmp_path / "processed"
    config = {
        "paths": {"interim": tmp_path, "processed": output_dir},
        "split": {
            "train": 0.60,
            "validation": 0.15,
            "test": 0.25,
            "final": {
                "variant": "segment",
                "gap_minutes": 0.05,
                "min_flows_per_block": 1,
            },
        },
    }

    paths, counts, gaps = build_final_splits(
        config,
        input_path=source_path,
        batch_size=5,
    )

    expected_columns = (
        ID_COLS
        + ["Flow Duration", "feature_a"]
        + TARGET_COLS
        + ["split", "day"]
    )
    assert set(paths) == {"train", "val", "test", "meta"}
    assert sum(counts.values()) + sum(gaps.values()) == rows
    assert sum(counts.values()) == pq.ParquetFile(paths["meta"]).metadata.num_rows
    for split in ("train", "val", "test"):
        result = pd.read_parquet(paths[split])
        assert list(result.columns) == expected_columns
        assert result["ts_end"].is_monotonic_increasing
        assert set(result["split"].astype(str)) == {split}
    meta = pd.read_parquet(paths["meta"])
    assert list(meta.columns) == ["flow_id", "orig_flow_id", "source_file"]
