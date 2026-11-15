"""Diagnostics de similarité des features entre les splits finaux."""

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.spatial import cKDTree

from src.data.schema import ID_COLS, META_COLS, TARGET_COLS
from src.utils.config import load_config

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
    frame = pd.read_parquet(path, columns=["flow_id"] + features + ["label_multi"])
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


def _rounded_hashes(frame: pd.DataFrame, features: list[str]):
    labels = frame["label_multi"].astype(str).to_numpy()
    indexes = np.arange(len(frame))
    for start in range(0, len(indexes), _BATCH_SIZE):
        batch_indexes = indexes[start : start + _BATCH_SIZE]
        rows = frame.iloc[batch_indexes][features]
        rounded = np.round(rows.to_numpy(dtype=np.float64), decimals=6)
        rounded[rounded == 0] = 0.0
        yield labels[batch_indexes], [
            row.tobytes() for row in np.ascontiguousarray(rounded)
        ]


def _train_hashes(
    train: pd.DataFrame,
    features: list[str],
) -> tuple[dict[str, set[bytes]], dict[str, int]]:
    hashes: dict[str, set[bytes]] = {}
    counts: dict[str, int] = {}
    for labels, rows in _rounded_hashes(train, features):
        for label, row_hash in zip(labels, rows):
            hashes.setdefault(label, set()).add(row_hash)
            counts[label] = counts.get(label, 0) + 1
    return hashes, counts


def _seen_in_train(
    frame: pd.DataFrame,
    train_hashes: dict[str, set[bytes]],
    features: list[str],
) -> pd.DataFrame:
    seen = np.empty(len(frame), dtype=bool)
    offset = 0
    for labels, rows in _rounded_hashes(frame, features):
        stop = offset + len(rows)
        seen[offset:stop] = [
            label in train_hashes and row_hash in train_hashes[label]
            for label, row_hash in zip(labels, rows)
        ]
        offset = stop
    if offset != len(frame):
        raise ValueError("Le calcul des drapeaux seen_in_train est incomplet.")
    return pd.DataFrame(
        {
            "flow_id": frame["flow_id"].astype(str).to_numpy(),
            "label_multi": frame["label_multi"].astype(str).to_numpy(),
            "seen_in_train": seen,
        }
    )


def _write_seen_flags_to_meta(
    meta_path: Path,
    seen_by_flow_id: dict[str, bool],
) -> None:
    if not meta_path.exists():
        raise FileNotFoundError(f"Métadonnées finales introuvables : {meta_path}.")
    parquet_file = pq.ParquetFile(meta_path)
    schema = parquet_file.schema_arrow
    if "flow_id" not in schema.names:
        raise ValueError(f"{meta_path} ne contient pas flow_id.")
    if (
        "seen_in_train" in schema.names
        and schema.field("seen_in_train").type != pa.bool_()
    ):
        raise ValueError("meta.parquet : seen_in_train doit être de type bool.")

    with TemporaryDirectory(prefix=".meta-seen-", dir=meta_path.parent) as temp_dir:
        staged_path = Path(temp_dir) / meta_path.name
        writer: pq.ParquetWriter | None = None
        try:
            for batch in parquet_file.iter_batches(batch_size=_BATCH_SIZE):
                table = pa.Table.from_batches([batch])
                flow_ids = table.column("flow_id").to_pylist()
                flags: list[bool | None] = []
                for flow_id in flow_ids:
                    key = str(flow_id)
                    flags.append(
                        seen_by_flow_id.pop(key) if key in seen_by_flow_id else None
                    )
                flag_array = pa.array(flags, type=pa.bool_())
                if "seen_in_train" in table.column_names:
                    table = table.set_column(
                        table.column_names.index("seen_in_train"),
                        "seen_in_train",
                        flag_array,
                    )
                else:
                    table = table.append_column("seen_in_train", flag_array)
                if writer is None:
                    writer = pq.ParquetWriter(staged_path, table.schema)
                else:
                    table = table.cast(writer.schema)
                writer.write_table(table, row_group_size=_BATCH_SIZE)
        finally:
            if writer is not None:
                writer.close()

        if seen_by_flow_id:
            raise ValueError(
                f"{len(seen_by_flow_id)} flux val/test absents de meta.parquet."
            )
        if writer is None:
            raise ValueError(f"{meta_path} est vide.")
        parquet_file.close()
        staged_path.replace(meta_path)


