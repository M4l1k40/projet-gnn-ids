import json
import re
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import pytest
import yaml

from src.data.access import (
    feature_names,
    get_cv_fold,
    load_audit_labels,
    load_meta,
    load_p2_fold,
    load_split,
    multiclass_classes,
    strict_test_mask,
)
from src.utils.config import load_config


def _paths() -> tuple[Path, Path, Path]:
    config = load_config()
    processed = Path(config["paths"]["processed"])
    interim = Path(config["paths"]["interim"])
    return interim, processed, processed.parent.parent


def _skip_if_missing(*paths: Path) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        pytest.skip("Artefacts réels absents : " + ", ".join(missing))


def test_split_feature_and_class_access_shapes() -> None:
    _, processed, project_root = _paths()
    _skip_if_missing(
        *(processed / f"{split}.parquet" for split in ("train", "val", "test")),
        project_root / "models" / "features.json",
        project_root / "configs" / "classes.yaml",
    )

    for split in ("train", "val", "test"):
        frame = load_split(split, columns=["flow_id", "label_bin"])
        assert isinstance(frame, pd.DataFrame)
        assert frame.columns.tolist() == ["flow_id", "label_bin"]
        assert len(frame) == pq.ParquetFile(processed / f"{split}.parquet").metadata.num_rows

    names = feature_names()
    assert names == json.loads(
        (project_root / "models" / "features.json").read_text(encoding="utf-8")
    )
    train_columns = set(pq.ParquetFile(processed / "train.parquet").schema_arrow.names)
    assert names and set(names).issubset(train_columns)

    classes = multiclass_classes()
    yaml_classes = yaml.safe_load(
        (project_root / "configs" / "classes.yaml").read_text(encoding="utf-8")
    )["multiclass_classes"]
    assert classes == yaml_classes


def test_meta_strict_mask_and_audit_labels_align_to_split_order() -> None:
    _, processed, project_root = _paths()
    required = [
        processed / "meta.parquet",
        processed / "test.parquet",
        processed / "label_audit.parquet",
        project_root / "reports" / "data_card.md",
    ]
    _skip_if_missing(*required)

    test = load_split("test", columns=["flow_id"])
    meta = load_meta()
    assert isinstance(meta, pd.DataFrame)
    assert {"flow_id", "seen_in_train"}.issubset(meta.columns)

    mask = strict_test_mask()
    assert isinstance(mask, pd.Series)
    assert mask.dtype == bool
    assert mask.index.equals(test.index)
    sample_indexes = sorted({0, len(test) // 2, len(test) - 1})
    meta_positions = meta.set_index("flow_id").index.get_indexer(
        test["flow_id"].iloc[sample_indexes]
    )
    assert (meta_positions >= 0).all()
    expected_sample = meta["seen_in_train"].iloc[meta_positions].eq(False).tolist()
    assert mask.iloc[sample_indexes].tolist() == expected_sample

    card = (project_root / "reports" / "data_card.md").read_text(encoding="utf-8")
    strict_count = re.search(r"Flux test strict:\s*(\d+)", card)
    if strict_count:
        assert int(mask.sum()) == int(strict_count.group(1))

    split_ids = load_split("test", columns=["flow_id"])
    audit = load_audit_labels("test")
    assert audit.columns.tolist() == ["label_rule", "attempted_category"]
    assert audit.index.equals(split_ids.index)
    assert len(audit) == len(split_ids)


def test_cv_and_p2_access_return_real_fold_shapes() -> None:
    interim, processed, project_root = _paths()
    p2_scaler = project_root / "models" / "p2" / "day_Tuesday.joblib"
    _skip_if_missing(
        processed / "train.parquet",
        processed / "folds.parquet",
        processed / "p2_folds.parquet",
        interim / "clean.parquet",
        p2_scaler,
    )

    train_path = processed / "train.parquet"
    train_count = pq.ParquetFile(train_path).metadata.num_rows
    train_indexes, validation_indexes = get_cv_fold(0)
    assert train_indexes.ndim == validation_indexes.ndim == 1
    assert len(train_indexes) + len(validation_indexes) <= train_count
    assert set(train_indexes).isdisjoint(validation_indexes)
    assert validation_indexes.size > 0

    p2 = load_p2_fold("day_Tuesday")
    clean_count = pq.ParquetFile(interim / "clean.parquet").metadata.num_rows
    assert isinstance(p2, pd.DataFrame)
    assert len(p2) == clean_count
    assert "role" in p2.columns
    assert set(feature_names()).issubset(p2.columns)
    assert p2["role"].notna().all()
