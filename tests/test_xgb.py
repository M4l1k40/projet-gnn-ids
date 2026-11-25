import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.fake import generate_fake_flows
from src.data.folds import build_cv_folds
from src.data.schema import PREDICTION_COLUMNS
from src.models import xgb as xgb_model


def _fake_project(tmp_path: Path) -> tuple[dict, pd.DataFrame]:
    interim = tmp_path / "data" / "interim"
    processed = tmp_path / "data" / "processed"
    feature_list = tmp_path / "models" / "features.json"
    interim.mkdir(parents=True)
    processed.mkdir(parents=True)
    feature_list.parent.mkdir(parents=True)
    config = {
        "_project_root": tmp_path,
        "paths": {
            "raw": tmp_path / "data" / "raw",
            "interim": interim,
            "processed": processed,
            "processed_v3": tmp_path / "data" / "processed_v3",
            "labels_v2_all": processed / "labels_v2_all.parquet",
            "feature_list": feature_list,
            "model_dir": tmp_path / "models" / "xgboost",
            "prediction_dir": tmp_path / "predictions" / "xgboost",
            "report_dir": tmp_path / "reports" / "xgboost",
            "oof_metrics_csv": tmp_path / "reports" / "xgboost" / "oof_fold_metrics_bin.csv",
            "summary_report": tmp_path / "reports" / "xgboost_report.md",
            "summary_csv": tmp_path / "reports" / "xgboost_report.csv",
            "audit_metrics_csv": tmp_path / "reports" / "xgboost_audit_metrics.csv",
            "importance_csv": tmp_path / "reports" / "xgboost_feature_importance.csv",
            "data_config": tmp_path / "configs" / "data.yaml",
        },
        "seeds": [42],
        "search_seed": 42,
        "n_trials": 1,
        "cv_folds": 3,
        "multiclass_blocks": ["train", "test"],
        "undersampling_benign_train": False,
        "benign_to_attack_ratio": 1.0,
        "fixed": {
            "booster": "gbtree",
            "tree_method": "hist",
            "eta": 0.1,
            "n_estimators": 12,
            "early_stopping_rounds": 3,
            "n_jobs": 1,
            "eval_metric": {"bin": "aucpr", "multi": "mlogloss"},
        },
        "search_space": {
            "max_depth": [2, 3],
            "min_child_weight": [1, 2],
            "subsample": [0.8, 0.9],
            "colsample_bytree": [0.8, 0.9],
            "lambda": [0.1, 1.0],
            "alpha": [0.01, 0.1],
        },
        "label_rule_to_multi": {
            "BENIGN": "BENIGN",
            "AttackA": "AttackA",
            "AttackB": "AttackB",
            "AttackC": "AttackC",
        },
        "split": {"final": {"min_flows_per_block": 20}},
    }
    fake_config = {
        "paths": {
            "raw": tmp_path / "data" / "raw",
            "interim": interim,
            "processed": processed,
        },
        "split": {
            "train": 0.6,
            "validation": 0.15,
            "test": 0.25,
            "gap_minutes": 0,
        },
        "seeds": {"global": 42},
        "fake": {
            "n_days": 3,
            "flows_per_day": 600,
            "n_features": 4,
            "benign_ratio": 0.4,
            "classes": ["BENIGN", "AttackA", "AttackB", "AttackC"],
        },
    }
    flows = generate_fake_flows(fake_config)
    features = [f"feature_{index:03d}" for index in range(4)]
    feature_list.write_text(json.dumps(features), encoding="utf-8")
    for split in ("train", "val", "test"):
        flows.loc[flows["split"].eq(split)].drop(columns="split").to_parquet(
            processed / f"{split}.parquet",
            index=False,
        )
    metadata = flows[["flow_id", "split"]].copy()
    metadata["seen_in_train"] = None
    validation_mask = metadata["split"].eq("val")
    metadata.loc[validation_mask, "seen_in_train"] = (
        metadata.loc[validation_mask, "flow_id"].str[-1].astype(int).mod(2).eq(0)
    )
    test_mask = metadata["split"].eq("test")
    metadata.loc[test_mask, "seen_in_train"] = (
        np.arange(int(test_mask.sum())) % 2 == 0
    )
    metadata_table = pa.Table.from_pydict(
        {
            "flow_id": metadata["flow_id"].astype(str).tolist(),
            "seen_in_train": pa.array(
                metadata["seen_in_train"].tolist(),
                type=pa.bool_(),
            ),
        }
    )
    metadata_table = metadata_table.take(
        pa.array(np.arange(len(metadata) - 1, -1, -1), type=pa.int64())
    )
    pq.write_table(metadata_table, processed / "meta.parquet")
    audit = flows[["flow_id", "label_multi"]].rename(
        columns={"label_multi": "label_rule"}
    )
    audit["attempted_category"] = -1
    benign_index = audit.index[audit["label_rule"].eq("BENIGN")][0]
    audit.loc[benign_index, "label_rule"] = "AttackA"
    attempted_index = flows.index[
        flows["split"].eq("val") & flows["label_multi"].eq("AttackA")
    ][0]
    audit.loc[attempted_index, "attempted_category"] = 0
    audit.to_parquet(processed / "label_audit.parquet", index=False)
    folds_config = {
        "paths": {"processed": processed},
        "cv": {"k": 3, "purge_minutes": 0},
    }
    build_cv_folds(
        folds_config,
        train_path=processed / "train.parquet",
        output_path=processed / "folds.parquet",
        report_path=tmp_path / "reports" / "folds.md",
        batch_size=500,
    )
    config["paths"]["data_config"] = tmp_path / "configs" / "data.yaml"
    return config, flows


