"""XGBoost binaire sur les plis P2, avec seuil calibré sur la validation."""

import gc
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import xgboost as xgb
from sklearn.metrics import average_precision_score, roc_curve

from src.data.p2 import _feature_columns, _prepare_features
from src.data.schema import PREDICTION_COLUMNS
from src.models import xgb as xgb_model
from src.utils.config import load_config

_ATTACK_LABEL = "label_multi"


@dataclass
class P2Partition:
    """Un sous-ensemble P2 chargé uniquement pour les rôles demandés."""

    flow_ids: np.ndarray
    X: np.ndarray
    y_bin: np.ndarray
    y_multi: np.ndarray
    roles: np.ndarray
    feature_names: list[str]


def _configured_path(config: dict[str, Any], key: str) -> Path:
    return xgb_model._configured_path(config, key)


def _folds(config: dict[str, Any]) -> list[str]:
    values = config["p2"]["folds"]
    if not isinstance(values, list) or not values:
        raise ValueError("p2.folds doit contenir au moins un pli.")
    if len(set(values)) != len(values) or any(
        not isinstance(value, str)
        or not re.fullmatch(r"(day|family)_[A-Za-z0-9_-]+", value)
        for value in values
    ):
        raise ValueError("p2.folds contient un identifiant invalide ou dupliqué.")
    return values


def _trial_parameters(config: dict[str, Any]) -> tuple[dict[str, Any], int]:
    path = _configured_path(config, "report_dir") / "best_bin.json"
    if not path.exists():
        raise FileNotFoundError(f"Paramètres existants de l’essai 24 introuvables : {path}.")
    result = json.loads(path.read_text(encoding="utf-8"))
    top_trials = result.get("top_10_trials", [])
    parameters = result.get("best_parameters")
    rounds = int(result.get("best_rounds", 0))
    if (
        not top_trials
        or int(top_trials[0].get("trial", -1)) != 24
        or not isinstance(parameters, dict)
        or rounds != 199
        or int(config["p2"]["n_estimators"]) != rounds
    ):
        raise ValueError("L’essai 24 et ses 199 rounds fixes ne sont pas confirmés.")
    return parameters, rounds


def _load_role_partition(
    pli: str,
    roles: Sequence[str],
    config: dict[str, Any],
) -> P2Partition:
    """Charge train/val ou test sans exposer les autres rôles au modèle."""
    requested = tuple(dict.fromkeys(str(role) for role in roles))
    if not requested or not set(requested).issubset({"train", "val", "test"}):
        raise ValueError("Les rôles demandés doivent être train, val ou test.")

    mapping_path = _configured_path(config, "p2_fold_mapping")
    clean_path = Path(config["paths"]["interim"]) / "clean.parquet"
    scaler_path = _configured_path(config, "p2_scaler_dir") / f"{pli}.joblib"
    for path in (mapping_path, clean_path, scaler_path):
        if not path.exists():
            raise FileNotFoundError(f"Source P2 introuvable : {path}.")

    mapping_dataset = ds.dataset(mapping_path, format="parquet")
    mapping_filter = (ds.field("pli") == pli) & ds.field("role").isin(
        list(requested)
    )
    mapping = mapping_dataset.to_table(
        columns=["flow_id", "role"],
        filter=mapping_filter,
    ).to_pandas()
    if mapping.empty or mapping["flow_id"].duplicated().any():
        raise ValueError(f"Rôles P2 absents ou flow_id dupliqué pour {pli}: {requested}.")
    mapping["flow_id"] = mapping["flow_id"].astype(str)
    mapping["role"] = mapping["role"].astype(str)
    role_by_id = mapping.set_index("flow_id")["role"]

    clean_dataset = ds.dataset(clean_path, format="parquet")
    features = xgb_model._feature_names(config)
    p2_features = _feature_columns(clean_dataset.schema)
    if features != p2_features:
        raise ValueError("Les 69 features configurées diffèrent de l’ordre source P2.")
    required = ["flow_id", "label_bin", _ATTACK_LABEL, *features]
    missing = set(required) - set(clean_dataset.schema.names)
    if missing:
        raise ValueError("Colonnes absentes de clean.parquet : " + ", ".join(sorted(missing)))

    id_type = clean_dataset.schema.field("flow_id").type
    selected_ids = pa.array(mapping["flow_id"].tolist(), type=id_type)
    flow_filter = ds.field("flow_id").isin(selected_ids)
    table = clean_dataset.to_table(columns=required, filter=flow_filter)
    frame = table.to_pandas()
    frame["flow_id"] = frame["flow_id"].astype(str)
    if (
        len(frame) != len(mapping)
        or frame["flow_id"].duplicated().any()
        or set(frame["flow_id"]) != set(mapping["flow_id"])
    ):
        raise ValueError(f"Les flow_id P2 de {pli} ne s’alignent pas sur clean.parquet.")

    assigned_roles = frame["flow_id"].map(role_by_id)
    if assigned_roles.isna().any() or not assigned_roles.isin(requested).all():
        raise ValueError(f"Rôles inattendus dans le chargement P2 de {pli}.")
    feature_frame = frame.loc[:, features]
    invalid_dtypes = [
        f"{name}={dtype}"
        for name, dtype in feature_frame.dtypes.items()
        if str(dtype) != "float32"
    ]
    if invalid_dtypes:
        raise TypeError("Features P2 attendues en float32 : " + ", ".join(invalid_dtypes))
    values = feature_frame.to_numpy(dtype=np.float64, copy=False)
    if not np.isfinite(values).all():
        raise ValueError(f"Features P2 non finies dans {pli}.")
    data_config = xgb_model._data_config(config)
    method = str(data_config["normalization"]["method"])
    scaler = joblib.load(scaler_path)
    if int(scaler.n_features_in_) != len(features):
        raise ValueError(f"Le scaler P2 de {pli} n’a pas les 69 features attendues.")
    transformed = scaler.transform(_prepare_features(values, method)).astype(
        np.float32
    )
    if not np.isfinite(transformed).all():
        raise ValueError(f"Features normalisées non finies dans {pli}.")

    return P2Partition(
        flow_ids=frame["flow_id"].to_numpy(dtype=str, copy=True),
        X=transformed,
        y_bin=frame["label_bin"].to_numpy(dtype=np.int8, copy=True),
        y_multi=frame[_ATTACK_LABEL].astype(str).to_numpy(),
        roles=assigned_roles.to_numpy(dtype=str, copy=True),
        feature_names=features,
    )


