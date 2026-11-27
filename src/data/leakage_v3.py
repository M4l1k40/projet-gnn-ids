"""Diagnostic de voisinage V3 en lecture seule des splits et métadonnées."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.spatial import cKDTree
from src.utils.config import load_config

_QUANTILES = (0, 1, 5, 25, 50, 75, 90, 95, 99, 100)
_DISTANCE_BANDS = ("distance nulle", "0 < distance ≤ p25", "p25–p75", "> p75")


def _project_root(config: dict[str, Any]) -> Path:
    if "_project_root" in config:
        return Path(config["_project_root"]).resolve()
    return Path(__file__).resolve().parents[2]


def _path(config: dict[str, Any], key: str) -> Path:
    value = config["paths"].get(key)
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(f"Chemin de configuration manquant : paths.{key}.")
    candidate = Path(value)
    return (
        candidate.resolve()
        if candidate.is_absolute()
        else (_project_root(config) / candidate).resolve()
    )


def load_leakage_v3_config(
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    path = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).resolve().parents[2]
        / "configs"
        / "leakage_v3.yaml"
    ).resolve()
    config = load_config(path)
    config["_project_root"] = path.parent.parent
    return config


def _features(config: dict[str, Any]) -> list[str]:
    path = _path(config, "feature_list")
    if not path.exists():
        raise FileNotFoundError(f"Liste des features introuvable : {path}.")
    features = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(features, list) or not features or not all(
        isinstance(feature, str) for feature in features
    ):
        raise ValueError("models/features.json doit contenir une liste non vide.")
    if len(set(features)) != len(features):
        raise ValueError("La liste des features contient des doublons.")
    return features


def _read_split(
    path: Path,
    features: list[str],
    include_bin: bool,
    variant: str,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Split {variant.upper()} introuvable : {path}.")
    required = ["flow_id", "label_multi", *features]
    if include_bin:
        required.append("label_bin")
    available = set(pq.ParquetFile(path).schema_arrow.names)
    missing = sorted(set(required) - available)
    if missing:
        raise ValueError(f"Colonnes absentes de {path} : {', '.join(missing)}.")
    frame = pd.read_parquet(path, columns=required)
    if frame["flow_id"].duplicated().any() or frame["label_multi"].isna().any():
        raise ValueError(f"{path} contient des identifiants dupliqués ou labels nuls.")
    if any(str(frame[name].dtype) != "float32" for name in features):
        raise TypeError(
            f"Les features {variant.upper()} doivent être déjà normalisées en float32."
        )
    values = frame.loc[:, features].to_numpy(dtype=np.float32, copy=False)
    if not np.isfinite(values).all():
        raise ValueError(f"{path} contient des features non finies.")
    return frame


def _verify_scaler(
    config: dict[str, Any],
    feature_count: int,
    scaler_key: str = "scaler_v3",
) -> None:
    scaler_path = _path(config, scaler_key)
    if not scaler_path.exists():
        raise FileNotFoundError(f"Scaler V3 introuvable : {scaler_path}.")
    scaler = joblib.load(scaler_path)
    if int(scaler.n_features_in_) != feature_count:
        raise ValueError(f"Le scaler {scaler_key} ne correspond pas aux features.")


def _stratified_test_sample(
    test: pd.DataFrame,
    features: list[str],
    seed: int,
    benign_limit: int,
    attack_limit: int,
) -> pd.DataFrame:
    if benign_limit < 1 or attack_limit < 1:
        raise ValueError("Les tailles d’échantillon doivent être positives.")
    rng = np.random.default_rng(seed)
    labels = test["label_multi"].astype(str).to_numpy()
    selected: list[np.ndarray] = []
    for label in sorted(set(labels)):
        indexes = np.flatnonzero(labels == label)
        limit = benign_limit if label == "BENIGN" else attack_limit
        size = min(limit, len(indexes))
        selected.append(
            np.sort(rng.choice(indexes, size=size, replace=False))
        )
    selected_indexes = np.sort(np.concatenate(selected))
    sample = test.iloc[selected_indexes].reset_index(drop=True)
    columns = ["flow_id", "label_multi", *features]
    if "label_bin" in test.columns:
        columns.insert(2, "label_bin")
    return sample.loc[:, columns]


def _peak_working_set_bytes() -> int:
    try:
        import psutil

        memory = psutil.Process(os.getpid()).memory_info()
        if hasattr(memory, "peak_wset"):
            return int(memory.peak_wset)
        if os.name != "nt":
            return int(memory.rss)
    except ImportError:
        pass
    if os.name != "nt":
        raise RuntimeError("La mesure du pic mémoire requiert psutil hors Windows.")
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if not psapi.GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(),
        ctypes.byref(counters),
        counters.cb,
    ):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.PeakWorkingSetSize)


def _load_inputs(
    config: dict[str, Any],
    variant: str = "v3",
) -> tuple[list[str], pd.DataFrame, pd.DataFrame]:
    if variant not in {"v2", "v3"}:
        raise ValueError("variant doit être v2 ou v3.")
    features = _features(config)
    _verify_scaler(config, len(features), f"scaler_{variant}")
    processed = _path(config, f"processed_{variant}")
    train = _read_split(
        processed / "train.parquet", features, include_bin=True, variant=variant
    )
    test = _read_split(
        processed / "test.parquet", features, include_bin=True, variant=variant
    )
    return features, train, test


def benchmark_v3(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construit l’index train et mesure 500 requêtes, sans écrire d’artefact."""
    project = load_leakage_v3_config() if config is None else config
    workers = int(project["workers"])
    query_batch_size = int(project["query_batch_size"])
    benchmark_queries = int(project["benchmark_queries"])
    if workers <= 1:
        raise ValueError("workers doit être supérieur à 1.")
    if query_batch_size < 1 or benchmark_queries < 1:
        raise ValueError("Les tailles de requête doivent être positives.")

    read_started = time.perf_counter()
    features, train, test = _load_inputs(project)
    sample = _stratified_test_sample(
        test,
        features,
        int(project["seed"]),
        int(project["benign_sample"]),
        int(project["attack_sample_per_class"]),
    )
    load_seconds = time.perf_counter() - read_started
    train_values = train.loc[:, features].to_numpy(dtype=np.float64, copy=True)
    query_values = sample.loc[:, features].to_numpy(dtype=np.float64, copy=True)

    build_started = time.perf_counter()
    tree = cKDTree(train_values, copy_data=False, compact_nodes=True, balanced_tree=True)
    build_seconds = time.perf_counter() - build_started
    measured = min(benchmark_queries, len(query_values))
    query_started = time.perf_counter()
    tree.query(
        query_values[:measured],
        k=1,
        workers=workers,
    )
    query_seconds = time.perf_counter() - query_started
    estimated_query_seconds = query_seconds / measured * len(query_values)
    estimate = load_seconds + build_seconds + estimated_query_seconds
    result = {
        "train_rows": len(train),
        "test_rows": len(test),
        "features": len(features),
        "sample_rows": len(sample),
        "sample_by_class": sample["label_multi"].value_counts().sort_index().to_dict(),
        "workers": workers,
        "query_batch_size": query_batch_size,
        "benchmark_queries": measured,
        "load_and_sample_seconds": load_seconds,
        "tree_build_seconds": build_seconds,
        "query_500_seconds": query_seconds,
        "estimated_all_query_seconds": estimated_query_seconds,
        "estimated_total_v3_seconds": estimate,
        "estimated_total_v3_minutes": estimate / 60,
        "estimated_train_float64_bytes": int(train_values.nbytes),
        "estimated_test_sample_float64_bytes": int(query_values.nbytes),
        "peak_working_set_bytes": _peak_working_set_bytes(),
        "v2_comparison_recommended": estimate < 30 * 60,
    }
    del tree, train_values, query_values, train, test, sample
    return result


