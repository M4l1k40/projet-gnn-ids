"""Exécution reprenable des variantes binaires XGBoost sur le split V3."""

import gc
import json
import time
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb

from src.models import xgb as xgb_model
from src.utils.config import load_config

VARIANTS = ("b0", "v2a", "v2b")
EVALUATIONS = (
    "labels d'origine",
    "v2 — Attempted comptés",
    "v2 — Attempted exclus",
)
_V2_BASELINE = "V2 origine (split différent)"


def _v3_config(config: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(config)
    if result.get("data_variant", "v2") != "v3":
        raise ValueError("La configuration doit choisir data_variant: v3.")
    result["paths"]["legacy_processed"] = result["paths"]["processed"]
    result["paths"]["legacy_prediction_dir"] = result["paths"]["prediction_dir"]
    result["paths"]["legacy_report_dir"] = result["paths"]["report_dir"]
    result["paths"]["processed"] = xgb_model._configured_path(
        result, "processed_v3"
    )
    result["paths"]["model_dir"] = xgb_model._configured_path(
        result, "model_dir_v3"
    )
    result["paths"]["prediction_dir"] = xgb_model._configured_path(
        result, "prediction_dir_v3"
    )
    result["paths"]["report_dir"] = xgb_model._configured_path(
        result, "report_dir_v3"
    )
    return result


def _threshold_path(config: dict[str, Any], variant: str) -> Path:
    return xgb_model._configured_path(config, "report_dir") / (
        f"thresholds_bin_v3_{variant}.json"
    )


def _oof_path(config: dict[str, Any], variant: str) -> Path:
    return xgb_model._configured_path(config, "report_dir") / (
        f"oof_bin_{variant}_v3.parquet"
    )


def _seed_model_path(config: dict[str, Any], variant: str, seed: int) -> Path:
    return xgb_model._configured_path(config, "model_dir") / (
        f"xgb_bin_{variant}_seed{seed}_v3.json"
    )


def _seed_prediction_path(config: dict[str, Any], variant: str, seed: int) -> Path:
    return xgb_model._configured_path(config, "prediction_dir") / (
        f"xgb_bin_{variant}_seed{seed}_v3.parquet"
    )


def _target_labels(split: xgb_model.LoadedSplit, variant: str) -> np.ndarray:
    if variant == "b0":
        return split.y_bin
    if variant in {"v2a", "v2b"} and split.y_v2_bin is not None:
        return split.y_v2_bin
    raise ValueError(f"Labels v2 indisponibles pour la variante {variant}.")


def _eligible_rows(split: xgb_model.LoadedSplit, variant: str) -> np.ndarray:
    if variant == "v2b":
        if split.attempted is None:
            raise ValueError("Le flag Attempted est requis pour v2b.")
        return ~split.attempted
    return np.ones(len(split.flow_ids), dtype=bool)


def _fixed_parameters(
    config: dict[str, Any],
    parameters: dict[str, Any],
    labels: np.ndarray,
    indexes: np.ndarray,
    seed: int,
) -> dict[str, Any]:
    benign = int(np.count_nonzero(labels[indexes] == 0))
    attack = int(np.count_nonzero(labels[indexes] == 1))
    if not benign or not attack:
        raise ValueError("Chaque fit binaire doit avoir des bénins et des attaques.")
    fixed_parameters = xgb_model._fit_parameters(
        "bin",
        parameters,
        config,
        scale_pos_weight=benign / attack,
    )
    fixed_parameters["seed"] = int(seed)
    return fixed_parameters


def _load_parameters(config: dict[str, Any]) -> tuple[dict[str, Any], int]:
    legacy_report = xgb_model._configured_path(config, "legacy_report_dir")
    best_path = legacy_report / "best_bin.json"
    if not best_path.exists():
        raise FileNotFoundError(f"Paramètres de l’essai 24 introuvables : {best_path}.")
    best = json.loads(best_path.read_text(encoding="utf-8"))
    top_trials = best.get("top_10_trials", [])
    if not top_trials or int(top_trials[0].get("trial", -1)) != 24:
        raise ValueError("best_bin.json ne confirme pas l’essai 24 comme meilleur.")
    parameters = best.get("best_parameters")
    rounds = int(best.get("best_rounds", 0))
    if not isinstance(parameters, dict) or rounds != 199:
        raise ValueError("L’essai 24 doit fournir ses paramètres et exactement 199 rounds.")
    return parameters, rounds


def _oof_diagnostics(
    oof: pd.DataFrame,
    fold_count: int,
    threshold: float,
) -> list[dict[str, Any]]:
    diagnostics = []
    for fold in range(fold_count):
        group = oof.loc[oof["fold"].eq(fold)]
        values = xgb_model._binary_metric_values(
            group["y_true"].to_numpy(dtype=np.int8),
            group["score"].to_numpy(dtype=np.float64),
            threshold,
        )
        diagnostics.append(
            {
                "fold": fold,
                "effectif": len(group),
                "attaques": int(group["y_true"].sum()),
                "taux_attaque": float(group["y_true"].mean()),
                "best_iteration": 198,
                "fit_seconds": float(group["fit_seconds"].iloc[0]),
                **values,
            }
        )
    return diagnostics


def _get_or_build_threshold(
    config: dict[str, Any],
    variant: str,
    train: xgb_model.LoadedSplit,
    parameters: dict[str, Any],
    rounds: int,
) -> dict[str, Any]:
    path = _threshold_path(config, variant)
    oof_path = _oof_path(config, variant)
    labels = _target_labels(train, variant)
    eligible = _eligible_rows(train, variant)
    fold_ids, purged = xgb_model._fold_data(train, config)
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            data.get("variant") != variant
            or data.get("n_estimators") != rounds
            or data.get("hyperparameters") != parameters
            or data.get("train_rows") != len(train.flow_ids)
        ):
            raise ValueError(f"Le seuil existant ne correspond pas à {variant}: {path}.")
        return data

    if oof_path.exists():
        oof = pd.read_parquet(oof_path)
        expected_ids = pd.Index(train.flow_ids[eligible])
        if (
            oof["flow_id"].duplicated().any()
            or set(oof["flow_id"]) != set(expected_ids)
            or not np.array_equal(
                oof.set_index("flow_id").loc[expected_ids, "y_true"].to_numpy(
                    dtype=np.int8
                ),
                labels[eligible],
            )
        ):
            raise ValueError(f"Cache hors-pli invalide pour {variant}: {oof_path}.")
    else:
        matrix = xgb.DMatrix(
            train.X,
            label=labels,
            feature_names=train.feature_names,
            nthread=int(config["fixed"]["n_jobs"]),
        )
        rows: list[pd.DataFrame] = []
        for fold in range(int(config["cv_folds"])):
            validation = (fold_ids == fold) & eligible
            training = (fold_ids != fold) & ~purged[:, fold] & eligible
            train_indexes = np.flatnonzero(training)
            validation_indexes = np.flatnonzero(validation)
            if not len(train_indexes) or not len(validation_indexes):
                raise ValueError(f"Pli {fold} vide pour la variante {variant}.")
            training_matrix = matrix.slice(train_indexes)
            validation_matrix = matrix.slice(validation_indexes)
            fit_parameters = _fixed_parameters(
                config, parameters, labels, train_indexes, 42 + fold
            )
            started = time.perf_counter()
            booster = xgb.train(
                fit_parameters,
                training_matrix,
                num_boost_round=rounds,
                verbose_eval=False,
            )
            elapsed = time.perf_counter() - started
            scores = booster.predict(validation_matrix)
            rows.append(
                pd.DataFrame(
                    {
                        "flow_id": train.flow_ids[validation_indexes],
                        "fold": fold,
                        "y_true": labels[validation_indexes],
                        "score": np.asarray(scores, dtype=np.float32),
                        "fit_seconds": elapsed,
                    }
                )
            )
            del training_matrix, validation_matrix, booster
        del matrix
        oof = pd.concat(rows, ignore_index=True)
        if oof_path.exists():
            raise FileExistsError(f"Refus d’écraser le cache hors-pli : {oof_path}.")
        oof_path.parent.mkdir(parents=True, exist_ok=True)
        oof.to_parquet(oof_path, index=False)

    threshold_values = xgb_model._threshold_values(
        oof["y_true"].to_numpy(dtype=np.int8),
        oof["score"].to_numpy(dtype=np.float64),
    )
    diagnostics = _oof_diagnostics(
        oof,
        int(config["cv_folds"]),
        threshold_values["threshold_fpr_1pct"],
    )
    data = {
        "variant": variant,
        "data_variant": "v3",
        "hyperparameters": parameters,
        "n_estimators": rounds,
        "threshold_fpr_1pct": threshold_values["threshold_fpr_1pct"],
        "achieved_fpr": threshold_values["achieved_fpr"],
        "threshold_f1_max": threshold_values["threshold_f1_max"],
        "f1_max": threshold_values["f1_max"],
        "train_rows": len(train.flow_ids),
        "oof_rows": len(oof),
        "excluded_attempted_from_oof": (
            int(np.count_nonzero(~eligible)) if variant == "v2b" else 0
        ),
        "fold_diagnostics": diagnostics,
    }
    if path.exists():
        raise FileExistsError(f"Refus d’écraser le seuil existant : {path}.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def _seed_sidecar(config: dict[str, Any], variant: str, seed: int) -> Path:
    return xgb_model._configured_path(config, "report_dir") / (
        f"training_bin_{variant}_seed{seed}_v3.json"
    )


def _importance_path(config: dict[str, Any], variant: str, seed: int) -> Path:
    return xgb_model._configured_path(config, "report_dir") / (
        f"importance_bin_{variant}_seed{seed}_v3.csv"
    )


def _train_variant(
    config: dict[str, Any],
    variant: str,
    train: xgb_model.LoadedSplit,
    test: xgb_model.LoadedSplit,
    parameters: dict[str, Any],
    rounds: int,
    threshold: float,
) -> None:
    labels = _target_labels(train, variant)
    eligible = _eligible_rows(train, variant)
    indexes = np.flatnonzero(eligible)
    if np.intersect1d(train.flow_ids[indexes], test.flow_ids).size:
        raise ValueError("Un flow_id du test V3 apparaît dans le train retenu.")
    matrix = xgb.DMatrix(
        train.X,
        label=labels,
        feature_names=train.feature_names,
        nthread=int(config["fixed"]["n_jobs"]),
    )
    training = matrix.slice(indexes)
    model_dir = xgb_model._configured_path(config, "model_dir")
    prediction_dir = xgb_model._configured_path(config, "prediction_dir")
    report_dir = xgb_model._configured_path(config, "report_dir")
    model_dir.mkdir(parents=True, exist_ok=True)
    prediction_dir.mkdir(parents=True, exist_ok=True)
    test_matrix = xgb.DMatrix(
        test.X,
        feature_names=test.feature_names,
        nthread=int(config["fixed"]["n_jobs"]),
    )
    for seed in config["seeds"]:
        seed = int(seed)
        model_path = _seed_model_path(config, variant, seed)
        prediction_path = _seed_prediction_path(config, variant, seed)
        timing_path = _seed_sidecar(config, variant, seed)
        importance_path = _importance_path(config, variant, seed)
        if prediction_path.exists():
            if not model_path.exists():
                raise FileNotFoundError(
                    f"Prédictions présentes sans modèle associé: {prediction_path}."
                )
            prediction = pd.read_parquet(prediction_path, columns=["flow_id", "seed"])
            if len(prediction) != len(test.flow_ids) or not prediction["seed"].eq(seed).all():
                raise ValueError(f"Prédictions existantes invalides: {prediction_path}.")
            if not timing_path.exists() or not importance_path.exists():
                booster = xgb.Booster()
                booster.load_model(model_path)
                gain = booster.get_score(importance_type="gain")
                if not importance_path.exists():
                    pd.DataFrame(
                        [
                            {"seed": seed, "feature": feature, "gain": float(gain.get(feature, 0.0))}
                            for feature in test.feature_names
                        ]
                    ).to_csv(importance_path, index=False)
                del booster
            if not timing_path.exists():
                timing_path.write_text(
                    json.dumps(
                        {
                            "variant": variant,
                            "seed": seed,
                            "n_estimators": rounds,
                            "training_seconds": None,
                            "inference_seconds": None,
                        },
                        indent=2,
                    )
                    + "\n",
                    encoding="utf-8",
                )
            print(f"{variant}: graine {seed} déjà présente, reprise sans réentraînement.")
            continue

        if model_path.exists():
            booster = xgb.Booster()
            booster.load_model(model_path)
            training_seconds = None
        else:
            fit_parameters = _fixed_parameters(
                config, parameters, labels, indexes, seed
            )
            started = time.perf_counter()
            booster = xgb.train(
                fit_parameters,
                training,
                num_boost_round=rounds,
                verbose_eval=False,
            )
            training_seconds = time.perf_counter() - started
            booster.save_model(model_path)
        inference_started = time.perf_counter()
        scores = np.asarray(booster.predict(test_matrix), dtype=np.float32)
        inference_seconds = time.perf_counter() - inference_started
        gain = booster.get_score(importance_type="gain")
        if not importance_path.exists():
            pd.DataFrame(
                [
                    {"seed": seed, "feature": feature, "gain": float(gain.get(feature, 0.0))}
                    for feature in test.feature_names
                ]
            ).to_csv(importance_path, index=False)
        predicted = (scores >= threshold).astype(np.int8)
        prediction = xgb_model.prediction_frame(
            test.flow_ids,
            _target_labels(test, variant if variant != "v2b" else "v2a"),
            predicted,
            scores,
            seed,
        )
        if prediction_path.exists():
            raise FileExistsError(f"Refus d’écraser les prédictions : {prediction_path}.")
        prediction.to_parquet(prediction_path, index=False)
        if not timing_path.exists():
            timing_path.write_text(
                json.dumps(
                    {
                        "variant": variant,
                        "seed": seed,
                        "n_estimators": rounds,
                        "training_seconds": training_seconds,
                        "inference_seconds": inference_seconds,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        del booster, prediction
        print(
            f"{variant}: graine {seed} terminée"
            + (
                f" ({training_seconds:.1f} s fit, {inference_seconds:.1f} s inférence)."
                if training_seconds is not None
                else f" (modèle repris, {inference_seconds:.1f} s inférence)."
            )
        )
    del training, matrix, test_matrix


def _evaluation_context(
    config: dict[str, Any],
    data_variant: str,
) -> pd.DataFrame:
    processed = (
        xgb_model._configured_path(config, "legacy_processed")
        if data_variant == "v2"
        else xgb_model._configured_path(config, "processed_v3")
    )
    test = pd.read_parquet(
        processed / "test.parquet",
        columns=["flow_id", "label_bin", "label_multi"],
    )
    labels = pd.read_parquet(
        xgb_model._configured_path(config, "labels_v2_all"),
        columns=[
            "flow_id",
            "label_v2_bin",
            "attempted",
            "changed",
            "v2_family",
        ],
    )
    context = test.merge(labels, on="flow_id", how="left", validate="one_to_one")
    if context[["label_v2_bin", "attempted", "changed", "v2_family"]].isna().any().any():
        raise ValueError(f"labels_v2_all ne couvre pas le test {data_variant}.")
    context["audit_signaled"] = context["changed"].astype(bool) | context[
        "attempted"
    ].astype(bool)
    context["audit_counted"] = context["label_v2_bin"].astype(np.int8) | context[
        "attempted"
    ].astype(np.int8)
    return context


def _read_predictions(
    path: Path,
    context: pd.DataFrame,
    seed: int,
) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Prédictions manquantes : {path}.")
    predictions = pd.read_parquet(
        path,
        columns=["flow_id", "y_pred", "score", "seed"],
    )
    if predictions["flow_id"].duplicated().any() or not predictions["seed"].eq(seed).all():
        raise ValueError(f"Prédictions invalides : {path}.")
    result = predictions.merge(context, on="flow_id", how="left", validate="one_to_one")
    if len(result) != len(context) or result["label_bin"].isna().any():
        raise ValueError(f"Les prédictions ne couvrent pas intégralement {path}.")
    return result


def _evaluate_predictions(
    predictions: pd.DataFrame,
    threshold: float,
    seed: int,
    training_variant: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scores = predictions["score"].to_numpy(dtype=np.float64)
    predicted = (scores >= threshold).astype(np.int8)
    signals = predictions["audit_signaled"].to_numpy(dtype=bool)
    evaluation_targets = {
        EVALUATIONS[0]: (
            predictions["label_bin"].to_numpy(dtype=np.int8),
            np.ones(len(predictions), dtype=bool),
        ),
        EVALUATIONS[1]: (
            predictions["audit_counted"].to_numpy(dtype=np.int8),
            np.ones(len(predictions), dtype=bool),
        ),
        EVALUATIONS[2]: (
            predictions["label_v2_bin"].to_numpy(dtype=np.int8),
            ~predictions["attempted"].to_numpy(dtype=bool),
        ),
    }
    metric_rows: list[dict[str, Any]] = []
    recall_rows: list[dict[str, Any]] = []
    families = predictions["v2_family"].astype(str).to_numpy()
    classes = predictions["label_multi"].astype(str).to_numpy()
    for evaluation, (labels, keep) in evaluation_targets.items():
        values = xgb_model._binary_metric_values(labels[keep], scores[keep], threshold)
        fp_mask = keep & (predicted == 1) & (labels == 0)
        metric_rows.append(
            {
                "training_variant": training_variant,
                "evaluation": evaluation,
                "seed": seed,
                "effectif": int(np.count_nonzero(keep)),
                **values,
                "false_negatives": int(values["attack_count"] - values["true_positives"]),
                "fp_signaled": int(np.count_nonzero(fp_mask & signals)),
                "fp_signal_share": (
                    float(np.count_nonzero(fp_mask & signals) / np.count_nonzero(fp_mask))
                    if np.any(fp_mask)
                    else 0.0
                ),
            }
        )
        for group_name, group_values in (
            ("v2_family", families),
            ("label_orig_multi", classes),
        ):
            for label in sorted(set(group_values[keep])):
                group_mask = keep & (group_values == label)
                positive_mask = group_mask & (labels == 1)
                count = int(np.count_nonzero(positive_mask))
                recall = (
                    float(np.mean(predicted[positive_mask] == 1))
                    if count
                    else float("nan")
                )
                recall_rows.append(
                    {
                        "training_variant": training_variant,
                        "evaluation": evaluation,
                        "seed": seed,
                        "group_type": group_name,
                        "group": label,
                        "positive_support": count,
                        "recall": recall,
                    }
                )
    return metric_rows, recall_rows


def _baseline_evaluations(config: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pred_dir = xgb_model._configured_path(config, "legacy_prediction_dir")
    report_dir = xgb_model._configured_path(config, "legacy_report_dir")
    thresholds = json.loads((report_dir / "thresholds_bin.json").read_text(encoding="utf-8"))
    threshold = float(thresholds["threshold_fpr_1pct"])
    context = _evaluation_context(config, "v2")
    metrics: list[dict[str, Any]] = []
    recalls: list[dict[str, Any]] = []
    for seed in config["seeds"]:
        predictions = _read_predictions(
            pred_dir / f"xgb_bin_seed{int(seed)}.parquet",
            context,
            int(seed),
        )
        rows, recall = _evaluate_predictions(
            predictions,
            threshold,
            int(seed),
            _V2_BASELINE,
        )
        metrics.extend(rows)
        recalls.extend(recall)
    return metrics, recalls


def _variant_evaluations(
    config: dict[str, Any],
    variant: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    report_dir = xgb_model._configured_path(config, "report_dir")
    prediction_dir = xgb_model._configured_path(config, "prediction_dir")
    thresholds = json.loads(_threshold_path(config, variant).read_text(encoding="utf-8"))
    threshold = float(thresholds["threshold_fpr_1pct"])
    context = _evaluation_context(config, "v3")
    metrics: list[dict[str, Any]] = []
    recalls: list[dict[str, Any]] = []
    for seed in config["seeds"]:
        predictions = _read_predictions(
            _seed_prediction_path(config, variant, int(seed)),
            context,
            int(seed),
        )
        rows, recall = _evaluate_predictions(
            predictions,
            threshold,
            int(seed),
            f"V3 {variant}",
        )
        metrics.extend(rows)
        recalls.extend(recall)
    return metrics, recalls


def _aggregate_metrics(metrics: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (training_variant, evaluation), group in metrics.groupby(
        ["training_variant", "evaluation"], sort=False
    ):
        row: dict[str, Any] = {
            "training_variant": training_variant,
            "evaluation": evaluation,
            "false_positives_min": int(group["false_positives"].min()),
            "false_positives_max": int(group["false_positives"].max()),
        }
        for column in (
            "pr_auc",
            "tpr_at_fpr_1pct",
            "false_positives",
            "false_negatives",
            "tpr_at_threshold",
            "fpr_at_threshold",
            "fp_signal_share",
        ):
            values = pd.to_numeric(group[column], errors="coerce").dropna()
            row[column + "_mean"] = float(values.mean()) if len(values) else float("nan")
            row[column + "_std"] = (
                float(values.std(ddof=1)) if len(values) > 1 else 0.0
            )
            row[column + "_median"] = float(values.median()) if len(values) else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def _format_cell(row: pd.Series) -> str:
    def summary(name: str, digits: int = 4) -> str:
        return (
            f"{row[name + '_mean']:.{digits}f} ± {row[name + '_std']:.{digits}f} / "
            f"{row[name + '_median']:.{digits}f}"
        )

    return (
        f"PR-AUC {summary('pr_auc')}<br>"
        f"TPR@FPR≤1% {summary('tpr_at_fpr_1pct')}<br>"
        f"FP {summary('false_positives', 1)} (min–max "
        f"{int(row['false_positives_min'])}–{int(row['false_positives_max'])})<br>"
        f"FN {summary('false_negatives', 1)}<br>"
        f"TPR/FPR seuil {summary('tpr_at_threshold')} / "
        f"{summary('fpr_at_threshold')}<br>"
        f"FP signalés {summary('fp_signal_share', 3)}"
    )


def _write_progress(
    config: dict[str, Any],
    variant: str,
    aggregate: pd.DataFrame,
    threshold: dict[str, Any],
) -> None:
    path = xgb_model._configured_path(config, "progress_report_v3")
    marker = f"## V3 {variant} — résultats intermédiaires"
    if path.exists() and marker in path.read_text(encoding="utf-8"):
        return
    lines = [
        marker,
        "",
        f"- Seuil OOF FPR 1 % : {threshold['threshold_fpr_1pct']:.8f} "
        f"(FPR OOF observée {threshold['achieved_fpr']:.4%}); 199 rounds fixes.",
        "",
        "| Vérité test | PR-AUC (moyenne ± écart-type / médiane) | FP min–max |",
        "|---|---:|---:|",
    ]
    for evaluation in EVALUATIONS:
        row = aggregate.loc[aggregate["evaluation"].eq(evaluation)].iloc[0]
        lines.append(
            f"| {evaluation} | {_format_cell(row)} | "
            f"{int(row['false_positives_min'])}–{int(row['false_positives_max'])} |"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        if not path.stat().st_size:
            stream.write("# Résultats intermédiaires XGBoost V3\n\n")
        stream.write("\n".join(lines))
        stream.flush()


def _write_final_report(
    config: dict[str, Any],
    metrics: pd.DataFrame,
    recalls: pd.DataFrame,
    thresholds: dict[str, dict[str, Any]],
) -> dict[str, str]:
    report_path = xgb_model._configured_path(config, "summary_report_v3")
    metrics_path = xgb_model._configured_path(config, "summary_csv_v3")
    recall_path = xgb_model._configured_path(config, "recall_csv_v3")
    for path in (report_path, metrics_path, recall_path):
        if path.exists():
            raise FileExistsError(f"Refus d’écraser le rapport ou CSV existant : {path}.")
    aggregate = _aggregate_metrics(metrics)
    metric_cells = aggregate.pivot(
        index="training_variant", columns="evaluation"
    )
    training_rows = [_V2_BASELINE, "V3 b0", "V3 v2a", "V3 v2b"]
    lines = [
        "# Évaluation XGBoost binaire — split V3",
        "",
        "- Essai 24 appris sur les plis V2; hyperparamètres fixes, 199 rounds, sans early stopping.",
        "- Graines 42–51; les scores sont présentés moyenne ± écart-type / médiane.",
        "- Le V2 d’origine est un point de comparaison sur un split différent; aucune prédiction V2 n’a été recalculée.",
        "- La vérité « v2 — Attempted comptés » définit une attaque par `label_v2_bin == 1` ou `attempted`; "
        "« Attempted exclus » retire les lignes Attempted de l’évaluation.",
        "",
        "## Comparaison 4 × 3",
        "",
        "| Entraînement | Test labels d’origine | Test v2 Attempted comptés | Test v2 Attempted exclus |",
        "|---|---|---|---|",
    ]
    for training_variant in training_rows:
        cells = []
        for evaluation in EVALUATIONS:
            row = aggregate.loc[
                aggregate["training_variant"].eq(training_variant)
                & aggregate["evaluation"].eq(evaluation)
            ]
            cells.append(_format_cell(row.iloc[0]) if not row.empty else "n.d.")
        lines.append(f"| {training_variant} | " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "Chaque mesure est agrégée sur les dix graines; FP signalés désigne la part des FP "
            "dont le flux est divergent ou Attempted selon l’audit.",
            "",
            "## Rappel des seuils hors-pli",
            "",
            "| Variante | Seuil FPR 1 % | FPR hors-pli atteinte | OOF lignes |",
            "|---|---:|---:|---:|",
        ]
    )
    for variant in VARIANTS:
        item = thresholds[variant]
        lines.append(
            f"| V3 {variant} | {item['threshold_fpr_1pct']:.8f} | "
            f"{item['achieved_fpr']:.4%} | {item['oof_rows']:,} |"
        )
    lines.extend(
        [
            "",
            "## Recall par famille v2 et classe d’origine",
            "",
            "Les supports sont les flux positifs dans chaque groupe; le tableau donne la moyenne ± "
            "écart-type / médiane du recall par graine.",
            "",
            "| Entraînement | Vérité test | Type | Groupe | Support | Recall |",
            "|---|---|---|---|---:|---:|",
        ]
    )
    recall_agg = (
        recalls.groupby(
            ["training_variant", "evaluation", "group_type", "group"],
            sort=True,
            dropna=False,
        )
        .agg(
            positive_support=("positive_support", "first"),
            mean=("recall", "mean"),
            std=("recall", "std"),
            median=("recall", "median"),
        )
        .reset_index()
    )
    for row in recall_agg.itertuples(index=False):
        recall_text = (
            f"{row.mean:.4f} ± {0.0 if pd.isna(row.std) else row.std:.4f} / {row.median:.4f}"
            if pd.notna(row.mean)
            else "n.d."
        )
        lines.append(
            f"| {row.training_variant} | {row.evaluation} | {row.group_type} | "
            f"{row.group} | {row.positive_support:,} | {recall_text} |"
        )
    lines.extend(
        [
            "",
            "## Limites",
            "",
            "- Les hyperparamètres ont été choisis sur les plis V2. Le test V3 ne recouvre pas V2-train "
            "(0 flux V3-test issus de V2-train), tandis que 118 497 flux V3-train viennent de V2-test; "
            "la comparaison entre versions de split n’est donc pas indépendante.",
            "- Les règles d’audit sont heuristiques issues d’un article et ne constituent pas une vérité terrain.",
            "- v2a utilise toutes les lignes avec les labels corrigés; v2b retire les Attempted du train. "
            "La comparaison isole l’effet du retrait des Attempted à paramètres et rounds identiques.",
            "- Les 199 rounds sont fixes, sans early stopping ni nouvelle recherche d’hyperparamètres; "
            "les seuils sont recalibrés sur les prédictions hors-pli V3 de chaque variante.",
            "- Le split V3 reste différent du §5.1 du guide, qui décrit un split par segments de classe.",
            "- Évaluation de laboratoire sur CIC-IDS2017; les résultats ne garantissent pas la généralisation "
            "à un trafic de production.",
            "",
            f"Métriques par graine/scénario : `{metrics_path}`.",
            f"Recall par graine/famille et classe : `{recall_path}`.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(metrics_path, index=False, encoding="utf-8")
    recalls.to_csv(recall_path, index=False, encoding="utf-8")
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "report_path": str(report_path),
        "metrics_csv": str(metrics_path),
        "recall_csv": str(recall_path),
    }


def run_v3_variants(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Exécute b0, v2a, v2b en ordre, avec reprise par artefact existant."""
    base = xgb_model.load_xgboost_config() if config is None else config
    if base.get("data_variant", "v2") not in {"v2", "v3"}:
        raise ValueError("data_variant doit être v2 ou v3.")
    base = deepcopy(base)
    base["data_variant"] = "v3"
    project = _v3_config(base)
    final_paths = (
        xgb_model._configured_path(project, "summary_report_v3"),
        xgb_model._configured_path(project, "summary_csv_v3"),
        xgb_model._configured_path(project, "recall_csv_v3"),
    )
    existing = [path for path in final_paths if path.exists()]
    if existing:
        raise FileExistsError(
            "Refus d’écraser des sorties finales V3 existantes : "
            + ", ".join(str(path) for path in existing)
        )
    parameters, rounds = _load_parameters(project)
    train = xgb_model.load_split("train", project)
    test = xgb_model.load_split("test", project)
    if train.y_v2_bin is None or train.attempted is None or test.y_v2_bin is None:
        raise ValueError("labels_v2_all est requis pour les variantes V3.")
    thresholds: dict[str, dict[str, Any]] = {}
    all_metrics, all_recalls = _baseline_evaluations(project)
    completed: list[str] = []
    for variant in VARIANTS:
        threshold = _get_or_build_threshold(
            project,
            variant,
            train,
            parameters,
            rounds,
        )
        thresholds[variant] = threshold
        _train_variant(
            project,
            variant,
            train,
            test,
            parameters,
            rounds,
            float(threshold["threshold_fpr_1pct"]),
        )
        metric_rows, recall_rows = _variant_evaluations(project, variant)
        all_metrics.extend(metric_rows)
        all_recalls.extend(recall_rows)
        _write_progress(
            project,
            variant,
            _aggregate_metrics(pd.DataFrame(metric_rows)),
            threshold,
        )
        completed.append(variant)
        print(f"Résumé intermédiaire écrit pour V3 {variant}.")
        gc.collect()

    report_paths = _write_final_report(
        project,
        pd.DataFrame(all_metrics),
        pd.DataFrame(all_recalls),
        thresholds,
    )
    del train, test
    return {
        "completed_variants": completed,
        "thresholds": {
            variant: thresholds[variant]["threshold_fpr_1pct"]
            for variant in VARIANTS
        },
        **report_paths,
    }


if __name__ == "__main__":
    config = xgb_model.load_xgboost_config()
    config["data_variant"] = "v3"
    print(json.dumps(run_v3_variants(config), ensure_ascii=False, indent=2))
