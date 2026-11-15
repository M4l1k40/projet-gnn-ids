from pathlib import Path

import pyarrow.parquet as pq
import pytest
import yaml

from src.utils.config import load_config


def _configured_paths() -> tuple[Path, Path, Path]:
    config = load_config()
    processed = Path(config["paths"]["processed"])
    interim = Path(config["paths"]["interim"])
    return interim, processed, processed.parent.parent


def test_real_label_audit_has_one_row_per_clean_flow() -> None:
    interim, processed, _ = _configured_paths()
    clean_path = interim / "clean.parquet"
    audit_path = processed / "label_audit.parquet"
    if not clean_path.exists() or not audit_path.exists():
        pytest.skip("Jeu réel absent : clean.parquet ou label_audit.parquet manquant.")

    clean = pq.ParquetFile(clean_path)
    audit = pq.ParquetFile(audit_path)
    assert audit.metadata.num_rows == clean.metadata.num_rows
    assert audit.schema_arrow.names == ["flow_id", "label_rule", "attempted_category"]


def test_real_redundancy_control_matches_expected_test_count() -> None:
    _, processed, project_root = _configured_paths()
    flags_path = processed / "redundancy_flags.parquet"
    report_path = project_root / "reports" / "redundancy_report.md"
    if not flags_path.exists() or not report_path.exists():
        pytest.skip("Jeu réel absent : flags ou rapport de redondance manquant.")

    flags = pq.ParquetFile(flags_path)
    assert flags.metadata.num_rows == sum(
        pq.ParquetFile(processed / f"{split}.parquet").metadata.num_rows
        for split in ("train", "val", "test")
    )
    report = report_path.read_text(encoding="utf-8")
    assert "Contrôle test/same-class : 200,648 flux (attendu : 200,648)." in report


def test_real_cv_folds_cover_train_rows() -> None:
    _, processed, _ = _configured_paths()
    train_path = processed / "train.parquet"
    folds_path = processed / "folds.parquet"
    if not train_path.exists() or not folds_path.exists():
        pytest.skip("Jeu réel absent : train.parquet ou folds.parquet manquant.")

    train = pq.ParquetFile(train_path)
    folds = pq.ParquetFile(folds_path)
    assert folds.metadata.num_rows == train.metadata.num_rows
    assert folds.schema_arrow.names == [
        "flow_id",
        "fold",
        "purged_0",
        "purged_1",
        "purged_2",
        "purged_3",
        "purged_4",
    ]


def test_real_p2_mapping_has_roles_without_features() -> None:
    interim, processed, project_root = _configured_paths()
    mapping_path = processed / "p2_folds.parquet"
    clean_path = interim / "clean.parquet"
    report_path = project_root / "reports" / "p2_report.md"
    families_path = project_root / "configs" / "attack_families.yaml"
    if not all(
        path.exists()
        for path in (mapping_path, clean_path, report_path, families_path)
    ):
        pytest.skip("Jeu réel absent : mapping, clean, rapport ou familles P2 manquant.")

    clean = pq.ParquetFile(clean_path)
    mapping = pq.ParquetFile(mapping_path)
    families = yaml.safe_load(families_path.read_text(encoding="utf-8"))
    expected_folds = 4 + sum(key != "rare_excluded" for key in families)
    assert mapping.schema_arrow.names == ["flow_id", "pli", "role"]
    assert mapping.metadata.num_rows == clean.metadata.num_rows * expected_folds
    assert set(mapping.schema_arrow.names).isdisjoint(
        {"Protocol", "Flow Duration", "Total Fwd Packets"}
    )
    scaler_names = [
        *(f"day_{day}" for day in ("Tuesday", "Wednesday", "Thursday", "Friday")),
        *(
            f"family_{family}"
            for family in families
            if family != "rare_excluded"
        ),
    ]
    for fold in scaler_names:
        assert (project_root / "models" / "p2" / f"{fold}.joblib").exists()