def _distance_bands(distances: np.ndarray) -> tuple[np.ndarray, float, float]:
    p25, p75 = (float(value) for value in np.percentile(distances, [25, 75]))
    bands = np.full(len(distances), _DISTANCE_BANDS[3], dtype=object)
    bands[distances == 0] = _DISTANCE_BANDS[0]
    bands[(distances > 0) & (distances <= p25)] = _DISTANCE_BANDS[1]
    bands[(distances > p25) & (distances <= p75)] = _DISTANCE_BANDS[2]
    return bands, p25, p75


def _nearest_statistics(
    test_sample: pd.DataFrame,
    distances: np.ndarray,
    nearest_labels: np.ndarray,
    seen: np.ndarray,
    xgb_predictions: np.ndarray,
) -> pd.DataFrame:
    true_labels = test_sample["label_multi"].astype(str).to_numpy()
    zero = distances == 0
    labels_bin = test_sample["label_bin"].to_numpy(dtype=np.int8)
    rows = []
    for label in sorted(set(true_labels)):
        mask = true_labels == label
        values = distances[mask]
        quantiles = np.percentile(values, _QUANTILES)
        same_label = nearest_labels[mask] == true_labels[mask]
        different_label = ~same_label
        xgb_positive = xgb_predictions[mask] == 1
        attack = labels_bin[mask] == 1
        row: dict[str, Any] = {
            "label_multi": label,
            "sample_count": int(mask.sum()),
            "zero_distance_count": int(np.count_nonzero(zero & mask)),
            "zero_distance_share": float(np.mean(zero[mask])),
            "seen_in_train_count": int(np.count_nonzero(seen[mask])),
            "seen_in_train_share": float(np.mean(seen[mask])),
            "seen_and_zero_count": int(np.count_nonzero(seen[mask] & zero[mask])),
            "seen_but_nonzero_count": int(np.count_nonzero(seen[mask] & ~zero[mask])),
            "unseen_but_zero_count": int(np.count_nonzero(~seen[mask] & zero[mask])),
            "same_label_neighbor_count": int(np.count_nonzero(same_label)),
            "same_label_neighbor_share": float(np.mean(same_label)),
            "different_label_neighbor_count": int(np.count_nonzero(different_label)),
            "different_label_neighbor_share": float(np.mean(different_label)),
            "different_label_bin_count": int(
                np.count_nonzero(
                    labels_bin[mask] != (nearest_labels[mask] != "BENIGN").astype(np.int8)
                )
            ),
            "different_label_bin_share": float(
                np.mean(
                    labels_bin[mask]
                    != (nearest_labels[mask] != "BENIGN").astype(np.int8)
                )
            ),
            "xgb_attack_support": int(np.count_nonzero(attack)),
            "xgb_true_positives": int(np.count_nonzero(xgb_positive & attack)),
            "xgb_recall": (
                float(np.count_nonzero(xgb_positive & attack) / np.count_nonzero(attack))
                if np.any(attack)
                else float("nan")
            ),
            "one_nn_recall": float(
                np.mean(same_label)
            ),
        }
        row.update(
            {
                f"distance_q{quantile:02d}": float(value)
                for quantile, value in zip(_QUANTILES, quantiles)
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def _prediction_artifacts(
    config: dict[str, Any],
    variant: str,
) -> tuple[Path, Path, str]:
    if variant == "v3":
        return (
            _path(config, "xgb_v3_prediction_dir"),
            _path(config, "xgb_v3_threshold"),
            "xgb_bin_b0_seed42_v3.parquet",
        )
    return (
        _path(config, "xgb_v2_prediction_dir"),
        _path(config, "xgb_v2_threshold"),
        "xgb_bin_seed42.parquet",
    )


def _write_variant_report(
    config: dict[str, Any],
    variant: str,
) -> dict[str, str]:
    report_path = _path(config, f"report_{variant}")
    class_csv = _path(config, f"class_csv_{variant}")
    band_csv = _path(config, f"distance_band_csv_{variant}")
    existing = [path for path in (report_path, class_csv, band_csv) if path.exists()]
    if existing:
        raise FileExistsError(
            f"Refus d’écraser des sorties leakage {variant.upper()} : "
            + ", ".join(str(path) for path in existing)
        )

    features, train, test = _load_inputs(config, variant)
    sample = _stratified_test_sample(
        test,
        features,
        int(config["seed"]),
        int(config["benign_sample"]),
        int(config["attack_sample_per_class"]),
    )
    if variant == "v2":
        v3_class_path = _path(config, "class_csv_v3")
        if not v3_class_path.exists():
            raise FileNotFoundError("Le diagnostic V3 doit précéder la comparaison V2.")
        expected_rows = int(pd.read_csv(v3_class_path)["sample_count"].sum())
        if len(sample) != expected_rows:
            raise ValueError(
                f"Les échantillons V2/V3 diffèrent ({len(sample)} contre "
                f"{expected_rows}); impossible de comparer à taille égale."
            )

    train_values = train.loc[:, features].to_numpy(dtype=np.float64, copy=True)
    query_values = sample.loc[:, features].to_numpy(dtype=np.float64, copy=True)
    tree = cKDTree(train_values, copy_data=False, compact_nodes=True, balanced_tree=True)
    distances = np.empty(len(sample), dtype=np.float64)
    nearest_indexes = np.empty(len(sample), dtype=np.intp)
    batch_size = int(config["query_batch_size"])
    for start in range(0, len(sample), batch_size):
        stop = min(start + batch_size, len(sample))
        distances[start:stop], nearest_indexes[start:stop] = tree.query(
            query_values[start:stop],
            k=1,
            workers=int(config["workers"]),
        )
    nearest_labels = train["label_multi"].astype(str).to_numpy()[nearest_indexes]

    meta = pd.read_parquet(
        _path(config, f"meta_{variant}"),
        columns=["flow_id", "seen_in_train"],
    )
    if meta["flow_id"].duplicated().any():
        raise ValueError(f"meta {variant.upper()} contient des flow_id dupliqués.")
    seen_series = meta.set_index("flow_id")["seen_in_train"].reindex(sample["flow_id"])
    if seen_series.isna().any():
        raise ValueError(f"meta {variant.upper()} n’aligne pas seen_in_train.")
    seen = seen_series.to_numpy(dtype=bool)
    del meta, seen_series

    prediction_dir, threshold_path, prediction_name = _prediction_artifacts(
        config, variant
    )
    xgb_predictions = pd.read_parquet(
        prediction_dir / prediction_name,
        columns=["flow_id", "y_pred", "score", "seed"],
    )
    if (
        xgb_predictions["flow_id"].duplicated().any()
        or not xgb_predictions["seed"].eq(42).all()
    ):
        raise ValueError(f"Prédictions XGBoost {variant.upper()} seed 42 invalides.")
    prediction_index = xgb_predictions.set_index("flow_id")
    aligned_predictions = prediction_index.reindex(sample["flow_id"])
    if aligned_predictions[["y_pred", "score"]].isna().any().any():
        raise ValueError(f"Prédictions XGBoost {variant.upper()} incomplètes.")
    xgb_y_pred = aligned_predictions["y_pred"].to_numpy(dtype=np.int8)
    xgb_scores = aligned_predictions["score"].to_numpy(dtype=np.float64)
    del xgb_predictions, prediction_index, aligned_predictions
    threshold = json.loads(threshold_path.read_text(encoding="utf-8"))
    threshold_value = float(threshold["threshold_fpr_1pct"])
    if variant == "v3" and (
        threshold.get("variant") != "b0" or threshold.get("data_variant") != "v3"
    ):
        raise ValueError("Le seuil chargé ne correspond pas à XGBoost V3 b0.")
    if not np.array_equal(xgb_y_pred, (xgb_scores >= threshold_value).astype(np.int8)):
        raise ValueError(
            f"y_pred ne correspond pas au seuil chargé de XGBoost {variant.upper()} b0."
        )

    class_table = _nearest_statistics(
        sample,
        distances,
        nearest_labels,
        seen,
        xgb_y_pred,
    )
    bands, p25, p75 = _distance_bands(distances)
    y_true = sample["label_bin"].to_numpy(dtype=np.int8)
    band_rows = []
    for band in _DISTANCE_BANDS:
        mask = bands == band
        positive = y_true[mask] == 1
        negative = ~positive
        tp = int(np.count_nonzero(xgb_y_pred[mask] & positive))
        fp = int(np.count_nonzero(xgb_y_pred[mask] & negative))
        support = int(np.count_nonzero(positive))
        band_rows.append(
            {
                "distance_band": band,
                "sample_count": int(mask.sum()),
                "positive_support": support,
                "recall_xgboost": tp / support if support else float("nan"),
                "false_positives_xgboost": fp,
            }
        )
    band_table = pd.DataFrame(band_rows)
    class_csv.parent.mkdir(parents=True, exist_ok=True)
    band_csv.parent.mkdir(parents=True, exist_ok=True)
    class_table.to_csv(class_csv, index=False, encoding="utf-8")
    band_table.to_csv(band_csv, index=False, encoding="utf-8")

    scaler_path = _path(config, f"scaler_{variant}")
    lines = [
        f"# Diagnostic de voisinage et de fuite — split {variant.upper()}",
        "",
        f"- Test {variant.upper()} échantillonné avec la graine {config['seed']} : "
        f"{len(sample):,} flux; {len(features)} features déjà normalisées.",
        f"- Recherche 1-NN sur tout le train {variant.upper()} ({len(train):,} lignes), "
        f"requêtes par blocs de {batch_size}, workers={config['workers']}.",
        f"- Scaler propre à cette version : `{scaler_path}`; ses features sont vérifiées, "
        "mais il n’est pas réappliqué aux Parquets déjà normalisés.",
        f"- XGBoost {variant.upper()} b0 : seed 42, seuil {threshold_value:.8f}.",
        "",
        "## Distances, seen_in_train et 1-NN par classe",
        "",
        "| Classe | n | Distance nulle | seen_in_train | seen∩nulle | seen≠0 | unseen∩0 | Voisin même label | Voisin label différent | Voisin label_bin différent | Recall XGBoost | Recall 1-NN | Q1 | Q5 | Q25 | Q50 | Q75 | Q95 | Q99 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in class_table.itertuples(index=False):
        lines.append(
            f"| {row.label_multi} | {row.sample_count:,} | {row.zero_distance_share:.2%} "
            f"({row.zero_distance_count:,}) | {row.seen_in_train_share:.2%} "
            f"({row.seen_in_train_count:,}) | {row.seen_and_zero_count:,} | "
            f"{row.seen_but_nonzero_count:,} | {row.unseen_but_zero_count:,} | "
            f"{row.same_label_neighbor_share:.2%} ({row.same_label_neighbor_count:,}) | "
            f"{row.different_label_neighbor_share:.2%} ({row.different_label_neighbor_count:,}) | "
            f"{row.different_label_bin_share:.2%} ({row.different_label_bin_count:,}) | "
            f"{row.xgb_recall:.4f} | {row.one_nn_recall:.4f} | {row.distance_q01:.6g} | "
            f"{row.distance_q05:.6g} | {row.distance_q25:.6g} | {row.distance_q50:.6g} | "
            f"{row.distance_q75:.6g} | {row.distance_q95:.6g} | {row.distance_q99:.6g} |"
        )
    lines.extend(
        [
            "",
            "## Tableau de décision par classe",
            "",
            "| Classe | Voisin de même label | Voisin de label différent | Distance nulle |",
            "|---|---:|---:|---:|",
        ]
    )
    for row in class_table.itertuples(index=False):
        lines.append(
            f"| {row.label_multi} | {row.same_label_neighbor_share:.2%} "
            f"({row.same_label_neighbor_count:,}/{row.sample_count:,}) | "
            f"{row.different_label_neighbor_share:.2%} "
            f"({row.different_label_neighbor_count:,}/{row.sample_count:,}) | "
            f"{row.zero_distance_share:.2%} "
            f"({row.zero_distance_count:,}/{row.sample_count:,}) |"
        )
    low_recall = class_table.loc[
        class_table["label_multi"].ne("BENIGN")
        & class_table["xgb_recall"].lt(0.95)
    ]
    lines.extend(
        [
            "",
            "## Classes d’attaque avec recall XGBoost < 0,95",
            "",
            "| Classe | Recall XGBoost | Voisins de label différent |",
            "|---|---:|---:|",
        ]
    )
    for row in low_recall.itertuples(index=False):
        lines.append(
            f"| {row.label_multi} | {row.xgb_recall:.4f} | "
            f"{row.different_label_neighbor_share:.2%} "
            f"({row.different_label_neighbor_count:,}/{row.sample_count:,}) |"
        )
    if low_recall.empty:
        lines.append("| Aucune | — | — |")
    lines.extend(
        [
            "",
            "## XGBoost b0 par tranche de distance",
            "",
            f"Quantiles globaux de l’échantillon : p25={p25:.8g}, p75={p75:.8g}; "
            "la distance exactement nulle forme une catégorie séparée.",
            "",
            "| Tranche | n | Positifs | Recall XGBoost | Faux positifs XGBoost |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for row in band_table.itertuples(index=False):
        recall = (
            f"{row.recall_xgboost:.4f}"
            if np.isfinite(row.recall_xgboost)
            else "n.d."
        )
        lines.append(
            f"| {row.distance_band} | {row.sample_count:,} | {row.positive_support:,} | "
            f"{recall} | {row.false_positives_xgboost:,} |"
        )
    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- Les distances euclidiennes peuvent être dominées par les features de grande échelle malgré la standardisation.",
            "- Un voisin très proche n’établit pas une fuite : plusieurs flux peuvent provenir du même outil d’attaque et d’un même épisode.",
            "- Les statistiques décrivent un échantillon stratifié du test, pas une mesure exhaustive.",
            "",
            f"Table classe : `{class_csv}`. Tranches XGBoost : `{band_csv}`.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    del tree, train_values, query_values, train, test, sample
    return {
        "report_path": str(report_path),
        "class_csv": str(class_csv),
        "distance_band_csv": str(band_csv),
    }


def run_full_v3(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Calcule l’analyse complète et les rapports V3 sans toucher aux sources."""
    project = load_leakage_v3_config() if config is None else config
    return _write_variant_report(project, "v3")


def run_full_v2(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Calcule l’analyse V2 avec le scaler et les sorties qui lui sont propres."""
    project = load_leakage_v3_config() if config is None else config
    return _write_variant_report(project, "v2")


def append_variant_comparison(config: dict[str, Any] | None = None) -> None:
    """Ajoute la variation V3–V2 des taux de distance nulle aux deux rapports."""
    project = load_leakage_v3_config() if config is None else config
    v3_path = _path(project, "class_csv_v3")
    v2_path = _path(project, "class_csv_v2")
    reports = (_path(project, "report_v3"), _path(project, "report_v2"))
    if not v3_path.exists() or not v2_path.exists():
        raise FileNotFoundError("Les CSV de distance nulle V2 et V3 sont requis.")
    v3 = pd.read_csv(v3_path).set_index("label_multi")
    v2 = pd.read_csv(v2_path).set_index("label_multi")
    if set(v3.index) != set(v2.index):
        raise ValueError("Les classes échantillonnées V2 et V3 diffèrent.")
    comparison = pd.DataFrame(
        {
            "v3_zero_share": v3["zero_distance_share"],
            "v2_zero_share": v2["zero_distance_share"].reindex(v3.index),
        }
    )
    comparison["delta_v3_minus_v2_pp"] = (
        comparison["v3_zero_share"] - comparison["v2_zero_share"]
    ) * 100
    section = [
        "",
        "## Comparaison V3 contre V2 — distance nulle",
        "",
        "Part de l’échantillon dont la distance minimale est exactement nulle; variation exprimée en points de pourcentage (V3 − V2).",
        "",
        "| Classe | Part V2 | Part V3 | Variation (pp) |",
        "|---|---:|---:|---:|",
    ]
    for label, row in comparison.iterrows():
        section.append(
            f"| {label} | {row['v2_zero_share']:.2%} | {row['v3_zero_share']:.2%} | "
            f"{row['delta_v3_minus_v2_pp']:+.2f} |"
        )
    for report in reports:
        text = report.read_text(encoding="utf-8")
        marker = "## Comparaison V3 contre V2 — distance nulle"
        if marker in text:
            raise FileExistsError(f"La comparaison est déjà présente : {report}.")
        report.write_text(text.rstrip() + "\n" + "\n".join(section) + "\n", encoding="utf-8")


if __name__ == "__main__":
    print(json.dumps(benchmark_v3(), ensure_ascii=False, indent=2))
