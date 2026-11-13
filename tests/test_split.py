import pandas as pd

from src.data.fake import generate_fake_flows
from src.data.split import assign_split
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
