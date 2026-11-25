import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import yaml
from sklearn.preprocessing import StandardScaler

from src.data.schema import PREDICTION_COLUMNS
from src.models import xgb_p2


def _config(tmp_path: Path) -> dict:
    data_dir = tmp_path / "data"
    interim = data_dir / "interim"
    interim.mkdir(parents=True)
    feature_list = tmp_path / "models" / "features.json"
    feature_list.parent.mkdir(parents=True)
    feature_list.write_text(json.dumps(["feature_a", "feature_b"]), encoding="utf-8")
    data_config = tmp_path / "configs" / "data.yaml"
    data_config.parent.mkdir(parents=True)
    data_config.write_text(
        yaml.safe_dump(
            {
                "paths": {
                    "raw": str(data_dir / "raw"),
                    "interim": str(interim),
                    "processed": str(data_dir / "processed"),
                },
                "normalization": {"method": "standard"},
            }
        ),
        encoding="utf-8",
    )
    return {
        "_project_root": tmp_path,
        "paths": {
            "interim": interim,
            "feature_list": feature_list,
            "data_config": data_config,
            "p2_fold_mapping": data_dir / "processed" / "p2_folds.parquet",
            "p2_scaler_dir": tmp_path / "models" / "p2",
            "model_dir_p2": tmp_path / "models" / "xgboost_p2",
            "prediction_dir_p2": tmp_path / "predictions" / "xgboost_p2",
            "report_dir_p2": tmp_path / "reports" / "xgboost_p2",
        },
        "fixed": {
            "booster": "gbtree",
            "tree_method": "hist",
            "eta": 0.1,
            "n_jobs": 1,
            "eval_metric": {"bin": "aucpr"},
        },
        "search_seed": 42,
        "p2": {
            "seed": 42,
            "n_estimators": 2,
            "threshold": {
                "method": "validation_benign_fpr",
                "target_fpr": 0.25,
            },
        },
    }


def test_load_role_partition_excludes_test_rows_before_fit(tmp_path: Path) -> None:
    config = _config(tmp_path)
    clean_path = config["paths"]["interim"] / "clean.parquet"
    rows = []
    roles = ["train", "train", "train", "train", "val", "val", "test", "test"]
    for index, role in enumerate(roles):
        label = index % 2
        rows.append(
            {
                "flow_id": f"flow-{index}",
                "day": "Tuesday",
                "label_bin": np.int8(label),
                "label_multi": "Attack" if label else "BENIGN",
                "feature_a": np.float32(index),
                "feature_b": np.float32(index * 2),
            }
        )
    clean = pd.DataFrame(rows)
    clean.to_parquet(clean_path, index=False)
    config["paths"]["p2_fold_mapping"].parent.mkdir(parents=True)
    mapping = pd.DataFrame(
        {
            "flow_id": clean["flow_id"],
            "pli": "day_Tuesday",
            "role": roles,
        }
    )
    mapping.to_parquet(config["paths"]["p2_fold_mapping"], index=False)

    scaler_dir = config["paths"]["p2_scaler_dir"]
    scaler_dir.mkdir(parents=True)
    scaler = StandardScaler().fit(
        clean.loc[:3, ["feature_a", "feature_b"]].to_numpy(dtype=np.float64)
    )
    joblib.dump(scaler, scaler_dir / "day_Tuesday.joblib")

    partition = xgb_p2._load_role_partition(
        "day_Tuesday", ("train", "val"), config
    )

    assert set(partition.roles) == {"train", "val"}
    assert set(partition.flow_ids).isdisjoint({"flow-6", "flow-7"})
    assert partition.X.dtype == np.float32
    assert partition.X.shape == (6, 2)