def _threshold_for_fpr(
    labels: np.ndarray,
    scores: np.ndarray,
    target_fpr: float,
) -> dict[str, float]:
    labels = np.asarray(labels, dtype=np.int8)
    scores = np.asarray(scores, dtype=np.float64)
    if not 0 < target_fpr < 1:
        raise ValueError("Le FPR cible doit être entre 0 et 1.")
    benign = scores[labels == 0]
    if not len(benign) or not np.isfinite(scores).all():
        raise ValueError("La validation doit contenir des scores bénins finis.")
    candidates = np.unique(scores)
    candidates = np.append(candidates, np.nextafter(candidates[-1], np.inf))
    ordered_benign = np.sort(benign)
    false_positives = len(benign) - np.searchsorted(
        ordered_benign, candidates, side="left"
    )
    eligible = candidates[false_positives / len(benign) <= target_fpr]
    threshold = float(eligible[0])
    return {
        "threshold": threshold,
        "achieved_fpr": float(np.mean(benign >= threshold)),
        "benign_rows": int(len(benign)),
    }


def _threshold_path(config: dict[str, Any], pli: str) -> Path:
    return _configured_path(config, "report_dir_p2") / f"threshold_bin_{pli}_p2.json"


def _model_path(config: dict[str, Any], pli: str, seed: int) -> Path:
    return _configured_path(config, "model_dir_p2") / f"xgb_bin_{pli}_seed{seed}_p2.json"


def _prediction_path(config: dict[str, Any], pli: str, seed: int) -> Path:
    return _configured_path(config, "prediction_dir_p2") / (
        f"xgb_bin_{pli}_seed{seed}_p2.parquet"
    )


def _training_meta_path(config: dict[str, Any], pli: str, seed: int) -> Path:
    return _configured_path(config, "report_dir_p2") / (
        f"training_bin_{pli}_seed{seed}_p2.json"
    )


def _inference_meta_path(config: dict[str, Any], pli: str, seed: int) -> Path:
    return _configured_path(config, "report_dir_p2") / (
        f"inference_bin_{pli}_seed{seed}_p2.json"
    )


def _write_json_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _threshold_payload(
    pli: str,
    seed: int,
    rounds: int,
    target_fpr: float,
    values: dict[str, float],
    val_rows: int,
) -> dict[str, Any]:
    return {
        "pli": pli,
        "seed": seed,
        "n_estimators": rounds,
        "method": "validation_benign_fpr",
        "target_fpr": target_fpr,
        "threshold": values["threshold"],
        "achieved_fpr": values["achieved_fpr"],
        "validation_rows": val_rows,
        "validation_benign_rows": values["benign_rows"],
    }