def _exact_matches_by_class(
    train_hashes: dict[str, set[bytes]],
    train_counts: dict[str, int],
    test_seen: pd.DataFrame,
) -> list[dict[str, Any]]:
    test_counts = test_seen.groupby("label_multi", sort=False).size().to_dict()
    matched_counts = (
        test_seen.loc[test_seen["seen_in_train"]]
        .groupby("label_multi", sort=False)
        .size()
        .to_dict()
    )
    results: list[dict[str, Any]] = []
    for label in sorted(set(train_hashes) | set(test_counts)):
        test_count = int(test_counts.get(label, 0))
        matches = int(matched_counts.get(label, 0))
        results.append(
            {
                "analyse": "identique_test_train",
                "classe": label,
                "flux_test": test_count,
                "flux_train": int(train_counts.get(label, 0)),
                "effectif_echantillon_test": None,
                "effectif_echantillon_train": None,
                "flux_identiques": matches,
                "pourcentage_identique": 100 * matches / test_count
                if test_count
                else 0.0,
                "distance_q01": None,
                "distance_q05": None,
                "distance_q25": None,
                "distance_q50": None,
                "pourcentage_distance_nulle": None,
                "split": None,
                "effectif": None,
                "flux_seen_in_train": None,
                "pourcentage_seen_in_train": None,
                "flux_test_strict": None,
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
    train_hashes, train_counts = _train_hashes(train, features)
    test_seen = _seen_in_train(test, train_hashes, features)
    val_seen = _seen_in_train(val, train_hashes, features)
    seen_by_flow_id = {
        str(flow_id): bool(seen)
        for candidates in (val_seen, test_seen)
        for flow_id, seen in zip(
            candidates["flow_id"],
            candidates["seen_in_train"],
        )
    }
    if len(seen_by_flow_id) != len(val_seen) + len(test_seen):
        raise ValueError("flow_id dupliqué entre les splits val et test.")
    _write_seen_flags_to_meta(data_dir / "meta.parquet", seen_by_flow_id)

    leakage_config = project_config["leakage"]
    train_sample_size = int(leakage_config["train_sample"])
    test_sample_size = int(leakage_config["test_sample"])
    if train_sample_size < 1 or test_sample_size < 1:
        raise ValueError("leakage.train_sample et leakage.test_sample doivent être positifs.")
    seed = int(project_config["seeds"]["global"])
    train_sample = _stratified_sample(train, train_sample_size, seed)
    test_sample = _stratified_sample(test, test_sample_size, seed + 1)
    val_sample = _stratified_sample(val, test_sample_size, seed + 2)

    exact_rows = _exact_matches_by_class(
        train_hashes,
        train_counts,
        test_seen,
    )
    tree = cKDTree(train_sample[features].to_numpy(dtype=np.float64))
    test_distances = _nearest_distances(tree, test_sample, features)
    val_distances = _nearest_distances(tree, val_sample, features)

    rows = exact_rows[:]
    all_labels = set(train_counts)
    counts_by_split: dict[str, tuple[dict[str, int], dict[str, int]]] = {}
    for split_name, candidates in (("val", val_seen), ("test", test_seen)):
        all_labels.update(candidates["label_multi"].unique())
        counts = candidates.groupby("label_multi", sort=False).size().to_dict()
        seen_counts = (
            candidates.loc[candidates["seen_in_train"]]
            .groupby("label_multi", sort=False)
            .size()
            .to_dict()
        )
        counts_by_split[split_name] = (counts, seen_counts)
    for split_name in ("val", "test"):
        counts, seen_counts = counts_by_split[split_name]
        for label in sorted(all_labels):
            count = int(counts.get(label, 0))
            seen_count = int(seen_counts.get(label, 0))
            rows.append(
                {
                    "analyse": "seen_in_train",
                    "classe": label,
                    "flux_test": None,
                    "flux_train": None,
                    "effectif_echantillon_test": None,
                    "effectif_echantillon_train": None,
                    "flux_identiques": None,
                    "pourcentage_identique": None,
                    "distance_q01": None,
                    "distance_q05": None,
                    "distance_q25": None,
                    "distance_q50": None,
                    "pourcentage_distance_nulle": None,
                    "split": split_name,
                    "effectif": count,
                    "flux_seen_in_train": seen_count,
                    "pourcentage_seen_in_train": (
                        100 * seen_count / count if count else 0.0
                    ),
                    "flux_test_strict": (
                        count - seen_count if split_name == "test" else None
                    ),
                }
            )
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
                    "split": None,
                    "effectif": None,
                    "flux_seen_in_train": None,
                    "pourcentage_seen_in_train": None,
                    "flux_test_strict": None,
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
        "## Drapeau seen_in_train et test strict",
        "",
        "`meta.parquet` contient `seen_in_train` : la valeur est nulle pour train, "
        "et vaut vrai pour val/test si un vecteur arrondi à 6 décimales existe dans train "
        "pour la même classe. Les lignes false du test constituent le test strict.",
        "",
        "| Split | Classe | Effectif | seen_in_train | Part | Flux test strict |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        if row["analyse"] != "seen_in_train":
            continue
        strict_count = str(row["flux_test_strict"]) if row["split"] == "test" else "—"
        report_lines.append(
            f"| {row['split']} | {row['classe']} | {row['effectif']} | "
            f"{row['flux_seen_in_train']} | "
            f"{row['pourcentage_seen_in_train']:.4f} % | {strict_count} |"
        )
    report_lines.extend(
        [
            "",
        "## Vecteurs test identiques au train par classe",
        "",
        "| Classe | Flux test | Flux train même classe | Vecteurs identiques | Part du test |",
        "|---|---:|---:|---:|---:|",
        ]
    )
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
