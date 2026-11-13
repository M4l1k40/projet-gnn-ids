"""Affectation chronologique et diagnostics des blocs train, val, test et gap."""

from collections import Counter
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from src.utils.config import load_config

_BLOCKS = ("train", "val", "test", "gap")
_REQUIRED_INPUT_COLUMNS = (
    "day",
    "ts_end",
    "label_multi",
    "label_bin",
    "flow_id",
    "Flow Duration",
)
_GAP_MARGIN_SECONDS = 60.0


def _normalize_ratios(ratios: Mapping[str, float]) -> tuple[float, float, float]:
    validation_key = "validation" if "validation" in ratios else "val"
    required = ("train", validation_key, "test")
    missing = [key for key in required if key not in ratios]
    if missing:
        raise ValueError(f"Ratios manquants : {', '.join(missing)}.")
    values = tuple(float(ratios[key]) for key in required)
    if any(not np.isfinite(value) or value <= 0 for value in values):
        raise ValueError("Les ratios train/val/test doivent être positifs et finis.")
    if not np.isclose(sum(values), 1.0):
        raise ValueError("Les ratios train/val/test doivent totaliser 1.")
    return values


def _quantile_timestamp(values: np.ndarray, quantile: float, mode: str) -> float:
    if mode == "count":
        rank = max(0, min(len(values) - 1, int(np.ceil(len(values) * quantile)) - 1))
        return float(values[rank])
    if mode == "time":
        return float(values[0] + (values[-1] - values[0]) * quantile)
    raise ValueError("mode doit être 'count' ou 'time'.")