def test_load_split_uses_only_float32_features_and_shared_prediction_shape(
    tmp_path: Path,
) -> None:
    config, _ = _fake_project(tmp_path)
    train = xgb_model.load_split("train", config)
    assert train.X.dtype == np.float32
    assert train.feature_names == [f"feature_{index:03d}" for index in range(4)]
    assert not set(train.feature_names).intersection(
        {"flow_id", "src_ip", "dst_ip", "src_port", "dst_port", "ts_end"}
    )
    validation = xgb_model.load_split("val", config)
    assert validation.seen_in_train is not None
    meta = pd.read_parquet(
        config["paths"]["processed"] / "meta.parquet",
        columns=["flow_id", "seen_in_train"],
    )
    expected_flags = meta.set_index("flow_id").loc[
        validation.flow_ids,
        "seen_in_train",
    ].to_numpy(dtype=bool)
    np.testing.assert_array_equal(validation.seen_in_train, expected_flags)

    frame = xgb_model.prediction_frame(
        np.asarray(["test-1"]),
        np.asarray([1], dtype=np.int8),
        np.asarray([1], dtype=np.int8),
        np.asarray([0.75]),
        42,
    )
    assert list(frame.columns) == PREDICTION_COLUMNS
    assert pd.isna(frame.loc[0, "recon_error"])


def test_v3_data_variant_joins_full_v2_labels_by_flow_id(tmp_path: Path) -> None:
    config, flows = _fake_project(tmp_path)
    audit = pd.read_parquet(
        config["paths"]["processed"] / "label_audit.parquet"
    )
    labels_source = flows.merge(audit, on="flow_id", validate="one_to_one")
    canonical = labels_source["label_rule"].map(config["label_rule_to_multi"])
    labels = pd.DataFrame(
        {
            "flow_id": labels_source["flow_id"],
            "label_orig_multi": labels_source["label_multi"],
            "label_orig_bin": labels_source["label_bin"],
            "canonical_rule": canonical,
            "attempted": labels_source["attempted_category"].ge(0),
            "changed": canonical.ne(labels_source["label_multi"]),
            "label_v2_bin": canonical.ne("BENIGN").astype("int8"),
            "v2_family": "unchanged",
        }
    )
    labels.to_parquet(config["paths"]["labels_v2_all"], index=False)
    v3_dir = config["paths"]["processed_v3"]
    v3_dir.mkdir(parents=True)
    for split in ("train", "val", "test", "meta.parquet"):
        source = (
            config["paths"]["processed"] / split
            if split == "meta.parquet"
            else config["paths"]["processed"] / f"{split}.parquet"
        )
        destination = (
            v3_dir / split
            if split == "meta.parquet"
            else v3_dir / f"{split}.parquet"
        )
        pd.read_parquet(source).to_parquet(destination, index=False)
    config["data_variant"] = "v3"

    loaded = xgb_model.load_split("train", config)

    assert loaded.y_v2_bin is not None
    assert loaded.attempted is not None
    expected = labels.set_index("flow_id").loc[loaded.flow_ids]
    np.testing.assert_array_equal(
        loaded.y_v2_bin,
        expected["label_v2_bin"].to_numpy(dtype=np.int8),
    )
    np.testing.assert_array_equal(
        loaded.attempted,
        expected["attempted"].to_numpy(dtype=bool),
    )


def test_random_search_draws_are_reproducible(tmp_path: Path) -> None:
    config, _ = _fake_project(tmp_path)
    assert xgb_model._draw_trials(config) == xgb_model._draw_trials(config)


def test_oof_threshold_respects_one_percent_false_positive_rate() -> None:
    labels = np.asarray([0] * 100 + [1] * 20, dtype=np.int8)
    probabilities = np.concatenate(
        (np.linspace(0.01, 0.99, 100), np.linspace(0.55, 0.95, 20))
    )
    thresholds = xgb_model._threshold_values(labels, probabilities)

    assert np.mean(probabilities[labels == 0] >= thresholds["threshold_fpr_1pct"]) <= 0.01
    assert thresholds["achieved_fpr"] <= 0.01
    assert 0.0 <= thresholds["f1_max"] <= 1.0


