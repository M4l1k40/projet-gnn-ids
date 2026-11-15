import json

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.normalize import normalize_final_data


def _write_split(path, split, values, constant_values) -> None:
    rows = len(values)
    labels = ["BENIGN", "Attack"] * (rows // 2)
    if rows % 2:
        labels.append("BENIGN")
    frame = pd.DataFrame(
        {
            "flow_id": [f"{split}-{index}" for index in range(rows)],
            "src_ip": ["192.0.2.1"] * rows,
            "dst_ip": ["198.51.100.1"] * rows,
            "src_port": np.full(rows, 1234, dtype=np.int32),
            "dst_port": np.full(rows, 443, dtype=np.int32),
            "ts_end": np.arange(rows, dtype=np.float64),
            "feature": np.asarray(values, dtype=np.float32),
            "constant": np.asarray(constant_values, dtype=np.float32),
            "label_bin": np.array(
                [0 if label == "BENIGN" else 1 for label in labels],
                dtype=np.int8,
            ),
            "label_multi": labels,
            "split": pd.Categorical([split] * rows, categories=["train", "val", "test"]),
            "day": ["Monday"] * rows,
        }
    )
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), path)


def test_normalization_uses_train_only_and_keeps_zero_variance_safe(tmp_path) -> None:
    processed_dir = tmp_path / "processed"
    processed_dir.mkdir()
    _write_split(
        processed_dir / "train.parquet",
        "train",
        [0, 1, 2, 3],
        [1, 1, 1, 1],
    )
    _write_split(
        processed_dir / "val.parquet",
        "val",
        [4, 5],
        [3, 3],
    )
    _write_split(
        processed_dir / "test.parquet",
        "test",
        [10, 12],
        [4, 4],
    )
    models_dir = tmp_path / "models"
    report_path = tmp_path / "normalization_report.md"
    config = {
        "paths": {"processed": processed_dir},
        "normalization": {"method": "standard"},
    }

    scaler_path, features_path, report, _ = normalize_final_data(
        config,
        models_dir=models_dir,
        report_path=report_path,
        batch_size=2,
    )

    scaler = joblib.load(scaler_path)
    assert scaler.n_samples_seen_ == 4
    assert json.loads(features_path.read_text(encoding="utf-8")) == [
        "feature",
        "constant",
    ]
    train = pd.read_parquet(processed_dir / "train.parquet")
    assert abs(float(train["feature"].mean())) < 1e-6
    assert abs(float(train["feature"].std(ddof=0)) - 1) < 1e-6
    assert train["constant"].eq(0).all()
    val = pd.read_parquet(processed_dir / "val.parquet")
    test = pd.read_parquet(processed_dir / "test.parquet")
    assert val["feature"].mean() > 0
    assert test["feature"].mean() > 0
    assert val["constant"].eq(2).all()
    assert report == report_path
    assert "`constant`" in report_path.read_text(encoding="utf-8")
