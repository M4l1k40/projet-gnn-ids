"""Génération de la configuration de classes depuis les splits finaux."""

from collections import Counter
from pathlib import Path
from typing import Any, Mapping

import pyarrow.parquet as pq
import yaml

from src.utils.config import load_config

_SPLITS = ("train", "val", "test")
_TOO_RARE_EXCLUDED = (
    "Heartbleed",
    "Infiltration",
    "Web Attack - Sql Injection",
)
_LABEL_BATCH_SIZE = 100_000


def classify_classes(
    split_counts: Mapping[str, Mapping[str, int]],
    min_flows_per_block: int,
) -> dict[str, list[str]]:
    """Classe les labels selon leurs effectifs dans les trois splits."""
    missing_splits = set(_SPLITS) - set(split_counts)
    if missing_splits:
        raise ValueError(
            "Effectifs manquants pour les splits : "
            + ", ".join(sorted(missing_splits))
            + "."
        )
    if min_flows_per_block < 1:
        raise ValueError("min_flows_per_block doit être supérieur à zéro.")

    labels = set().union(*(split_counts[split].keys() for split in _SPLITS))
    if not labels:
        raise ValueError("Aucun label trouvé dans les splits finaux.")

    too_rare = set(_TOO_RARE_EXCLUDED)
    multiclass = sorted(
        (
            label
            for label in labels
            if label not in too_rare
            and all(
                int(split_counts[split].get(label, 0)) >= min_flows_per_block
                for split in _SPLITS
            )
        ),
        key=lambda label: (label != "BENIGN", label.casefold(), label),
    )
    if "BENIGN" not in multiclass:
        raise ValueError(
            "BENIGN doit atteindre min_flows_per_block dans train, val et test."
        )

    binary_only = sorted(
        (
            label
            for label in labels
            if label != "BENIGN"
            and label not in too_rare
            and label not in multiclass
        ),
        key=lambda label: (label.casefold(), label),
    )
    return {
        "multiclass_classes": multiclass,
        "binary_only": binary_only,
        "too_rare_excluded": list(_TOO_RARE_EXCLUDED),
    }


def _count_split_labels(processed_dir: Path) -> dict[str, Counter[str]]:
    counts: dict[str, Counter[str]] = {}
    for split in _SPLITS:
        path = processed_dir / f"{split}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Split final introuvable : {path}.")
        split_counts: Counter[str] = Counter()
        parquet_file = pq.ParquetFile(path)
        for batch in parquet_file.iter_batches(
            columns=["label_multi"],
            batch_size=_LABEL_BATCH_SIZE,
        ):
            labels = batch.column(0).to_pylist()
            if any(label is None for label in labels):
                raise ValueError(f"{path} contient des label_multi manquants.")
            split_counts.update(str(label) for label in labels)
        counts[split] = split_counts
    return counts


def generate_classes_config(
    config: dict[str, Any] | None = None,
    *,
    output_path: str | Path | None = None,
) -> tuple[Path, dict[str, list[str]]]:
    """Génère configs/classes.yaml à partir des Parquets finaux."""
    project_config = load_config() if config is None else config
    processed_dir = Path(project_config["paths"]["processed"])
    minimum = int(project_config["split"]["final"]["min_flows_per_block"])
    classes = classify_classes(_count_split_labels(processed_dir), minimum)
    destination = (
        Path(output_path)
        if output_path is not None
        else Path(__file__).resolve().parents[2] / "configs" / "classes.yaml"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        yaml.safe_dump(classes, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return destination, classes


if __name__ == "__main__":
    path, class_config = generate_classes_config()
    print(f"Configuration de classes générée : {path}")
    print(f"Classes multiclasse : {class_config['multiclass_classes']}")
    print(f"Classes binary-only : {class_config['binary_only']}")