def test_p2_fit_uses_validation_threshold_and_writes_common_predictions(
    tmp_path: Path,
) -> None:
    config = _config(tmp_path)
    fit_ids = np.asarray([f"fit-{index}" for index in range(12)])
    fit_labels = np.asarray([0, 1] * 6, dtype=np.int8)
    fit_partition = xgb_p2.P2Partition(
        flow_ids=fit_ids,
        X=np.asarray(
            [[float(label), float(index % 3)] for index, label in enumerate(fit_labels)],
            dtype=np.float32,
        ),
        y_bin=fit_labels,
        y_multi=np.where(fit_labels == 1, "Attack", "BENIGN"),
        roles=np.asarray(["train"] * 8 + ["val"] * 4),
        feature_names=["feature_a", "feature_b"],
    )
    test_partition = xgb_p2.P2Partition(
        flow_ids=np.asarray(["test-0", "test-1", "test-2", "test-3"]),
        X=np.asarray([[0, 0], [1, 0], [0, 1], [1, 1]], dtype=np.float32),
        y_bin=np.asarray([0, 1, 0, 1], dtype=np.int8),
        y_multi=np.asarray(["BENIGN", "Attack", "BENIGN", "Attack"]),
        roles=np.asarray(["test"] * 4),
        feature_names=["feature_a", "feature_b"],
    )
    calls = []

    def loader(pli: str, requested: tuple[str, ...], _: dict) -> xgb_p2.P2Partition:
        calls.append(requested)
        if requested == ("train", "val"):
            return fit_partition
        if requested == ("test",):
            assert xgb_p2._model_path(config, pli, 42).exists()
            return test_partition
        raise AssertionError(f"Rôles inattendus: {requested}")

    parameters = {
        "max_depth": 2,
        "min_child_weight": 1.0,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "lambda": 1.0,
        "alpha": 0.0,
    }
    metadata, threshold = xgb_p2._ensure_model_and_threshold(
        "day_Tuesday",
        config,
        parameters,
        2,
        partition_loader=loader,
    )
    test, predictions, _ = xgb_p2._test_predictions(
        "day_Tuesday",
        config,
        threshold,
        partition_loader=loader,
    )

    assert calls == [("train", "val"), ("test",)]
    assert metadata["n_estimators"] == 2
    assert threshold["method"] == "validation_benign_fpr"
    assert threshold["achieved_fpr"] <= 0.25
    assert list(predictions.columns) == PREDICTION_COLUMNS
    assert predictions["flow_id"].is_unique
    assert predictions["seed"].eq(42).all()
    assert predictions["y_true"].tolist() == test.y_bin.tolist()
    assert predictions["recon_error"].isna().all()

    def no_reload(*args, **kwargs):
        raise AssertionError("Un pli déjà entraîné ne doit pas être refitté.")

    xgb_p2._ensure_model_and_threshold(
        "day_Tuesday",
        config,
        parameters,
        2,
        partition_loader=no_reload,
    )


def test_threshold_is_calibrated_only_on_benign_validation_scores() -> None:
    result = xgb_p2._threshold_for_fpr(
        np.asarray([0, 0, 0, 0, 1, 1], dtype=np.int8),
        np.asarray([0.1, 0.2, 0.3, 0.4, 0.35, 0.9]),
        target_fpr=0.25,
    )

    assert result["achieved_fpr"] <= 0.25
    assert result["benign_rows"] == 4
    assert result["threshold"] == 0.35


def test_family_only_test_marks_roc_and_fpr_curve_as_undefined() -> None:
    labels = np.ones(4, dtype=np.int8)

    metrics = xgb_p2._metrics_row(
        "family_bot",
        "labels origine",
        labels,
        np.asarray([0.2, 0.4, 0.6, 0.8]),
        np.asarray([0, 0, 1, 1], dtype=np.int8),
        threshold=0.5,
    )

    assert np.isnan(metrics["roc_auc"])
    assert metrics["pr_auc"] == 1.0
    assert np.isnan(metrics["tpr_at_fpr_0_1pct"])
    assert np.isnan(metrics["tpr_at_fpr_1pct_curve"])
    assert np.isnan(metrics["fpr_at_threshold"])
