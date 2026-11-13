from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from src.data.timestamps import (
    add_ts_end,
    build_clean_dataset,
    check_attack_windows,
    correct_start_times,
)
from src.utils.config import load_config

_TIMESTAMP_CONFIG = {
    "timestamps": {
        "formats": {
            "Monday": "%d/%m/%Y %H:%M:%S",
            "other": "%d/%m/%Y %H:%M",
        },
        "pm_hour_threshold": 8,
    }
}


def _frame(
    timestamps: list[str],
    days: list[str],
    source_files: list[str] | None = None,
    durations: list[float] | None = None,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Timestamp": timestamps,
            "day": days,
            "source_file": source_files
            if source_files is not None
            else [f"{day}.csv" for day in days],
            "Flow Duration": durations
            if durations is not None
            else [0.0] * len(days),
        }
    )


def test_corrige_les_heures_12_heures_sans_decaler_les_heures_deja_pm() -> None:
    frame = _frame(
        [
            "04/07/2017 1:00",
            "04/07/2017 12:30",
            "04/07/2017 8:59",
            "04/07/2017 7:59",
        ],
        ["Tuesday"] * 4,
    )

    starts = correct_start_times(frame, _TIMESTAMP_CONFIG)

    assert starts.dt.strftime("%H:%M").tolist() == [
        "13:00",
        "12:30",
        "08:59",
        "19:59",
    ]


def test_lundi_parse_avec_secondes_et_calcul_de_ts_end() -> None:
    frame = _frame(
        ["03/07/2017 08:55:58", "03/07/2017 08:56:00"],
        ["Monday", "Monday"],
        durations=[1_500_000, 0],
    )

    starts, diagnostics = add_ts_end(frame, _TIMESTAMP_CONFIG)

    assert starts.dt.strftime("%H:%M:%S").tolist() == ["08:55:58", "08:56:00"]
    expected_start = starts.astype("int64").to_numpy(dtype=np.float64) / 1e9
    np.testing.assert_allclose(
        frame["ts_end"].to_numpy(),
        expected_start + np.array([1.5, 0.0]),
        rtol=0,
        atol=1e-6,
    )
    assert frame["ts_end"].dtype == np.dtype("float64")
    assert diagnostics.nonpositive_durations == {"Monday": 1}


def test_detecte_un_jour_de_semaine_incoherent() -> None:
    frame = _frame(["04/07/2017 01:00:00"], ["Monday"])

    with pytest.raises(ValueError, match="1 écart"):
        correct_start_times(frame, _TIMESTAMP_CONFIG)


def test_verification_des_plages_utilise_les_heures_corrigees() -> None:
    frame = _frame(
        ["04/07/2017 1:00", "04/07/2017 12:30"],
        ["Tuesday", "Tuesday"],
    )
    starts = correct_start_times(frame, _TIMESTAMP_CONFIG, afficher_resultats=False)
    diagnostics = check_attack_windows(
        pd.DataFrame(
            {
                "day": frame["day"],
                "label_multi": ["Bot", "Bot"],
            }
        ),
        starts,
        {
            "tolerance_minutes": 0,
            "windows": {"Tuesday": {"Bot": [["13:00", "13:00"]]}},
        },
    )

    tuesday_bot = next(
        row for row in diagnostics.rows
        if row["day"] == "Tuesday" and row["label_multi"] == "Bot"
    )
    assert tuesday_bot["flows"] == 2
    assert tuesday_bot["in_window"] == 1
    assert tuesday_bot["percentage"] == 50
    assert tuesday_bot["out_of_window"] == 1


def test_construit_les_parquets_tries_et_lechantillon_stratifie(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "clean_raw.parquet"
    output_dir = tmp_path / "interim"
    output_dir.mkdir()
    report_path = tmp_path / "reports" / "timestamps_check.md"
    windows_path = tmp_path / "attack_windows.yaml"
    windows_path.write_text(
        "tolerance_minutes: 0\n"
        "windows:\n"
        "  Tuesday:\n"
        "    Bot: [[\"13:00\", \"13:00\"]]\n",
        encoding="utf-8",
    )

    frame = pd.DataFrame(
        {
            "orig_flow_id": ["m2", "m1", "t1", "t2", "t3", "t4", "t5"],
            "src_ip": ["10.0.0.1"] * 7,
            "src_port": np.array([1000] * 7, dtype=np.int32),
            "dst_ip": ["10.0.0.2"] * 7,
            "dst_port": np.array([80] * 7, dtype=np.int32),
            "Flow Duration": np.array(
                [0, 1_000_000, 1_000_000, 0, 0, 0, -1_000_000],
                dtype=np.float32,
            ),
            "Feature": np.array([2, 1, 3, 4, 5, 6, 7], dtype=np.float32),
            "Timestamp": [
                "03/07/2017 08:56:00",
                "03/07/2017 08:55:58",
                "04/07/2017 1:00",
                "04/07/2017 12:30",
                "04/07/2017 8:59",
                "04/07/2017 7:59",
                "04/07/2017 12:31",
            ],
            "label_multi": [
                "BENIGN",
                "DoS",
                "Bot",
                "Bot",
                "BENIGN",
                "BENIGN",
                "DoS",
            ],
            "day": ["Monday", "Monday"] + ["Tuesday"] * 5,
            "source_file": ["Monday.csv"] * 2 + ["Tuesday.csv"] * 5,
            "flow_id": [f"flow-{index}" for index in range(7)],
            "label_bin": np.array([0, 1, 1, 1, 0, 0, 1], dtype=np.int8),
        }
    )
    pq.write_table(pa.Table.from_pandas(frame, preserve_index=False), input_path, row_group_size=2)

    config = load_config()
    config["paths"]["interim"] = output_dir
    clean_path, sample_path, generated_report = build_clean_dataset(
        config,
        input_path=input_path,
        report_path=report_path,
        attack_windows_path=windows_path,
        sample_size=5,
        batch_size=2,
    )

    clean = pq.ParquetFile(clean_path)
    output = clean.read().to_pandas()
    sample = pd.read_parquet(sample_path)
    assert len(output) == len(frame)
    assert clean.metadata.num_row_groups > 1
    assert "Timestamp" not in output.columns
    assert output.columns.tolist() == [
        column for column in frame.columns if column != "Timestamp"
    ] + ["ts_end"]
    assert output.groupby("day", sort=False)["ts_end"].apply(
        lambda values: values.is_monotonic_increasing
    ).all()
    assert output.loc[output["flow_id"] == "flow-2", "ts_end"].iloc[0] == pytest.approx(
        pd.Timestamp("2017-07-04 13:00:00").value / 1e9 + 1
    )
    assert output.loc[output["flow_id"] == "flow-6", "Flow Duration"].iloc[0] == -1_000_000
    assert len(sample) == 5
    assert sample.groupby(["day", "label_multi"], observed=True).size().min() >= 1
    assert sample["ts_end"].is_monotonic_increasing
    assert generated_report.exists()
    report = generated_report.read_text(encoding="utf-8")
    assert "Échecs de parsing Timestamp : 0" in report
    assert "Écarts entre date parsée et day : 0" in report
    assert "| Tuesday | Bot | 13:00–13:00 | 2 | 1 | 50.00% | 1 |" in report
    assert "Durées ≤ 0" in report
