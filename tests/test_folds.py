from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.data.folds import build_cv_folds, get_fold


def test_cv_folds_are_contiguous_purged_and_reproducible(tmp_path: Path) -> None:
    processed = tmp_path / "processed"
    reports = tmp_path / "reports"
    processed.mkdir()
    rows = []
    for label, count, offset in (("BENIGN", 12, 0), ("AttackA", 8, 0), ("AttackB", 5, 15)):
        for index in range(count):
            rows.append(
                {
                    "flow_id": f"{label}-{index}",
                    "day": "Tuesday",
                    "label_multi": label,
                    "ts_end": float(offset + index * 30),
                }
            )
    train_path = processed / "train.parquet"
    pq.write_table(pa.Table.from_pylist(rows), train_path)
    config = {
        "paths": {"processed": processed},
        "cv": {"k": 3, "purge_minutes": 1},
    }

    first_path, _, _ = build_cv_folds(
        config,
        train_path=train_path,
        output_path=processed / "folds-a.parquet",
        report_path=reports / "folds-a.md",
        batch_size=4,
    )
    second_path, _, _ = build_cv_folds(
        config,
        train_path=train_path,
        output_path=processed / "folds-b.parquet",
        report_path=reports / "folds-b.md",
        batch_size=5,
    )

    first = pd.read_parquet(first_path)
    second = pd.read_parquet(second_path)
    pd.testing.assert_frame_equal(first, second)
    timestamps = np.asarray([row["ts_end"] for row in rows], dtype=np.float64)
    days = np.asarray([row["day"] for row in rows])
    for fold in range(3):
        train_indexes, validation_indexes = get_fold(
            fold,
            config,
            folds_path=first_path,
        )
        assert not set(train_indexes).intersection(validation_indexes)
        assert np.all(first.loc[validation_indexes, "fold"].to_numpy() == fold)
        assert not first.loc[validation_indexes, f"purged_{fold}"].any()
        for train_index in train_indexes:
            same_day_validation = validation_indexes[
                days[validation_indexes] == days[train_index]
            ]
            if len(same_day_validation):
                assert (
                    np.abs(timestamps[same_day_validation] - timestamps[train_index])
                    >= 60
                ).all()
        purged_indexes = np.flatnonzero(first[f"purged_{fold}"].to_numpy())
        for index in purged_indexes:
            assert first.loc[index, "fold"] != fold
            same_day_validation = validation_indexes[
                days[validation_indexes] == days[index]
            ]
            assert (
                np.abs(timestamps[same_day_validation] - timestamps[index]) < 60
            ).any()