def assign_split(
    df: pd.DataFrame,
    ratios: Mapping[str, float],
    gap_minutes: float,
    mode: str = "count",
) -> tuple[pd.Series, dict[str, int]]:
    """Affecte chaque flux à un bloc chronologique ou marque sa ligne comme gap.

    En mode ``count``, les seuils sont déterminés par le rang des flux triés.
    En mode ``time``, ils sont déterminés par des quantiles du temps écoulé.
    Les valeurs retournées conservent l'index d'entrée et les lignes de gap
    restent marquées pour permettre leur diagnostic avant exclusion.
    """
    required = {"day", "ts_end"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError("Colonnes requises absentes : " + ", ".join(sorted(missing)))
    if mode not in {"count", "time"}:
        raise ValueError("mode doit être 'count' ou 'time'.")
    if not np.isfinite(gap_minutes) or gap_minutes < 0:
        raise ValueError("gap_minutes doit être positif ou nul et fini.")
    train_ratio, validation_ratio, _ = _normalize_ratios(ratios)
    gap_seconds = float(gap_minutes) * 60

    timestamps = pd.to_numeric(df["ts_end"], errors="coerce")
    invalid_timestamps = timestamps.isna() | ~np.isfinite(timestamps)
    if invalid_timestamps.any():
        raise ValueError(
            f"ts_end : {int(invalid_timestamps.sum())} valeur(s) absente(s) ou non finie(s)."
        )
    if df["day"].isna().any():
        raise ValueError(f"day : {int(df['day'].isna().sum())} valeur(s) manquante(s).")

    assigned = pd.Series("gap", index=df.index, dtype="string", name="split")
    lost_by_day: Counter[str] = Counter()
    for day, group in df.assign(_split_timestamp=timestamps).groupby(
        "day", sort=False, observed=True
    ):
        ordered = group.sort_values("_split_timestamp", kind="stable")
        values = ordered["_split_timestamp"].to_numpy(dtype=np.float64)
        if not len(values):
            continue
        t1 = _quantile_timestamp(values, train_ratio, mode)
        t2 = _quantile_timestamp(values, train_ratio + validation_ratio, mode)
        if t2 < t1:
            raise ValueError(f"Seuils chronologiques invalides pour {day}.")

        train_mask = values <= t1
        if gap_seconds == 0:
            val_mask = (values > t1) & (values <= t2)
            test_mask = values > t2
        else:
            val_mask = (values >= t1 + gap_seconds) & (values <= t2)
            test_mask = values >= t2 + gap_seconds

        labels = np.full(len(values), "gap", dtype=object)
        labels[train_mask] = "train"
        labels[val_mask] = "val"
        labels[test_mask] = "test"
        assigned.loc[ordered.index] = labels
        lost_by_day[str(day)] = int(np.count_nonzero(labels == "gap"))

    return assigned, dict(lost_by_day)


def _resolution_by_day(day: str) -> float:
    return 1.0 if day == "Monday" else 60.0


def _class_split_rows(
    frame: pd.DataFrame,
    min_flows_per_block: int,
    *,
    scope: str,
    analysis: str,
    label_column: str,
    label_mapper: Mapping[object, str] | None = None,
) -> tuple[list[dict[str, object]], dict[tuple[str, str], bool]]:
    if scope == "global":
        scopes: list[tuple[str, pd.DataFrame]] = [("global", frame)]
    else:
        scopes = [
            (str(day), group)
            for day, group in frame.groupby("day", sort=True, observed=True)
        ]

    rows: list[dict[str, object]] = []
    exploitability: dict[tuple[str, str], bool] = {}
    for day_name, scope_frame in scopes:
        labels = scope_frame[label_column]
        if label_mapper is not None:
            labels = labels.map(label_mapper)
        labels = labels.astype("string")
        for label in sorted(labels.dropna().unique().tolist()):
            label_mask = labels.eq(label)
            counts = {
                block: int((label_mask & scope_frame["split"].eq(block)).sum())
                for block in _BLOCKS
            }
            total = sum(counts.values())
            exploitable = all(
                counts[block] >= min_flows_per_block
                for block in ("train", "val", "test")
            )
            exploitability[(day_name, str(label))] = exploitable
            for block in _BLOCKS:
                count = counts[block]
                rows.append(
                    {
                        "analyse": analysis,
                        "portee": scope,
                        "jour": "" if scope == "global" else day_name,
                        "classe": str(label),
                        "bloc": block,
                        "effectif": count,
                        "pourcentage": 100.0 * count / total if total else 0.0,
                        "exploitable": exploitable,
                    }
                )
    return rows, exploitability


def _render_class_table(rows: list[dict[str, object]], scope: str) -> str:
    headers = [
        "Classe",
        "Train (n, %)",
        "Val (n, %)",
        "Test (n, %)",
        "Gap (n, %)",
        "Exploitable",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|---|---:|---:|---:|---:|:---:|",
    ]
    scoped_rows = [
        row
        for row in rows
        if row["analyse"] == "multiclasse"
        and (
            (scope == "global" and row["portee"] == "global")
            or (scope != "global" and row["portee"] == "jour" and row["jour"] == scope)
        )
    ]
    class_names = sorted({str(row["classe"]) for row in scoped_rows})
    for class_name in class_names:
        label_rows = {
            str(row["bloc"]): row
            for row in scoped_rows
            if row["classe"] == class_name
        }
        cells = [class_name]
        for block in _BLOCKS:
            row = label_rows[block]
            cells.append(f"{int(row['effectif'])} ({float(row['pourcentage']):.2f} %)")
        exploitable = bool(label_rows["train"]["exploitable"])
        cells.append("oui" if exploitable else "non")
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _non_exploitable_details(
    frame: pd.DataFrame,
    min_flows_per_block: int,
    *,
    label_column: str,
    label_mapper: Mapping[object, str] | None = None,
    label_name: str,
) -> list[str]:
    lines: list[str] = []
    starts = pd.to_datetime(
        frame["ts_end"].to_numpy(dtype=np.float64)
        - pd.to_numeric(frame["Flow Duration"]).to_numpy(dtype=np.float64) / 1e6,
        unit="s",
    )
    frame = frame.assign(_start_time=starts)
    scopes: list[tuple[str, pd.DataFrame]] = [("global", frame)]
    scopes.extend(
        (str(day), group)
        for day, group in frame.groupby("day", sort=True, observed=True)
    )
    for scope_name, scoped_frame in scopes:
        labels = scoped_frame[label_column]
        if label_mapper is not None:
            labels = labels.map(label_mapper)
        labels = labels.astype("string")
        for label in sorted(labels.dropna().unique().tolist()):
            class_rows = scoped_frame.loc[labels.eq(label)]
            counts = class_rows["split"].value_counts()
            if all(
                int(counts.get(block, 0)) >= min_flows_per_block
                for block in ("train", "val", "test")
            ):
                continue
            block_details: list[str] = []
            for block in _BLOCKS:
                block_rows = class_rows.loc[class_rows["split"].eq(block)]
                if block_rows.empty:
                    block_details.append(f"{block}: absent")
                else:
                    start_min = block_rows["_start_time"].min().strftime("%H:%M:%S")
                    start_max = block_rows["_start_time"].max().strftime("%H:%M:%S")
                    block_details.append(
                        f"{block}: {len(block_rows)} flux, {start_min}–{start_max}"
                    )
            lines.append(
                f"- {label_name} **{label}** ({scope_name}) — "
                + "; ".join(block_details)
                + "."
            )
    return lines


def run_split_diagnostics(
    config: dict[str, object] | None = None,
    *,
    input_path: str | Path | None = None,
    reports_dir: str | Path | None = None,
) -> tuple[Path, Path, pd.DataFrame]:
    """Produit gap_suggestion.md et les tableaux globaux et journaliers."""
    project_config = load_config() if config is None else config
    paths = project_config["paths"]
    split_config = project_config["split"]
    interim = Path(paths["interim"])
    source_path = Path(input_path) if input_path is not None else interim / "clean.parquet"
    if reports_dir is None:
        reports_dir = interim.resolve().parents[1] / "reports"
    reports_path = Path(reports_dir)
    reports_path.mkdir(parents=True, exist_ok=True)
    if not source_path.exists():
        raise FileNotFoundError(f"Parquet source introuvable : {source_path}.")

    frame = pd.read_parquet(source_path, columns=list(_REQUIRED_INPUT_COLUMNS))
    splits, gaps_by_day = assign_split(
        frame,
        ratios=split_config,
        gap_minutes=float(split_config["gap_minutes"]),
        mode=str(split_config.get("mode", "count")),
    )
    frame["split"] = splits
    minimum_flows = int(split_config["min_flows_per_block"])
    if minimum_flows < 1:
        raise ValueError("split.min_flows_per_block doit être supérieur à zéro.")

    duration_seconds = pd.to_numeric(frame["Flow Duration"], errors="coerce") / 1e6
    if duration_seconds.isna().any() or not np.isfinite(duration_seconds).all():
        raise ValueError(
            "Flow Duration contient "
            f"{int(duration_seconds.isna().sum())} valeur(s) absente(s) ou non finie(s)."
        )
    gap_rows: list[dict[str, object]] = []
    for day, indexes in frame.groupby("day", sort=True, observed=True).groups.items():
        day_name = str(day)
        day_durations = duration_seconds.loc[indexes]
        maximum = float(day_durations.max())
        resolution = _resolution_by_day(day_name)
        suggestion = maximum + resolution + _GAP_MARGIN_SECONDS
        gap_rows.append(
            {
                "day": day_name,
                "max_duration_seconds": maximum,
                "resolution_seconds": resolution,
                "current_gap_seconds": float(split_config["gap_minutes"]) * 60,
                "margin_seconds": _GAP_MARGIN_SECONDS,
                "suggested_gap_seconds": suggestion,
                "lost_in_gap": gaps_by_day.get(day_name, 0),
            }
        )
    gap_csv = pd.DataFrame(gap_rows)
    max_duration = max(float(row["max_duration_seconds"]) for row in gap_rows)
    max_resolution = max(float(row["resolution_seconds"]) for row in gap_rows)
    suggested_overall = max_duration + max_resolution + _GAP_MARGIN_SECONDS
    gap_report = [
        "# Suggestion de durée de gap",
        "",
        f"- Mode de split : `{split_config.get('mode', 'count')}`.",
        f"- Gap actuel : {float(split_config['gap_minutes']) * 60:.0f} s "
        f"({float(split_config['gap_minutes']):g} min).",
        f"- Marge appliquée pour la suggestion : {_GAP_MARGIN_SECONDS:.0f} s "
        "(hypothèse de diagnostic, soit une minute supplémentaire).",
        f"- Suggestion globale conservatrice : {suggested_overall:.0f} s "
        f"({suggested_overall / 60:.2f} min).",
        "",
        "| Jour | Durée max Flow Duration (s) | Résolution ts_end (s) | Gap actuel (s) | Marge (s) | Gap minimal suggéré (s) | Flux marqués gap |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in gap_rows:
        gap_report.append(
            f"| {row['day']} | {row['max_duration_seconds']:.6f} | "
            f"{row['resolution_seconds']:.0f} | {row['current_gap_seconds']:.0f} | "
            f"{row['margin_seconds']:.0f} | {row['suggested_gap_seconds']:.6f} | "
            f"{row['lost_in_gap']} |"
        )
    gap_report_path = reports_path / "gap_suggestion.md"
    gap_report_path.write_text("\n".join(gap_report) + "\n", encoding="utf-8")

    binary_mapping = {0: "BENIGN", 1: "ATTACK"}
    global_multi, exploitable_multi = _class_split_rows(
        frame,
        minimum_flows,
        scope="global",
        analysis="multiclasse",
        label_column="label_multi",
    )
    daily_multi, _ = _class_split_rows(
        frame,
        minimum_flows,
        scope="jour",
        analysis="multiclasse",
        label_column="label_multi",
    )
    global_binary, exploitable_binary = _class_split_rows(
        frame,
        minimum_flows,
        scope="global",
        analysis="binaire",
        label_column="label_bin",
        label_mapper=binary_mapping,
    )
    daily_binary, _ = _class_split_rows(
        frame,
        minimum_flows,
        scope="jour",
        analysis="binaire",
        label_column="label_bin",
        label_mapper=binary_mapping,
    )
    table_rows = global_multi + daily_multi + global_binary + daily_binary
    table = pd.DataFrame(table_rows)
    csv_path = reports_path / "class_by_split.csv"
    table.to_csv(csv_path, index=False, encoding="utf-8")

    non_exploitable = _non_exploitable_details(
        frame,
        minimum_flows,
        label_column="label_multi",
        label_name="Multiclasse",
    )
    binary_non_exploitable = _non_exploitable_details(
        frame,
        minimum_flows,
        label_column="label_bin",
        label_mapper=binary_mapping,
        label_name="Binaire",
    )
    report_lines = [
        "# Répartition des classes par bloc chronologique",
        "",
        f"- Mode : `{split_config.get('mode', 'count')}`.",
        f"- Ratios : train {float(split_config['train']):.0%}, "
        f"val {float(split_config['validation']):.0%}, "
        f"test {float(split_config['test']):.0%}.",
        f"- Gap : {float(split_config['gap_minutes']):g} minute(s).",
        f"- Seuil d’exploitabilité : au moins {minimum_flows} flux dans chacun "
        "des blocs train, val et test.",
        "",
        "Les pourcentages sont calculés sur l’effectif total de chaque classe "
        "dans la portée concernée. Les flux du bloc gap restent visibles et les "
        "classes ne sont ni supprimées ni regroupées dans l’analyse multiclasse.",
        "",
        "## Vue globale — multiclasse",
        "",
        _render_class_table(global_multi, "global"),
        "",
        "## Vue par jour — multiclasse",
        "",
    ]
    for day in sorted(frame["day"].astype(str).unique()):
        report_lines.extend(
            [
                f"### {day}",
                "",
                _render_class_table(daily_multi, day),
                "",
            ]
        )
    report_lines.extend(
        [
            "## Exploitabilité binaire",
            "",
            f"- Classes exploitables : {sum(exploitable_binary.values())}/"
            f"{len(exploitable_binary)} ({', '.join(label for (_, label), ok in exploitable_binary.items() if ok) or 'aucune'}).",
            "",
            "## Classes multiclasse non exploitables et heures observées",
            "",
        ]
    )
    report_lines.extend(non_exploitable or ["Toutes les classes sont exploitables."])
    report_lines.extend(
        [
            "",
            "## Classes binaires non exploitables et heures observées",
            "",
        ]
    )
    report_lines.extend(
        binary_non_exploitable or ["Toutes les classes binaires sont exploitables."]
    )
    report_path = reports_path / "class_by_split.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print("Tableau global des classes multiclasse par bloc :")
    print(_render_class_table(global_multi, "global"))
    print(
        "Classes exploitables en binaire : "
        f"{sum(exploitable_binary.values())}/{len(exploitable_binary)}."
    )
    print(
        "Classes exploitables en multiclasse : "
        f"{sum(exploitable_multi.values())}/{len(exploitable_multi)}."
    )
    print(f"Flux perdus dans les gaps par jour : {gaps_by_day}.")
    return gap_report_path, report_path, table


if __name__ == "__main__":
    gap_report, class_report, class_table = run_split_diagnostics()
    print(f"Rapport de gap : {gap_report}")
    print(f"Rapport de classes : {class_report}")
    print(f"CSV des classes : {class_report.with_suffix('.csv')}")
