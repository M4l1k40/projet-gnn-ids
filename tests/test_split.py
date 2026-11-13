import pandas as pd
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.fake import generate_fake_flows
from src.data.split import assign_split, run_split_diagnostics
from src.utils.config import load_config


def _check_day_splits(
    frame: pd.DataFrame,
    gap_minutes: float,
) -> dict[str, int]:
    splits, lost_by_day = assign_split(
        frame,
        ratios=load_config()["split"],
        gap_minutes=gap_minutes,
        mode="count",
    )
    for day, indexes in frame.groupby("day", observed=True).groups.items():
        day_frame = frame.loc[indexes].copy()
        day_frame["assigned_split"] = splits.loc[indexes]
        timestamps = {
            name: day_frame.loc[
                day_frame["assigned_split"] == name, "ts_end"
            ]
            for name in ("train", "val", "test")
        }
        assert all(not values.empty for values in timestamps.values())
        assert timestamps["train"].max() < timestamps["val"].min()
        assert timestamps["val"].max() < timestamps["test"].min()
        assert (
            timestamps["val"].min() - timestamps["train"].max()
            >= gap_minutes * 60
        )
        assert (
            timestamps["test"].min() - timestamps["val"].max()
            >= gap_minutes * 60
        )
        assert lost_by_day[str(day)] == int((day_frame["assigned_split"] == "gap").sum())
    return lost_by_day


def test_assign_split_sur_le_jeu_factice_respecte_ordre_et_gaps() -> None:
    config = load_config()
    fake_flows = generate_fake_flows(config)
    input_frame = fake_flows.drop(columns="split")

    lost_by_day = _check_day_splits(
        input_frame,
        gap_minutes=config["split"]["gap_minutes"],
    )

    assert len(lost_by_day) == config["fake"]["n_days"]
    assert set(lost_by_day) == {
        f"fake_day_{index}"
        for index in range(1, config["fake"]["n_days"] + 1)
    }


def test_assign_split_mode_time_et_gaps_nuls() -> None:
    frame = pd.DataFrame(
        {
            "day": ["Monday"] * 8,
            "ts_end": [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0],
        }
    )

    split, lost_by_day = assign_split(
        frame,
        ratios={"train": 0.5, "val": 0.25, "test": 0.25},
        gap_minutes=0,
        mode="time",
    )

    assert split.tolist() == [
        "train",
        "train",
        "train",
        "train",
        "val",
        "val",
        "test",
        "test",
    ]
    assert lost_by_day == {"Monday": 0}


def test_diagnostics_creent_les_rapports_sans_ecrire_de_parquets_split(
    tmp_path,
) -> None:
    input_path = tmp_path / "clean.parquet"
    report_path = tmp_path / "reports"
    rows = 20
    labels = ["BENIGN", "DoS"] * (rows // 2)
    frame = pd.DataFrame(
        {
            "day": ["Monday"] * rows,
            "ts_end": np.arange(rows, dtype=np.float64),
            "label_multi": labels,
            "label_bin": np.array(
                [0 if label == "BENIGN" else 1 for label in labels],
                dtype=np.int8,
            ),
            "flow_id": [f"flow-{index}" for index in range(rows)],
            "Flow Duration": np.zeros(rows, dtype=np.float32),
        }
    )
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), input_path)
    config = {
        "paths": {"interim": tmp_path},
        "split": {
            "train": 0.6,
            "validation": 0.15,
            "test": 0.25,
            "gap_minutes": 0,
            "mode": "count",
            "min_flows_per_block": 1,
        },
    }

    gap_report, classes_report, table = run_split_diagnostics(
        config,
        input_path=input_path,
        reports_dir=report_path,
    )

    assert gap_report.exists()
    assert classes_report.exists()
    assert classes_report.with_suffix(".csv").exists()
    assert {"train", "val", "test", "gap"} == set(table["bloc"])
    report = classes_report.read_text(encoding="utf-8")
    assert "### Monday" in report
    assert "| BENIGN |" in report
    assert "| DoS |" in report
    assert not any(
        (tmp_path / f"{block}.parquet").exists()
        for block in ("train", "val", "test")
    )