def _load_threshold(path: Path, pli: str, seed: int, rounds: int, target: float) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Seuil de validation absent : {path}.")
    threshold = json.loads(path.read_text(encoding="utf-8"))
    if (
        threshold.get("pli") != pli
        or threshold.get("seed") != seed
        or threshold.get("n_estimators") != rounds
        or threshold.get("method") != "validation_benign_fpr"
        or not np.isclose(float(threshold.get("target_fpr", np.nan)), target)
        or not np.isfinite(float(threshold.get("threshold", np.nan)))
        or float(threshold["achieved_fpr"]) > target
    ):
        raise ValueError(f"Le seuil existant ne correspond pas au protocole P2 : {path}.")
    return threshold


def _validation_threshold(
    config: dict[str, Any],
    pli: str,
    seed: int,
    rounds: int,
    booster: xgb.Booster,
    partition_loader: Callable[..., P2Partition],
) -> dict[str, Any]:
    policy = config["p2"]["threshold"]
    target = float(policy["target_fpr"])
    partition = partition_loader(pli, ("val",), config)
    val_mask = partition.roles == "val"
    if not val_mask.any():
        raise ValueError(f"Le rôle val est vide pour {pli}.")
    val_matrix = xgb.DMatrix(
        partition.X[val_mask],
        feature_names=partition.feature_names,
        nthread=int(config["fixed"]["n_jobs"]),
    )
    scores = np.asarray(booster.predict(val_matrix), dtype=np.float64)
    values = _threshold_for_fpr(partition.y_bin[val_mask], scores, target)
    result = _threshold_payload(
        pli, seed, rounds, target, values, int(val_mask.sum())
    )
    del partition, val_matrix
    return result


def _ensure_model_and_threshold(
    pli: str,
    config: dict[str, Any],
    parameters: dict[str, Any],
    rounds: int,
    partition_loader: Callable[..., P2Partition] = _load_role_partition,
) -> tuple[dict[str, Any], dict[str, Any]]:
    seed = int(config["p2"]["seed"])
    target_fpr = float(config["p2"]["threshold"]["target_fpr"])
    model_path = _model_path(config, pli, seed)
    meta_path = _training_meta_path(config, pli, seed)
    threshold_path = _threshold_path(config, pli)
    prediction_path = _prediction_path(config, pli, seed)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    threshold_path.parent.mkdir(parents=True, exist_ok=True)

    if model_path.exists():
        if not meta_path.exists():
            raise FileNotFoundError(
                f"Modèle P2 existant sans métadonnées; refus de le réentraîner : {model_path}."
            )
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
        if (
            metadata.get("pli") != pli
            or metadata.get("seed") != seed
            or metadata.get("n_estimators") != rounds
            or metadata.get("hyperparameters") != parameters
        ):
            raise ValueError(f"Le modèle P2 existant ne correspond pas à la configuration: {model_path}.")
        booster = xgb.Booster()
        booster.load_model(model_path)
        if booster.num_boosted_rounds() != rounds:
            raise ValueError(f"Le modèle P2 n’a pas {rounds} rounds: {model_path}.")
        if threshold_path.exists():
            threshold = _load_threshold(
                threshold_path, pli, seed, rounds, target_fpr
            )
        else:
            threshold = _validation_threshold(
                config, pli, seed, rounds, booster, partition_loader
            )
            _write_json_new(threshold_path, threshold)
        del booster
        print(f"{pli}: modèle déjà entraîné, reprise sans refit.")
        return metadata, threshold

    stale = [
        path for path in (meta_path, threshold_path, prediction_path) if path.exists()
    ]
    if stale:
        raise FileExistsError(
            "Artefacts P2 partiels sans modèle; refus d’écraser : "
            + ", ".join(str(path) for path in stale)
        )

    partition = partition_loader(pli, ("train", "val"), config)
    train_mask = partition.roles == "train"
    val_mask = partition.roles == "val"
    if not train_mask.any() or not val_mask.any():
        raise ValueError(f"Le pli {pli} doit avoir des rôles train et val non vides.")
    train_y = partition.y_bin[train_mask]
    benign = int(np.count_nonzero(train_y == 0))
    attack = int(np.count_nonzero(train_y == 1))
    if not benign or not attack:
        raise ValueError(f"Le train de {pli} doit contenir les deux labels binaires.")
    train_classes = sorted(set(partition.y_multi[train_mask].astype(str)))
    train_matrix = xgb.DMatrix(
        partition.X[train_mask],
        label=train_y,
        feature_names=partition.feature_names,
        nthread=int(config["fixed"]["n_jobs"]),
    )
    val_matrix = xgb.DMatrix(
        partition.X[val_mask],
        label=partition.y_bin[val_mask],
        feature_names=partition.feature_names,
        nthread=int(config["fixed"]["n_jobs"]),
    )
    fit_parameters = xgb_model._fit_parameters(
        "bin",
        parameters,
        config,
        scale_pos_weight=benign / attack,
    )
    fit_parameters["seed"] = seed
    started = time.perf_counter()
    booster = xgb.train(
        fit_parameters,
        train_matrix,
        num_boost_round=rounds,
        verbose_eval=False,
    )
    training_seconds = time.perf_counter() - started
    if booster.num_boosted_rounds() != rounds:
        raise RuntimeError(f"XGBoost n’a pas produit les {rounds} rounds pour {pli}.")
    val_scores = np.asarray(booster.predict(val_matrix), dtype=np.float64)
    threshold_values = _threshold_for_fpr(
        partition.y_bin[val_mask],
        val_scores,
        target_fpr,
    )
    threshold = _threshold_payload(
        pli,
        seed,
        rounds,
        target_fpr,
        threshold_values,
        int(val_mask.sum()),
    )
    metadata = {
        "pli": pli,
        "seed": seed,
        "n_estimators": rounds,
        "hyperparameters": parameters,
        "scale_pos_weight": benign / attack,
        "train_rows": int(train_mask.sum()),
        "val_rows": int(val_mask.sum()),
        "train_classes": train_classes,
        "fit_seconds": training_seconds,
        "feature_count": len(partition.feature_names),
    }
    if model_path.exists():
        raise FileExistsError(f"Refus d’écraser le modèle P2 : {model_path}.")
    booster.save_model(model_path)
    _write_json_new(meta_path, metadata)
    _write_json_new(threshold_path, threshold)
    print(
        f"{pli}: entraîné {rounds} rounds en {training_seconds:.1f} s; "
        f"seuil val={threshold['threshold']:.8g}."
    )
    del partition, train_matrix, val_matrix, booster
    gc.collect()
    return metadata, threshold


