import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.fake import generate_fake_flows
from src.data.split import (
    assign_split,
    assign_split_blocks,
    assign_split_segment,
    find_attack_window_overlaps,
    run_split_diagnostics,
)
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


def _assert_split_changes_have_gap(
    frame: pd.DataFrame,
    splits: pd.Series,
    gap_seconds: float,
) -> None:
    for indexes in frame.groupby("day", observed=True).groups.values():
        ordered = frame.loc[indexes].sort_values("ts_end", kind="stable")
        kept = ordered.loc[splits.loc[ordered.index].ne("gap")]
        kept_splits = splits.loc[kept.index].to_numpy()
        differences = np.diff(kept["ts_end"].to_numpy(dtype=np.float64))
        transitions = kept_splits[1:] != kept_splits[:-1]
        if transitions.any():
            assert (differences[transitions] >= gap_seconds).all()


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


def test_trois_variantes_sur_factice_sont_reproductibles_et_respectent_les_gaps() -> None:
    config = load_config()
    fake = generate_fake_flows(config).drop(columns="split")
    ratios = config["split"]
    gap = 4
    assignments = {
        "V1": assign_split(fake, ratios, gap, mode="count")[0],
        "V2": assign_split_segment(fake, ratios, gap)[0],
        "V3": assign_split_blocks(
            fake,
            ratios,
            gap,
            block_minutes=config["split"]["variants"]["blocks"]["block_minutes"],
            seed=config["seeds"]["split"],
        )[0],
    }

    for variant, splits in assignments.items():
        assert splits.index.equals(fake.index)
        assert len(splits) == len(fake)
        assert splits.index.is_unique
        assert splits.isin(["train", "val", "test", "gap"]).all()
        if variant == "V3":
            _assert_split_changes_have_gap(fake, splits, gap * 120)
        elif variant == "V1":
            _assert_split_changes_have_gap(fake, splits, gap * 60)

    baseline_four = assignments["V1"]
    baseline_five, _ = assign_split(fake, ratios, 5, mode="count")
    _assert_split_changes_have_gap(fake, baseline_five, 5 * 60)

    segment = assignments["V2"]
    repeated_segment, _ = assign_split_segment(fake, ratios, gap)
    pd.testing.assert_series_equal(segment, repeated_segment)
    repeated_blocks, _ = assign_split_blocks(
        fake,
        ratios,
        gap,
        block_minutes=config["split"]["variants"]["blocks"]["block_minutes"],
        seed=config["seeds"]["split"],
    )
    pd.testing.assert_series_equal(assignments["V3"], repeated_blocks)

    for _, attack in fake.loc[fake["label_multi"].ne("BENIGN")].groupby(
        ["day", "label_multi"], observed=True
    ):
        _assert_split_changes_have_gap(
            attack,
            segment.loc[attack.index],
            gap * 60,
        )

    fallback, _ = assign_split(fake, ratios, gap, mode="count")
    for _, day in fake.groupby("day", observed=True):
        attack_ranges = (
            day.loc[day["label_multi"].ne("BENIGN")]
            .groupby("label_multi", observed=True)["ts_end"]
            .agg(["min", "max"])
        )
        outside = np.ones(len(day), dtype=bool)
        values = day["ts_end"].to_numpy(dtype=np.float64)
        for start, end in attack_ranges.itertuples(index=False, name=None):
            outside &= ~((values >= start) & (values <= end))
        benign_outside = day.loc[outside & day["label_multi"].eq("BENIGN").to_numpy()]
        pd.testing.assert_series_equal(
            segment.loc[benign_outside.index],
            fallback.loc[benign_outside.index],
        )

    assert not baseline_four.equals(baseline_five)


def test_variantes_blocs_stratifient_une_attaque_presente_en_trois_blocs() -> None:
    blocks = 30
    timestamps = np.array(
        [0.0] + [300 + 600 * index for index in range(blocks)],
        dtype=np.float64,
    )
    frame = pd.DataFrame(
        {
            "day": ["Monday"] * len(timestamps),
            "ts_end": timestamps,
            "label_multi": ["BENIGN"] + [
                "RareAttack" if index in {3, 12, 24} else "BENIGN"
                for index in range(blocks)
            ],
        }
    )
    ratios = {"train": 0.6, "validation": 0.15, "test": 0.25}

    splits, _ = assign_split_blocks(
        frame,
        ratios,
        gap_minutes=4,
        block_minutes=10,
        seed=42,
    )

    attack_splits = set(splits.loc[frame["label_multi"].eq("RareAttack")])
    assert attack_splits == {"train", "val", "test"}
    _assert_split_changes_have_gap(frame, splits, 8 * 60)


def test_v2_signale_les_plages_chevauchantes_et_priorise_la_plus_ancienne() -> None:
    frame = pd.DataFrame(
        {
            "day": ["Tuesday"] * 12,
            "ts_end": [
                100, 200, 300, 400, 500,
                300, 400, 500, 600, 700,
                350, 650,
            ],
            "label_multi": [
                "AttackA", "AttackA", "AttackA", "AttackA", "AttackA",
                "AttackB", "AttackB", "AttackB", "AttackB", "AttackB",
                "BENIGN", "BENIGN",
            ],
        }
    )
    ratios = {"train": 0.6, "validation": 0.15, "test": 0.25}

    overlaps = find_attack_window_overlaps(frame)
    splits, _ = assign_split_segment(frame, ratios, gap_minutes=0)

    assert len(overlaps) == 1
    assert overlaps[0]["first_class"] == "AttackA"
    assert overlaps[0]["second_class"] == "AttackB"
    assert splits.iloc[10] == "val"
    assert splits.iloc[11] == "test"
