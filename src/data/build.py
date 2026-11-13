"""Orchestration de bout en bout du pipeline de données."""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml

from src.data.classes import generate_classes_config
from src.data.clean import clean_raw
from src.data.final_split import build_final_splits
from src.data.leakage import run_leakage_diagnostics
from src.data.normalize import normalize_final_data
from src.data.schema import ID_COLS, META_COLS, TARGET_COLS
from src.data.timestamps import build_clean_dataset
from src.utils.config import load_config

_BATCH_SIZE = 50_000
_SPLITS = ("train", "val", "test")


def _run_stage(
    name: str,
    outputs: Sequence[Path],
    action: Callable[[], Any],
    *,
    force: bool,
) -> None:
    existing = [path.exists() for path in outputs]
    if not force and all(existing):
        print(f"Étape {name} ignorée : ses sorties existent déjà.")
        return
    if not force and any(existing):
        missing = [str(path) for path, exists in zip(outputs, existing) if not exists]
        raise FileNotFoundError(
            f"Sorties partielles pour {name}; relancez avec --force. "
            f"Manquantes : {', '.join(missing)}."
        )
    print(f"Étape {name} : lancement.")
    action()
    missing = [str(path) for path in outputs if not path.exists()]
    if missing:
        raise FileNotFoundError(
            f"Étape {name} terminée sans produire : {', '.join(missing)}."
        )


def _class_counts(processed_dir: Path) -> dict[str, Counter[str]]:
    result: dict[str, Counter[str]] = {}
    for split in _SPLITS:
        parquet_file = pq.ParquetFile(processed_dir / f"{split}.parquet")
        counts: Counter[str] = Counter()
        for batch in parquet_file.iter_batches(
            columns=["label_multi"],
            batch_size=_BATCH_SIZE,
        ):
            labels = batch.column(0).to_pylist()
            if any(label is None for label in labels):
                raise ValueError(f"{split}.parquet contient des labels manquants.")
            counts.update(str(label) for label in labels)
        result[split] = counts
    return result


def _raw_data_limits(clean_path: Path) -> tuple[int, int, int]:
    parquet_file = pq.ParquetFile(clean_path)
    files_by_day: dict[str, str] = {}
    nonpositive_durations = 0
    for batch in parquet_file.iter_batches(
        columns=["day", "source_file", "Flow Duration"],
        batch_size=_BATCH_SIZE,
    ):
        frame = batch.to_pandas()
        for day, source_file in zip(frame["day"], frame["source_file"]):
            files_by_day[str(source_file)] = str(day)
        durations = pd.to_numeric(frame["Flow Duration"], errors="coerce").to_numpy(
            dtype=np.float64,
            na_value=np.nan,
        )
        if not np.isfinite(durations).all():
            raise ValueError("Flow Duration contient une valeur non finie.")
        nonpositive_durations += int(np.count_nonzero(durations <= 0))
    no_seconds_files = sum(day != "Monday" for day in files_by_day.values())
    return len(files_by_day), no_seconds_files, nonpositive_durations


