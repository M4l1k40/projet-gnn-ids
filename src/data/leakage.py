"""Diagnostics de similarité des features entre les splits finaux."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.spatial import cKDTree

from src.data.schema import ID_COLS, META_COLS, TARGET_COLS
from src.utils.config import load_config

_SPLITS = ("train", "val", "test")
_BATCH_SIZE = 50_000
_QUANTILES = (1, 5, 25, 50)


def _feature_columns(schema: pa.Schema) -> list[str]:
    excluded = set(ID_COLS + TARGET_COLS + META_COLS)
    features = [name for name in schema.names if name not in excluded]
    invalid = [
        name for name in features if not pa.types.is_float32(schema.field(name).type)
    ]
    if invalid:
        raise ValueError(
            "Features attendues en float32 : " + ", ".join(invalid) + "."
        )
    if not features:
        raise ValueError("Aucune feature disponible pour le diagnostic.")
    return features


def _read_split(path: Path, features: list[str]) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Split final introuvable : {path}.")
    frame = pd.read_parquet(path, columns=features + ["label_multi"])
    if frame["label_multi"].isna().any():
        raise ValueError(f"{path} contient des label_multi manquants.")
    if not np.isfinite(frame[features].to_numpy(dtype=np.float64)).all():
        raise ValueError(f"{path} contient des features non finies.")
    return frame


def _stratified_quotas(counts: dict[str, int], sample_size: int) -> dict[str, int]:
    total = sum(counts.values())
    target = min(sample_size, total)
    if target < len(counts):
        raise ValueError(
            f"L’échantillon de {target} flux ne couvre pas les "
            f"{len(counts)} classes présentes."
        )
    exact = {label: target * count / total for label, count in counts.items()}
    quotas = {
        label: min(counts[label], max(1, int(np.floor(exact[label]))))
        for label in counts
    }
    while sum(quotas.values()) > target:
        candidates = [label for label in quotas if quotas[label] > 1]
        if not candidates:
            raise ValueError("Impossible de réduire les quotas stratifiés.")
        label = max(
            candidates,
            key=lambda name: (quotas[name] - exact[name], quotas[name], name),
        )
        quotas[label] -= 1
    while sum(quotas.values()) < target:
        candidates = [label for label in quotas if quotas[label] < counts[label]]
        if not candidates:
            raise ValueError("Impossible d’atteindre la taille d’échantillon.")
        label = max(
            candidates,
            key=lambda name: (exact[name] - quotas[name], counts[name] - quotas[name], name),
        )
        quotas[label] += 1
    return quotas


def _stratified_sample(
    frame: pd.DataFrame,
    sample_size: int,
    seed: int,
) -> pd.DataFrame:
    labels = frame["label_multi"].astype(str)
    counts = {
        str(label): int(count)
        for label, count in labels.value_counts(sort=False).items()
    }
    quotas = _stratified_quotas(counts, sample_size)
    sampled: list[pd.DataFrame] = []
    for index, label in enumerate(sorted(quotas)):
        group = frame.loc[labels.eq(label)]
        sampled.append(
            group.sample(
                n=quotas[label],
                random_state=(seed + index) % (2**32 - 1),
            )
        )
    return pd.concat(sampled, ignore_index=True)


def _rounded_rows(frame: pd.DataFrame, indexes: np.ndarray, features: list[str]):
    for start in range(0, len(indexes), _BATCH_SIZE):
        rows = frame.iloc[indexes[start : start + _BATCH_SIZE]][features]
        rounded = np.round(rows.to_numpy(dtype=np.float64), decimals=6)
        rounded[rounded == 0] = 0.0
        yield np.ascontiguousarray(rounded)


def _exact_matches_by_class(
    train: pd.DataFrame,
    test: pd.DataFrame,
    features: list[str],
) -> list[dict[str, Any]]:
    train_labels = train["label_multi"].astype(str).to_numpy()
    test_labels = test["label_multi"].astype(str).to_numpy()
    results: list[dict[str, Any]] = []
    for label in sorted(set(train_labels) | set(test_labels)):
        train_indexes = np.flatnonzero(train_labels == label)
        test_indexes = np.flatnonzero(test_labels == label)
        train_rows = set()
        for rows in _rounded_rows(train, train_indexes, features):
            train_rows.update(row.tobytes() for row in rows)
        matches = 0
        for rows in _rounded_rows(test, test_indexes, features):
            matches += sum(row.tobytes() in train_rows for row in rows)
        results.append(
            {
                "analyse": "identique_test_train",
                "classe": label,
                "flux_test": len(test_indexes),
                "flux_train": len(train_indexes),
                "effectif_echantillon_test": None,
                "effectif_echantillon_train": None,
                "flux_identiques": matches,
                "pourcentage_identique": 100 * matches / len(test_indexes)
                if len(test_indexes)
                else 0.0,
                "distance_q01": None,
                "distance_q05": None,
                "distance_q25": None,
                "distance_q50": None,
                "pourcentage_distance_nulle": None,
            }
        )
    return results


def _nearest_distances(
    tree: cKDTree,
    sample: pd.DataFrame,
    features: list[str],
) -> np.ndarray:
    values = sample[features].to_numpy(dtype=np.float64)
    distances = np.empty(len(values), dtype=np.float64)
    for start in range(0, len(values), _BATCH_SIZE):
        stop = min(start + _BATCH_SIZE, len(values))
        distances[start:stop] = tree.query(
            values[start:stop],
            k=1,
            workers=-1,
        )[0]
    return distances


def run_leakage_diagnostics(
    config: dict[str, Any] | None = None,
    *,
    processed_dir: str | Path | None = None,
    reports_dir: str | Path | None = None,
) -> tuple[Path, Path, Path, pd.DataFrame, dict[str, Any]]:
    """Produit le rapport exact, les distances par classe et l’histogramme."""
    project_config = load_config() if config is None else config
    paths = project_config["paths"]
    data_dir = (
        Path(processed_dir) if processed_dir is not None else Path(paths["processed"])
    )
    if reports_dir is None:
        reports_dir = Path(__file__).resolve().parents[2] / "reports"
    report_dir = Path(reports_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    train_path = data_dir / "train.parquet"
    schema = pq.ParquetFile(train_path).schema_arrow
    features = _feature_columns(schema)
    train = _read_split(train_path, features)
    test = _read_split(data_dir / "test.parquet", features)
    val = _read_split(data_dir / "val.parquet", features)

    leakage_config = project_config["leakage"]
    train_sample_size = int(leakage_config["train_sample"])
    test_sample_size = int(leakage_config["test_sample"])
    if train_sample_size < 1 or test_sample_size < 1:
        raise ValueError("leakage.train_sample et leakage.test_sample doivent être positifs.")
    seed = int(project_config["seeds"]["global"])
    train_sample = _stratified_sample(train, train_sample_size, seed)
    test_sample = _stratified_sample(test, test_sample_size, seed + 1)
    val_sample = _stratified_sample(val, test_sample_size, seed + 2)

    exact_rows = _exact_matches_by_class(train, test, features)
    tree = cKDTree(train_sample[features].to_numpy(dtype=np.float64))
    test_distances = _nearest_distances(tree, test_sample, features)
    val_distances = _nearest_distances(tree, val_sample, features)

    rows = exact_rows[:]
    distance_sets = (
        ("test_vers_train", test_sample, test_distances, len(train_sample)),
        ("val_vers_train", val_sample, val_distances, len(train_sample)),
    )
    for analysis, sample, distances, train_count in distance_sets:
        labels = sample["label_multi"].astype(str).to_numpy()
        for label in sorted(set(labels)):
            class_distances = distances[labels == label]
            quantiles = np.percentile(class_distances, _QUANTILES)
            rows.append(
                {
                    "analyse": analysis,
                    "classe": label,
                    "flux_test": None,
                    "flux_train": None,
                    "effectif_echantillon_test": len(class_distances),
                    "effectif_echantillon_train": train_count,
                    "flux_identiques": None,
                    "pourcentage_identique": None,
                    "distance_q01": float(quantiles[0]),
                    "distance_q05": float(quantiles[1]),
                    "distance_q25": float(quantiles[2]),
                    "distance_q50": float(quantiles[3]),
                    "pourcentage_distance_nulle": (
                        100 * np.count_nonzero(class_distances == 0) / len(class_distances)
                    ),
                }
            )

    table = pd.DataFrame(rows)
    csv_path = report_dir / "leakage_report.csv"
    table.to_csv(csv_path, index=False, encoding="utf-8")
    exact_total = sum(int(row["flux_identiques"]) for row in exact_rows)
    exact_test_total = len(test)
    test_median = float(np.median(test_distances))
    test_zero_pct = 100 * np.count_nonzero(test_distances == 0) / len(test_distances)

    report_lines = [
        "# Diagnostic de fuite entre splits",
        "",
        f"- Features comparées : {len(features)} ; les ports, identifiants, `ts_end` et labels sont exclus.",
        f"- Échantillonnage stratifié : train {len(train_sample)}/{train_sample_size}, "
        f"test {len(test_sample)}/{test_sample_size}, val {len(val_sample)}/{test_sample_size}.",
        "- Les vecteurs identiques sont comparés après arrondi à 6 décimales et uniquement au sein de la même classe.",
        "- Les distances sont euclidiennes dans l’espace des features normalisées ; les voisins sont recherchés dans l’échantillon train stratifié.",
        "",
        "## Vecteurs test identiques au train par classe",
        "",
        "| Classe | Flux test | Flux train même classe | Vecteurs identiques | Part du test |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in exact_rows:
        report_lines.append(
            f"| {row['classe']} | {row['flux_test']} | {row['flux_train']} | "
            f"{row['flux_identiques']} | {row['pourcentage_identique']:.4f} % |"
        )
    report_lines.extend(
        [
            "",
            "## Distances au plus proche voisin",
            "",
            "| Comparaison | Classe | Échantillon | Train échantillonné | Q1 | Q5 | Q25 | Q50 | Distance nulle |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        if row["distance_q01"] is None:
            continue
        report_lines.append(
            f"| {row['analyse']} | {row['classe']} | "
            f"{row['effectif_echantillon_test']} | "
            f"{row['effectif_echantillon_train']} | "
            f"{row['distance_q01']:.8g} | {row['distance_q05']:.8g} | "
            f"{row['distance_q25']:.8g} | {row['distance_q50']:.8g} | "
            f"{row['pourcentage_distance_nulle']:.4f} % |"
        )
    report_lines.extend(
        [
            "",
            "## Résumé",
            "",
            f"- Flux test identiques au train, même classe : {exact_total}/{exact_test_total} "
            f"({100 * exact_total / exact_test_total:.4f} %).",
            f"- Médiane de distance test→train : {test_median:.8g}.",
            f"- Distances test→train nulles dans l’échantillon : {test_zero_pct:.4f} %.",
        ]
    )
    report_path = report_dir / "leakage_report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    histogram_path = report_dir / "leakage_histogram.png"
    figure, axis = plt.subplots(figsize=(9, 5))
    axis.hist(test_distances, bins=50, alpha=0.65, label="test → train")
    axis.hist(val_distances, bins=50, alpha=0.55, label="val → train")
    axis.set(title="Distances au plus proche voisin", xlabel="Distance euclidienne", ylabel="Flux")
    axis.legend()
    figure.tight_layout()
    figure.savefig(histogram_path, dpi=150)
    plt.close(figure)

    summary = {
        "exact_matches": exact_total,
        "exact_test_rows": exact_test_total,
        "exact_match_pct": 100 * exact_total / exact_test_total,
        "test_nn_median": test_median,
        "test_nn_zero_pct": test_zero_pct,
    }
    print(
        "Test exact same-class overlaps: "
        f"{exact_total}/{exact_test_total} ({summary['exact_match_pct']:.4f}%)."
    )
    print(f"Test-to-train nearest-neighbor median: {test_median:.8g}.")
    print(f"Test-to-train zero-distance sample rate: {test_zero_pct:.4f}%.")
    return report_path, csv_path, histogram_path, table, summary
