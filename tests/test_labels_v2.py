from pathlib import Path

import pandas as pd
import pytest

from src.data.fake import generate_fake_flows
from src.data.labels_v2 import build_labels_v2, build_labels_v2_all


def _fake_label_project(tmp_path: Path) -> tuple[dict, pd.DataFrame]:
    processed = tmp_path / "data" / "processed"
    interim = tmp_path / "data" / "interim"
    processed.mkdir(parents=True)
    interim.mkdir(parents=True)
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
    flows["label_rule"] = flows["label_multi"]
    flows["attempted_category"] = -1
    train_benign = flows.index[flows["split"].eq("train") & flows["label_multi"].eq("BENIGN")]
    flows.loc[train_benign[0], "label_rule"] = "Infiltration - Portscan"
    flows.loc[train_benign[1], "label_rule"] = "AttackA"
    flows.loc[train_benign[1], "src_ip"] = "192.168.10.50"
    flows.loc[train_benign[1], "dst_ip"] = "172.16.0.1"
    flows.loc[train_benign[1], "src_port"] = 80
    train_attack = flows.index[
        flows["split"].eq("train") & flows["label_multi"].eq("AttackA")
    ]
    flows.loc[train_attack[0], "label_rule"] = "AttackA - Attempted"
    flows.loc[train_attack[0], "attempted_category"] = 0
    flows.loc[train_attack[1], "label_rule"] = "AttackC"

    flows.drop(
        columns=["split", "label_rule", "attempted_category"]
    ).to_parquet(interim / "clean.parquet", index=False)
    for block in ("train", "val", "test"):
        flows.loc[flows["split"].eq(block)].drop(
            columns=["split", "label_rule", "attempted_category"],
            errors="ignore",
        ).to_parquet(processed / f"{block}.parquet", index=False)
    audit = flows[["flow_id", "label_rule", "attempted_category"]]
    audit.to_parquet(processed / "label_audit.parquet", index=False)

    config = {
        "_project_root": tmp_path,
        "paths": {
            "processed": processed,
            "processed_v3": tmp_path / "data" / "processed_v3",
            "clean": interim / "clean.parquet",
            "train": processed / "train.parquet",
            "val": processed / "val.parquet",
            "test": processed / "test.parquet",
            "audit": processed / "label_audit.parquet",
            "output": processed / "labels_v2.parquet",
            "output_all": processed / "labels_v2_all.parquet",
            "report": tmp_path / "reports" / "labels_v2.md",
        },
        "label_rule_to_multi": {
            "BENIGN": "BENIGN",
            "AttackA": "AttackA",
            "AttackA - Attempted": "AttackA",
            "AttackB": "AttackB",
            "AttackC": "AttackC",
            "Infiltration - Portscan": "PortScan",
        },
        "families": {
            "portscan_infiltration_rule": "Infiltration - Portscan",
            "server_response": {
                "source_ip": "192.168.10.50",
                "destination_ip": "172.16.0.1",
                "ftp_source_port": 21,
            },
        },
    }
    return config, flows


