"""Analyse TreeSHAP du modèle binaire V3 b0, graine 42."""

import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xgboost as xgb

from src.models import xgb as xgb_model

_REQUIRED_FEATURES = (
    "Fwd Header Length",
    "Total Fwd Packets",
    "min_seg_size_forward",
    "Init_Win_bytes_forward",
    "Bwd Packet Length Min",
    "Fwd Packet Length Min",
)


def _sample_indexes(
    labels: np.ndarray,
    benign_limit: int,
    attack_limit: int,
    seed: int,
) -> tuple[np.ndarray, dict[str, int]]:
    values = np.asarray(labels).astype(str)
    rng = np.random.default_rng(seed)
    selected: list[np.ndarray] = []
    counts: dict[str, int] = {}
    for label in sorted(set(values)):
        indexes = np.flatnonzero(values == label)
        limit = benign_limit if label == "BENIGN" else attack_limit
        count = min(len(indexes), limit)
        if count:
            selected.append(rng.choice(indexes, size=count, replace=False))
            counts[label] = count
    result = np.concatenate(selected).astype(np.int64)
    rng.shuffle(result)
    return result, counts


def _direction_rows(
    values: np.ndarray,
    shap_values: np.ndarray,
    feature_names: list[str],
    top_features: list[str],
) -> list[dict[str, Any]]:
    rows = []
    for feature in top_features:
        index = feature_names.index(feature)
        column = np.asarray(values[:, index], dtype=np.float64)
        contribution = np.asarray(shap_values[:, index], dtype=np.float64)
        ranks = pd.Series(column).rank(method="average", pct=True).to_numpy()
        for label, quantile in (("bas (Q10)", 0.10), ("médian (Q50)", 0.50), ("haut (Q90)", 0.90)):
            mask = np.abs(ranks - quantile) <= 0.05
            if not mask.any():
                nearest = np.argsort(np.abs(ranks - quantile))[: max(1, len(ranks) // 100)]
                mask[nearest] = True
            rows.append(
                {
                    "feature": feature,
                    "quantile": label,
                    "quantile_value": float(np.quantile(column, quantile)),
                    "sample_rows": int(mask.sum()),
                    "mean_feature_value": float(np.mean(column[mask])),
                    "mean_shap_log_odds": float(np.mean(contribution[mask])),
                }
            )
    return rows


def _output_paths(config: dict[str, Any]) -> dict[str, Path]:
    return {
        "report": xgb_model._configured_path(config, "shap_report_v3"),
        "global": xgb_model._configured_path(config, "shap_global_csv_v3"),
        "classes": xgb_model._configured_path(config, "shap_class_csv_v3"),
        "direction": xgb_model._configured_path(config, "shap_direction_csv_v3"),
        "gain": xgb_model._configured_path(config, "shap_gain_csv_v3"),
        "figures": xgb_model._configured_path(config, "shap_figure_dir"),
    }


def _assert_new_outputs(paths: dict[str, Path]) -> list[Path]:
    figures = [
        paths["figures"] / "xgb_v3_b0_seed42_shap_global.png",
        paths["figures"] / "xgb_v3_b0_seed42_shap_by_class.png",
        paths["figures"] / "xgb_v3_b0_seed42_shap_dependence.png",
    ]
    conflicts = [
        path
        for path in [*paths.values(), *figures]
        if path.exists() and path.is_file()
    ]
    if conflicts:
        raise FileExistsError(
            "Refus d’écraser des sorties SHAP existantes : "
            + ", ".join(str(path) for path in conflicts)
        )
    return figures


def _cross_check(
    booster: xgb.Booster,
    sample: np.ndarray,
    feature_names: list[str],
    expected: np.ndarray,
    rows: int,
) -> dict[str, Any]:
    import shap

    explainer = shap.TreeExplainer(booster, model_output="raw")
    values = np.asarray(
        explainer.shap_values(
            pd.DataFrame(sample[:rows], columns=feature_names)
        ),
        dtype=np.float64,
    )
    target = np.asarray(expected[:rows, :-1], dtype=np.float64)
    if values.shape != target.shape:
        raise ValueError(
            f"TreeExplainer a retourné {values.shape}, attendu {target.shape}."
        )
    difference = np.abs(values - target)
    maximum = float(difference.max(initial=0.0))
    mean = float(difference.mean())
    if not np.allclose(values, target, rtol=2e-4, atol=2e-5):
        raise ValueError(
            f"TreeSHAP direct et shap.TreeExplainer divergent "
            f"(max={maximum:.6g}, moyen={mean:.6g})."
        )
    return {
        "method": "shap.TreeExplainer(model_output='raw')",
        "rows": rows,
        "max_abs_difference": maximum,
        "mean_abs_difference": mean,
    }


def _figures(
    paths: dict[str, Path],
    global_table: pd.DataFrame,
    class_table: pd.DataFrame,
    x_sample: np.ndarray,
    shap_values: np.ndarray,
    feature_names: list[str],
    top_features: list[str],
    seed: int,
    dependence_max_rows: int,
) -> None:
    paths["figures"].mkdir(parents=True, exist_ok=True)
    global_plot = global_table.head(20).sort_values("mean_abs_shap")
    figure, axis = plt.subplots(figsize=(11, 8))
    axis.barh(global_plot["feature"], global_plot["mean_abs_shap"], color="#4472C4")
    axis.set_title("TreeSHAP global — V3 b0, graine 42")
    axis.set_xlabel("Moyenne |SHAP| (log-odds)")
    figure.tight_layout()
    figure.savefig(
        paths["figures"] / "xgb_v3_b0_seed42_shap_global.png",
        dpi=180,
    )
    plt.close(figure)

    classes = sorted(class_table["label_multi"].unique())
    columns = 3
    rows = math.ceil(len(classes) / columns)
    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(18, max(4, rows * 3.2)),
        squeeze=False,
    )
    for axis, label in zip(axes.flat, classes):
        subset = (
            class_table.loc[class_table["label_multi"].eq(label)]
            .nlargest(10, "mean_abs_shap")
            .sort_values("mean_abs_shap")
        )
        axis.barh(subset["feature"], subset["mean_abs_shap"], color="#70AD47")
        axis.set_title(label)
        axis.set_xlabel("Moyenne |SHAP|")
        axis.tick_params(axis="y", labelsize=7)
    for axis in axes.flat[len(classes) :]:
        axis.remove()
    figure.suptitle("TreeSHAP par classe d’attaque — V3 b0, graine 42")
    figure.tight_layout()
    figure.savefig(
        paths["figures"] / "xgb_v3_b0_seed42_shap_by_class.png",
        dpi=180,
    )
    plt.close(figure)

    sample_count = min(
        int(x_sample.shape[0]),
        int(max(1, dependence_max_rows)),
    )
    rng = np.random.default_rng(seed)
    indexes = np.sort(rng.choice(x_sample.shape[0], size=sample_count, replace=False))
    figure, axes = plt.subplots(1, len(top_features), figsize=(6 * len(top_features), 5))
    for axis, feature in zip(axes, top_features):
        index = feature_names.index(feature)
        points = axis.scatter(
            x_sample[indexes, index],
            shap_values[indexes, index],
            c=x_sample[indexes, index],
            cmap="viridis",
            s=8,
            alpha=0.55,
            rasterized=True,
        )
        axis.set_title(feature)
        axis.set_xlabel("Valeur de feature")
        axis.set_ylabel("SHAP (log-odds)")
        figure.colorbar(points, ax=axis, label="Valeur")
    figure.suptitle("Dépendances TreeSHAP — trois premières features")
    figure.tight_layout()
    figure.savefig(
        paths["figures"] / "xgb_v3_b0_seed42_shap_dependence.png",
        dpi=180,
    )
    plt.close(figure)


def run_shap(config: dict[str, Any] | None = None) -> dict[str, str]:
    """Calcule les explications TreeSHAP sur l’échantillon stratifié du test V3."""
    project = xgb_model.load_xgboost_config() if config is None else config
    if project.get("data_variant", "v2") not in {"v2", "v3"}:
        raise ValueError("data_variant doit être v2 ou v3.")
    project = dict(project)
    project["data_variant"] = "v3"
    paths = _output_paths(project)
    figures = _assert_new_outputs(paths)

    settings = project["shap_v3"]
    seed = int(settings["seed"])
    split = xgb_model.load_split("test", project)
    sample_indexes, sample_counts = _sample_indexes(
        split.y_multi,
        int(settings["benign_sample"]),
        int(settings["attack_sample_per_class"]),
        seed,
    )
    if len(sample_indexes) == 0:
        raise ValueError("L’échantillon TreeSHAP est vide.")
    feature_names = split.feature_names
    x_sample = split.X[sample_indexes]
    labels = split.y_multi[sample_indexes].astype(str)
    flow_ids = split.flow_ids[sample_indexes].astype(str)
    matrix = xgb.DMatrix(
        x_sample,
        feature_names=feature_names,
        nthread=int(project["fixed"]["n_jobs"]),
    )

    model_path = xgb_model._configured_path(project, "model_dir_v3") / (
        "xgb_bin_b0_seed42_v3.json"
    )
    gain_path = xgb_model._configured_path(project, "report_dir_v3") / (
        "importance_bin_b0_seed42_v3.csv"
    )
    if not model_path.exists() or not gain_path.exists():
        raise FileNotFoundError(f"Modèle ou importance V3 b0 graine 42 absent : {model_path}.")
    booster = xgb.Booster()
    booster.load_model(model_path)
    contributions = np.asarray(
        booster.predict(matrix, pred_contribs=True),
        dtype=np.float64,
    )
    if (
        contributions.shape != (len(sample_indexes), len(feature_names) + 1)
        or not np.isfinite(contributions).all()
    ):
        raise ValueError("La sortie pred_contribs n’a pas les dimensions TreeSHAP attendues.")

    cross_check_rows = min(
        int(settings["cross_check_rows"]),
        len(sample_indexes),
    )
    cross_check = _cross_check(
        booster,
        x_sample,
        feature_names,
        contributions,
        cross_check_rows,
    )
    shap_values = contributions[:, :-1]
    global_table = pd.DataFrame(
        {
            "feature": feature_names,
            "mean_abs_shap": np.mean(np.abs(shap_values), axis=0),
            "mean_shap": np.mean(shap_values, axis=0),
        }
    ).sort_values("mean_abs_shap", ascending=False, ignore_index=True)
    global_table.insert(0, "rank", np.arange(1, len(global_table) + 1))
    global_table["sample_rows"] = len(sample_indexes)

    class_rows = []
    for label in sorted(set(labels) - {"BENIGN"}):
        mask = labels == label
        values = np.mean(np.abs(shap_values[mask]), axis=0)
        order = np.argsort(values)[::-1][:10]
        for rank, index in enumerate(order, start=1):
            class_rows.append(
                {
                    "label_multi": label,
                    "support": int(mask.sum()),
                    "rank": rank,
                    "feature": feature_names[int(index)],
                    "mean_abs_shap": float(values[index]),
                    "mean_shap": float(np.mean(shap_values[mask, index])),
                }
            )
    class_table = pd.DataFrame(class_rows)
    top_features = global_table.head(10)["feature"].tolist()
    direction_table = pd.DataFrame(
        _direction_rows(x_sample, shap_values, feature_names, top_features)
    )

    gain = pd.read_csv(gain_path)
    if not {"feature", "gain"}.issubset(gain.columns):
        raise ValueError(f"Colonnes gain/features absentes de {gain_path}.")
    gain = gain.groupby("feature", as_index=False)["gain"].mean()
    gain_table = global_table[["feature", "rank", "mean_abs_shap"]].merge(
        gain,
        on="feature",
        how="left",
        validate="one_to_one",
    )
    gain_table["gain"] = gain_table["gain"].fillna(0.0)
    gain_table["gain_rank"] = gain_table["gain"].rank(
        method="min", ascending=False
    ).astype(int)
    gain_table["shap_rank"] = gain_table["rank"]

    top_three = global_table.head(3)["feature"].tolist()
    _figures(
        paths,
        global_table,
        class_table,
        x_sample,
        shap_values,
        feature_names,
        top_three,
        seed,
        int(settings["dependence_max_rows"]),
    )

    report_lines = [
        "# TreeSHAP — XGBoost V3 b0, graine 42",
        "",
        "- Les contributions sont calculées par `Booster.predict(pred_contribs=True)` en log-odds; la dernière colonne de sortie est la valeur de base et n’est pas incluse dans les classements.",
        f"- Échantillonnage stratifié reproductible (graine {seed}) : "
        + ", ".join(f"{label}={count:,}" for label, count in sorted(sample_counts.items()))
        + f"; total {len(sample_indexes):,}.",
        f"- Contrôle croisé : {cross_check['method']}, {cross_check['rows']} lignes, "
        f"écart absolu max {cross_check['max_abs_difference']:.3g}, "
        f"moyen {cross_check['mean_abs_difference']:.3g}.",
        "",
        "## Top 20 global par moyenne de |SHAP|",
        "",
        "| Rang | Feature | Moyenne |SHAP| | SHAP moyen (log-odds) |",
        "|---:|---|---:|---:|",
    ]
    report_lines.extend(
        f"| {row.rank} | {row.feature} | {row.mean_abs_shap:.6g} | {row.mean_shap:.6g} |"
        for row in global_table.head(20).itertuples(index=False)
    )
    report_lines.extend(
        [
            "",
            "## Top 10 par classe d’attaque",
            "",
            "| Classe | Support échantillonné | Rang | Feature | Moyenne |SHAP| | SHAP moyen |",
            "|---|---:|---:|---|---:|---:|",
        ]
    )
    report_lines.extend(
        f"| {row.label_multi} | {row.support:,} | {row.rank} | {row.feature} | "
        f"{row.mean_abs_shap:.6g} | {row.mean_shap:.6g} |"
        for row in class_table.itertuples(index=False)
    )
    report_lines.extend(
        [
            "",
            "## Sens de l’effet selon la valeur",
            "",
            "Les contributions moyennes sont estimées dans des bandes de rang percentile ±5 points autour de Q10, Q50 et Q90; les ex æquo restent regroupés.",
            "",
            "| Feature | Bande | Valeur au quantile | Valeur moyenne échantillon | SHAP moyen log-odds | n |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    report_lines.extend(
        f"| {row.feature} | {row.quantile} | {row.quantile_value:.6g} | "
        f"{row.mean_feature_value:.6g} | {row.mean_shap_log_odds:.6g} | {row.sample_rows:,} |"
        for row in direction_table.itertuples(index=False)
    )
    report_lines.extend(
        [
            "",
            "## Gain contre TreeSHAP",
            "",
            "| Feature | Rang gain | Rang |SHAP| | Gain | Moyenne |SHAP| |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    rank_by_feature = gain_table.set_index("feature")
    for row in global_table.head(20).itertuples(index=False):
        other = rank_by_feature.loc[row.feature]
        report_lines.append(
            f"| {row.feature} | {int(other['gain_rank'])} | {int(other['shap_rank'])} | "
            f"{other['gain']:.6g} | {other['mean_abs_shap']:.6g} |"
        )
    report_lines.extend(
        [
            "",
            "### Features surveillées",
            "",
            "| Feature | Rang gain | Rang SHAP |",
            "|---|---:|---:|",
        ]
    )
    for feature in _REQUIRED_FEATURES:
        if feature in rank_by_feature.index:
            row = rank_by_feature.loc[feature]
            report_lines.append(
                f"| {feature} | {int(row['gain_rank'])} | {int(row['shap_rank'])} |"
            )
        else:
            report_lines.append(f"| {feature} | absent | absent |")
    report_lines.extend(
        [
            "",
            "## Limites",
            "",
            "- Les labels d’origine CIC-IDS2017 contiennent du bruit et des divergences d’audit; les explications décrivent le modèle entraîné sur ces labels, pas une vérité réseau vérifiée.",
            "- Des features corrélées peuvent se partager ou se substituer l’importance; les rangs SHAP ne démontrent pas une contribution unique.",
            "- SHAP décrit la contribution à la sortie du modèle et n’établit aucune causalité.",
            "",
            "CSV global : "
            f"[{paths['global'].name}](./{paths['global'].name}); CSV par classe : "
            f"[{paths['classes'].name}](./{paths['classes'].name}); sens de l’effet : "
            f"[{paths['direction'].name}](./{paths['direction'].name}); comparaison gain/SHAP : "
            f"[{paths['gain'].name}](./{paths['gain'].name}).",
            "",
            "Figures : [importance globale](./figures/xgb_v3_b0_seed42_shap_global.png), "
            "[par classe](./figures/xgb_v3_b0_seed42_shap_by_class.png) et "
            "[dépendances](./figures/xgb_v3_b0_seed42_shap_dependence.png).",
        ]
    )

    outputs = {
        "global": global_table,
        "classes": class_table,
        "direction": direction_table,
        "gain": gain_table,
    }
    for key in ("global", "classes", "direction", "gain"):
        paths[key].parent.mkdir(parents=True, exist_ok=True)
        outputs[key].to_csv(paths[key], index=False, encoding="utf-8")
    paths["report"].write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )
    del split, matrix, booster
    return {
        "report_path": str(paths["report"]),
        "global_csv": str(paths["global"]),
        "class_csv": str(paths["classes"]),
        "direction_csv": str(paths["direction"]),
        "gain_csv": str(paths["gain"]),
        "global_figure": str(figures[0]),
        "class_figure": str(figures[1]),
        "dependence_figure": str(figures[2]),
    }


if __name__ == "__main__":
    print(json.dumps(run_shap(), ensure_ascii=False, indent=2))
