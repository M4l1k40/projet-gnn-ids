"""Compare XGBoost et RF sur la normalisation log-z optionnelle V3."""

from __future__ import annotations

import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from scipy.stats import pearsonr, spearmanr
from sklearn.metrics import roc_curve

from src.data.schema import PREDICTION_COLUMNS
from src.models import rf as rf_model
from src.models import xgb as xgb_model
from src.models import xgb_v3


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration d’évaluation introuvable : {path}.")
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"Objet JSON invalide : {path}.")
    return result


def _project_config(
    config: dict[str, Any],
    processed_logz: Path,
) -> dict[str, Any]:
    project = deepcopy(config)
    project["data_variant"] = "v3"
    project["paths"]["processed_v3"] = str(processed_logz)
    project["paths"]["model_dir"] = str(
        xgb_model._configured_path(config, "model_dir_v3_logz")
    )
    project["paths"]["prediction_dir"] = str(
        xgb_model._configured_path(config, "prediction_dir_v3_logz")
    )
    project["paths"]["report_dir"] = str(
        xgb_model._configured_path(config, "report_dir_v3_logz")
    )
    return project


def _aligned_scores(
    path: Path,
    flow_ids: np.ndarray,
    seed: int,
) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(f"Prédictions de référence introuvables : {path}.")
    frame = pd.read_parquet(path, columns=["flow_id", "score", "seed"])
    if (
        frame["flow_id"].duplicated().any()
        or len(frame) != len(flow_ids)
        or not frame["seed"].eq(seed).all()
        or set(frame["flow_id"]) != set(flow_ids)
    ):
        raise ValueError(f"Prédictions de référence non alignées : {path}.")
    return frame.set_index("flow_id").loc[flow_ids, "score"].to_numpy(
        dtype=np.float32,
        copy=True,
    )


def _metrics(
    name: str,
    labels: np.ndarray,
    scores: np.ndarray,
    threshold: float,
    training_seconds: float | None,
    inference_seconds: float | None,
) -> dict[str, Any]:
    values = xgb_model._binary_metric_values(labels, scores, threshold)
    curve_fpr, curve_tpr, _ = roc_curve(labels, scores)
    allowed_01 = np.flatnonzero(curve_fpr <= 0.001)
    allowed_1 = np.flatnonzero(curve_fpr <= 0.01)
    false_negatives = int(values["attack_count"] - values["true_positives"])
    return {
        "model": name,
        "threshold": threshold,
        **values,
        "tpr_at_fpr_0_1pct": float(curve_tpr[allowed_01[-1]]),
        "tpr_at_fpr_1pct": float(curve_tpr[allowed_1[-1]]),
        "false_negatives": false_negatives,
        "training_seconds": training_seconds,
        "inference_seconds": inference_seconds,
    }


