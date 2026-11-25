"""Entraînement XGBoost avec validation croisée purgée."""

import argparse
import csv
import json
import math
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import joblib
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.preprocessing import LabelEncoder

from src.data.schema import ID_COLS, PREDICTION_COLUMNS
from src.utils.config import load_config

Mode = Literal["bin", "multi"]
_IDENTIFIER_COLUMNS = set(ID_COLS) | {
    "flow_id",
    "orig_flow_id",
    "source_file",
    "ts_end",
}


@dataclass
class LoadedSplit:
    """Split en mémoire avec features float32 et identifiants séparés."""

    name: str
    feature_names: list[str]
    X: np.ndarray
    y_bin: np.ndarray
    y_multi: np.ndarray
    flow_ids: np.ndarray
    seen_in_train: np.ndarray | None = None
    y_v2_bin: np.ndarray | None = None
    attempted: np.ndarray | None = None
    changed: np.ndarray | None = None
    v2_family: np.ndarray | None = None


def load_xgboost_config(
    config_path: str | Path | None = None,
) -> dict[str, Any]:
    """Charge la configuration XGBoost et résout ses chemins relatifs."""
    path = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).resolve().parents[2] / "configs" / "xgboost.yaml"
    ).resolve()
    config = load_config(path)
    config["_project_root"] = path.parent.parent
    return config


def _project_root(config: dict[str, Any]) -> Path:
    if "_project_root" in config:
        return Path(config["_project_root"]).resolve()
    processed = Path(config["paths"]["processed"]).resolve()
    if processed.parent.name == "data":
        return processed.parent.parent
    return processed.parent


def _configured_path(config: dict[str, Any], key: str) -> Path:
    value = config["paths"].get(key)
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(f"Chemin de configuration manquant : paths.{key}.")
    path = Path(value)
    return path.resolve() if path.is_absolute() else (_project_root(config) / path).resolve()


def _split_processed_dir(config: dict[str, Any]) -> Path:
    variant = config.get("data_variant", "v2")
    if variant == "v2":
        return Path(config["paths"]["processed"])
    if variant != "v3":
        raise ValueError("data_variant doit être v2 ou v3.")
    if config["paths"].get("processed_v3"):
        return _configured_path(config, "processed_v3")
    data_config = _data_config(config)
    path = data_config["paths"].get("processed_v3")
    if not isinstance(path, str) or not path:
        raise ValueError("Chemin data/processed_v3 manquant dans la configuration.")
    path = Path(path)
    return path.resolve() if path.is_absolute() else (_project_root(config) / path).resolve()


def _data_config(config: dict[str, Any]) -> dict[str, Any]:
    data_config_path = _configured_path(config, "data_config")
    return load_config(data_config_path)


def _label_rule_mapping(config: dict[str, Any]) -> dict[str, str]:
    mapping = config.get("label_rule_to_multi")
    if mapping is None:
        labels_config_path = _configured_path(config, "labels_config")
        labels_config = load_config(labels_config_path)
        mapping = labels_config.get("label_rule_to_multi")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("label_rule_to_multi doit définir une correspondance non vide.")
    return mapping


def _feature_names(config: dict[str, Any]) -> list[str]:
    path = _configured_path(config, "feature_list")
    if not path.exists():
        raise FileNotFoundError(f"Liste des features introuvable : {path}.")
    features = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(features, list) or not features or not all(
        isinstance(feature, str) for feature in features
    ):
        raise ValueError(f"{path} doit contenir une liste JSON non vide de chaînes.")
    forbidden = sorted(set(features) & _IDENTIFIER_COLUMNS)
    if forbidden:
        raise ValueError(
            "La liste de features contient des identifiants : "
            + ", ".join(forbidden)
            + "."
        )
    return features


def _attach_seen_flag(
    flow_ids: np.ndarray,
    split: str,
    processed_dir: Path,
) -> np.ndarray:
    meta_path = processed_dir / "meta.parquet"
    if not meta_path.exists():
        raise FileNotFoundError(f"Métadonnées introuvables : {meta_path}.")
    meta = pd.read_parquet(meta_path, columns=["flow_id", "seen_in_train"])
    if meta["flow_id"].duplicated().any():
        raise ValueError("meta.parquet contient des flow_id dupliqués.")
    flags = meta.set_index("flow_id")["seen_in_train"].reindex(flow_ids)
    if flags.isna().any():
        raise ValueError(
            f"seen_in_train absent ou nul pour {split} "
            f"({int(flags.isna().sum())} flux)."
        )
    if not flags.map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise TypeError("seen_in_train doit contenir des booléens.")
    return flags.to_numpy(dtype=bool, copy=True)


def load_split(
    name: str,
    config: dict[str, Any] | None = None,
) -> LoadedSplit:
    """Charge les seules features configurées et les labels d'un split."""
    if name not in {"train", "val", "test"}:
        raise ValueError("name doit être train, val ou test.")
    project_config = load_xgboost_config() if config is None else config
    processed_dir = _split_processed_dir(project_config)
    parquet_path = processed_dir / f"{name}.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(f"Split introuvable : {parquet_path}.")

    features = _feature_names(project_config)
    available = set(pq.ParquetFile(parquet_path).schema_arrow.names)
    required = set(features) | {"flow_id", "label_bin", "label_multi"}
    missing = sorted(required - available)
    if missing:
        raise ValueError(
            f"Colonnes absentes de {parquet_path} : {', '.join(missing)}."
        )
    frame = pd.read_parquet(
        parquet_path,
        columns=["flow_id", "label_bin", "label_multi", *features],
    )
    feature_frame = frame.loc[:, features]
    if any(str(dtype) != "float32" for dtype in feature_frame.dtypes):
        invalid = [
            f"{column}={dtype}"
            for column, dtype in feature_frame.dtypes.items()
            if str(dtype) != "float32"
        ]
        raise TypeError("Features attendues en float32 : " + ", ".join(invalid) + ".")
    matrix = feature_frame.to_numpy(dtype=np.float32, copy=False)
    if not matrix.flags.c_contiguous:
        matrix = np.ascontiguousarray(matrix)
    y_bin = frame["label_bin"].to_numpy(dtype=np.int8, copy=True)
    y_multi = frame["label_multi"].to_numpy(copy=False)
    flow_ids = frame["flow_id"].to_numpy(copy=False)
    y_v2_bin = attempted = changed = v2_family = None
    if project_config.get("data_variant", "v2") == "v3":
        labels_path = _configured_path(project_config, "labels_v2_all")
        labels = pd.read_parquet(
            labels_path,
            columns=[
                "flow_id",
                "label_orig_multi",
                "label_v2_bin",
                "attempted",
                "changed",
                "v2_family",
            ],
        )
        if labels["flow_id"].duplicated().any():
            raise ValueError("labels_v2_all.parquet contient des flow_id dupliqués.")
        label_index = labels.set_index("flow_id")
        aligned = label_index.reindex(flow_ids)
        if aligned.isna().any().any():
            raise ValueError(f"labels_v2_all.parquet ne couvre pas tout le bloc {name}.")
        if not np.array_equal(
            aligned["label_orig_multi"].astype(str).to_numpy(),
            y_multi.astype(str),
        ):
            raise ValueError(f"label_orig_multi diffère de {name}.parquet.")
        y_v2_bin = aligned["label_v2_bin"].to_numpy(dtype=np.int8, copy=True)
        attempted = aligned["attempted"].to_numpy(dtype=bool, copy=True)
        changed = aligned["changed"].to_numpy(dtype=bool, copy=True)
        v2_family = aligned["v2_family"].to_numpy(copy=True)
    seen = (
        _attach_seen_flag(flow_ids, name, processed_dir)
        if name in {"val", "test"}
        else None
    )
    del feature_frame, frame
    return LoadedSplit(
        name,
        features,
        matrix,
        y_bin,
        y_multi,
        flow_ids,
        seen,
        y_v2_bin,
        attempted,
        changed,
        v2_family,
    )


def _fold_data(
    train: LoadedSplit,
    config: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    fold_count = int(config["cv_folds"])
    folds_path = _split_processed_dir(config) / "folds.parquet"
    if not folds_path.exists():
        raise FileNotFoundError(f"Plis purgés introuvables : {folds_path}.")
    schema_columns = pq.ParquetFile(folds_path).schema_arrow.names
    purge_columns = sorted(
        (
            column
            for column in schema_columns
            if column.startswith("purged_")
            and column.removeprefix("purged_").isdigit()
        ),
        key=lambda column: int(column.removeprefix("purged_")),
    )
    if len(purge_columns) < fold_count:
        raise ValueError("folds.parquet ne contient pas assez de plis purgés.")
    columns = ["flow_id", "fold", *purge_columns]
    folds = pd.read_parquet(folds_path, columns=columns)
    if len(folds) != len(train.flow_ids):
        raise ValueError("folds.parquet n'est pas aligné sur le nombre de lignes train.")
    if not np.array_equal(folds["flow_id"].to_numpy(), train.flow_ids):
        raise ValueError("L'ordre des flow_id de folds.parquet diffère du train.")
    fold_ids = folds["fold"].to_numpy(dtype=np.int8, copy=True)
    purged = np.column_stack(
        [
            folds[column].to_numpy(dtype=bool, copy=True)
            for column in purge_columns
        ]
    )
    if not set(np.unique(fold_ids)).issubset(set(range(len(purge_columns)))):
        raise ValueError("folds.parquet contient un numéro de pli inattendu.")
    return fold_ids, purged


def _search_folds(config: dict[str, Any]) -> list[int]:
    fold_count = int(config["cv_folds"])
    folds = list(config.get("search_folds", range(fold_count)))
    if not folds or len(set(folds)) != len(folds):
        raise ValueError("search_folds doit contenir au moins un pli unique.")
    if any(not isinstance(fold, int) or not 0 <= fold < fold_count for fold in folds):
        raise ValueError("search_folds contient un pli hors de cv_folds.")
    return folds


def _label_encoder(classes: list[str]) -> LabelEncoder:
    encoder = LabelEncoder()
    encoder.fit(np.asarray(classes, dtype=str))
    if len(encoder.classes_) != len(classes):
        raise ValueError("Les classes multiclasse doivent être uniques.")
    return encoder


def select_multiclass_classes(
    config: dict[str, Any] | None = None,
    *,
    write_report: bool = True,
) -> dict[str, Any]:
    """Sélectionne les classes au seuil configuré, en lisant seulement les labels."""
    project_config = load_xgboost_config() if config is None else config
    data_config = _data_config(project_config)
    minimum = int(data_config["split"]["final"]["min_flows_per_block"])
    blocks = list(project_config["multiclass_blocks"])
    if not blocks or any(block not in {"train", "val", "test"} for block in blocks):
        raise ValueError("multiclass_blocks doit contenir train, val ou test.")

    report_blocks = list(dict.fromkeys([*blocks, "train", "val", "test"]))
    counts_by_block: dict[str, Counter[str]] = {}
    for block in report_blocks:
        path = Path(data_config["paths"]["processed"]) / f"{block}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Split requis pour les classes absent : {path}.")
        labels = pd.read_parquet(path, columns=["label_multi"])["label_multi"]
        counts_by_block[block] = Counter(labels.astype(str))

    labels = sorted(set().union(*(counts.keys() for counts in counts_by_block.values())))
    def eligible(required_blocks: list[str]) -> list[str]:
        return [
            label
            for label in labels
            if all(
                counts_by_block[block].get(label, 0) >= minimum
                for block in required_blocks
            )
        ]

    selected = eligible(blocks)
    all_three_blocks = ["train", "val", "test"]
    selected_all_three = eligible(all_three_blocks)
    excluded = [
        {
            "label": label,
            "counts": {
                block: counts_by_block[block].get(label, 0) for block in blocks
            },
        }
        for label in labels
        if label not in selected
    ]
    result = {
        "minimum_per_block": minimum,
        "blocks": blocks,
        "multiclass_classes": selected,
        "multiclass_classes_train_val_test": selected_all_three,
        "excluded_classes": excluded,
        "excluded_classes_train_val_test": [
            {
                "label": label,
                "counts": {
                    block: counts_by_block[block].get(label, 0)
                    for block in all_three_blocks
                },
            }
            for label in labels
            if label not in selected_all_three
        ],
        "counts_by_block": {
            block: dict(counts_by_block[block]) for block in blocks
        },
    }
    if not selected or "BENIGN" not in selected:
        raise ValueError("La sélection multiclasse doit inclure BENIGN et une attaque.")
    if write_report:
        report_dir = _configured_path(project_config, "report_dir")
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "multiclass_classes.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return result


