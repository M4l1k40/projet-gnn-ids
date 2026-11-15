from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.relabel import build_label_audit, _flow_start_utc_ns


def _flow(
    flow_id: str,
    day: str,
    source_file: str,
    start_local: pd.Timestamp,
    label: str,
    *,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    forward_length: float,
) -> dict[str, object]:
    duration_us = 5_000_000.0
    end_local_ns = start_local.value + int(duration_us * 1_000)
    return {
        "flow_id": flow_id,
        "orig_flow_id": flow_id,
        "day": day,
        "source_file": source_file,
        "src_ip": src_ip,
        "dst_ip": dst_ip,
        "src_port": np.int32(src_port),
        "dst_port": np.int32(dst_port),
        "Flow Duration": np.float32(duration_us),
        "ts_end": np.float64(end_local_ns / 1_000_000_000),
        "label_multi": label,
        "Total Fwd Packets": np.float32(2),
        "Total Backward Packets": np.float32(1),
        "Total Length of Fwd Packets": np.float32(forward_length),
        "Total Length of Bwd Packets": np.float32(10),
        "Fwd Packet Length Max": np.float32(forward_length),
    }


def test_flow_start_is_shifted_from_local_as_utc_to_utc() -> None:
    local_start = pd.Timestamp("2017-07-04 10:00:00")
    frame = pd.DataFrame(
        {
            "ts_end": [float((local_start.value + 5_000_000_000) / 1_000_000_000)],
            "Flow Duration": [5_000_000.0],
        }
    )

    start_utc_ns = _flow_start_utc_ns(frame)[0]

    assert pd.Timestamp(start_utc_ns) == pd.Timestamp("2017-07-04 13:00:00")


def test_label_audit_applies_attempted_rules_without_changing_original_labels(
    tmp_path: Path,
) -> None:
    local_start = pd.Timestamp(1499170740, unit="s") - pd.Timedelta(hours=3)
    rows = [
        _flow(
            "ftp-attack",
            "Tuesday",
            "Tuesday-WorkingHours.pcap_ISCX.csv",
            local_start,
            "BENIGN",
            src_ip="172.16.0.1",
            dst_ip="192.168.10.50",
            src_port=50000,
            dst_port=21,
            forward_length=100,
        ),
        _flow(
            "ftp-attempted",
            "Tuesday",
            "Tuesday-WorkingHours.pcap_ISCX.csv",
            local_start,
            "FTP-Patator",
            src_ip="172.16.0.1",
            dst_ip="192.168.10.50",
            src_port=50001,
            dst_port=21,
            forward_length=0,
        ),
        _flow(
            "monday-fallback",
            "Monday",
            "Monday-WorkingHours.pcap_ISCX.csv",
            local_start,
            "DoS Hulk",
            src_ip="172.16.0.1",
            dst_ip="192.168.10.50",
            src_port=50002,
            dst_port=80,
            forward_length=100,
        ),
    ]
    input_path = tmp_path / "interim" / "clean.parquet"
    input_path.parent.mkdir(parents=True)
    pq.write_table(pa.Table.from_pylist(rows), input_path)

    audit_path, report_path, csv_path, summary = build_label_audit(
        {"paths": {"interim": input_path.parent, "processed": tmp_path / "processed"}},
        input_path=input_path,
        output_path=tmp_path / "processed" / "label_audit.parquet",
        report_path=tmp_path / "reports" / "label_audit.md",
        csv_path=tmp_path / "reports" / "label_audit.csv",
        batch_size=1,
    )

    audit = pd.read_parquet(audit_path).set_index("flow_id")
    assert audit.loc["ftp-attack", "label_rule"] == "FTP-Patator"
    assert audit.loc["ftp-attack", "attempted_category"] == -1
    assert audit.loc["ftp-attempted", "label_rule"] == "FTP-Patator - Attempted"
    assert audit.loc["ftp-attempted", "attempted_category"] == 0
    assert audit.loc["monday-fallback", "label_rule"] == "BENIGN"
    assert audit.loc["monday-fallback", "attempted_category"] == -1
    assert pd.read_parquet(input_path)["label_multi"].tolist() == [
        "BENIGN",
        "FTP-Patator",
        "DoS Hulk",
    ]
    assert summary.set_index("label_multi").loc["BENIGN", "different_flows"] == 1
    assert report_path.exists() and csv_path.exists()
    report = report_path.read_text(encoding="utf-8")
    assert "Monday" in report and "Tuesday" in report
    assert "ne corrige PAS" in report