def build_data_card(
    config: dict[str, Any] | None = None,
    *,
    report_path: str | Path | None = None,
) -> Path:
    """Génère la fiche de données depuis les Parquets et artefacts existants."""
    project_config = load_config() if config is None else config
    project_root = Path(__file__).resolve().parents[2]
    processed_dir = Path(project_config["paths"]["processed"])
    clean_path = Path(project_config["paths"]["interim"]) / "clean.parquet"
    report_dir = project_root / "reports"
    output_path = (
        Path(report_path) if report_path is not None else report_dir / "data_card.md"
    )
    train_path = processed_dir / "train.parquet"
    train_schema = pq.ParquetFile(train_path).schema_arrow
    features_path = project_root / "models" / "features.json"
    features = json.loads(features_path.read_text(encoding="utf-8"))
    classes_path = project_root / "configs" / "classes.yaml"
    classes = yaml.safe_load(classes_path.read_text(encoding="utf-8"))
    counts = _class_counts(processed_dir)
    split_rows = {
        split: pq.ParquetFile(processed_dir / f"{split}.parquet").metadata.num_rows
        for split in _SPLITS
    }
    clean_rows = pq.ParquetFile(clean_path).metadata.num_rows
    kept_rows = sum(split_rows.values())
    gap_rows = clean_rows - kept_rows
    if gap_rows < 0:
        raise ValueError("Les splits contiennent plus de lignes que clean.parquet.")
    file_count, no_seconds_files, nonpositive_durations = _raw_data_limits(clean_path)

    labels = sorted(set().union(*(counter.keys() for counter in counts.values())))
    class_table = [
        "| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Total conservé |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in labels:
        total = sum(counts[split].get(label, 0) for split in _SPLITS)
        cells = [
            f"{counts[split].get(label, 0)} "
            f"({100 * counts[split].get(label, 0) / total if total else 0:.2f} %)"
            for split in _SPLITS
        ]
        class_table.append(
            f"| {label} | " + " | ".join(cells) + f" | {total} |"
        )

    schema_rows = [
        "| Colonne | Type Parquet |",
        "|---|---|",
    ]
    schema_rows.extend(
        f"| `{field.name}` | `{field.type}` |" for field in train_schema
    )
    ratios = project_config["split"]
    seeds = project_config["seeds"]
    final_split = ratios["final"]
    leakage_csv = report_dir / "leakage_report.csv"
    exact_matches = None
    if leakage_csv.exists():
        leakage = pd.read_csv(leakage_csv)
        exact = leakage.loc[leakage["analyse"].eq("identique_test_train")]
        exact_matches = int(pd.to_numeric(exact["flux_identiques"]).sum())

    lines = [
        "# Fiche des données finales",
        "",
        "## Schéma final",
        "",
        f"- {len(ID_COLS)} colonnes d’identification, {len(features)} features float32, "
        f"{len(TARGET_COLS)} cibles et {len(META_COLS)} colonnes de méta-données.",
        "- Les features sont toutes les colonnes numériques hors identifiants, ports, ts_end, cibles et méta-données.",
        "",
        *schema_rows,
        "",
        "### Features normalisées",
        "",
        *[f"- `{feature}`" for feature in features],
        "",
        "## Effectifs",
        "",
        "| Split | Lignes |",
        "|---|---:|",
        *[f"| {split} | {split_rows[split]} |" for split in _SPLITS],
        f"| Gap supprimé | {gap_rows} |",
        f"| Total clean.parquet | {clean_rows} |",
        "",
        "## Classes par split",
        "",
        "Les pourcentages sont calculés dans chaque classe, sur les flux conservés.",
        "",
        *class_table,
        "",
        "## Classes d’expérience",
        "",
        "- Multiclasse : "
        + ", ".join(classes["multiclass_classes"])
        + ".",
        "- Binary-only (conservées avec `label_bin=1`) : "
        + (", ".join(classes["binary_only"]) or "aucune")
        + ".",
        "- Exclues des expériences : "
        + ", ".join(classes["too_rare_excluded"])
        + ". Les valeurs `label_multi` du Parquet restent intactes.",
        "",
        "## Paramètres et limites connues",
        "",
        f"- Split final : `{final_split['variant']}` (V2), gap {final_split['gap_minutes']:g} min ; "
        f"ratios train/val/test {ratios['train']:.0%}/{ratios['validation']:.0%}/{ratios['test']:.0%}.",
        f"- Seuil multiclasse : {final_split['min_flows_per_block']} flux dans chaque split.",
        f"- Graine split : {seeds['split']} ; globale : {seeds['global']} ; modèle : {seeds['model']}.",
        f"- Normalisation : `{project_config['normalization']['method']}`, ajustée uniquement sur train.",
        "- Les labels d’origine sont conservés sans correction ni regroupement.",
        f"- Résolution d’une minute sur {no_seconds_files} fichier(s) sur {file_count}.",
        f"- {nonpositive_durations} flux de durée nulle ou négative sont conservés.",
        "- `dst_port` est exclu des features car c’est une colonne d’identification.",
        "- Le split V2 n’est pas chronologique globalement ; les frontières sont définies par classe et jour.",
        f"- {gap_rows} flux marqués gap ont été supprimés des splits.",
        (
            f"- Fuite intra-attaque observée : {exact_matches} vecteurs test identiques au train "
            "dans la même classe ; voir `leakage_report.md`."
            if exact_matches is not None
            else "- Une fuite intra-attaque est possible ; voir `leakage_report.md`."
        ),
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def build_pipeline(
    config: dict[str, Any] | None = None,
    *,
    force: bool = False,
) -> dict[str, Path]:
    """Exécute le pipeline séquentiel ; les étapes complètes sont réutilisées."""
    project_config = load_config() if config is None else config
    project_root = Path(__file__).resolve().parents[2]
    interim = Path(project_config["paths"]["interim"])
    processed = Path(project_config["paths"]["processed"])
    reports = project_root / "reports"
    models = project_root / "models"
    classes_path = project_root / "configs" / "classes.yaml"

    _run_stage(
        "clean",
        [interim / "clean_raw.parquet", reports / "cleaning_report.md"],
        lambda: clean_raw(project_config),
        force=force,
    )
    _run_stage(
        "timestamps",
        [
            interim / "clean.parquet",
            interim / "clean_sample.parquet",
            reports / "timestamps_check.md",
        ],
        lambda: build_clean_dataset(project_config),
        force=force,
    )
    _run_stage(
        "split final",
        [processed / f"{split}.parquet" for split in (*_SPLITS, "meta")],
        lambda: build_final_splits(project_config),
        force=force,
    )
    _run_stage(
        "classes",
        [classes_path],
        lambda: generate_classes_config(project_config),
        force=force,
    )
    _run_stage(
        "normalisation",
        [
            models / "scaler.joblib",
            models / "features.json",
            reports / "normalization_report.md",
        ],
        lambda: normalize_final_data(project_config),
        force=force,
    )
    _run_stage(
        "fuite",
        [
            reports / "leakage_report.md",
            reports / "leakage_report.csv",
            reports / "leakage_histogram.png",
        ],
        lambda: run_leakage_diagnostics(project_config),
        force=force,
    )
    data_card = reports / "data_card.md"
    _run_stage(
        "fiche de données",
        [data_card],
        lambda: build_data_card(project_config),
        force=force,
    )
    return {
        "train": processed / "train.parquet",
        "val": processed / "val.parquet",
        "test": processed / "test.parquet",
        "meta": processed / "meta.parquet",
        "scaler": models / "scaler.joblib",
        "features": models / "features.json",
        "data_card": data_card,
    }


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Régénère toutes les étapes même si leurs sorties existent.",
    )
    arguments = parser.parse_args(argv)
    outputs = build_pipeline(force=arguments.force)
    for name, path in outputs.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