def test_labels_v2_writes_expected_fields_and_partitioned_families(
    tmp_path: Path,
) -> None:
    config, flows = _fake_label_project(tmp_path)

    result = build_labels_v2(config)

    labels = pd.read_parquet(result["output_path"])
    labels_by_id = labels.set_index("flow_id")
    portscan_id = flows.loc[
        flows["label_rule"].eq("Infiltration - Portscan"), "flow_id"
    ].iloc[0]
    server_id = flows.loc[
        flows["src_ip"].eq("192.168.10.50") & flows["label_rule"].eq("AttackA"),
        "flow_id",
    ].iloc[0]
    attempted_id = flows.loc[
        flows["label_rule"].eq("AttackA - Attempted"), "flow_id"
    ].iloc[0]
    other_change_id = flows.loc[
        flows["label_multi"].eq("AttackA") & flows["label_rule"].eq("AttackC"),
        "flow_id",
    ].iloc[0]
    assert labels["flow_id"].is_unique
    assert list(labels.columns) == [
        "flow_id",
        "label_orig_multi",
        "label_orig_bin",
        "canonical_rule",
        "attempted",
        "changed",
        "label_v2_bin",
        "v2_family",
    ]
    assert not labels.isna().any().any()
    assert len(labels) == sum(result["block_counts"].values())
    assert set(labels["v2_family"]) == {
        "portscan_infiltration",
        "server_response",
        "other_change",
        "unchanged",
    }
    assert labels_by_id.loc[portscan_id, "v2_family"] == "portscan_infiltration"
    assert labels_by_id.loc[server_id, "v2_family"] == "server_response"
    assert labels_by_id.loc[attempted_id, "v2_family"] == "unchanged"
    assert labels_by_id.loc[other_change_id, "v2_family"] == "other_change"
    assert labels["attempted"].sum() == 1
    assert labels.loc[labels["attempted"], "changed"].eq(False).all()
    assert result["changed_by_block"]["train"] >= 3
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Transitions de classe" in report
    assert "Flux Attempted" in report


def test_labels_v2_rejects_unmapped_rule_without_creating_outputs(
    tmp_path: Path,
) -> None:
    config, flows = _fake_label_project(tmp_path)
    audit_path = config["paths"]["audit"]
    audit = pd.read_parquet(audit_path)
    audit.loc[0, "label_rule"] = "Unknown rule"
    audit.to_parquet(audit_path, index=False)

    with pytest.raises(ValueError, match="Règles absentes"):
        build_labels_v2(config)

    assert not config["paths"]["output"].exists()
    assert not config["paths"]["report"].exists()


def test_labels_v2_all_covers_clean_and_preserves_existing_labels(
    tmp_path: Path,
) -> None:
    config, flows = _fake_label_project(tmp_path)
    omitted = flows.loc[
        flows["split"].eq("train") & flows["label_multi"].eq("BENIGN"),
        "flow_id",
    ].iloc[-1]
    train_path = config["paths"]["train"]
    train = pd.read_parquet(train_path)
    train.loc[train["flow_id"].ne(omitted)].to_parquet(train_path, index=False)
    old_result = build_labels_v2(config)

    v3_dir = config["paths"]["processed_v3"]
    v3_dir.mkdir(parents=True)
    for block in ("train", "val", "test"):
        split = flows.loc[flows["split"].eq(block)].drop(
            columns=["split", "label_rule", "attempted_category"],
            errors="ignore",
        )
        split.to_parquet(v3_dir / f"{block}.parquet", index=False)

    result = build_labels_v2_all(config)

    labels = pd.read_parquet(result["output_path"])
    old_labels = pd.read_parquet(old_result["output_path"])
    all_by_id = labels.set_index("flow_id")
    old_by_id = old_labels.set_index("flow_id")
    assert len(labels) == len(flows)
    assert labels["flow_id"].is_unique
    assert list(labels.columns) == list(old_labels.columns)
    assert all_by_id.loc[old_by_id.index].equals(old_by_id)
    assert all_by_id.loc[omitted, "label_orig_multi"] == "BENIGN"
    assert result["missing_from_old_v2"] == 1
    assert result["v3_block_counts"]["train"] == len(
        pd.read_parquet(v3_dir / "train.parquet")
    )
    assert not labels.isna().any().any()
    report = Path(result["report_path"]).read_text(encoding="utf-8")
    assert "Couverture complète des labels v2" in report
    assert "Couverture complète de l’audit" in report


def test_labels_v2_all_refuses_to_overwrite_existing_output(
    tmp_path: Path,
) -> None:
    config, _ = _fake_label_project(tmp_path)
    config["paths"]["output_all"].write_text("protected", encoding="utf-8")

    with pytest.raises(FileExistsError, match="Refus d’écraser"):
        build_labels_v2_all(config)

    assert config["paths"]["output_all"].read_text(encoding="utf-8") == "protected"
