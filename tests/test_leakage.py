import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.leakage import run_leakage_diagnostics


def _split_frame(split, labels, first_feature, second_feature):
    rows = len(labels)
    return pd.DataFrame(
        {
            "flow_id": [f"{split}-{index}" for index in range(rows)],
            "src_ip": ["192.0.2.1"] * rows,
            "dst_ip": ["198.51.100.1"] * rows,
            "src_port": np.full(rows, 1234, dtype=np.int32),
            "dst_port": np.full(rows, 443, dtype=np.int32),
            "ts_end": np.arange(rows, dtype=np.float64),
            "feature_a": np.asarray(first_feature, dtype=np.float32),
            "feature_b": np.asarray(second_feature, dtype=np.float32),
            "label_bin": np.array(
                [0 if label == "BENIGN" else 1 for label in labels],
                dtype=np.int8,
            ),
            "label_multi": labels,
            "split": pd.Categorical([split] * rows, categories=["train", "val", "test"]),
            "day": ["Monday"] * rows,
        }
    )


def test_leakage_report_counts_exact_vectors_and_nn_distributions(tmp_path) -> None:
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    processed.mkdir()
    frames = {
        "train": _split_frame(
            "train",
            ["BENIGN"] * 4 + ["Attack"] * 4 + ["TrainOnly"] * 2,
            [0, 1, 2, 3, 10, 11, 12, 13, 20, 21],
            [0, 1, 2, 3, 10, 11, 12, 13, 20, 21],
        ),
        "val": _split_frame(
            "val",
            ["BENIGN"] * 2 + ["Attack"] * 2,
            [1.0000001, 4, 11, 15],
            [1.0000001, 4, 11, 15],
        ),
        "test": _split_frame(
            "test",
            ["BENIGN"] * 2 + ["Attack"] * 2,
            [0, 5, 10, 0],
            [0, 5, 10, 0],
        ),
    }
    for split, frame in frames.items():
        pq.write_table(
            pa.Table.from_pandas(frame, preserve_index=False),
            processed / f"{split}.parquet",
        )
    meta = pd.concat(
        [
            frame[["flow_id"]].assign(
                orig_flow_id=lambda rows: rows["flow_id"],
                source_file=f"{split}.csv",
            )
            for split, frame in frames.items()
        ],
        ignore_index=True,
    )
    pq.write_table(
        pa.Table.from_pandas(meta, preserve_index=False),
        processed / "meta.parquet",
    )
    config = {
        "paths": {"processed": processed},
        "leakage": {"train_sample": 6, "test_sample": 4},
        "seeds": {"global": 42},
    }

    report_path, csv_path, png_path, table, summary = run_leakage_diagnostics(
        config,
        reports_dir=reports,
    )

    exact = table.loc[table["analyse"].eq("identique_test_train")]
    assert exact.set_index("classe")["flux_identiques"].to_dict() == {
        "Attack": 1,
        "BENIGN": 1,
        "TrainOnly": 0,
    }
    assert set(table["analyse"]) == {
        "identique_test_train",
        "seen_in_train",
        "test_vers_train",
        "val_vers_train",
    }
    assert summary["exact_matches"] == 2
    meta_output = pd.read_parquet(processed / "meta.parquet")
    meta_seen = meta_output.set_index("flow_id")["seen_in_train"]
    assert meta_seen.loc[frames["train"]["flow_id"]].isna().all()
    assert meta_seen.loc[frames["val"]["flow_id"]].tolist() == [
        True,
        False,
        True,
        False,
    ]
    assert meta_seen.loc[frames["test"]["flow_id"]].tolist() == [
        True,
        False,
        True,
        False,
    ]
    seen_rows = table.loc[table["analyse"].eq("seen_in_train")]
    test_strict = seen_rows.loc[seen_rows["split"].eq("test")]
    assert test_strict.set_index("classe")["flux_test_strict"].to_dict() == {
        "Attack": 1,
        "BENIGN": 1,
        "TrainOnly": 0,
    }
    assert report_path.exists()
    assert csv_path.exists()
    assert png_path.exists() and png_path.stat().st_size > 0
    assert "test strict" in report_path.read_text(encoding="utf-8").lower()