def _train_xgb(
    config: dict[str, Any],
    project: dict[str, Any],
    train: xgb_model.LoadedSplit,
    test: xgb_model.LoadedSplit,
    labels: np.ndarray,
    threshold: float,
    parameters: dict[str, Any],
    rounds: int,
) -> tuple[np.ndarray, float | None, float, Path, Path]:
    model_dir = xgb_model._configured_path(config, "model_dir_v3_logz")
    prediction_dir = xgb_model._configured_path(config, "prediction_dir_v3_logz")
    model_path = model_dir / "xgb_bin_b0_seed42_logz_v3.json"
    prediction_path = prediction_dir / "xgb_bin_b0_seed42_logz_v3.parquet"
    if model_path.exists() and not prediction_path.exists():
        booster = xgb.Booster()
        booster.load_model(model_path)
        training_seconds = None
    elif prediction_path.exists() and not model_path.exists():
        raise FileNotFoundError(
            f"Prédictions présentes sans modèle associé : {prediction_path}."
        )
    elif model_path.exists() and prediction_path.exists():
        saved = pd.read_parquet(prediction_path, columns=["flow_id", "score", "seed"])
        if (
            len(saved) != len(test.flow_ids)
            or not saved["seed"].eq(42).all()
            or not np.array_equal(saved["flow_id"].to_numpy(), test.flow_ids)
        ):
            raise ValueError(f"Prédictions log-z existantes non alignées : {prediction_path}.")
        booster = xgb.Booster()
        booster.load_model(model_path)
        scores = saved["score"].to_numpy(dtype=np.float32, copy=True)
        return scores, None, 0.0, model_path, prediction_path
    else:
        model_dir.mkdir(parents=True, exist_ok=True)
        train_matrix = xgb.DMatrix(
            train.X,
            label=labels,
            feature_names=train.feature_names,
            nthread=int(config["fixed"]["n_jobs"]),
        )
        benign = int(np.count_nonzero(labels == 0))
        attack = int(np.count_nonzero(labels == 1))
        if not benign or not attack:
            raise ValueError("Le train log-z doit contenir bénins et attaques.")
        fit_parameters = xgb_v3._fixed_parameters(
            config,
            parameters,
            labels,
            np.arange(len(labels)),
            42,
        )
        started = time.perf_counter()
        booster = xgb.train(
            fit_parameters,
            train_matrix,
            num_boost_round=rounds,
            verbose_eval=False,
        )
        training_seconds = time.perf_counter() - started
        booster.save_model(model_path)

    test_matrix = xgb.DMatrix(
        test.X,
        feature_names=test.feature_names,
        nthread=int(config["fixed"]["n_jobs"]),
    )
    started = time.perf_counter()
    scores = np.asarray(booster.predict(test_matrix), dtype=np.float32)
    inference_seconds = time.perf_counter() - started
    prediction = xgb_model.prediction_frame(
        test.flow_ids,
        test.y_bin,
        (scores >= threshold).astype(np.int8),
        scores,
        42,
    )
    if list(prediction.columns) != PREDICTION_COLUMNS:
        raise ValueError("Le format de prédictions log-z est invalide.")
    prediction_dir.mkdir(parents=True, exist_ok=True)
    if prediction_path.exists():
        raise FileExistsError(f"Refus d’écraser des prédictions : {prediction_path}.")
    prediction.to_parquet(prediction_path, index=False)
    return scores, training_seconds, inference_seconds, model_path, prediction_path


def _train_rf(
    config: dict[str, Any],
    train: xgb_model.LoadedSplit,
    test: xgb_model.LoadedSplit,
    threshold_data: dict[str, Any],
    threshold: float,
) -> tuple[np.ndarray, float | None, float, Path, Path]:
    model_dir = xgb_model._configured_path(config, "model_dir_v3_logz")
    prediction_dir = xgb_model._configured_path(config, "prediction_dir_v3_logz")
    model_path = model_dir / "rf_bin_b0_seed42_logz_v3.joblib"
    prediction_path = prediction_dir / "rf_bin_b0_seed42_logz_v3.parquet"
    if model_path.exists() and not prediction_path.exists():
        model = joblib.load(model_path)
        training_seconds = None
    elif prediction_path.exists() and not model_path.exists():
        raise FileNotFoundError(
            f"Prédictions présentes sans modèle associé : {prediction_path}."
        )
    elif model_path.exists() and prediction_path.exists():
        saved = pd.read_parquet(prediction_path, columns=["flow_id", "score", "seed"])
        if (
            len(saved) != len(test.flow_ids)
            or not saved["seed"].eq(42).all()
            or not np.array_equal(saved["flow_id"].to_numpy(), test.flow_ids)
        ):
            raise ValueError(f"Prédictions RF log-z existantes non alignées: {prediction_path}.")
        scores = saved["score"].to_numpy(dtype=np.float32, copy=True)
        return scores, None, 0.0, model_path, prediction_path
    else:
        model_dir.mkdir(parents=True, exist_ok=True)
        model_config = rf_model.load_rf_config()
        model_config["model"].update(threshold_data["model"])
        model = rf_model._estimator(model_config, 42)
        started = time.perf_counter()
        model.fit(train.X, train.y_bin)
        training_seconds = time.perf_counter() - started
        joblib.dump(
            model,
            model_path,
            compress=int(model_config["model"]["compression"]),
        )

    started = time.perf_counter()
    scores = rf_model._positive_probability(model, test.X)
    inference_seconds = time.perf_counter() - started
    prediction = xgb_model.prediction_frame(
        test.flow_ids,
        test.y_bin,
        (scores >= threshold).astype(np.int8),
        scores,
        42,
    )
    prediction_dir.mkdir(parents=True, exist_ok=True)
    if prediction_path.exists():
        raise FileExistsError(f"Refus d’écraser des prédictions : {prediction_path}.")
    prediction.to_parquet(prediction_path, index=False)
    return scores, training_seconds, inference_seconds, model_path, prediction_path