def test_binary_metric_values_reports_threshold_and_curve_rates() -> None:
    metrics = xgb_model._binary_metric_values(
        np.asarray([0, 0, 1, 1], dtype=np.int8),
        np.asarray([0.1, 0.4, 0.5, 0.9]),
        0.5,
    )

    assert metrics["pr_auc"] == 1.0
    assert metrics["roc_auc"] == 1.0
    assert metrics["false_positives"] == 0
    assert metrics["tpr_at_threshold"] == 1.0
    assert metrics["tpr_at_fpr_1pct"] == 1.0


def test_binary_report_writes_metrics_and_class_recall(tmp_path: Path) -> None:
    config, flows = _fake_project(tmp_path)
    test = flows.loc[flows["split"].eq("test")]
    scores = np.where(test["label_bin"].to_numpy() == 1, 0.9, 0.1)
    predictions = xgb_model.prediction_frame(
        test["flow_id"].to_numpy(),
        test["label_bin"].to_numpy(dtype=np.int8),
        test["label_bin"].to_numpy(dtype=np.int8),
        scores,
        42,
    )
    prediction_dir = config["paths"]["prediction_dir"]
    prediction_dir.mkdir(parents=True)
    predictions.to_parquet(prediction_dir / "xgb_bin_seed42.parquet", index=False)

    report_dir = config["paths"]["report_dir"]
    report_dir.mkdir(parents=True)
    (report_dir / "thresholds_bin.json").write_text(
        json.dumps(
            {
                "threshold_fpr_1pct": 0.5,
                "achieved_fpr": 0.0,
                "best_rounds": 199,
                "top_5_trials": [
                    {"trial": index, "mean_score": 0.9 - index * 0.001, "std_score": 0.04}
                    for index in range(5)
                ],
                "fold_diagnostics": [
                    {
                        "fold": fold,
                        "effectif": 20,
                        "attaques": 4,
                        "taux_attaque": 0.2,
                        "pr_auc": 1.0,
                        "fpr": 0.0,
                        "tpr_at_threshold": 1.0,
                        "tpr_at_fpr_1pct": 1.0,
                        "best_iteration": fold + 1,
                        "fit_seconds": 1.0,
                    }
                    for fold in range(config["cv_folds"])
                ],
            }
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [{"seed": 42, "training_seconds": 1.0, "inference_seconds": 0.1}]
    ).to_json(report_dir / "training_bin.json", orient="records")
    pd.DataFrame(
        [
            {"seed": 42, "feature": feature, "gain": 1.0}
            for feature in ["feature_000", "feature_001", "feature_002", "feature_003"]
        ]
    ).to_csv(config["paths"]["importance_csv"], index=False)

    paths = xgb_model.write_binary_evaluation_report(config)
    report = Path(paths["report_path"]).read_text(encoding="utf-8")
    metric_csv = pd.read_csv(paths["summary_csv"])

    assert "test complet" in report
    assert "test strict" in report
    assert "test sans signalés" in report
    assert "test complet sans Bot" in report
    assert "Attaques hors Bot seulement" in report
    assert "Bot — diagnostic séparé" in report
    assert "faux positifs vont de" in report
    assert "Matrice de confusion" in report
    assert len(metric_csv) == 4


def test_label_audit_uses_canonical_mapping_and_union_flag(tmp_path: Path) -> None:
    config, _ = _fake_project(tmp_path)
    result = xgb_model.recompute_label_audit(config)

    assert result["summary"]["train"]["divergences_reelles"] == 1
    assert result["summary"]["train"]["signales"] == 1
    assert result["summary"]["train"]["regles_attempted"] == 0
    assert result["summary"]["val"]["regles_attempted"] >= 1
    assert result["summary"]["val"]["signales"] >= 1
    assert Path(result["csv_path"]).exists()
    assert Path(result["report_path"]).exists()


def test_binary_search_never_reads_test_and_has_no_flow_id_overlap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    config, flows = _fake_project(tmp_path)
    train_ids = set(flows.loc[flows["split"].eq("train"), "flow_id"])
    test_ids = set(flows.loc[flows["split"].eq("test"), "flow_id"])
    assert train_ids.isdisjoint(test_ids)

    original_load_split = xgb_model.load_split
    loaded_names = []

    def guarded_load_split(name: str, supplied_config: dict | None = None):
        loaded_names.append(name)
        assert name != "test"
        return original_load_split(name, supplied_config)

    monkeypatch.setattr(xgb_model, "load_split", guarded_load_split)
    result = xgb_model.search_hyperparameters(
        "bin",
        config,
        calculate_thresholds=False,
    )
    assert loaded_names == ["train"]
    assert result["trial_count"] == 1
    assert len(result["best_iterations"]) == 3
    assert (tmp_path / "reports" / "xgboost" / "search_bin.csv").exists()
