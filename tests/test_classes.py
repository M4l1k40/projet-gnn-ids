import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from src.data.classes import classify_classes, generate_classes_config


def test_classify_classes_respects_final_block_counts() -> None:
    counts = {
        "train": {
            "BENIGN": 100,
            "AttackA": 80,
            "AttackB": 60,
            "AttackC": 20,
            "Heartbleed": 100,
        },
        "val": {
            "BENIGN": 100,
            "AttackA": 50,
            "AttackB": 60,
            "AttackC": 30,
            "Heartbleed": 100,
        },
        "test": {
            "BENIGN": 100,
            "AttackA": 50,
            "AttackB": 40,
            "AttackC": 100,
            "Heartbleed": 100,
        },
    }

    result = classify_classes(counts, min_flows_per_block=50)

    assert result == {
        "multiclass_classes": ["BENIGN", "AttackA"],
        "binary_only": ["AttackB", "AttackC"],
        "too_rare_excluded": [
            "Heartbleed",
            "Infiltration",
            "Web Attack - Sql Injection",
        ],
    }


def test_generate_classes_config_reads_final_split_parquets(tmp_path) -> None:
    split_labels = {
        "train": ["BENIGN", "AttackA", "AttackA"],
        "val": ["BENIGN", "AttackA"],
        "test": ["BENIGN", "AttackA"],
    }
    for split, labels in split_labels.items():
        table = pa.Table.from_pandas(
            pd.DataFrame({"label_multi": labels}),
            preserve_index=False,
        )
        pq.write_table(table, tmp_path / f"{split}.parquet")

    output_path = tmp_path / "configs" / "classes.yaml"
    config = {
        "paths": {"processed": tmp_path},
        "split": {"final": {"min_flows_per_block": 1}},
    }

    written_path, classes = generate_classes_config(
        config,
        output_path=output_path,
    )

    assert written_path == output_path
    assert classes["multiclass_classes"] == ["BENIGN", "AttackA"]
    assert yaml.safe_load(output_path.read_text(encoding="utf-8")) == classes
