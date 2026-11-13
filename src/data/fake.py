"""Génération d'un jeu de flux factices reproductible."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.data.schema import validate_schema
from src.utils.config import load_config

_SECONDS_PER_DAY = 24 * 60 * 60


def generate_fake_flows(config: dict[str, Any] | None = None) -> pd.DataFrame:
    """Génère les flux factices et écrit leur version finale en Parquet."""
    project_config = load_config() if config is None else config
    fake_config = project_config["fake"]
    split_config = project_config["split"]

    n_days = int(fake_config["n_days"])
    flows_per_day = int(fake_config["flows_per_day"])
    n_features = int(fake_config["n_features"])
    benign_ratio = float(fake_config["benign_ratio"])
    classes = list(fake_config["classes"])
    gap_seconds = float(split_config["gap_minutes"]) * 60
    seed = int(project_config["seeds"]["global"])

    if n_days < 1 or flows_per_day < 1 or n_features < 1:
        raise ValueError("n_days, flows_per_day et n_features doivent être positifs.")
    if not 0 < benign_ratio < 1:
        raise ValueError("benign_ratio doit être strictement compris entre 0 et 1.")
    if len(classes) < 3 or classes[0] != "BENIGN" or len(set(classes)) != len(classes):
        raise ValueError(
            "classes doit commencer par BENIGN et contenir au moins deux attaques uniques."
        )

    train_ratio = float(split_config["train"])
    validation_ratio = float(split_config["validation"])
    test_ratio = float(split_config["test"])
    if not np.isclose(train_ratio + validation_ratio + test_ratio, 1.0):
        raise ValueError("Les proportions de split doivent totaliser 1.")
    if gap_seconds < 0:
        raise ValueError("gap_minutes ne peut pas être négatif.")

    n_benign = int(round(flows_per_day * benign_ratio))
    n_attacks = flows_per_day - n_benign
    rare_count = max(1, int(flows_per_day * 0.001))
    attack_classes = classes[1:]
    if n_attacks < len(attack_classes):
        raise ValueError("flows_per_day ne permet pas de représenter toutes les classes.")
    if rare_count >= n_attacks or rare_count / flows_per_day >= 0.002:
        raise ValueError("flows_per_day doit permettre une classe rare sous 0,2 %.")

    attack_counts = [0] * len(attack_classes)
    remaining_attacks = n_attacks - rare_count
    regular_class_count = len(attack_classes) - 1
    if regular_class_count:
        base_count, remainder = divmod(remaining_attacks, regular_class_count)
        attack_counts[:-1] = [
            base_count + (1 if index < remainder else 0)
            for index in range(regular_class_count)
        ]
    attack_counts[-1] = rare_count
    if any(count == 0 for count in attack_counts):
        raise ValueError("Chaque classe d'attaque doit être représentée.")

    rng = np.random.default_rng(seed)
    base_epoch = float(pd.Timestamp("2024-01-01T00:00:00Z").timestamp())
    frames: list[pd.DataFrame] = []

    for day_index in range(n_days):
        timestamps = (
            base_epoch
            + day_index * 2 * _SECONDS_PER_DAY
            + np.arange(flows_per_day, dtype=np.float64)
            * (_SECONDS_PER_DAY / flows_per_day)
        )
        labels = np.full(flows_per_day, "BENIGN", dtype=object)
        attack_start = n_benign
        class_feature_offsets: dict[str, float] = {}
        for class_index, (attack_class, count) in enumerate(
            zip(attack_classes, attack_counts)
        ):
            labels[attack_start : attack_start + count] = attack_class
            class_feature_offsets[attack_class] = float(class_index + 1)
            attack_start += count

        features = rng.standard_normal((flows_per_day, n_features)).astype(np.float32)
        for attack_class, offset in class_feature_offsets.items():
            features[labels == attack_class] += np.float32(offset)

        first_cut = int(flows_per_day * train_ratio)
        second_cut = int(flows_per_day * (train_ratio + validation_ratio))
        if first_cut == 0 or second_cut <= first_cut or second_cut >= flows_per_day:
            raise ValueError("Les proportions de split ne produisent pas trois segments.")
        first_boundary = timestamps[first_cut]
        second_boundary = timestamps[second_cut]
        split_values = np.full(flows_per_day, None, dtype=object)
        split_values[timestamps < first_boundary] = "train"
        split_values[
            (timestamps >= first_boundary + gap_seconds)
            & (timestamps < second_boundary)
        ] = "val"
        split_values[timestamps >= second_boundary + gap_seconds] = "test"
        keep = pd.notna(split_values)
        if any(not np.any(split_values[keep] == name) for name in ("train", "val", "test")):
            raise ValueError(
                f"Le gap_minutes élimine un segment de split pour fake_day_{day_index + 1}."
            )

        kept_indices = np.flatnonzero(keep)
        frame_data: dict[str, Any] = {
            "flow_id": [
                f"fake-flow-{day_index * flows_per_day + index:08d}"
                for index in kept_indices
            ],
            "src_ip": [
                f"10.{day_index}.{(index // 254) % 256}.{index % 254 + 1}"
                for index in kept_indices
            ],
            "dst_ip": [
                f"192.168.{(index // 254) % 256}.{index % 254 + 1}"
                for index in kept_indices
            ],
            "src_port": rng.integers(
                1024, 65536, size=len(kept_indices), dtype=np.int32
            ),
            "dst_port": rng.integers(
                1, 65536, size=len(kept_indices), dtype=np.int32
            ),
            "ts_end": timestamps[keep].astype(np.float64, copy=False),
            "label_bin": (labels[keep] != "BENIGN").astype(np.int8),
            "label_multi": labels[keep].tolist(),
            "split": pd.Categorical(
                split_values[keep], categories=["train", "val", "test"], ordered=True
            ),
            "day": [f"fake_day_{day_index + 1}"] * len(kept_indices),
        }
        for feature_index in range(n_features):
            frame_data[f"feature_{feature_index:03d}"] = features[
                keep, feature_index
            ].astype(np.float32, copy=False)
        frames.append(pd.DataFrame(frame_data))

    flows = pd.concat(frames, ignore_index=True)
    validate_schema(flows, stage="final")

    output_path = Path(project_config["paths"]["interim"]) / "fake_flows.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    flows.to_parquet(output_path, index=False)
    return flows


if __name__ == "__main__":
    config = load_config()
    generated = generate_fake_flows(config)
    output_path = Path(config["paths"]["interim"]) / "fake_flows.parquet"
    print(f"{len(generated)} flux factices écrits dans {output_path}.")
