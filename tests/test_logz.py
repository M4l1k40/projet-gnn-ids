import json
import subprocess
import sys

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.normalize_logz import (
    LogZTransformer,
    _dump_transformer,
    prepare_logz_data,
)


def _write_split(path, split, flow_ids, feature_values):
    rows = len(flow_ids)
    labels = ["BENIGN" if index % 2 == 0 else "Attack" for index in range(rows)]
    frame = pd.DataFrame(
        {
            "flow_id": flow_ids,
            "src_ip": ["192.0.2.1"] * rows,
            "dst_ip": ["198.51.100.1"] * rows,
            "src_port": np.full(rows, 1234, dtype=np.int32),
            "dst_port": np.full(rows, 443, dtype=np.int32),
            "ts_end": np.arange(rows, dtype=np.float64),
            "feature": np.asarray(feature_values, dtype=np.float32),
            "label_bin": np.asarray(
                [0 if label == "BENIGN" else 1 for label in labels],
                dtype=np.int8,
            ),
            "label_multi": labels,
            "split": pd.Categorical(
                [split] * rows,
                categories=["train", "val", "test"],
            ),
            "day": ["Monday"] * rows,
        }
    )
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), path)


def test_logz_transform_accepts_dataframe_and_ndarray_and_preserves_input():
    transformer = LogZTransformer(
        ["feature", "invalid", "sentinel"],
        np.asarray([0.0, 3.0, 0.0]),
        np.asarray([1]),
        np.asarray([np.log1p(2.0), np.log1p(3.0), 0.0]),
        np.ones(3),
    )
    values = np.asarray([[1.0, -4.0, -1.0], [3.0, 5.0, 1.0]], dtype=np.float32)
    original = values.copy()
    expected = transformer.transform(values)
    frame = pd.DataFrame(
        {
            "sentinel": values[:, 2],
            "extra_identifier": ["a", "b"],
            "invalid": values[:, 1],
            "feature": values[:, 0],
        }
    )

    np.testing.assert_array_equal(transformer.transform(frame), expected)
    np.testing.assert_array_equal(values, original)
    assert expected[0, 1] == 0.0
    assert expected[0, 2] < 0.0


def test_logz_transform_rejects_bad_shapes_and_non_finite_values():
    transformer = LogZTransformer(
        ["first", "second"],
        np.zeros(2),
        np.asarray([], dtype=np.int64),
        np.zeros(2),
        np.ones(2),
    )

    try:
        transformer.transform(np.zeros((2, 1)))
    except ValueError as error:
        assert "2 features" in str(error)
    else:
        raise AssertionError("Une matrice avec une mauvaise largeur doit échouer.")

    try:
        transformer.transform(np.asarray([[np.nan, 0.0]]))
    except ValueError as error:
        assert "NaN ou infini" in str(error)
    else:
        raise AssertionError("Une entrée non finie doit échouer.")


def test_logz_joblib_artifact_loads_without_project_imports(tmp_path):
    transformer = LogZTransformer(
        ["feature"],
        np.zeros(1),
        np.asarray([], dtype=np.int64),
        np.zeros(1),
        np.ones(1),
    )
    artifact = tmp_path / "scaler.joblib"
    _dump_transformer(transformer, artifact)

    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import joblib,sys; obj=joblib.load(sys.argv[1]); "
                "print(obj.transform([[2.0]]).tolist())"
            ),
            str(artifact),
        ],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "[[1.0986123085021973]]"


def test_logz_data_generation_preserves_non_features_and_copies_mapping_files(
    tmp_path,
):
    data = tmp_path / "data"
    source = data / "processed_v3"
    interim = data / "interim"
    source.mkdir(parents=True)
    interim.mkdir(parents=True)
    train_ids = ["t0", "t1", "t2", "t3"]
    val_ids = ["v0", "v1"]
    test_ids = ["x0", "x1"]
    _write_split(source / "train.parquet", "train", train_ids, [1, -2, 3, 4])
    _write_split(source / "val.parquet", "val", val_ids, [2, -1])
    _write_split(source / "test.parquet", "test", test_ids, [6, 8])
    clean = pd.DataFrame(
        {
            "flow_id": train_ids + val_ids + test_ids,
            "feature": np.asarray([1, -2, 3, 4, 2, -1, 6, 8], dtype=np.float32),
        }
    )
    pq.write_table(pa.Table.from_pandas(clean, preserve_index=False), interim / "clean.parquet")
    (source / "meta.parquet").write_bytes(b"meta-copy")
    (source / "folds.parquet").write_bytes(b"folds-copy")
    p2_source = data / "p2_folds.parquet"
    p2_source.write_bytes(b"p2-copy")

    models = tmp_path / "models"
    models.mkdir()
    feature_list = models / "features.json"
    feature_list.write_text(json.dumps(["feature"]), encoding="utf-8")
    audit = tmp_path / "feature_audit.csv"
    pd.DataFrame(
        {
            "feature": ["feature"],
            "raw_p1": [1.0],
            "raw_p99": [8.0],
        }
    ).to_csv(audit, index=False)
    processed_logz = data / "processed_v3_logz"
    scaler_path = models / "scaler_v3_logz.joblib"
    report_path = tmp_path / "normalization_v3_logz.md"
    config = {
        "paths": {
            "processed_v3": source,
            "processed_v3_logz": processed_logz,
            "interim": interim,
            "scaler_v3_logz": scaler_path,
            "p2_folds_source": p2_source,
            "scaler_audit_v3": audit,
            "normalization_v3_logz_report": report_path,
            "feature_list": feature_list,
        },
        "normalization_logz": {
            "batch_size": 2,
            "sample_size": 4,
            "sample_seed": 42,
            "invalid_negative_features": ["feature"],
        },
    }

    result = prepare_logz_data(config)

    assert result["imputed"]["train"]["feature"] == 1
    assert result["imputed"]["val"]["feature"] == 1
    for name in ("meta.parquet", "folds.parquet", "p2_folds.parquet"):
        assert (processed_logz / name).read_bytes() == (
            (source / name).read_bytes()
            if name != "p2_folds.parquet"
            else p2_source.read_bytes()
        )
    for split, expected_ids in (
        ("train", train_ids),
        ("val", val_ids),
        ("test", test_ids),
    ):
        original = pd.read_parquet(source / f"{split}.parquet")
        generated = pd.read_parquet(processed_logz / f"{split}.parquet")
        assert list(generated.columns) == list(original.columns)
        assert generated["flow_id"].tolist() == expected_ids
        pd.testing.assert_frame_equal(
            generated.drop(columns="feature"),
            original.drop(columns="feature"),
        )
        assert np.isfinite(generated["feature"]).all()
    transformer = joblib.load(scaler_path)
    assert transformer.feature_names == ["feature"]
    assert report_path.exists()
