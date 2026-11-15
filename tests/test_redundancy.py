from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.redundancy import build_redundancy_flags


def _split_frame(
    split: str,
    flow_ids: list[str],
    labels: list[str],
    features: list[tuple[float, float]],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "flow_id": flow_ids,
            "label_multi": labels,
            "split": pd.Categorical([split] * len(flow_ids), categories=["train", "val", "test"]),
            "day": ["Tuesday"] * len(flow_ids),
            "feature_a": np.asarray([row[0] for row in features], dtype=np.float32),
            "feature_b": np.asarray([row[1] for row in features], dtype=np.float32),
        }
    )


def test_redundancy_flags_detect_cross_class_conflicts_and_train_counts(
    tmp_path: Path,
) -> None:
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    processed.mkdir()
    frames = {
        "train": _split_frame(
            "train",
            ["tr-1", "tr-2", "tr-3", "tr-4"],
            ["BENIGN", "BENIGN", "Attack", "Attack"],
            [(1, 1), (1, 1), (1, 1), (2, 2)],
        ),
        "val": _split_frame(
            "val",
            ["val-1", "val-2", "val-3"],
            ["BENIGN", "Attack", "NewClass"],
            [(1, 1), (2, 2), (3, 3)],
        ),
        "test": _split_frame(
            "test",
            ["te-1", "te-2"],
            ["BENIGN", "Attack"],
            [(2, 2), (3, 3)],
        ),
    }
    for split, frame in frames.items():
        pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), processed / f"{split}.parquet")

    flags_path, report_path, summary = build_redundancy_flags(
        {"paths": {"processed": processed}},
        processed_dir=processed,
        output_path=processed / "redundancy_flags.parquet",
        report_path=reports / "redundancy_report.md",
        batch_size=2,
    )

    flags = pd.read_parquet(flags_path).set_index("flow_id")
    assert flags.loc["tr-1", "train_dup_count"] == 3
    assert bool(flags.loc["tr-1", "conflict_in_train"])
    assert bool(flags.loc["val-1", "seen_in_train_any_label"])
    assert bool(flags.loc["val-1", "conflict_in_train"])
    assert flags.loc["val-3", "train_dup_count"] == 0
    assert not bool(flags.loc["val-3", "seen_in_train_any_label"])
    assert bool(flags.loc["te-1", "seen_in_train_any_label"])
    assert bool(flags.loc["te-1", "conflict_in_train"])
    assert summary["train_rows"] == 4
    assert summary["output_rows"] == 9
    assert summary["test_seen_same_class"] == 0
    assert report_path.exists()
    assert "conflict_in_train" in report_path.read_text(encoding="utf-8")
