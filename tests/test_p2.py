from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.p2 import build_p2_folds, load_p2


def _row(
    flow_id: str,
    day: str,
    label: str,
    ts_end: float,
    feature: float,
) -> dict[str, object]:
    return {
        "flow_id": flow_id,
        "orig_flow_id": flow_id,
        "source_file": f"{day}.csv",
        "src_ip": "192.0.2.1",
        "dst_ip": "198.51.100.1",
        "src_port": np.int32(1234),
        "dst_port": np.int32(80),
        "ts_end": np.float64(ts_end),
        "feature_a": np.float32(feature),
        "label_bin": np.int8(0 if label == "BENIGN" else 1),
        "label_multi": label,
        "day": day,
    }


def test_p2_day_and_family_folds_purge_and_normalize_train_only(
    tmp_path: Path,
) -> None:
    interim = tmp_path / "data" / "interim"
    processed = tmp_path / "data" / "processed"
    models = tmp_path / "models" / "p2"
    reports = tmp_path / "reports"
    interim.mkdir(parents=True)
    processed.mkdir(parents=True)
    rows = [
        _row("mon-val", "Monday", "BENIGN", 100, 0),
        _row("mon-train", "Monday", "BENIGN", 500, 2),
        _row("tue-benign", "Tuesday", "BENIGN", 1000, 5),
        _row("tue-ftp", "Tuesday", "FTP-Patator", 1200, 10),
        _row("wed-val-benign", "Wednesday", "BENIGN", 2000, 20),
        _row("wed-near-benign", "Wednesday", "BENIGN", 2050, 22),
        _row("wed-safe-benign", "Wednesday", "BENIGN", 2300, 24),
        _row("wed-val-dos", "Wednesday", "DoS slowloris", 3000, 30),
        _row("wed-near-dos", "Wednesday", "DoS slowloris", 3100, 32),
        _row("thu-web", "Thursday", "Web Attack - Brute Force", 4000, 40),
        _row("fri-portscan", "Friday", "PortScan", 5000, 50),
        _row("rare", "Wednesday", "Heartbleed", 6000, 60),
    ]
    clean_path = interim / "clean.parquet"
    pq.write_table(pa.Table.from_pylist(rows), clean_path)
    val_path = processed / "val.parquet"
    pq.write_table(pa.table({"flow_id": ["mon-val", "wed-val-benign", "wed-val-dos"]}), val_path)
    config = {
        "paths": {"interim": interim, "processed": processed},
        "cv": {"purge_minutes": 3},
        "normalization": {"method": "standard"},
    }

    mapping_path, report_path, summaries = build_p2_folds(
        config,
        clean_path=clean_path,
        val_path=val_path,
        processed_dir=processed,
        output_path=processed / "p2_folds.parquet",
        models_dir=models,
        report_path=reports / "p2_report.md",
        families={"bruteforce": ["FTP-Patator"], "rare_excluded": ["Heartbleed", "Infiltration"]},
        batch_size=3,
    )

    mapping = pd.read_parquet(mapping_path)
    assert set(mapping["pli"]) == {"day_Tuesday", "day_Wednesday", "day_Thursday", "day_Friday", "family_bruteforce"}
    day_tuesday = mapping.loc[mapping["pli"].eq("day_Tuesday")].set_index("flow_id")
    assert day_tuesday.loc["tue-ftp", "role"] == "test"
    assert day_tuesday.loc["mon-val", "role"] == "train"
    assert day_tuesday.loc["wed-val-benign", "role"] == "val"
    assert day_tuesday.loc["wed-near-benign", "role"] == "purged"
    assert day_tuesday.loc["wed-safe-benign", "role"] == "train"
    assert day_tuesday.loc["rare", "role"] == "excluded"

    family_fold = mapping.loc[mapping["pli"].eq("family_bruteforce")].set_index("flow_id")
    assert family_fold.loc["tue-ftp", "role"] == "test"
    assert family_fold.loc["mon-val", "role"] == "train"
    assert family_fold.loc["wed-near-dos", "role"] == "purged"

    loaded = load_p2(
        "day_Tuesday",
        config,
        clean_path=clean_path,
        processed_dir=processed,
        models_dir=models,
        batch_size=3,
    ).set_index("flow_id")
    train_mask = loaded["role"].eq("train")
    assert np.isclose(loaded.loc[train_mask, "feature_a"].mean(), 0, atol=1e-6)
    scaler = joblib.load(models / "day_Tuesday.joblib")
    assert int(scaler.n_samples_seen_) == int(train_mask.sum())
    assert loaded.loc["mon-val", "role"] == "train"

    summary = {item["pli"]: item for item in summaries}
    assert summary["day_Tuesday"]["test_classes_absent_from_train"] == [
        "FTP-Patator"
    ]
    assert summary["family_bruteforce"]["test_classes_absent_from_train"] == [
        "FTP-Patator"
    ]
    report = report_path.read_text(encoding="utf-8")
    assert "BENIGN du lundi" in report