def _curve_tpr(labels: np.ndarray, scores: np.ndarray, target_fpr: float) -> float:
    labels = np.asarray(labels, dtype=np.int8)
    if len(np.unique(labels)) < 2:
        return float("nan")
    false_positive_rate, true_positive_rate, _ = roc_curve(labels, scores)
    eligible = np.flatnonzero(false_positive_rate <= target_fpr)
    return float(true_positive_rate[eligible[-1]]) if len(eligible) else 0.0


def _curve_threshold(labels: np.ndarray, scores: np.ndarray, target_fpr: float) -> float:
    return _threshold_for_fpr(labels, scores, target_fpr)["threshold"]


def _metrics_row(
    pli: str,
    evaluation: str,
    labels: np.ndarray,
    scores: np.ndarray,
    predictions: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    values = xgb_model._binary_metric_values(labels, scores, threshold)
    if len(np.unique(labels)) == 1 and np.any(labels == 1):
        values["pr_auc"] = float(average_precision_score(labels, scores))
    return {
        "pli": pli,
        "evaluation": evaluation,
        "test_rows": int(len(labels)),
        "prevalence": float(np.mean(labels)),
        **values,
        "tpr_at_fpr_0_1pct": _curve_tpr(labels, scores, 0.001),
        "tpr_at_fpr_1pct_curve": _curve_tpr(labels, scores, 0.01),
        "threshold_validation": float(threshold),
        "threshold_prediction_count": int(np.count_nonzero(predictions)),
    }


def _test_predictions(
    pli: str,
    config: dict[str, Any],
    threshold: dict[str, Any],
    partition_loader: Callable[..., P2Partition],
) -> tuple[P2Partition, pd.DataFrame, float]:
    seed = int(config["p2"]["seed"])
    path = _prediction_path(config, pli, seed)
    test = partition_loader(pli, ("test",), config)
    if not np.all(test.roles == "test"):
        raise ValueError(f"Le chargement du test P2 contient un rôle inattendu : {pli}.")
    threshold_value = float(threshold["threshold"])
    if path.exists():
        prediction = pd.read_parquet(path)
        if (
            list(prediction.columns) != PREDICTION_COLUMNS
            or len(prediction) != len(test.flow_ids)
            or prediction["flow_id"].duplicated().any()
            or not prediction["seed"].eq(seed).all()
        ):
            raise ValueError(f"Prédictions P2 existantes invalides : {path}.")
        aligned = prediction.set_index("flow_id").reindex(test.flow_ids.astype(str))
        if aligned["y_true"].isna().any() or aligned["score"].isna().any():
            raise ValueError(f"Prédictions P2 incomplètes : {path}.")
        if not np.array_equal(
            aligned["y_true"].to_numpy(dtype=np.int8), test.y_bin
        ):
            raise ValueError(f"Labels originaux changés dans les prédictions : {path}.")
        if not np.array_equal(
            aligned["y_pred"].to_numpy(dtype=np.int8),
            (aligned["score"].to_numpy(dtype=np.float64) >= threshold_value).astype(np.int8),
        ):
            raise ValueError(f"Seuil incohérent dans les prédictions : {path}.")
        prediction = aligned.reset_index()
        inference_seconds = float("nan")
        print(f"{pli}: prédictions existantes conservées.")
    else:
        model_path = _model_path(config, pli, seed)
        booster = xgb.Booster()
        booster.load_model(model_path)
        test_matrix = xgb.DMatrix(
            test.X,
            feature_names=test.feature_names,
            nthread=int(config["fixed"]["n_jobs"]),
        )
        started = time.perf_counter()
        scores = np.asarray(booster.predict(test_matrix), dtype=np.float32)
        inference_seconds = time.perf_counter() - started
        y_pred = (scores >= threshold_value).astype(np.int8)
        prediction = xgb_model.prediction_frame(
            test.flow_ids.astype(str),
            test.y_bin,
            y_pred,
            scores,
            seed,
        )
        if path.exists():
            raise FileExistsError(f"Refus d’écraser les prédictions P2 : {path}.")
        path.parent.mkdir(parents=True, exist_ok=True)
        prediction.to_parquet(path, index=False)
        _write_json_new(
            _inference_meta_path(config, pli, seed),
            {"pli": pli, "seed": seed, "inference_seconds": inference_seconds},
        )
        del booster, test_matrix

    if list(prediction.columns) != PREDICTION_COLUMNS:
        raise ValueError("Le schéma des prédictions P2 diffère du format commun.")
    return test, prediction, inference_seconds


def _recall_rows(
    pli: str,
    y_multi: np.ndarray,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    evaluation: str,
    train_classes: set[str],
) -> list[dict[str, Any]]:
    rows = []
    for label in sorted(set(y_multi.astype(str))):
        mask = y_multi.astype(str) == label
        if label == "BENIGN":
            value = float(np.mean(y_pred[mask] == 0))
            metric = "specificity"
            support = int(np.count_nonzero(mask & (y_true == 0)))
        else:
            positive = mask & (y_true == 1)
            support = int(positive.sum())
            value = (
                float(np.mean(y_pred[positive] == 1))
                if support
                else float("nan")
            )
            metric = "recall"
        rows.append(
            {
                "pli": pli,
                "evaluation": evaluation,
                "label_orig_multi": label,
                "support": support,
                "metric": metric,
                "value": value,
                "present_in_train": label in train_classes,
            }
        )
    return rows


def _baseline_v3(config: dict[str, Any]) -> tuple[pd.DataFrame, float]:
    processed = _configured_path(config, "processed_v3")
    test_path = processed / "test.parquet"
    prediction_path = _configured_path(config, "prediction_dir_v3") / (
        "xgb_bin_b0_seed42_v3.parquet"
    )
    threshold_path = _configured_path(config, "report_dir_v3") / "thresholds_bin_v3_b0.json"
    for path in (test_path, prediction_path, threshold_path):
        if not path.exists():
            raise FileNotFoundError(f"Référence V3 b0 manquante : {path}.")
    test = pd.read_parquet(test_path, columns=["flow_id", "label_bin", "label_multi"])
    prediction = pd.read_parquet(
        prediction_path,
        columns=["flow_id", "y_pred", "score", "seed"],
    )
    if (
        prediction["flow_id"].duplicated().any()
        or len(prediction) != len(test)
        or not prediction["seed"].eq(42).all()
    ):
        raise ValueError("Prédictions de référence V3 b0 invalides.")
    result = test.merge(prediction, on="flow_id", how="left", validate="one_to_one")
    if result[["score", "y_pred"]].isna().any().any():
        raise ValueError("Prédictions V3 b0 incomplètes.")
    threshold = float(
        json.loads(threshold_path.read_text(encoding="utf-8"))["threshold_fpr_1pct"]
    )
    return result, threshold


def _comparison_rows(
    pli: str,
    test: P2Partition,
    scores: np.ndarray,
    threshold: float,
    train_classes: set[str],
    v3: pd.DataFrame,
    v3_threshold: float,
) -> list[dict[str, Any]]:
    rows = []
    y_true = test.y_bin
    test_curve_threshold = (
        _curve_threshold(y_true, scores, 0.01)
        if len(np.unique(y_true)) == 2
        else float("nan")
    )
    v3_labels = v3["label_bin"].to_numpy(dtype=np.int8)
    v3_scores = v3["score"].to_numpy(dtype=np.float64)
    v3_curve_threshold = _curve_threshold(v3_labels, v3_scores, 0.01)
    for label in sorted(set(test.y_multi.astype(str)) - {"BENIGN"}):
        if label in train_classes:
            continue
        p2_mask = test.y_multi.astype(str) == label
        p2_support = int(np.count_nonzero(p2_mask & (y_true == 1)))
        if p2_support == 0:
            continue
        v3_mask = v3["label_multi"].astype(str).to_numpy() == label
        v3_support = int(np.count_nonzero(v3_mask & (v3_labels == 1)))
        rows.append(
            {
                "pli": pli,
                "label_multi": label,
                "p2_support": p2_support,
                "p2_validation_threshold": threshold,
                "p2_recall_validation_threshold": float(
                    np.mean(scores[p2_mask] >= threshold)
                ),
                "p2_recall_test_fpr_1pct": (
                    float(np.mean(scores[p2_mask] >= test_curve_threshold))
                    if np.isfinite(test_curve_threshold)
                    else float("nan")
                ),
                "p2_test_curve_threshold_diagnostic": test_curve_threshold,
                "v3_support": v3_support,
                "v3_b0_oof_threshold": v3_threshold,
                "v3_b0_recall_oof_threshold": (
                    float(np.mean(v3.loc[v3_mask, "score"].to_numpy() >= v3_threshold))
                    if v3_support
                    else float("nan")
                ),
                "v3_b0_recall_test_fpr_1pct": (
                    float(np.mean(v3.loc[v3_mask, "score"].to_numpy() >= v3_curve_threshold))
                    if v3_support
                    else float("nan")
                ),
                "v3_test_curve_threshold_diagnostic": v3_curve_threshold,
            }
        )
    return rows


def _write_report(
    config: dict[str, Any],
    metrics: pd.DataFrame,
    recalls: pd.DataFrame,
    comparisons: pd.DataFrame,
    fold_metadata: dict[str, dict[str, Any]],
    thresholds: dict[str, dict[str, Any]],
) -> dict[str, str]:
    report_path = _configured_path(config, "summary_report_p2")
    metrics_path = _configured_path(config, "metrics_csv_p2")
    recall_path = _configured_path(config, "recall_csv_p2")
    comparison_path = _configured_path(config, "comparison_csv_p2")
    conflicts = [
        path for path in (report_path, metrics_path, recall_path, comparison_path)
        if path.exists()
    ]
    if conflicts:
        raise FileExistsError(
            "Refus d’écraser les rapports P2 existants : "
            + ", ".join(str(path) for path in conflicts)
        )

    lines = [
        "# Évaluation XGBoost binaire — généralisation P2 / E5",
        "",
        "- Labels d’origine `label_bin`; paramètres de l’essai 24 conservés, 199 rounds fixes, sans early stopping ni nouvelle recherche.",
        "- Un modèle, graine 42, par pli; `scale_pos_weight` recalculé sur le train de ce pli; 69 features.",
        "- Le seuil de chaque pli est choisi sur les scores de validation BENIGN pour atteindre un FPR ≤ 1 %.",
        "- Les données test ne sont chargées qu’après la fin des entraînements des neuf plis.",
        "- Les vues v2 comptent `label_v2_bin == 1 OR attempted == True` comme positif.",
        "",
        "## Résultats par pli et vérité",
        "",
        "| Pli | Vérité | Train | Val | Test | Prévalence | Classes test (présentes dans train) | ROC-AUC | PR-AUC | TPR@FPR≤0,1 % | TPR@FPR≤1 % | Seuil val | TPR/FPR au seuil | FP/FN au seuil |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics.itertuples(index=False):
        meta = fold_metadata[row.pli]
        presence = ", ".join(
            f"{label} ({'train' if label in meta['train_classes'] else 'zéro-shot'})"
            for label in meta["test_classes"]
        )
        lines.append(
            f"| {row.pli} | {row.evaluation} | {meta['train_rows']:,} | "
            f"{meta['val_rows']:,} | {row.test_rows:,} | {row.prevalence:.4%} | "
            f"{presence} | {row.roc_auc:.5f} | {row.pr_auc:.5f} | "
            f"{row.tpr_at_fpr_0_1pct:.4f} | {row.tpr_at_fpr_1pct_curve:.4f} | "
            f"{row.threshold_validation:.8g} | {row.tpr_at_threshold:.4f}/"
            f"{row.fpr_at_threshold:.4f} | {row.false_positives:,}/{row.attack_count-row.true_positives:,} |"
        )
    lines.extend(
        [
            "",
            "Les PR-AUC sont des average precision et doivent être lues avec la prévalence affichée.",
            "Les plis famille ne contiennent aucun BENIGN en test : ROC-AUC et points TPR@FPR ne sont pas définis; la PR-AUC de 1,0 est dégénérée (prévalence 100 %) et n’indique pas de séparation.",
            "",
            "## Recall par classe d’origine",
            "",
            "Le BENIGN est présenté en spécificité; les classes d’attaque sont présentées en recall avec support.",
            "",
            "| Pli | Vérité | Classe d’origine | Effectif positif | Présente dans train | Mesure |",
            "|---|---|---|---:|---|---:|",
        ]
    )
    for row in recalls.itertuples(index=False):
        lines.append(
            f"| {row.pli} | {row.evaluation} | {row.label_orig_multi} | "
            f"{row.support:,} | {'oui' if row.present_in_train else 'non'} | "
            f"{row.metric} {row.value:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Diagnostic zéro-shot P2 contre V3 b0 en distribution",
            "",
            "La ligne P2 compare le recall au seuil calibré sur val et au point de la courbe du test "
            "dont le FPR est ≤ 1 %. La référence V3 b0 utilise son seuil OOF et son propre point de "
            "courbe test. Ces comparaisons sont diagnostiques, avec des splits et supports différents.",
            "",
            "| Pli P2 | Classe absente du train | Support P2 | Recall P2 au seuil val | Recall P2 à FPR test≤1 % | Support V3 | Recall V3 au seuil OOF | Recall V3 à FPR test≤1 % |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in comparisons.itertuples(index=False):
        lines.append(
            f"| {row.pli} | {row.label_multi} | {row.p2_support:,} | "
            f"{row.p2_recall_validation_threshold:.4f} | {row.p2_recall_test_fpr_1pct:.4f} | "
            f"{row.v3_support:,} | {row.v3_b0_recall_oof_threshold:.4f} | "
            f"{row.v3_b0_recall_test_fpr_1pct:.4f} |"
        )
    lines.extend(
        [
            "",
            "## Seuils et temps",
            "",
            "| Pli | Seuil val | FPR val BENIGN atteint | Fit (s) | Inférence (s) |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for pli, metadata in fold_metadata.items():
        threshold = thresholds[pli]
        inference_path = _inference_meta_path(config, pli, int(config["p2"]["seed"]))
        inference = (
            json.loads(inference_path.read_text(encoding="utf-8"))["inference_seconds"]
            if inference_path.exists()
            else float("nan")
        )
        lines.append(
            f"| {pli} | {threshold['threshold']:.8g} | {threshold['achieved_fpr']:.4%} | "
            f"{metadata['fit_seconds']:.1f} | {inference:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- Plusieurs classes d’attaque du test sont absentes du train : ces recalls mesurent une généralisation zéro-shot, pas une classification apprise de ces classes.",
            "- Les hyperparamètres de l’essai 24 ont été choisis sur des plis V2 qui contenaient ces classes; le protocole P2 n’est donc pas une sélection entièrement indépendante.",
            "- Une seule graine (42) a été exécutée; la dispersion entre graines n’est pas estimée.",
            "- Le seuil est calibré sur val, et les TPR à FPR 0,1 %/1 % sont des points descriptifs de la courbe test, pas des seuils de déploiement.",
            "- Heartbleed et Infiltration sont exclus des plis P2 faute d’effectif suffisant.",
            "- Les règles v2 sont des heuristiques d’audit, pas une vérité terrain; la vue v2 est une analyse secondaire.",
            "",
            f"Métriques par pli : [{metrics_path.name}](./{metrics_path.name}).",
            f"Recall par classe : [{recall_path.name}](./{recall_path.name}).",
            f"Comparaison zéro-shot : [{comparison_path.name}](./{comparison_path.name}).",
        ]
    )
    for path in (metrics_path, recall_path, comparison_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(metrics_path, index=False, encoding="utf-8")
    recalls.to_csv(recall_path, index=False, encoding="utf-8")
    comparisons.to_csv(comparison_path, index=False, encoding="utf-8")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "report_path": str(report_path),
        "metrics_csv": str(metrics_path),
        "recall_csv": str(recall_path),
        "comparison_csv": str(comparison_path),
    }


def run_p2(
    config: dict[str, Any] | None = None,
    *,
    partition_loader: Callable[..., P2Partition] = _load_role_partition,
) -> dict[str, str]:
    """Entraîne ou reprend les neuf plis, puis lit leurs tests."""
    project = xgb_model.load_xgboost_config() if config is None else config
    parameters, rounds = _trial_parameters(project)
    folds = _folds(project)
    output_paths = (
        _configured_path(project, "summary_report_p2"),
        _configured_path(project, "metrics_csv_p2"),
        _configured_path(project, "recall_csv_p2"),
        _configured_path(project, "comparison_csv_p2"),
    )
    existing_reports = [path for path in output_paths if path.exists()]
    if existing_reports:
        raise FileExistsError(
            "Refus d’écraser les rapports P2 existants : "
            + ", ".join(str(path) for path in existing_reports)
        )

    metadata_by_fold: dict[str, dict[str, Any]] = {}
    thresholds: dict[str, dict[str, Any]] = {}
    for pli in folds:
        metadata, threshold = _ensure_model_and_threshold(
            pli, project, parameters, rounds, partition_loader
        )
        metadata_by_fold[pli] = metadata
        thresholds[pli] = threshold
        gc.collect()

    # Phase test séparée : aucun test n’est chargé avant la fin des neuf fits.
    v2_labels = pd.read_parquet(
        _configured_path(project, "labels_v2_all"),
        columns=["flow_id", "label_v2_bin", "attempted"],
    )
    if v2_labels["flow_id"].duplicated().any():
        raise ValueError("labels_v2_all contient des flow_id dupliqués.")
    v2_labels = v2_labels.set_index("flow_id")
    baseline, baseline_threshold = _baseline_v3(project)
    metric_rows: list[dict[str, Any]] = []
    recall_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []

    for pli in folds:
        metadata = metadata_by_fold[pli]
        threshold_info = thresholds[pli]
        threshold = float(threshold_info["threshold"])
        test, prediction, _ = _test_predictions(
            pli, project, threshold_info, partition_loader
        )
        metadata["test_rows"] = int(len(test.flow_ids))
        metadata["test_classes"] = sorted(set(test.y_multi.astype(str)))
        aligned = prediction.set_index("flow_id").reindex(test.flow_ids.astype(str))
        scores = aligned["score"].to_numpy(dtype=np.float64)
        y_pred = aligned["y_pred"].to_numpy(dtype=np.int8)
        origin = test.y_bin
        v2_aligned = v2_labels.reindex(test.flow_ids.astype(str))
        if v2_aligned.isna().any().any():
            raise ValueError(f"labels_v2_all ne couvre pas le test de {pli}.")
        y_v2 = np.logical_or(
            v2_aligned["label_v2_bin"].to_numpy(dtype=np.int8) == 1,
            v2_aligned["attempted"].to_numpy(dtype=bool),
        ).astype(np.int8)
        for evaluation, truth in (("labels origine", origin), ("v2 Attempted comptés", y_v2)):
            metric_rows.append(
                _metrics_row(pli, evaluation, truth, scores, y_pred, threshold)
            )
            recall_rows.extend(
                _recall_rows(
                    pli,
                    test.y_multi,
                    truth,
                    y_pred,
                    evaluation,
                    set(metadata["train_classes"]),
                )
            )
        comparison_rows.extend(
            _comparison_rows(
                pli,
                test,
                scores,
                threshold,
                set(metadata["train_classes"]),
                baseline,
                baseline_threshold,
            )
        )
        del test, prediction, aligned, v2_aligned
        gc.collect()

    results = _write_report(
        project,
        pd.DataFrame(metric_rows),
        pd.DataFrame(recall_rows),
        pd.DataFrame(comparison_rows),
        metadata_by_fold,
        thresholds,
    )
    return results


if __name__ == "__main__":
    print(json.dumps(run_p2(), ensure_ascii=False, indent=2))