def _append_report(
    report_path: Path,
    metrics: pd.DataFrame,
    correlation: dict[str, float],
    model_files: dict[str, tuple[Path, Path]],
    rounds: int,
) -> None:
    marker = "## Réentraînement seed 42 — comparaison log-z"
    if not report_path.is_file():
        raise FileNotFoundError(f"Rapport de normalisation introuvable : {report_path}.")
    text = report_path.read_text(encoding="utf-8")
    if marker in text:
        raise FileExistsError("La comparaison log-z est déjà inscrite dans le rapport.")
    lines = [
        "",
        marker,
        "",
        (
            f"- XGBoost : essai 24, {rounds} rounds fixes, graine 42; RF : configuration "
            "sélectionnée en V3 (100 arbres, max_samples=0,5, min_samples_leaf=5)."
        ),
        (
            "- Les seuils restent ceux des modèles b0 existants (XGBoost et RF "
            "respectivement); le test n’a servi qu’à l’évaluation."
        ),
        "- Comparaison XGBoost des scores test : "
        f"Pearson r={correlation['pearson']:.8f}, Spearman ρ={correlation['spearman']:.8f}.",
        "",
        "| Modèle | PR-AUC | ROC-AUC | TPR@FPR≤0,1 % | TPR@FPR≤1 % | FP | FN | TPR au seuil | FPR au seuil | Fit (s) | Inférence (s) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, row in metrics.iterrows():
        lines.append(
            f"| {row['model']} | {row['pr_auc']:.6f} | {row['roc_auc']:.6f} | "
            f"{row['tpr_at_fpr_0_1pct']:.6f} | {row['tpr_at_fpr_1pct']:.6f} | "
            f"{int(row['false_positives'])} | {int(row['false_negatives'])} | "
            f"{row['tpr_at_threshold']:.6f} | {row['fpr_at_threshold']:.6f} | "
            f"{row['training_seconds'] if pd.notna(row['training_seconds']) else 'repris'} | "
            f"{row['inference_seconds'] if pd.notna(row['inference_seconds']) else 'repris'} |"
        )
    lines.extend(["", "### Artefacts de comparaison", ""])
    for name, (model_path, prediction_path) in model_files.items():
        lines.append(f"- {name} : modèle `{model_path}`; prédictions `{prediction_path}`.")
    lines.extend(
        [
            "",
            "Les seuils sont des seuils de validation hors-pli appris sur les modèles b0; les métriques ROC/PR et TPR à FPR fixé sont calculées sur le test. Le test n’a pas été utilisé pour l’ajustement du transformeur.",
            "",
        ]
    )
    with report_path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n".join(lines))


def run_logz_comparison(
    config: dict[str, Any] | None = None,
    *,
    run_rf: bool = True,
) -> pd.DataFrame:
    """Réentraîne XGB et, si demandé, RF sur train log-z et compare seed 42."""
    project_config = xgb_model.load_xgboost_config() if config is None else config
    data_config = xgb_model._data_config(project_config)
    processed_logz = Path(data_config["paths"]["processed_v3_logz"])
    if not processed_logz.is_dir():
        raise FileNotFoundError(f"Jeu log-z introuvable : {processed_logz}.")
    threshold_data = _read_json(
        xgb_model._configured_path(project_config, "logz_xgb_threshold")
    )
    parameters = threshold_data.get("hyperparameters")
    rounds = int(threshold_data.get("n_estimators", 0))
    if threshold_data.get("variant") != "b0" or not isinstance(parameters, dict):
        raise ValueError("Le seuil existant ne correspond pas à XGBoost b0.")
    if rounds != 199:
        raise ValueError("Le modèle de référence doit utiliser 199 rounds.")
    xgb_threshold = float(threshold_data["threshold_fpr_1pct"])
    project = _project_config(project_config, processed_logz)
    train = xgb_model.load_split("train", project)
    test = xgb_model.load_split("test", project)
    if set(train.flow_ids) & set(test.flow_ids):
        raise ValueError("Un flow_id du test apparaît dans le train log-z.")
    if train.feature_names != test.feature_names:
        raise ValueError("Ordre des features différent entre train et test.")

    metrics: list[dict[str, Any]] = []
    model_files: dict[str, tuple[Path, Path]] = {}
    xgb_scores, xgb_fit, xgb_inference, xgb_model_path, xgb_prediction_path = _train_xgb(
        project_config,
        project,
        train,
        test,
        train.y_bin,
        xgb_threshold,
        parameters,
        rounds,
    )
    model_files["XGBoost log-z"] = (xgb_model_path, xgb_prediction_path)

    xgb_reference_path = (
        xgb_model._configured_path(project_config, "logz_xgb_reference_prediction_dir")
        / "xgb_bin_b0_seed42_v3.parquet"
    )
    xgb_reference_scores = _aligned_scores(xgb_reference_path, test.flow_ids, 42)
    metrics.extend(
        [
            _metrics(
                "XGBoost V3 b0 original",
                test.y_bin,
                xgb_reference_scores,
                xgb_threshold,
                None,
                None,
            ),
            _metrics(
                "XGBoost V3 b0 log-z",
                test.y_bin,
                xgb_scores,
                xgb_threshold,
                xgb_fit,
                xgb_inference,
            ),
        ]
    )
    correlations = {
        "pearson": float(pearsonr(xgb_reference_scores, xgb_scores).statistic),
        "spearman": float(spearmanr(xgb_reference_scores, xgb_scores).statistic),
    }

    if run_rf:
        rf_config = rf_model.load_rf_config()
        rf_threshold_data = _read_json(
            xgb_model._configured_path(rf_config, "logz_rf_threshold")
        )
        rf_threshold = float(rf_threshold_data["threshold_fpr_1pct"])
        rf_scores, rf_fit, rf_inference, rf_model_path, rf_prediction_path = _train_rf(
            rf_config,
            train,
            test,
            rf_threshold_data,
            rf_threshold,
        )
        model_files["Random Forest log-z"] = (rf_model_path, rf_prediction_path)
        rf_reference_path = (
            xgb_model._configured_path(rf_config, "logz_rf_reference_prediction_dir")
            / "rf_bin_b0_seed42_rf.parquet"
        )
        rf_reference_scores = _aligned_scores(rf_reference_path, test.flow_ids, 42)
        metrics.extend(
            [
                _metrics(
                    "RF V3 b0 original",
                    test.y_bin,
                    rf_reference_scores,
                    rf_threshold,
                    None,
                    None,
                ),
                _metrics(
                    "RF V3 b0 log-z",
                    test.y_bin,
                    rf_scores,
                    rf_threshold,
                    rf_fit,
                    rf_inference,
                ),
            ]
        )

    result = pd.DataFrame(metrics)
    csv_path = xgb_model._configured_path(project_config, "logz_metrics_csv")
    report_path = xgb_model._configured_path(project_config, "logz_report")
    if csv_path.exists():
        previous = pd.read_csv(csv_path)
        expected_models = {
            "XGBoost V3 b0 original",
            "XGBoost V3 b0 log-z",
            "RF V3 b0 original",
            "RF V3 b0 log-z",
        }
        if (
            set(previous.get("model", [])) != expected_models
            or "tpr_at_fpr_0_1pct" in previous.columns
            or "false_negatives" in previous.columns
            or not report_path.is_file()
            or "## Réentraînement seed 42 — comparaison log-z"
            in report_path.read_text(encoding="utf-8")
        ):
            raise FileExistsError(f"Refus d’écraser un CSV existant : {csv_path}.")
        previous_times = previous.set_index("model")
        for column in ("training_seconds", "inference_seconds"):
            result[column] = result.apply(
                lambda row: (
                    previous_times.loc[row["model"], column]
                    if row["model"] in previous_times.index
                    and pd.notna(previous_times.loc[row["model"], column])
                    else row[column]
                ),
                axis=1,
            )
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(csv_path, index=False, encoding="utf-8")
    _append_report(report_path, result, correlations, model_files, rounds)
    return result


def main() -> None:
    result = run_logz_comparison()
    print(result.to_string(index=False))


if __name__ == "__main__":
    main()