def recompute_label_audit(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Recalcule les divergences après normalisation des noms de règles."""
    project_config = load_xgboost_config() if config is None else config
    mapping = _label_rule_mapping(project_config)
    processed = Path(project_config["paths"]["processed"])
    audit_path = processed / "label_audit.parquet"
    if not audit_path.exists():
        raise FileNotFoundError(f"Audit de labels introuvable : {audit_path}.")
    audit = pd.read_parquet(
        audit_path,
        columns=["flow_id", "label_rule", "attempted_category"],
    )
    if audit["flow_id"].duplicated().any():
        raise ValueError("label_audit.parquet contient des flow_id dupliqués.")
    audit_by_id = audit.set_index("flow_id")
    rows: list[dict[str, Any]] = []
    summary: dict[str, dict[str, int]] = {}

    for split in ("train", "val", "test"):
        split_path = processed / f"{split}.parquet"
        frame = pd.read_parquet(split_path, columns=["flow_id", "label_multi"])
        positions = audit_by_id.index.get_indexer(frame["flow_id"])
        if np.any(positions < 0):
            raise ValueError(
                f"label_audit.parquet ne couvre pas toutes les lignes de {split}."
            )
        matched = audit_by_id.take(positions)
        canonical = matched["label_rule"].map(mapping)
        unknown = canonical.isna()
        if unknown.any():
            values = sorted(matched.loc[unknown, "label_rule"].astype(str).unique())
            raise ValueError(
                "Règles absentes de label_rule_to_multi : " + ", ".join(values) + "."
            )
        original_labels = frame["label_multi"].astype(str)
        divergence = canonical.to_numpy() != original_labels.to_numpy()
        attempted = matched["attempted_category"].to_numpy(dtype=np.int16) >= 0
        flagged = divergence | attempted
        summary[split] = {
            "effectif": len(frame),
            "divergences_reelles": int(np.count_nonzero(divergence)),
            "regles_attempted": int(np.count_nonzero(attempted)),
            "signales": int(np.count_nonzero(flagged)),
        }

        per_class = pd.DataFrame(
            {
                "classe": original_labels.to_numpy(),
                "divergence_reelle": divergence,
                "attempted": attempted,
                "signale": flagged,
            }
        ).groupby("classe", sort=True, observed=True)
        for label, group in per_class:
            rows.append(
                {
                    "bloc": split,
                    "label_multi": label,
                    "effectif": len(group),
                    "divergences_reelles": int(group["divergence_reelle"].sum()),
                    "attempted_category_nonnegatif": int(group["attempted"].sum()),
                    "signales_union": int(group["signale"].sum()),
                }
            )

    report_dir = _configured_path(project_config, "report_dir")
    report_dir.mkdir(parents=True, exist_ok=True)
    csv_path = report_dir / "label_audit_divergences.csv"
    report_path = report_dir / "label_audit_divergences.md"
    table = pd.DataFrame(rows)
    table.to_csv(csv_path, index=False, encoding="utf-8")
    lines = [
        "# Divergences réelles de l’audit des labels",
        "",
        "- `label_rule` est d’abord converti en label CIC-IDS2017 canonique via "
        "`configs/xgboost.yaml` ; les labels originaux ne sont pas modifiés.",
        "- Un flux est « signalé » si `label_rule` canonique diffère de `label_multi` "
        "ou si `attempted_category >= 0`.",
        "- Les effectifs portent uniquement sur les lignes des splits finaux ; les "
        "flux du gap ne sont pas inclus.",
        "",
        "| Bloc | Flux | Divergences réelles | Règle Attempted | Signalés (union) |",
        "|---|---:|---:|---:|---:|",
    ]
    for split, counts in summary.items():
        lines.append(
            f"| {split} | {counts['effectif']} | "
            f"{counts['divergences_reelles']} | {counts['regles_attempted']} | "
            f"{counts['signales']} |"
        )
    lines.extend(
        [
            "",
            "## Divergences et signalements par classe",
            "",
            "| Bloc | Classe | Effectif | Divergences réelles | Attempted | Signalés (union) |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    lines.extend(
        f"| {row['bloc']} | {row['label_multi']} | {row['effectif']} | "
        f"{row['divergences_reelles']} | {row['attempted_category_nonnegatif']} | "
        f"{row['signales_union']} |"
        for row in rows
    )
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "summary": summary,
        "csv_path": str(csv_path),
        "report_path": str(report_path),
    }


def _read_multiclass_selection(config: dict[str, Any]) -> dict[str, Any]:
    path = _configured_path(config, "report_dir") / "multiclass_classes.json"
    if not path.exists():
        raise FileNotFoundError(
            "La sélection multi doit être calculée avant la recherche : "
            f"{path}."
        )
    selection = json.loads(path.read_text(encoding="utf-8"))
    if selection.get("blocks") != list(config["multiclass_blocks"]):
        raise ValueError("La sélection multi ne correspond pas à multiclass_blocks.")
    if not selection.get("multiclass_classes"):
        raise ValueError("La sélection multi ne contient aucune classe.")
    return selection


def _draw_trials(config: dict[str, Any]) -> list[dict[str, float | int]]:
    rng = np.random.default_rng(int(config["search_seed"]))
    space = config["search_space"]

    def uniform(name: str) -> float:
        lower, upper = map(float, space[name])
        return float(rng.uniform(lower, upper))

    def log_uniform(name: str) -> float:
        lower, upper = map(float, space[name])
        return float(np.exp(rng.uniform(np.log(lower), np.log(upper))))

    return [
        {
            "max_depth": int(rng.integers(int(space["max_depth"][0]), int(space["max_depth"][1]) + 1)),
            "min_child_weight": uniform("min_child_weight"),
            "subsample": uniform("subsample"),
            "colsample_bytree": uniform("colsample_bytree"),
            "lambda": log_uniform("lambda"),
            "alpha": log_uniform("alpha"),
        }
        for _ in range(int(config["n_trials"]))
    ]


def _base_matrix(
    train: LoadedSplit,
    mode: Mode,
    classes: list[str] | None,
    n_jobs: int,
) -> tuple[xgb.DMatrix, np.ndarray, np.ndarray | None, LabelEncoder | None]:
    if mode == "bin":
        labels = train.y_bin
        selected = np.ones(len(labels), dtype=bool)
        encoder = None
        weights = None
    else:
        if not classes:
            raise ValueError("Les classes multiclasse doivent être fournies.")
        encoder = _label_encoder(classes)
        codes = pd.Categorical(train.y_multi, categories=encoder.classes_).codes
        selected = codes >= 0
        labels = np.maximum(codes, 0).astype(np.int32, copy=False)
        weights = None
    matrix = xgb.DMatrix(
        train.X,
        label=labels,
        feature_names=train.feature_names,
        nthread=n_jobs,
    )
    return matrix, labels, selected, encoder


def _sample_training_rows(
    indexes: np.ndarray,
    labels: np.ndarray,
    mode: Mode,
    fold: int,
    config: dict[str, Any],
) -> np.ndarray:
    if not config.get("undersampling_benign_train", False):
        return indexes
    benign = indexes[labels[indexes] == 0] if mode == "bin" else np.array(
        [index for index in indexes if labels[index] == 0], dtype=np.int64
    )
    attacks = indexes[labels[indexes] != 0] if mode == "bin" else np.array(
        [index for index in indexes if labels[index] != 0], dtype=np.int64
    )
    maximum_benign = int(
        math.ceil(len(attacks) * float(config.get("benign_to_attack_ratio", 1.0)))
    )
    if len(benign) <= maximum_benign:
        return indexes
    rng = np.random.default_rng(int(config["search_seed"]) + fold)
    sampled = rng.choice(benign, size=maximum_benign, replace=False)
    return np.sort(np.concatenate((attacks, sampled)))


def _fold_indices(
    fold: int,
    fold_ids: np.ndarray,
    purged: np.ndarray,
    selected: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    validation = (fold_ids == fold) & selected
    training = (fold_ids != fold) & ~purged[:, fold] & selected
    return np.flatnonzero(training), np.flatnonzero(validation)


def _fit_parameters(
    mode: Mode,
    trial: dict[str, float | int],
    config: dict[str, Any],
    *,
    scale_pos_weight: float | None = None,
    class_count: int | None = None,
) -> dict[str, Any]:
    fixed = config["fixed"]
    params: dict[str, Any] = {
        "booster": fixed["booster"],
        "tree_method": fixed["tree_method"],
        "eta": float(fixed["eta"]),
        "max_depth": int(trial["max_depth"]),
        "min_child_weight": float(trial["min_child_weight"]),
        "subsample": float(trial["subsample"]),
        "colsample_bytree": float(trial["colsample_bytree"]),
        "lambda": float(trial["lambda"]),
        "alpha": float(trial["alpha"]),
        "seed": int(config["search_seed"]),
        "nthread": int(fixed["n_jobs"]),
        "eval_metric": fixed["eval_metric"][mode],
        "objective": "binary:logistic" if mode == "bin" else "multi:softprob",
    }
    if mode == "bin":
        if scale_pos_weight is None or not np.isfinite(scale_pos_weight):
            raise ValueError("scale_pos_weight doit être fini.")
        params["scale_pos_weight"] = float(scale_pos_weight)
    else:
        if class_count is None or class_count < 2:
            raise ValueError("class_count doit être supérieur ou égal à 2.")
        params["num_class"] = int(class_count)
    return params


def _fit_fold(
    matrix: xgb.DMatrix,
    labels: np.ndarray,
    train_indexes: np.ndarray,
    validation_indexes: np.ndarray,
    mode: Mode,
    trial: dict[str, float | int],
    config: dict[str, Any],
    class_count: int | None,
) -> tuple[float, int, float, int, np.ndarray]:
    training = matrix.slice(train_indexes)
    validation = matrix.slice(validation_indexes)
    if mode == "bin":
        benign_count = int(np.count_nonzero(labels[train_indexes] == 0))
        attack_count = int(np.count_nonzero(labels[train_indexes] == 1))
        if not benign_count or not attack_count:
            raise ValueError("Chaque pli binaire doit avoir les deux classes.")
        params = _fit_parameters(
            mode,
            trial,
            config,
            scale_pos_weight=benign_count / attack_count,
        )
    else:
        assert class_count is not None
        counts = np.bincount(labels[train_indexes], minlength=class_count)
        if np.any(counts == 0):
            raise ValueError("Chaque pli multiclasse doit avoir toutes les classes.")
        per_class_weight = len(train_indexes) / (class_count * counts)
        training.set_weight(per_class_weight[labels[train_indexes]])
        params = _fit_parameters(
            mode,
            trial,
            config,
            class_count=class_count,
        )

    started = time.perf_counter()
    booster = xgb.train(
        params,
        training,
        num_boost_round=int(config["fixed"]["n_estimators"]),
        evals=[(validation, "validation")],
        early_stopping_rounds=int(config["fixed"]["early_stopping_rounds"]),
        verbose_eval=False,
    )
    elapsed = time.perf_counter() - started
    best_iteration = int(booster.best_iteration)
    rounds_trained = int(booster.num_boosted_rounds())
    probabilities = booster.predict(
        validation,
        iteration_range=(0, best_iteration + 1),
    )
    if mode == "bin":
        score = float(average_precision_score(validation.get_label(), probabilities))
    else:
        if class_count is None:
            raise ValueError("class_count est requis en multiclasse.")
        score = float(
            f1_score(
                validation.get_label().astype(np.int32),
                np.asarray(probabilities).reshape(-1, class_count).argmax(axis=1),
                labels=np.arange(class_count),
                average="macro",
                zero_division=0,
            )
        )
    del training, validation, booster
    return score, best_iteration, elapsed, rounds_trained, np.asarray(probabilities)


def benchmark_one_fit(
    mode: Mode = "bin",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Chronomètre un seul fit du premier tirage sur le pli 0."""
    project_config = load_xgboost_config() if config is None else config
    if mode == "multi":
        selection = _read_multiclass_selection(project_config)
        classes = selection["multiclass_classes"]
    else:
        classes = None
    train = load_split("train", project_config)
    fold_ids, purged = _fold_data(train, project_config)
    matrix, labels, selected, encoder = _base_matrix(
        train,
        mode,
        classes,
        int(project_config["fixed"]["n_jobs"]),
    )
    trial = _draw_trials(project_config)[0]
    train_indexes, validation_indexes = _fold_indices(
        0,
        fold_ids,
        purged,
        selected,
    )
    train_indexes = _sample_training_rows(
        train_indexes,
        labels,
        mode,
        0,
        project_config,
    )
    score, best_iteration, elapsed, rounds_trained, _ = _fit_fold(
        matrix,
        labels,
        train_indexes,
        validation_indexes,
        mode,
        trial,
        project_config,
        len(classes) if classes is not None else None,
    )
    median_fold_rows = float(
        np.median(
            [
                np.count_nonzero((fold_ids != fold) & ~purged[:, fold])
                for fold in range(int(project_config["cv_folds"]))
            ]
        )
    )
    estimated_final_fit = (
        elapsed
        * max(best_iteration + 1, 1)
        * len(train.X)
        / (max(rounds_trained, 1) * max(median_fold_rows, 1))
    )
    result = {
        "mode": mode,
        "xgboost_version": xgb.__version__,
        "trial": trial,
        "fold": 0,
        "score": score,
        "best_iteration": best_iteration,
        "rounds_trained": rounds_trained,
        "fit_seconds": elapsed,
        "estimated_final_fit_seconds": estimated_final_fit,
        "estimated_ten_seeds_seconds": 10 * estimated_final_fit,
    }
    report_dir = _configured_path(project_config, "report_dir")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"benchmark_{mode}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    del matrix, train, encoder
    return result


def _append_search_row(path: Path, row: dict[str, Any]) -> None:
    columns = [
        "trial",
        "parameters",
        "fold_scores",
        "mean_score",
        "std_score",
        "best_iterations",
        "fold_fit_seconds",
        "fold_rounds_trained",
        "elapsed_seconds",
    ]
    write_header = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
        stream.flush()


def _top_trials(results: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    ordered = sorted(results, key=lambda item: item["mean_score"], reverse=True)
    return [
        {
            "trial": result["trial"],
            "parameters": result["parameters"],
            "fold_scores": result["fold_scores"],
            "mean_score": result["mean_score"],
            "std_score": result["std_score"],
            "best_iterations": result["best_iterations"],
        }
        for result in ordered[:limit]
    ]


def _threshold_values(
    labels: np.ndarray,
    probabilities: np.ndarray,
    target_fpr: float = 0.01,
) -> dict[str, float]:
    benign = probabilities[labels == 0]
    if not len(benign) or not np.any(labels == 1):
        raise ValueError("Le train hors-pli doit contenir des bénins et des attaques.")
    sorted_benign = np.sort(benign)
    candidates = np.unique(probabilities)
    candidates = np.append(candidates, np.nextafter(candidates[-1], np.inf))
    false_positives = len(sorted_benign) - np.searchsorted(
        sorted_benign,
        candidates,
        side="left",
    )
    feasible = candidates[false_positives / len(sorted_benign) <= target_fpr]
    threshold_fpr = float(feasible[0])
    achieved_fpr = float(np.mean(benign >= threshold_fpr))

    precision, recall, thresholds = precision_recall_curve(labels, probabilities)
    f1_values = 2 * precision[:-1] * recall[:-1] / np.maximum(
        precision[:-1] + recall[:-1],
        np.finfo(float).eps,
    )
    best_index = int(np.argmax(f1_values))
    threshold_f1 = float(thresholds[best_index])
    return {
        "threshold_fpr_1pct": threshold_fpr,
        "achieved_fpr": achieved_fpr,
        "threshold_f1_max": threshold_f1,
        "f1_max": float(f1_values[best_index]),
    }


def _oof_binary_predictions(
    train: LoadedSplit,
    config: dict[str, Any],
    parameters: dict[str, float | int],
) -> tuple[np.ndarray, list[int], list[float]]:
    fold_ids, purged = _fold_data(train, config)
    matrix, labels, selected, _ = _base_matrix(
        train,
        "bin",
        None,
        int(config["fixed"]["n_jobs"]),
    )
    probabilities = np.empty(len(labels), dtype=np.float32)
    best_iterations: list[int] = []
    fit_seconds: list[float] = []
    for fold in range(int(config["cv_folds"])):
        train_indexes, validation_indexes = _fold_indices(
            fold,
            fold_ids,
            purged,
            selected,
        )
        train_indexes = _sample_training_rows(
            train_indexes,
            labels,
            "bin",
            fold,
            config,
        )
        _, best_iteration, elapsed, _, fold_probabilities = _fit_fold(
            matrix,
            labels,
            train_indexes,
            validation_indexes,
            "bin",
            parameters,
            config,
            None,
        )
        probabilities[validation_indexes] = fold_probabilities
        best_iterations.append(best_iteration)
        fit_seconds.append(elapsed)
    del matrix
    return probabilities, best_iterations, fit_seconds


def _binary_metric_values(
    labels: np.ndarray,
    scores: np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    labels = np.asarray(labels, dtype=np.int8)
    scores = np.asarray(scores, dtype=np.float64)
    if len(labels) != len(scores) or not len(labels):
        raise ValueError("Les labels et scores doivent avoir la même taille non nulle.")
    if not np.isfinite(scores).all() or not set(np.unique(labels)).issubset({0, 1}):
        raise ValueError("Labels ou scores binaires invalides.")

    predictions = scores >= threshold
    tn, fp, fn, tp = (
        int(value)
        for value in confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    )
    negatives = tn + fp
    positives = tp + fn
    if positives and negatives:
        curve_fpr, curve_tpr, _ = roc_curve(labels, scores)
        eligible = np.flatnonzero(curve_fpr <= 0.01)
        curve_index = int(eligible[-1])
        tpr_at_fpr_1pct = float(curve_tpr[curve_index])
        fpr_at_fpr_1pct = float(curve_fpr[curve_index])
    else:
        tpr_at_fpr_1pct = float("nan")
        fpr_at_fpr_1pct = float("nan")

    return {
        "pr_auc": (
            float(average_precision_score(labels, scores))
            if positives and negatives
            else float("nan")
        ),
        "roc_auc": (
            float(roc_auc_score(labels, scores))
            if positives and negatives
            else float("nan")
        ),
        "mcc": (
            float(matthews_corrcoef(labels, predictions))
            if positives and negatives
            else float("nan")
        ),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "fpr": float(fp / negatives) if negatives else float("nan"),
        "tpr_at_threshold": float(tp / positives) if positives else float("nan"),
        "fpr_at_threshold": float(fp / negatives) if negatives else float("nan"),
        "tpr_at_fpr_1pct": tpr_at_fpr_1pct,
        "fpr_at_fpr_1pct": fpr_at_fpr_1pct,
        "false_positives": fp,
        "benign_count": negatives,
        "true_positives": tp,
        "attack_count": positives,
    }


def calculate_oof_binary_diagnostics(
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Recalcule les métriques par pli avec la configuration binaire retenue."""
    project_config = load_xgboost_config() if config is None else config
    report_dir = _configured_path(project_config, "report_dir")
    threshold_path = report_dir / "thresholds_bin.json"
    if not threshold_path.exists():
        raise FileNotFoundError(f"Seuil OOF introuvable : {threshold_path}.")
    threshold_data = json.loads(threshold_path.read_text(encoding="utf-8"))
    parameters = threshold_data.get("hyperparameters")
    if not isinstance(parameters, dict):
        raise ValueError("Les hyperparamètres retenus manquent dans thresholds_bin.json.")

    train = load_split("train", project_config)
    fold_ids, _ = _fold_data(train, project_config)
    probabilities, best_iterations, fit_seconds = _oof_binary_predictions(
        train,
        project_config,
        parameters,
    )
    expected_iterations = threshold_data.get("oof_best_iterations")
    if expected_iterations is not None and best_iterations != expected_iterations:
        raise RuntimeError(
            "Les best_iteration recalculées diffèrent de thresholds_bin.json : "
            f"{best_iterations} != {expected_iterations}."
        )

    threshold = float(threshold_data["threshold_fpr_1pct"])
    diagnostics: list[dict[str, Any]] = []
    for fold in range(int(project_config["cv_folds"])):
        validation = fold_ids == fold
        values = _binary_metric_values(
            train.y_bin[validation],
            probabilities[validation],
            threshold,
        )
        diagnostics.append(
            {
                "fold": fold,
                "effectif": int(np.count_nonzero(validation)),
                "attaques": int(np.count_nonzero(train.y_bin[validation])),
                "taux_attaque": float(np.mean(train.y_bin[validation])),
                "best_iteration": int(best_iterations[fold]),
                "fit_seconds": float(fit_seconds[fold]),
                **values,
            }
        )

    threshold_data["fold_diagnostics"] = diagnostics
    threshold_path.write_text(
        json.dumps(threshold_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    csv_path = _configured_path(project_config, "oof_metrics_csv")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(diagnostics).to_csv(csv_path, index=False, encoding="utf-8")
    del probabilities, train
    return diagnostics


def search_hyperparameters(
    mode: Mode = "bin",
    config: dict[str, Any] | None = None,
    *,
    calculate_thresholds: bool = True,
) -> dict[str, Any]:
    """Exécute les tirages identiques sur les plis purgés et journalise chaque essai."""
    project_config = load_xgboost_config() if config is None else config
    if mode == "multi":
        selection = _read_multiclass_selection(project_config)
        classes = selection["multiclass_classes"]
    else:
        selection = None
        classes = None
    train = load_split("train", project_config)
    fold_ids, purged = _fold_data(train, project_config)
    matrix, labels, selected, encoder = _base_matrix(
        train,
        mode,
        classes,
        int(project_config["fixed"]["n_jobs"]),
    )
    report_dir = _configured_path(project_config, "report_dir")
    report_dir.mkdir(parents=True, exist_ok=True)
    search_path = report_dir / f"search_{mode}.csv"
    if search_path.exists():
        search_path.unlink()

    results: list[dict[str, Any]] = []
    trials = _draw_trials(project_config)
    for trial_index, parameters in enumerate(trials, start=1):
        started = time.perf_counter()
        fold_scores: list[float] = []
        best_iterations: list[int] = []
        fold_fit_seconds: list[float] = []
        fold_rounds_trained: list[int] = []
        for fold in _search_folds(project_config):
            train_indexes, validation_indexes = _fold_indices(
                fold,
                fold_ids,
                purged,
                selected,
            )
            train_indexes = _sample_training_rows(
                train_indexes,
                labels,
                mode,
                fold,
                project_config,
            )
            score, best_iteration, elapsed, rounds_trained, _ = _fit_fold(
                matrix,
                labels,
                train_indexes,
                validation_indexes,
                mode,
                parameters,
                project_config,
                len(classes) if classes is not None else None,
            )
            fold_scores.append(score)
            best_iterations.append(best_iteration)
            fold_fit_seconds.append(elapsed)
            fold_rounds_trained.append(rounds_trained)
        row = {
            "trial": trial_index,
            "parameters": json.dumps(parameters, ensure_ascii=False, sort_keys=True),
            "fold_scores": json.dumps(fold_scores),
            "mean_score": float(np.mean(fold_scores)),
            "std_score": float(np.std(fold_scores, ddof=1)) if len(fold_scores) > 1 else 0.0,
            "best_iterations": json.dumps(best_iterations),
            "fold_fit_seconds": json.dumps(fold_fit_seconds),
            "fold_rounds_trained": json.dumps(fold_rounds_trained),
            "elapsed_seconds": time.perf_counter() - started,
        }
        _append_search_row(search_path, row)
        results.append(
            {
                "trial": trial_index,
                "parameters": parameters,
                "fold_scores": fold_scores,
                "mean_score": row["mean_score"],
                "std_score": row["std_score"],
                "best_iterations": best_iterations,
                "fold_fit_seconds": fold_fit_seconds,
                "fold_rounds_trained": fold_rounds_trained,
                "elapsed_seconds": row["elapsed_seconds"],
            }
        )

    best = max(results, key=lambda result: result["mean_score"])
    best_rounds = max(1, int(np.median(np.asarray(best["best_iterations"]) + 1)))
    result: dict[str, Any] = {
        "mode": mode,
        "metric": "PR-AUC (average precision)" if mode == "bin" else "Macro-F1",
        "classes": classes,
        "class_selection": selection,
        "best_parameters": best["parameters"],
        "best_rounds": best_rounds,
        "best_iterations": best["best_iterations"],
        "top_10_trials": _top_trials(results, 10),
        "top_5_trials": _top_trials(results, 5),
        "trial_count": len(results),
        "fold_count": len(_search_folds(project_config)),
    }
    benchmark_path = report_dir / f"benchmark_{mode}.json"
    if benchmark_path.exists():
        result["benchmark"] = json.loads(
            benchmark_path.read_text(encoding="utf-8")
        )
        search_folds = _search_folds(project_config)
        median_fold_rows = float(
            np.median(
                [
                    np.count_nonzero((fold_ids != fold) & ~purged[:, fold])
                    for fold in search_folds
                ]
            )
        )
        benchmark = result["benchmark"]
        result["estimated_final_fit_seconds"] = (
            float(benchmark["fit_seconds"])
            * best_rounds
            * len(train.X)
            / (
                max(int(benchmark["rounds_trained"]), 1)
                * max(median_fold_rows, 1)
            )
        )
        result["estimated_ten_seeds_seconds"] = (
            10 * result["estimated_final_fit_seconds"]
        )
    (report_dir / f"best_{mode}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if mode == "bin" and calculate_thresholds:
        oof, oof_iterations, oof_times = _oof_binary_predictions(
            train,
            project_config,
            best["parameters"],
        )
        threshold_data = _threshold_values(train.y_bin, oof)
        threshold_data.update(
            {
                "hyperparameters": best["parameters"],
                "best_rounds": best_rounds,
                "oof_best_iterations": oof_iterations,
                "oof_fit_seconds": oof_times,
                "top_5_trials": _top_trials(results, 5),
            }
        )
        (report_dir / "thresholds_bin.json").write_text(
            json.dumps(threshold_data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        result["thresholds"] = threshold_data
        result["oof_fit_seconds"] = oof_times
    del matrix, train, encoder
    return result


def prediction_frame(
    flow_ids: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scores: np.ndarray,
    seed: int,
) -> pd.DataFrame:
    """Construit et vérifie le format de prédictions commun."""
    predictions = pd.DataFrame(
        {
            "flow_id": flow_ids,
            "y_true": y_true,
            "y_pred": y_pred,
            "score": np.asarray(scores, dtype=np.float32),
            "recon_error": np.full(len(flow_ids), np.nan, dtype=np.float32),
            "seed": np.full(len(flow_ids), seed, dtype=np.int32),
        },
        columns=PREDICTION_COLUMNS,
    )
    if list(predictions.columns) != PREDICTION_COLUMNS:
        raise ValueError("Le schéma des prédictions diffère du format commun.")
    return predictions


def run_final_training(
    mode: Mode,
    search_result: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> list[Path]:
    """Entraîne les graines sur tout le train puis écrit les prédictions test."""
    project_config = load_xgboost_config() if config is None else config
    classes = search_result.get("classes") if mode == "multi" else None
    if mode == "multi" and not classes:
        raise ValueError("La recherche doit fournir les classes multiclasse retenues.")
    model_dir = _configured_path(project_config, "model_dir")
    prediction_dir = _configured_path(project_config, "prediction_dir")
    model_dir.mkdir(parents=True, exist_ok=True)
    prediction_dir.mkdir(parents=True, exist_ok=True)

    train = load_split("train", project_config)
    matrix, labels, selected, encoder = _base_matrix(
        train,
        mode,
        classes,
        int(project_config["fixed"]["n_jobs"]),
    )
    train_indexes = np.flatnonzero(selected)
    training = matrix.slice(train_indexes)
    if mode == "multi":
        class_count = len(classes)
        class_weights = len(train_indexes) / (
            class_count * np.bincount(labels[train_indexes], minlength=class_count)
        )
        training.set_weight(class_weights[labels[train_indexes]])
    else:
        class_count = None

    params = _fit_parameters(
        mode,
        search_result["best_parameters"],
        project_config,
        scale_pos_weight=(
            float(np.count_nonzero(labels[train_indexes] == 0))
            / float(np.count_nonzero(labels[train_indexes] == 1))
            if mode == "bin"
            else None
        ),
        class_count=class_count,
    )
    rounds = int(search_result["best_rounds"])
    model_paths: list[Path] = []
    training_log: list[dict[str, Any]] = []
    for seed in project_config["seeds"]:
        seed_params = {**params, "seed": int(seed)}
        started = time.perf_counter()
        booster = xgb.train(seed_params, training, num_boost_round=rounds)
        elapsed = time.perf_counter() - started
        model_path = model_dir / f"xgb_{mode}_seed{seed}.json"
        booster.save_model(model_path)
        model_paths.append(model_path)
        training_log.append(
            {"seed": int(seed), "n_estimators": rounds, "training_seconds": elapsed}
        )
        del booster
    if encoder is not None:
        joblib.dump(encoder, model_dir / "label_encoder_multi.joblib")

    train_ids = train.flow_ids
    del training, matrix, train
    test = load_split("test", project_config)
    if np.intersect1d(train_ids, test.flow_ids).size:
        raise ValueError("Un flow_id du test apparaît dans le train.")
    del train_ids

    if mode == "bin":
        threshold_path = _configured_path(project_config, "report_dir") / "thresholds_bin.json"
        if not threshold_path.exists():
            raise FileNotFoundError(f"Seuils OOF introuvables : {threshold_path}.")
        thresholds = json.loads(threshold_path.read_text(encoding="utf-8"))
        threshold = float(thresholds["threshold_fpr_1pct"])
        test_indexes = np.arange(len(test.flow_ids))
    else:
        thresholds = {}
        threshold = None
        test_indexes = np.flatnonzero(np.isin(test.y_multi, classes))
    test_features = (
        test.X if mode == "bin" else test.X[test_indexes]
    )
    test_matrix = xgb.DMatrix(
        test_features,
        feature_names=test.feature_names,
        nthread=int(project_config["fixed"]["n_jobs"]),
    )
    del test_features
    outputs: list[Path] = []
    feature_importance_rows: list[dict[str, Any]] = []
    for seed_index, (seed, model_path) in enumerate(
        zip(project_config["seeds"], model_paths)
    ):
        booster = xgb.Booster()
        booster.load_model(model_path)
        inference_started = time.perf_counter()
        predictions = booster.predict(test_matrix)
        inference_seconds = time.perf_counter() - inference_started
        training_log[seed_index]["inference_seconds"] = inference_seconds
        gain_by_feature = booster.get_score(importance_type="gain")
        feature_importance_rows.extend(
            {
                "seed": int(seed),
                "feature": feature,
                "gain": float(gain_by_feature.get(feature, 0.0)),
            }
            for feature in test.feature_names
        )
        if mode == "bin":
            scores = np.asarray(predictions, dtype=np.float32)
            y_pred = (scores >= threshold).astype(np.int8)
            y_true = test.y_bin[test_indexes]
        else:
            class_probabilities = np.asarray(predictions).reshape(
                -1,
                len(classes),
            )
            class_indexes = class_probabilities.argmax(axis=1)
            scores = class_probabilities[
                np.arange(len(class_indexes)),
                class_indexes,
            ]
            y_pred = np.asarray(classes, dtype=object)[class_indexes]
            y_true = test.y_multi[test_indexes]
        frame = prediction_frame(
            test.flow_ids[test_indexes],
            y_true,
            y_pred,
            scores,
            int(seed),
        )
        output_path = prediction_dir / f"xgb_{mode}_seed{seed}.parquet"
        frame.to_parquet(output_path, index=False)
        outputs.append(output_path)
        del booster, frame
    report_dir = _configured_path(project_config, "report_dir")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / f"training_{mode}.json").write_text(
        json.dumps(training_log, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    importance_path = _configured_path(project_config, "importance_csv")
    importance_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(feature_importance_rows).to_csv(
        importance_path,
        index=False,
        encoding="utf-8",
    )
    del test_matrix, test
    return outputs


def _format_mean_std(values: pd.Series, digits: int = 4) -> str:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return "n.d."
    deviation = float(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0
    return f"{numeric.mean():.{digits}f} ± {deviation:.{digits}f}"


def _format_mean_std_median(values: pd.Series, digits: int = 4) -> str:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return "n.d."
    deviation = float(numeric.std(ddof=1)) if len(numeric) > 1 else 0.0
    return (
        f"{numeric.mean():.{digits}f} ± {deviation:.{digits}f} / "
        f"{numeric.median():.{digits}f}"
    )


def write_binary_evaluation_report(
    config: dict[str, Any] | None = None,
) -> dict[str, str]:
    """Évalue les prédictions binaires et rédige le rapport et ses CSV."""
    project_config = load_xgboost_config() if config is None else config
    processed = _configured_path(project_config, "processed")
    prediction_dir = _configured_path(project_config, "prediction_dir")
    report_dir = _configured_path(project_config, "report_dir")
    thresholds_path = report_dir / "thresholds_bin.json"
    thresholds = json.loads(thresholds_path.read_text(encoding="utf-8"))
    threshold = float(thresholds["threshold_fpr_1pct"])
    seeds = [int(seed) for seed in project_config["seeds"]]
    if 42 not in seeds:
        raise ValueError("La graine 42 est requise pour la matrice de confusion.")

    test_path = processed / "test.parquet"
    test_schema = set(pq.ParquetFile(test_path).schema_arrow.names)
    diagnostic_columns = [
        "day",
        "ts_end",
        "Protocol",
        "src_ip",
        "dst_ip",
        "src_port",
        "dst_port",
    ]
    test = pd.read_parquet(
        test_path,
        columns=[
            "flow_id",
            "label_bin",
            "label_multi",
            *[column for column in diagnostic_columns if column in test_schema],
        ],
    )
    for column in diagnostic_columns:
        if column not in test.columns:
            test[column] = np.nan
    metadata = pd.read_parquet(
        processed / "meta.parquet",
        columns=["flow_id", "seen_in_train"],
    )
    if metadata["flow_id"].duplicated().any():
        raise ValueError("meta.parquet contient des flow_id dupliqués.")
    context = test.merge(metadata, on="flow_id", how="left", validate="one_to_one")
    if context["seen_in_train"].isna().any():
        raise ValueError("seen_in_train manque pour au moins un flux test.")
    context["seen_in_train"] = context["seen_in_train"].astype(bool)

    audit = pd.read_parquet(
        processed / "label_audit.parquet",
        columns=["flow_id", "label_rule", "attempted_category"],
    )
    if audit["flow_id"].duplicated().any():
        raise ValueError("label_audit.parquet contient des flow_id dupliqués.")
    context = context.merge(
        audit,
        on="flow_id",
        how="left",
        validate="one_to_one",
    )
    if context["label_rule"].isna().any():
        raise ValueError("label_audit.parquet ne couvre pas tout le test.")
    canonical = context["label_rule"].map(_label_rule_mapping(project_config))
    if canonical.isna().any():
        unknown = sorted(
            context.loc[canonical.isna(), "label_rule"].astype(str).unique()
        )
        raise ValueError("Règles inconnues dans l'audit : " + ", ".join(unknown))
    context["canonical_rule"] = canonical
    context["attempted"] = context["attempted_category"].ge(0)
    context["signale"] = (
        context["canonical_rule"].ne(context["label_multi"])
        | context["attempted"]
    )
    context["seen_strict"] = ~context["seen_in_train"]

    evaluation_masks = {
        "test complet": np.ones(len(context), dtype=bool),
        "test strict": context["seen_strict"].to_numpy(dtype=bool),
        "test sans signalés": ~context["signale"].to_numpy(dtype=bool),
        "test complet sans Bot": context["label_multi"].ne("Bot").to_numpy(dtype=bool),
    }
    metric_rows: list[dict[str, Any]] = []
    class_rows: list[dict[str, Any]] = []
    bot_rows: list[dict[str, Any]] = []
    non_bot_attack_rows: list[dict[str, Any]] = []
    audit_metric_rows: list[dict[str, Any]] = []
    false_positive_rows: dict[int, pd.DataFrame] = {}
    hulk_true_positives_42 = pd.DataFrame()
    confusion_42: np.ndarray | None = None
    for seed in seeds:
        prediction_path = prediction_dir / f"xgb_bin_seed{seed}.parquet"
        if not prediction_path.exists():
            raise FileNotFoundError(f"Prédictions de la graine {seed} absentes : {prediction_path}.")
        prediction = pd.read_parquet(
            prediction_path,
            columns=["flow_id", "y_true", "y_pred", "score", "seed"],
        )
        if prediction["flow_id"].duplicated().any():
            raise ValueError(f"Prédictions dupliquées pour la graine {seed}.")
        if not prediction["seed"].eq(seed).all():
            raise ValueError(f"Colonne seed incohérente dans {prediction_path}.")
        frame = prediction.merge(
            context,
            on="flow_id",
            how="left",
            validate="one_to_one",
        )
        if len(frame) != len(context) or frame["label_bin"].isna().any():
            raise ValueError(f"Les prédictions de la graine {seed} ne couvrent pas le test.")
        if not np.array_equal(
            frame["y_true"].to_numpy(dtype=np.int8),
            frame["label_bin"].to_numpy(dtype=np.int8),
        ):
            raise ValueError(f"y_true ne correspond pas au test pour la graine {seed}.")
        labels = frame["y_true"].to_numpy(dtype=np.int8)
        scores = frame["score"].to_numpy(dtype=np.float64)
        predicted = frame["y_pred"].to_numpy(dtype=np.int8)
        if not np.array_equal(predicted, (scores >= threshold).astype(np.int8)):
            raise ValueError(f"Le seuil OOF n'a pas été appliqué pour la graine {seed}.")
        false_positive_mask = (predicted == 1) & (labels == 0)
        false_positive_rows[seed] = frame.loc[
            false_positive_mask,
            [
                "flow_id",
                "signale",
                "score",
                "label_multi",
                "day",
                "ts_end",
                "Protocol",
                "src_ip",
                "dst_ip",
                "src_port",
                "dst_port",
            ],
        ].copy()

        audit_attack_rule = frame["canonical_rule"].ne("BENIGN").to_numpy()
        attempted = frame["attempted"].to_numpy(dtype=bool)
        audit_variants = {
            "Attempted compté comme attaque": (
                audit_attack_rule | attempted,
                np.ones(len(frame), dtype=bool),
            ),
            "Attempted exclu": (
                audit_attack_rule,
                ~attempted,
            ),
        }
        for variant, (audit_labels, keep) in audit_variants.items():
            values = _binary_metric_values(
                audit_labels[keep].astype(np.int8),
                scores[keep],
                threshold,
            )
            audit_metric_rows.append(
                {
                    "seed": seed,
                    "variant": variant,
                    "effectif": int(np.count_nonzero(keep)),
                    "pr_auc": values["pr_auc"],
                    "tpr_at_fpr_1pct": values["tpr_at_fpr_1pct"],
                    "fpr_at_fpr_1pct": values["fpr_at_fpr_1pct"],
                    "false_positives": values["false_positives"],
                    "false_negatives": values["attack_count"] - values["true_positives"],
                    "fpr_at_threshold": values["fpr"],
                    "tpr_at_threshold": values["tpr_at_threshold"],
                }
            )

        for evaluation, mask in evaluation_masks.items():
            values = _binary_metric_values(labels[mask], scores[mask], threshold)
            metric_rows.append(
                {
                    "seed": seed,
                    "evaluation": evaluation,
                    "effectif": int(np.count_nonzero(mask)),
                    **values,
                    "fp_par_benin": (
                        float(values["false_positives"] / values["benign_count"])
                        if values["benign_count"]
                        else float("nan")
                    ),
                }
            )
        non_bot_attacks = (labels == 1) & (frame["label_multi"].astype(str).to_numpy() != "Bot")
        non_bot_attack_rows.append(
            {
                "seed": seed,
                "effectif": int(np.count_nonzero(non_bot_attacks)),
                "true_positives": int(
                    np.count_nonzero(predicted[non_bot_attacks] == 1)
                ),
                "recall": (
                    float(np.mean(predicted[non_bot_attacks] == 1))
                    if np.any(non_bot_attacks)
                    else float("nan")
                ),
            }
        )

        labels_multi = frame["label_multi"].astype(str).to_numpy()
        bot_mask = labels_multi == "Bot"
        attempted_mask = frame["attempted_category"].to_numpy(dtype=np.int16) >= 0
        for subgroup, subgroup_mask in (
            ("Attempted", bot_mask & attempted_mask),
            ("non-Attempted", bot_mask & ~attempted_mask),
        ):
            count = int(np.count_nonzero(subgroup_mask))
            bot_rows.append(
                {
                    "seed": seed,
                    "groupe": subgroup,
                    "effectif": count,
                    "score_median": (
                        float(np.median(scores[subgroup_mask]))
                        if count
                        else float("nan")
                    ),
                    "recall": (
                        float(np.mean(predicted[subgroup_mask] == 1))
                        if count
                        else float("nan")
                    ),
                }
            )
        for evaluation, mask in evaluation_masks.items():
            for attack_class in sorted(set(labels_multi[mask]) - {"BENIGN"}):
                class_mask = mask & (labels_multi == attack_class)
                count = int(np.count_nonzero(class_mask))
                class_rows.append(
                    {
                        "seed": seed,
                        "evaluation": evaluation,
                        "classe": attack_class,
                        "effectif": count,
                        "recall": (
                            float(np.mean(predicted[class_mask] == 1))
                            if count
                            else float("nan")
                        ),
                    }
                )
        if seed == 42:
            confusion_42 = confusion_matrix(labels, predicted, labels=[0, 1])
            hulk_true_positives_42 = frame.loc[
                frame["label_multi"].eq("DoS Hulk")
                & frame["label_bin"].eq(1)
                & frame["y_pred"].eq(1),
                [
                    "flow_id",
                    "day",
                    "ts_end",
                    "src_ip",
                    "dst_ip",
                    "src_port",
                    "dst_port",
                ],
            ].copy()

    metric_table = pd.DataFrame(metric_rows)
    summary_csv = _configured_path(project_config, "summary_csv")
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    metric_table.to_csv(summary_csv, index=False, encoding="utf-8")
    audit_metric_table = pd.DataFrame(audit_metric_rows)
    audit_metrics_csv = _configured_path(project_config, "audit_metrics_csv")
    audit_metrics_csv.parent.mkdir(parents=True, exist_ok=True)
    audit_metric_table.to_csv(audit_metrics_csv, index=False, encoding="utf-8")

    false_positive_summary = []
    false_positive_sets: dict[int, set[str]] = {}
    for seed, false_positive_frame in false_positive_rows.items():
        ids = set(false_positive_frame["flow_id"].astype(str))
        false_positive_sets[seed] = ids
        flagged_count = int(false_positive_frame["signale"].sum())
        false_positive_summary.append(
            {
                "seed": seed,
                "false_positives": len(false_positive_frame),
                "audit_signales": flagged_count,
                "non_signales": len(false_positive_frame) - flagged_count,
            }
        )
    common_false_positives = set.intersection(*false_positive_sets.values())
    outlier_seeds = {43, 45, 50}
    comparison_seeds = set(seeds) - outlier_seeds
    if outlier_seeds.issubset(false_positive_sets) and comparison_seeds.issubset(
        false_positive_sets
    ):
        unstable_false_positives = (
            set.union(*(false_positive_sets[seed] for seed in outlier_seeds))
            - set.union(
                *(false_positive_sets[seed] for seed in comparison_seeds)
            )
        )
    else:
        unstable_false_positives = set()
    unstable_frame = context.loc[
        context["flow_id"].astype(str).isin(unstable_false_positives)
    ].copy()
    unstable_wednesday = unstable_frame.loc[
        unstable_frame["day"].astype(str).eq("Wednesday")
    ].copy()
    unstable_time = pd.to_datetime(
        unstable_wednesday["ts_end"],
        unit="s",
        utc=True,
        errors="coerce",
    )
    unstable_hours = unstable_time.dt.strftime("%Y-%m-%d %H").value_counts().sort_index()
    unstable_score_rows = []
    score_seed_ids = (
        sorted(outlier_seeds.intersection(seeds))
        if unstable_false_positives
        else []
    )
    for seed in score_seed_ids:
        prediction = pd.read_parquet(
            prediction_dir / f"xgb_bin_seed{seed}.parquet",
            columns=["flow_id", "score"],
        )
        selected_scores = prediction.loc[
            prediction["flow_id"].astype(str).isin(unstable_false_positives),
            "score",
        ].to_numpy(dtype=np.float64)
        unstable_score_rows.append(
            {
                "seed": seed,
                "min": float(np.min(selected_scores)),
                "median": float(np.median(selected_scores)),
                "max": float(np.max(selected_scores)),
                "share_040_055": float(
                    np.mean((selected_scores >= 0.40) & (selected_scores <= 0.55))
                ),
            }
        )

    features_path = _configured_path(project_config, "feature_list")
    feature_names = json.loads(features_path.read_text(encoding="utf-8"))
    if unstable_false_positives:
        unstable_features = pd.read_parquet(
            test_path,
            columns=["flow_id", *feature_names],
            filters=[
                ("flow_id", "in", list(unstable_false_positives)),
            ],
        )
        if set(unstable_features["flow_id"].astype(str)) != unstable_false_positives:
            raise ValueError("Lecture filtrée des vecteurs FP instables incomplète.")
        unstable_feature_values = unstable_features[feature_names].to_numpy(
            dtype=np.float32,
            copy=False,
        )
        unique_unstable_vectors = int(
            np.unique(unstable_feature_values, axis=0).shape[0]
        )
    else:
        unstable_features = pd.DataFrame(columns=["flow_id", *feature_names])
        unique_unstable_vectors = 0

    hulk_wednesday = hulk_true_positives_42.loc[
        hulk_true_positives_42["day"].astype(str).eq("Wednesday")
    ]
    unstable_hour_text = (
        ", ".join(f"{hour} ({count:,})" for hour, count in unstable_hours.items())
        if not unstable_hours.empty
        else "n.d."
    )
    unstable_time_text = (
        f"{unstable_time.min().strftime('%Y-%m-%d %H:%M:%S')} à "
        f"{unstable_time.max().strftime('%Y-%m-%d %H:%M:%S')}"
        if unstable_time.notna().any()
        else "n.d."
    )
    unstable_protocol_counts = (
        unstable_wednesday["Protocol"].value_counts(dropna=False).head(3)
    )
    unstable_destination_ports = unstable_wednesday["dst_port"].value_counts(
        dropna=False
    ).head(5)
    unstable_fp_pair = int(
        (
            unstable_wednesday["src_ip"].eq("192.168.10.50")
            & unstable_wednesday["dst_ip"].eq("172.16.0.1")
        ).sum()
    )
    hulk_tp_pair = int(
        (
            hulk_wednesday["src_ip"].eq("172.16.0.1")
            & hulk_wednesday["dst_ip"].eq("192.168.10.50")
        ).sum()
    )

    class_table = pd.DataFrame(class_rows)
    class_summary = (
        class_table.groupby(["evaluation", "classe"], sort=True)
        .agg(
            effectif=("effectif", "first"),
            recall_moyen=("recall", "mean"),
            recall_ecart_type=("recall", "std"),
        )
        .reset_index()
    )
    non_bot_attack = context["label_multi"].ne("BENIGN") & context["label_multi"].ne("Bot")
    class_counts = context.loc[non_bot_attack].groupby(
        "label_multi",
        sort=True,
    ).size()
    strict_counts = context.loc[context["seen_strict"] & non_bot_attack].groupby(
        "label_multi",
        sort=True,
    ).size()
    unflagged_counts = context.loc[~context["signale"] & non_bot_attack].groupby(
        "label_multi",
        sort=True,
    ).size()

    importance_path = _configured_path(project_config, "importance_csv")
    importance = pd.read_csv(importance_path)
    if set(importance["seed"].astype(int)) != set(seeds):
        raise ValueError("L'importance des features ne couvre pas toutes les graines.")
    gain_totals = importance.groupby("seed")["gain"].transform("sum")
    importance["gain_share"] = np.divide(
        importance["gain"],
        gain_totals,
        out=np.zeros(len(importance), dtype=np.float64),
        where=gain_totals.to_numpy() > 0,
    )
    importance_summary = (
        importance.groupby("feature", sort=True)
        .agg(
            gain_moyen=("gain", "mean"),
            part_gain_moyenne=("gain_share", "mean"),
        )
        .sort_values("part_gain_moyenne", ascending=False)
    )
    importance_summary["rang"] = np.arange(1, len(importance_summary) + 1)

    training_log_path = report_dir / "training_bin.json"
    training_log = pd.DataFrame(
        json.loads(training_log_path.read_text(encoding="utf-8"))
    ).set_index("seed")
    if set(training_log.index.astype(int)) != set(seeds):
        raise ValueError("Le journal de temps ne couvre pas toutes les graines.")

    threshold_summaries = []
    for evaluation, group in metric_table.groupby("evaluation", sort=False):
        threshold_summaries.append(
            {
                "evaluation": evaluation,
                "effectif": int(group["effectif"].iloc[0]),
                "pr_auc": _format_mean_std_median(group["pr_auc"]),
                "roc_auc": _format_mean_std_median(group["roc_auc"]),
                "mcc": _format_mean_std_median(group["mcc"]),
                "f1": _format_mean_std_median(group["f1"]),
                "precision": _format_mean_std_median(group["precision"]),
                "recall": _format_mean_std_median(group["recall"]),
                "fpr": _format_mean_std_median(group["fpr"]),
                "tpr_at_threshold": _format_mean_std_median(
                    group["tpr_at_threshold"]
                ),
                "tpr_at_fpr_1pct": _format_mean_std_median(
                    group["tpr_at_fpr_1pct"]
                ),
                "fp_par_benin": _format_mean_std_median(
                    group["fp_par_benin"], 6
                ),
                "faux_positifs": _format_mean_std_median(
                    group["false_positives"], 1
                ),
                "benins": int(group["benign_count"].iloc[0]),
            }
        )
    threshold_summaries = pd.DataFrame(threshold_summaries)
    audit_metric_summaries = []
    for variant, group in audit_metric_table.groupby("variant", sort=False):
        audit_metric_summaries.append(
            {
                "variant": variant,
                "effectif": int(group["effectif"].iloc[0]),
                "pr_auc_mean": float(group["pr_auc"].mean()),
                "pr_auc_median": float(group["pr_auc"].median()),
                "tpr_at_fpr_1pct_mean": float(group["tpr_at_fpr_1pct"].mean()),
                "tpr_at_fpr_1pct_median": float(
                    group["tpr_at_fpr_1pct"].median()
                ),
                "fp_mean": float(group["false_positives"].mean()),
                "fp_median": float(group["false_positives"].median()),
                "fn_mean": float(group["false_negatives"].mean()),
                "fn_median": float(group["false_negatives"].median()),
            }
        )
    audit_metric_summary = pd.DataFrame(audit_metric_summaries)

    audit_directions = {
        "benign_regle_attaque": int(
            (context["label_multi"].eq("BENIGN") & canonical.ne("BENIGN")).sum()
        ),
        "attaque_regle_benign": int(
            (context["label_multi"].ne("BENIGN") & canonical.eq("BENIGN")).sum()
        ),
        "attaque_autre_regle_attaque": int(
            (
                context["label_multi"].ne("BENIGN")
                & canonical.ne("BENIGN")
                & canonical.ne(context["label_multi"])
            ).sum()
        ),
        "attempted": int((context["attempted_category"] >= 0).sum()),
    }
    attempted_by_block: list[dict[str, Any]] = []
    bot_block_summary: dict[str, dict[str, Any]] = {}
    audit_labels = audit[["flow_id", "attempted_category"]]
    for split in ("train", "val", "test"):
        split_frame = (
            pd.read_parquet(
                processed / f"{split}.parquet",
                columns=["flow_id", "label_multi"],
            )
            .merge(audit_labels, on="flow_id", validate="one_to_one")
        )
        split_frame["attempted"] = split_frame["attempted_category"].ge(0)
        grouped = split_frame.loc[split_frame["label_multi"].ne("BENIGN")].groupby(
            "label_multi",
            sort=True,
        )["attempted"].agg(["size", "sum", "mean"])
        for label, values in grouped.iterrows():
            attempted_by_block.append(
                {
                    "bloc": split,
                    "classe": str(label),
                    "effectif": int(values["size"]),
                    "attempted": int(values["sum"]),
                    "part_attempted": float(values["mean"]),
                }
            )
        bot_values = split_frame.loc[split_frame["label_multi"].eq("Bot"), "attempted"]
        bot_block_summary[split] = {
            "effectif": int(len(bot_values)),
            "attempted": int(bot_values.sum()),
            "part_attempted": float(bot_values.mean()) if len(bot_values) else float("nan"),
        }
    fold_diagnostics = thresholds.get("fold_diagnostics", [])
    fold_table = pd.DataFrame(fold_diagnostics)
    if len(fold_table) != int(project_config["cv_folds"]):
        raise ValueError("Métriques OOF par pli manquantes; recalculer les diagnostics.")

    gap = float(
        thresholds["top_5_trials"][0]["mean_score"]
        - thresholds["top_5_trials"][4]["mean_score"]
    )
    top_trials = thresholds["top_5_trials"]
    prevalence_cv = float(
        fold_table["attaques"].sum() / fold_table["effectif"].sum()
    )
    prevalence_test = float(context["label_bin"].mean())
    full_metrics = metric_table.loc[metric_table["evaluation"].eq("test complet")]
    bot_total = int(context["label_multi"].eq("Bot").sum())
    bot_attempted = int(
        (context["label_multi"].eq("Bot") & context["attempted_category"].ge(0)).sum()
    )
    false_positive_range = (
        int(full_metrics["false_positives"].min()),
        int(full_metrics["false_positives"].max()),
    )
    minimum_length_share = sum(
        float(importance_summary.loc[feature, "part_gain_moyenne"])
        for feature in ("Bwd Packet Length Min", "Fwd Packet Length Min")
        if feature in importance_summary.index
    )
    low_support_classes = [
        f"{label} ({int(count)})"
        for label, count in strict_counts.items()
        if int(count) < 100
    ]
    confusion_text = (
        "| Réel \\ Prédit | Bénin | Attaque |\n|---|---:|---:|\n"
        f"| Bénin | {int(confusion_42[0, 0])} | {int(confusion_42[0, 1])} |\n"
        f"| Attaque | {int(confusion_42[1, 0])} | {int(confusion_42[1, 1])} |"
        if confusion_42 is not None
        else "Matrice indisponible."
    )

    lines = [
        "# Évaluation XGBoost binaire — CIC-IDS2017",
        "",
        f"- Seuil OOF FPR 1 % : `{threshold:.6f}` ; FPR OOF observée : "
        f"{float(thresholds['achieved_fpr']):.4%}.",
        f"- Hyperparamètres : essai 24, {int(thresholds['best_rounds'])} rounds, "
        f"10 graines ({', '.join(map(str, seeds))}).",
        "- Les métriques sont calculées sur les scores de chaque graine; "
        "les agrégats donnent moyenne ± écart-type (échantillon) / médiane.",
        "",
        "## Métriques globales",
        "",
        "Chaque cellule numérique indique moyenne ± écart-type / médiane.",
        "",
        "| Évaluation | Flux | PR-AUC | ROC-AUC | MCC | F1 | Précision | Recall | FPR au seuil OOF | TPR au seuil OOF | TPR à FPR ≤ 1 % | FP / bénins |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in threshold_summaries.itertuples(index=False):
        lines.append(
            f"| {row.evaluation} | {row.effectif:,} | {row.pr_auc} | "
            f"{row.roc_auc} | {row.mcc} | "
            f"{row.f1} | {row.precision} | {row.recall} | {row.fpr} | "
            f"{row.tpr_at_threshold} | {row.tpr_at_fpr_1pct} | "
            f"{row.faux_positifs} / {int(row.benins):,} "
            f"({row.fp_par_benin}) |"
        )
    lines.extend(
        [
            "",
            "La colonne TPR à FPR ≤ 1 % utilise le point ROC atteignable de TPR maximal "
            "dont le FPR ne dépasse pas 1 %.",
            "",
            "## Test complet par graine",
            "",
            "| Graine/statistique | TP | FP | FN | FPR | Recall | PR-AUC | F1 | TPR à FPR ≤ 1 % |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    full_metrics = metric_table.loc[metric_table["evaluation"].eq("test complet")]
    for row in full_metrics.sort_values("seed").itertuples(index=False):
        lines.append(
            f"| {row.seed} | {row.true_positives:,} | {row.false_positives:,} | "
            f"{row.attack_count - row.true_positives:,} | {row.fpr:.6f} | "
            f"{row.recall:.6f} | {row.pr_auc:.6f} | {row.f1:.6f} | "
            f"{row.tpr_at_fpr_1pct:.6f} |"
        )
    for statistic, aggregate in (
        ("Moyenne", full_metrics.mean(numeric_only=True)),
        ("Médiane", full_metrics.median(numeric_only=True)),
    ):
        lines.append(
            f"| {statistic} | {aggregate['true_positives']:.1f} | "
            f"{aggregate['false_positives']:.1f} | "
            f"{aggregate['attack_count'] - aggregate['true_positives']:.1f} | "
            f"{aggregate['fpr']:.6f} | {aggregate['recall']:.6f} | "
            f"{aggregate['pr_auc']:.6f} | {aggregate['f1']:.6f} | "
            f"{aggregate['tpr_at_fpr_1pct']:.6f} |"
        )
    lines.extend(
        [
            "",
            "### Faux positifs et chevauchement entre graines",
            "",
            "Un FP est défini strictement par `y_pred == 1` et `label_bin == 0`. "
            f"FP communs aux dix graines : {len(common_false_positives):,}.",
            "",
            "| Graine | FP total | FP signalés par l'audit | FP non signalés |",
            "|---:|---:|---:|---:|",
        ]
    )
    for row in false_positive_summary:
        lines.append(
            f"| {row['seed']} | {row['false_positives']:,} | "
            f"{row['audit_signales']:,} | {row['non_signales']:,} |"
        )
    lines.extend(
        [
            "",
            "#### FP propres aux graines 43, 45 et 50",
            "",
            f"L'union des FP de 43/45/50, après retrait de tout FP des sept autres graines, "
            f"contient {len(unstable_false_positives):,} flux. "
            f"label_multi : BENIGN {len(unstable_frame):,}; "
            f"label_bin=0 : {int(unstable_frame['label_bin'].eq(0).sum()):,}.",
            "",
            "| Graine | Score min | Médiane | Max | Part dans [0,40; 0,55] |",
            "|---:|---:|---:|---:|---:|",
        ]
    )
    for row in unstable_score_rows:
        lines.append(
            f"| {row['seed']} | {row['min']:.6f} | {row['median']:.6f} | "
            f"{row['max']:.6f} | {row['share_040_055']:.2%} |"
        )
    lines.extend(
        [
            "",
            f"{len(unstable_wednesday):,}/{len(unstable_frame):,} sont du mercredi; "
            f"parmi eux, `src_port=80` : "
            f"{int(unstable_wednesday['src_port'].eq(80).sum()):,} "
            f"({unstable_wednesday['src_port'].eq(80).mean():.2%}), "
            f"`dst_port=80` : {int(unstable_wednesday['dst_port'].eq(80).sum()):,} "
            f"({unstable_wednesday['dst_port'].eq(80).mean():.2%}).",
            f"Plage mercredi (UTC) : {unstable_time_text}; "
            f"heures principales : {unstable_hour_text}.",
            "Top IP source mercredi : "
            + ", ".join(
                f"{ip} ({count:,})"
                for ip, count in unstable_wednesday["src_ip"].value_counts().head(3).items()
            )
            + ".",
            "Protocol standardisé mercredi : "
            + ", ".join(
                f"{protocol} ({count:,})"
                for protocol, count in unstable_protocol_counts.items()
            )
            + "; top dst_port : "
            + ", ".join(
                f"{port} ({count:,})"
                for port, count in unstable_destination_ports.items()
            )
            + ".",
            "Top IP destination mercredi : "
            + ", ".join(
                f"{ip} ({count:,})"
                for ip, count in unstable_wednesday["dst_ip"].value_counts().head(3).items()
            )
            + ".",
            f"Vecteurs distincts parmi ces FP : {unique_unstable_vectors:,}/"
            f"{len(unstable_features):,}; `seen_in_train=False` : "
            f"{int((~unstable_frame['seen_in_train']).sum()):,}; règle canonique : "
            + ", ".join(
                f"{label} ({count:,})"
                for label, count in unstable_frame["canonical_rule"].value_counts().items()
            )
            + ".",
            f"Comparaison TP DoS Hulk graine 42 : {len(hulk_true_positives_42):,} TP, "
            f"{len(hulk_wednesday):,} le mercredi; `dst_port=80` pour "
            f"{int(hulk_wednesday['dst_port'].eq(80).sum()):,}. "
            f"Adresse source/destination inversée observée : {unstable_fp_pair:,} FP "
            f"192.168.10.50→172.16.0.1 contre {hulk_tp_pair:,} TP "
            "172.16.0.1→192.168.10.50.",
        ]
    )
    sensitivity_recall = pd.DataFrame(non_bot_attack_rows)
    no_bot_summary = threshold_summaries.loc[
        threshold_summaries["evaluation"].eq("test complet sans Bot")
    ].iloc[0]
    lines.extend(
        [
            "",
            "## Analyse de sensibilité — Bot exclu",
            "",
            "Ces résultats complémentaires ne remplacent pas le test principal complet.",
            "",
            "| Sous-ensemble | Flux | TP moyen | Recall moyen ± écart-type | Recall médian |",
            "|---|---:|---:|---:|---:|",
            f"| Test complet sans Bot | {int(no_bot_summary['effectif']):,} | — | "
            f"{no_bot_summary['recall']} | — |",
            f"| Attaques hors Bot seulement | "
            f"{int(sensitivity_recall['effectif'].iloc[0]):,} | "
            f"{sensitivity_recall['true_positives'].mean():.1f} | "
            f"{_format_mean_std(sensitivity_recall['recall'])} | "
            f"{sensitivity_recall['recall'].median():.6f} |",
        ]
    )
    lines.extend(
        [
            "",
            "",
            "## Métriques hors-pli recalculées",
            "",
            "| Pli | Effectif | Attaques | Taux d'attaque | PR-AUC | FPR au seuil OOF | TPR au seuil OOF | TPR max à FPR ≤ 1 % | best_iteration | Fit (s) |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in fold_table.itertuples(index=False):
        lines.append(
            f"| {row.fold} | {row.effectif:,} | {row.attaques:,} | "
            f"{row.taux_attaque:.4%} | {row.pr_auc:.6f} | {row.fpr:.4%} | "
            f"{row.tpr_at_threshold:.4%} | {row.tpr_at_fpr_1pct:.4%} | "
            f"{row.best_iteration} | {row.fit_seconds:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Recall par classe d'attaque",
            "",
            "| Classe | Flux test complet | Recall complet | Flux test strict | Recall strict | Flux sans signalés | Recall sans signalés | Avertissement |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    recall_lookup = class_summary.set_index(["evaluation", "classe"])
    for attack_class in sorted(class_counts.index.astype(str)):
        counts = {
            "test complet": int(class_counts.get(attack_class, 0)),
            "test strict": int(strict_counts.get(attack_class, 0)),
            "test sans signalés": int(unflagged_counts.get(attack_class, 0)),
        }
        recalls: dict[str, str] = {}
        for evaluation in counts:
            try:
                row = recall_lookup.loc[(evaluation, attack_class)]
                deviation = (
                    float(row["recall_ecart_type"])
                    if pd.notna(row["recall_ecart_type"])
                    else 0.0
                )
                recalls[evaluation] = f"{float(row['recall_moyen']):.4f} ± {deviation:.4f}"
            except KeyError:
                recalls[evaluation] = "n.d."
        warning = "⚠ < 100 en strict" if counts["test strict"] < 100 else ""
        lines.append(
            f"| {attack_class} | {counts['test complet']} | {recalls['test complet']} | "
            f"{counts['test strict']} | {recalls['test strict']} | "
            f"{counts['test sans signalés']} | {recalls['test sans signalés']} | {warning} |"
        )
    bot_table = pd.DataFrame(bot_rows)
    bot42 = bot_table.loc[bot_table["seed"].eq(42)].set_index("groupe")
    lines.extend(
        [
            "",
            "## Bot — diagnostic séparé",
            "",
            f"- Support Bot : {bot_attempted}/{bot_total} Attempted.",
            "- Le recall Bot est séparé des autres classes; le modèle demeure un classifieur binaire.",
            "",
            "| Groupe Bot | Flux | Score médian graine 42 | Recall graine 42 | Recall moyen ± écart-type / médiane |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for subgroup in ("Attempted", "non-Attempted"):
        row = bot42.loc[subgroup]
        subgroup_scores = bot_table.loc[bot_table["groupe"].eq(subgroup)]
        score = float(row["score_median"])
        recall = float(row["recall"])
        lines.append(
            f"| {subgroup} | {int(row['effectif'])} | "
            f"{score:.8f}" if np.isfinite(score) else
            f"| {subgroup} | {int(row['effectif'])} | n.d."
        )
        lines[-1] += (
            f" | {recall:.4f} | "
            f"{_format_mean_std_median(subgroup_scores['recall'])} |"
            if np.isfinite(recall)
            else f" | n.d. | {_format_mean_std_median(subgroup_scores['recall'])} |"
        )
    lines.extend(
        [
            "",
            "Bot par bloc et part Attempted :",
            "",
            "| Bloc | Bot | Attempted | Part Attempted |",
            "|---|---:|---:|---:|",
        ]
    )
    for split in ("train", "val", "test"):
        row = bot_block_summary[split]
        lines.append(
            f"| {split} | {row['effectif']:,} | {row['attempted']:,} | "
            f"{row['part_attempted']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## Matrice de confusion — graine 42, test complet",
            "",
            confusion_text,
            "",
            "## Temps",
            "",
            f"- Entraînement par graine : {_format_mean_std(training_log['training_seconds'])} s.",
            f"- Inférence sur le test par graine : {_format_mean_std(training_log['inference_seconds'])} s.",
            "- Le temps d'inférence mesure l'appel predict; il exclut la lecture Parquet et le chargement du modèle.",
            "",
            "## Importance des features (gain)",
            "",
            "Le CSV contient le gain par feature et par graine; le tableau ci-dessous classe "
            "la part moyenne du gain normalisée par modèle.",
            "",
            "| Rang | Feature | Gain moyen | Part moyenne du gain |",
            "|---:|---|---:|---:|",
        ]
    )
    importance_report = importance_summary.head(15)
    for feature, row in importance_report.iterrows():
        lines.append(
            f"| {int(row['rang'])} | {feature} | {row['gain_moyen']:.6g} | "
            f"{row['part_gain_moyenne']:.4%} |"
        )
    target_features = {
        "fwd header length": "Fwd Header Length",
        "total fwd packets": "Total Fwd Packets",
        "min_seg_size_forward": "min_seg_size_forward",
        "init_win_bytes_forward": "Init_Win_bytes_forward",
    }
    lines.extend(["", "Features à risque de raccourci (rang/part moyenne) :"])
    dominant: list[str] = []
    for normalized, display in target_features.items():
        match = importance_summary.loc[
            importance_summary.index.astype(str).str.casefold() == normalized
        ]
        if match.empty:
            lines.append(f"- {display} : absente des features finales.")
            continue
        row = match.iloc[0]
        lines.append(
            f"- {display} : rang {int(row['rang'])}, "
            f"{float(row['part_gain_moyenne']):.4%} du gain moyen."
        )
        if int(row["rang"]) <= 5:
            dominant.append(display)
    if dominant:
        lines.append(
            "- Alerte : feature(s) parmi les cinq premières en gain normalisé — "
            + ", ".join(dominant)
            + " (risque de raccourci)."
        )
    else:
        lines.append("- Aucune des quatre features ne figure dans les cinq premières.")

    lines.extend(
        [
            "",
            "## Audit des labels dans le test",
            "",
            f"- BENIGN avec règle d'attaque : {audit_directions['benign_regle_attaque']:,}.",
            f"- Attaque avec règle BENIGN : {audit_directions['attaque_regle_benign']:,}.",
            f"- Attaque avec autre règle d'attaque : "
            f"{audit_directions['attaque_autre_regle_attaque']:,}.",
            f"- `attempted_category >= 0` : {audit_directions['attempted']:,}.",
            "- Les flux signalés sont exclus uniquement de l'analyse complémentaire; "
            "ils restent dans le test complet et le test strict.",
            "",
            "### Sensibilité aux labels de l'audit",
            "",
            "Analyse secondaire; les résultats principaux restent évalués sur `label_bin` "
            "d'origine. « Attempted compté » définit l'attaque par règle canonique "
            "non-BENIGN OU Attempted. « Attempted exclu » retire les lignes Attempted "
            "avant calcul et utilise règle canonique non-BENIGN comme vérité.",
            "",
            "| Variante | Graine | n | PR-AUC | TPR à FPR ≤ 1 % | FP au seuil | FN au seuil |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in audit_metric_table.sort_values(["variant", "seed"]).itertuples(index=False):
        lines.append(
            f"| {row.variant} | {row.seed} | {row.effectif:,} | "
            f"{row.pr_auc:.6f} | {row.tpr_at_fpr_1pct:.6f} | "
            f"{row.false_positives:,} | {row.false_negatives:,} |"
        )
    for row in audit_metric_summary.itertuples(index=False):
        lines.append(
            f"| {row.variant} — moyenne | — | {row.effectif:,} | "
            f"{row.pr_auc_mean:.6f} | {row.tpr_at_fpr_1pct_mean:.6f} | "
            f"{row.fp_mean:.1f} | {row.fn_mean:.1f} |"
        )
        lines.append(
            f"| {row.variant} — médiane | — | {row.effectif:,} | "
            f"{row.pr_auc_median:.6f} | {row.tpr_at_fpr_1pct_median:.6f} | "
            f"{row.fp_median:.1f} | {row.fn_median:.1f} |"
        )
    lines.extend(
        [
            "",
            "### Part Attempted par classe d'attaque et bloc",
            "",
            "| Bloc | Classe | Effectif | Attempted | Part Attempted |",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in attempted_by_block:
        lines.append(
            f"| {row['bloc']} | {row['classe']} | {row['effectif']:,} | "
            f"{row['attempted']:,} | {row['part_attempted']:.2%} |"
        )
    lines.extend(
        [
            "",
            "## Limites",
            "",
            f"- Les plis train sont proches de l'interpolation : PR-AUC CV "
            f"(prévalence {prevalence_cv:.2%}) n'est pas comparable directement à la PR-AUC "
            f"test (prévalence {prevalence_test:.2%}); le pli 0 s'arrête à "
            f"`best_iteration={int(fold_table.loc[fold_table['fold'].eq(0), 'best_iteration'].iloc[0])}`.",
            f"- Les cinq meilleurs essais sont difficilement distinguables : écart "
            f"premier-cinquième {gap:.4f}, contre un écart-type d'environ "
            f"{float(np.mean([trial['std_score'] for trial in top_trials])):.4f}.",
            "- La recherche n'a porté que sur les plis 0–2; les plis 3–4 n'ont servi "
            "qu'au calcul OOF du seuil.",
            "- Les plis sont non causaux, purgés à 3 minutes, et des vecteurs quasi "
            "identiques existent entre plis; une validation temporelle ne garantit pas "
            "la transférabilité à un trafic futur.",
            "- CIC-IDS2017 est une capture de laboratoire; les labels/règles comportent "
            "des divergences mesurées ci-dessus. Les résultats ne prouvent pas les "
            "performances en production.",
            "- Les cibles évaluées sont les labels finaux `label_bin` / `label_multi` "
            "des Parquet; l'audit compare les règles normalisées de `label_audit.parquet` "
            "à ces labels.",
            f"- Le seuil fixe est instable entre graines : les faux positifs vont de "
            f"{false_positive_range[0]:,} à {false_positive_range[1]:,}; ne pas interpréter "
            "la seule moyenne sans cette dispersion.",
            f"- Bot n'est pas mesurable par ce modèle binaire : part Attempted "
            f"{bot_block_summary['train']['part_attempted']:.1%} en train contre "
            f"{bot_block_summary['test']['part_attempted']:.1%} en test "
            f"({bot_attempted}/{bot_total}); recall observé nul.",
            f"- FP propres aux graines 43/45/50 : {len(unstable_false_positives):,} flux "
            f"au sens strict y_pred=1 et label_bin=0, dont "
            f"{int(unstable_frame['canonical_rule'].eq('DoS Hulk').sum()):,} avec règle "
            f"Hulk et {len(unstable_wednesday):,} le mercredi; scores des graines "
            "instables concentrés près/au-dessus du seuil fixe.",
            f"- Les deux features de longueur minimale (Bwd Packet Length Min et "
            f"Fwd Packet Length Min) représentent ensemble "
            f"{minimum_length_share:.2%} du gain normalisé moyen.",
            "- Les classes à moins de 100 flux en test strict sont "
            + ", ".join(low_support_classes)
            + ".",
            "",
            f"CSV des métriques par graine et scénario : `{summary_csv}`.",
            f"CSV complet des importances par graine : `{importance_path}`.",
        ]
    )
    report_path = _configured_path(project_config, "summary_report")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "report_path": str(report_path),
        "summary_csv": str(summary_csv),
        "audit_metrics_csv": str(audit_metrics_csv),
        "importance_csv": str(importance_path),
    }


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("classes", "audit-labels", "benchmark", "search"),
    )
    parser.add_argument("--mode", choices=("bin", "multi"), default="bin")
    arguments = parser.parse_args()
    config = load_xgboost_config()
    if arguments.action == "classes":
        result = select_multiclass_classes(config)
    elif arguments.action == "audit-labels":
        result = recompute_label_audit(config)
    elif arguments.action == "benchmark":
        result = benchmark_one_fit(arguments.mode, config)
    else:
        result = search_hyperparameters(arguments.mode, config)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _main()
