"""Correction des horodatages CIC-IDS2017 et calcul des fins de flux."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from src.data.schema import validate_schema
from src.utils.config import load_config

_JOURS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")
_ROW_GROUP_SIZE = 50_000


@dataclass(frozen=True)
class TimestampDiagnostics:
    """Comptages associés au parsing et au calcul de ts_end."""

    parse_failures: dict[str, int]
    weekday_mismatches: int
    nonpositive_durations: dict[str, int]


@dataclass(frozen=True)
class AttackWindowDiagnostics:
    """Comparaison des classes observées avec les plages configurées."""

    rows: list[dict[str, Any]]
    classes_missing_from_data: list[str]
    classes_missing_from_windows: list[str]


def load_attack_windows(path: str | Path | None = None) -> dict[str, Any]:
    """Charge et vérifie le document des plages d’attaque."""
    config_path = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parents[2]
        / "configs"
        / "attack_windows.yaml"
    )
    with config_path.open(encoding="utf-8") as config_file:
        attack_config = yaml.safe_load(config_file)
    if not isinstance(attack_config, dict):
        raise ValueError(f"Configuration de plages invalide dans {config_path}.")
    if not isinstance(attack_config.get("windows"), dict):
        raise ValueError(f"Clé windows invalide dans {config_path}.")
    if not isinstance(attack_config.get("tolerance_minutes"), (int, float)):
        raise ValueError(f"Clé tolerance_minutes invalide dans {config_path}.")
    return attack_config


def check_attack_windows(
    frame: pd.DataFrame,
    corrected_starts: pd.Series,
    attack_config: dict[str, Any],
) -> AttackWindowDiagnostics:
    """Calcule les comptes et taux dans les plages, sans modifier les labels."""
    if "day" not in frame or "label_multi" not in frame:
        raise ValueError("day et label_multi sont requis pour vérifier les plages.")
    if len(frame) != len(corrected_starts) or not frame.index.equals(corrected_starts.index):
        raise ValueError("Les horodatages corrigés doivent aligner les lignes du DataFrame.")
    windows_by_day = attack_config["windows"]
    tolerance = float(attack_config["tolerance_minutes"])
    if tolerance < 0:
        raise ValueError("tolerance_minutes ne peut pas être négatif.")

    classes_by_day: dict[str, list[str]] = {}
    configured_classes: set[str] = set()
    for day, class_windows in windows_by_day.items():
        if not isinstance(class_windows, dict):
            raise ValueError(f"Les fenêtres de {day} doivent être une table.")
        classes_by_day[str(day)] = [str(name) for name in class_windows]
        configured_classes.update(str(name) for name in class_windows)

    data_classes = set(frame["label_multi"].dropna().astype(str).unique())
    classes_missing_from_data = sorted(configured_classes - data_classes)
    classes_missing_from_windows = sorted(data_classes - configured_classes)
    data_days = [str(day) for day in frame["day"].dropna().unique()]
    start_minutes = (
        corrected_starts.dt.hour * 60
        + corrected_starts.dt.minute
        + corrected_starts.dt.second / 60
        + corrected_starts.dt.microsecond / 60_000_000
    )

    rows: list[dict[str, Any]] = []
    for day in data_days:
        day_mask = frame["day"].astype(str).eq(day)
        classes_for_day = list(dict.fromkeys(
            name for names in classes_by_day.values() for name in names
        ))
        for class_name in classes_for_day:
            class_mask = day_mask & frame["label_multi"].astype(str).eq(class_name)
            count = int(class_mask.sum())
            intervals = windows_by_day.get(day, {}).get(class_name)
            in_window: int | None = None
            percentage: float | None = None
            if intervals is not None:
                matching = pd.Series(False, index=frame.index)
                for interval in intervals:
                    if not isinstance(interval, (list, tuple)) or len(interval) != 2:
                        raise ValueError(
                            f"Intervalle invalide pour {day}/{class_name}."
                        )
                    start_minute = _minutes_from_hhmm(interval[0]) - tolerance
                    end_minute = _minutes_from_hhmm(interval[1]) + tolerance
                    matching |= start_minutes.ge(start_minute) & start_minutes.le(
                        end_minute
                    )
                in_window = int((class_mask & matching).sum())
                percentage = 100.0 * in_window / count if count else None
            rows.append(
                {
                    "day": day,
                    "label_multi": class_name,
                    "windows": intervals,
                    "flows": count,
                    "in_window": in_window,
                    "percentage": percentage,
                    "out_of_window": count - in_window if in_window is not None else None,
                }
            )
    return AttackWindowDiagnostics(
        rows=rows,
        classes_missing_from_data=classes_missing_from_data,
        classes_missing_from_windows=classes_missing_from_windows,
    )


def _minutes_from_hhmm(value: str) -> float:
    try:
        parsed = pd.to_datetime(value, format="%H:%M", errors="raise")
    except (TypeError, ValueError) as error:
        raise ValueError(f"Heure de fenêtre invalide : {value}.") from error
    return parsed.hour * 60 + parsed.minute


def _formats_et_seuil(
    config: dict[str, Any] | None,
) -> tuple[dict[str, str], int]:
    project_config = load_config() if config is None else config
    timestamp_config = project_config["timestamps"]
    formats = timestamp_config["formats"]
    if "Monday" not in formats or "other" not in formats:
        raise ValueError("timestamps.formats doit définir Monday et other.")
    threshold = int(timestamp_config["pm_hour_threshold"])
    if not 0 <= threshold <= 23:
        raise ValueError("timestamps.pm_hour_threshold doit être compris entre 0 et 23.")
    return formats, threshold


def correct_start_times(
    frame: pd.DataFrame,
    config: dict[str, Any] | None = None,
    *,
    afficher_resultats: bool = True,
) -> pd.Series:
    """Parse par fichier et corrige les heures ambiguës des journées non-Monday."""
    formats, threshold = _formats_et_seuil(config)
    required = {"Timestamp", "day", "source_file"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(
            "Colonnes nécessaires au parsing absentes : " + ", ".join(sorted(missing))
        )

    start_times = pd.Series(
        pd.NaT, index=frame.index, dtype="datetime64[ns]", name="_start_time"
    )
    parse_failures: Counter[str] = Counter()
    for source_file, indexes in frame.groupby("source_file", sort=False).groups.items():
        file_rows = frame.loc[indexes]
        days = file_rows["day"].dropna().unique()
        if len(days) != 1 or days[0] not in _JOURS:
            raise ValueError(
                f"{source_file} : jour ambigu ou invalide dans la colonne day."
            )
        day = str(days[0])
        date_format = formats["Monday"] if day == "Monday" else formats["other"]
        parsed = pd.to_datetime(
            file_rows["Timestamp"],
            format=date_format,
            errors="coerce",
            dayfirst=True,
        )
        failures = int(parsed.isna().sum())
        if failures:
            parse_failures[str(source_file)] += failures
        start_times.loc[indexes] = parsed
        if day != "Monday":
            before_pm = parsed.notna() & (parsed.dt.hour < threshold)
            start_times.loc[indexes[before_pm.to_numpy()]] += pd.Timedelta(hours=12)

    failure_total = sum(parse_failures.values())
    if afficher_resultats:
        print(f"Échecs de parsing Timestamp : {failure_total}.")
        for source_file, count in sorted(parse_failures.items()):
            print(f"  {source_file} : {count}")
    if failure_total:
        raise ValueError(
            f"Parsing Timestamp interrompu : {failure_total} échec(s) au total."
        )

    expected_days = frame["day"].astype("string")
    actual_days = start_times.dt.day_name().astype("string")
    mismatches = expected_days.ne(actual_days).fillna(True)
    mismatch_count = int(mismatches.sum())
    if afficher_resultats:
        print(f"Écarts entre le jour parsé et day : {mismatch_count}.")
    if mismatch_count:
        exemples = frame.loc[mismatches, ["source_file", "day", "Timestamp"]].head(5)
        raise ValueError(
            f"{mismatch_count} écart(s) entre la date parsée et day :\n"
            + exemples.to_string(index=False)
        )
    return start_times


def add_ts_end(
    frame: pd.DataFrame,
    config: dict[str, Any] | None = None,
    *,
    corrected_starts: pd.Series | None = None,
    afficher_resultats: bool = True,
) -> tuple[pd.Series, TimestampDiagnostics]:
    """Ajoute ts_end en secondes epoch, sans supprimer ni modifier les durées."""
    starts = (
        correct_start_times(frame, config, afficher_resultats=afficher_resultats)
        if corrected_starts is None
        else corrected_starts
    )
    if len(frame) != len(starts) or not frame.index.equals(starts.index):
        raise ValueError("Les horodatages corrigés doivent aligner les lignes du DataFrame.")
    if "Flow Duration" not in frame.columns:
        raise ValueError("Colonne requise absente : Flow Duration.")
    durations = pd.to_numeric(frame["Flow Duration"], errors="coerce").to_numpy(
        dtype=np.float64, na_value=np.nan
    )
    invalid_durations = ~np.isfinite(durations)
    invalid_count = int(invalid_durations.sum())
    if invalid_count:
        raise ValueError(
            f"Flow Duration : {invalid_count} valeur(s) absente(s) ou non finie(s)."
        )

    start_epoch = starts.astype("int64").to_numpy(dtype=np.float64) / 1_000_000_000
    frame["ts_end"] = (start_epoch + durations / 1_000_000).astype(np.float64)
    nonpositive = pd.Series(durations <= 0, index=frame.index)
    nonpositive_by_day = {
        str(day): int(count)
        for day, count in frame.loc[nonpositive].groupby("day", sort=True).size().items()
    }
    return starts, TimestampDiagnostics(
        parse_failures={},
        weekday_mismatches=0,
        nonpositive_durations=nonpositive_by_day,
    )


def _allocate_stratified_quotas(
    stratum_counts: Counter[tuple[str, str]], sample_size: int
) -> dict[tuple[str, str], int]:
    groups = {key: int(count) for key, count in stratum_counts.items() if count > 0}
    if sum(groups.values()) < sample_size:
        raise ValueError(
            f"Seulement {sum(groups.values())} flux disponibles pour "
            f"un échantillon de {sample_size}."
        )
    if len(groups) > sample_size:
        raise ValueError(
            f"{len(groups)} strates non vides dépassent la taille "
            f"d’échantillon {sample_size}."
        )
    quotas = {key: 1 for key in groups}
    remaining = sample_size - len(quotas)
    while remaining:
        capacities = {key: groups[key] - quotas[key] for key in groups}
        total_capacity = sum(capacities.values())
        if total_capacity <= 0:
            raise ValueError("Impossible d’allouer la taille d’échantillon demandée.")
        exact = {
            key: remaining * capacity / total_capacity
            for key, capacity in capacities.items()
            if capacity > 0
        }
        added = 0
        for key, allocation in exact.items():
            count = min(capacities[key], int(allocation))
            quotas[key] += count
            added += count
        remaining -= added
        if remaining:
            fractional_order = sorted(
                (key for key in exact if quotas[key] < groups[key]),
                key=lambda key: (-(exact[key] % 1), key),
            )
            for key in fractional_order:
                if remaining == 0:
                    break
                quotas[key] += 1
                remaining -= 1
            if not fractional_order and remaining:
                raise ValueError("Allocation stratifiée incomplète.")
    return quotas


def _format_windows(intervals: Any) -> str:
    if intervals is None:
        return "aucune plage définie"
    return ", ".join(f"{start}–{end}" for start, end in intervals)


def _write_timestamp_report(
    report_path: Path,
    day_stats: dict[str, dict[str, Any]],
    file_stats: dict[str, dict[str, Any]],
    attack_stats: AttackWindowDiagnostics,
    attack_counts: Counter[tuple[str, str]],
    attack_in_window: Counter[tuple[str, str]],
    parse_failures: Counter[str],
    weekday_mismatches: int,
    maximum_duration_seconds: float,
    sample_size: int,
) -> None:
    lines = [
        "# Vérification des horodatages et des plages d’attaque",
        "",
        f"- Lignes de sortie : {sum(item['rows'] for item in day_stats.values())}",
        f"- Échecs de parsing Timestamp : {sum(parse_failures.values())}",
        f"- Écarts entre date parsée et day : {weekday_mismatches}",
        f"- Échantillon de développement : {sample_size} flux (graine `seeds.global`)",
        "",
        "## Parsing par fichier",
        "",
        "| Fichier | Jour | Lignes | Échecs de parsing |",
        "|---|---|---:|---:|",
    ]
    for source_file, item in sorted(file_stats.items()):
        lines.append(
            f"| {source_file} | {item['day']} | {item['rows']} | "
            f"{parse_failures[source_file]} |"
        )

    lines.extend(
        [
            "",
            "## Résumé par jour",
            "",
            "| Jour | Flux | ts_end min (epoch s) | ts_end max (epoch s) | Étendue max-min (s) | Somme Flow Duration (s) | Durées ≤ 0 |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for day in _JOURS:
        if day not in day_stats:
            continue
        item = day_stats[day]
        lines.append(
            f"| {day} | {item['rows']} | {item['ts_min']:.6f} | "
            f"{item['ts_max']:.6f} | {item['ts_max'] - item['ts_min']:.6f} | "
            f"{item['duration_sum_seconds']:.6f} | {item['nonpositive']} |"
        )

    tolerance = float(attack_stats.rows[0]["tolerance"]) if attack_stats.rows else 0
    lines.extend(
        [
            "",
            "## Vérification des plages d’attaque",
            "",
            f"- Tolérance configurée : ±{tolerance:g} minute(s).",
            "",
            "| Jour | Classe | Plage(s) | Flux de la classe ce jour | Dans la plage | % dans la plage | Hors plage |",
            "|---|---|---|---:|---:|---:|---:|",
        ]
    )
    for row in attack_stats.rows:
        key = (row["day"], row["label_multi"])
        count = attack_counts[key]
        in_window = attack_in_window[key] if row["windows"] is not None else None
        percentage = 100 * in_window / count if in_window is not None and count else None
        in_window_text = str(in_window) if in_window is not None else "n/a"
        percentage_text = f"{percentage:.2f}%" if percentage is not None else "n/a"
        outside_text = (
            str(count - in_window) if in_window is not None else "n/a"
        )
        lines.append(
            f"| {row['day']} | {row['label_multi']} | "
            f"{_format_windows(row['windows'])} | {count} | "
            f"{in_window_text} | {percentage_text} | {outside_text} |"
        )

    lines.extend(["", "### Classes absentes ou hors configuration", ""])
    lines.append(
        "- Classes configurées absentes des données : "
        + (
            ", ".join(attack_stats.classes_missing_from_data)
            if attack_stats.classes_missing_from_data
            else "aucune"
        )
        + "."
    )
    lines.append(
        "- Classes des données absentes de la configuration : "
        + (
            ", ".join(attack_stats.classes_missing_from_windows)
            if attack_stats.classes_missing_from_windows
            else "aucune"
        )
        + ". Les labels ne sont pas modifiés."
    )

    monday_rows = sum(
        item["rows"] for item in file_stats.values() if item["day"] == "Monday"
    )
    other_rows = sum(
        item["rows"] for item in file_stats.values() if item["day"] != "Monday"
    )
    monday_zero = sum(
        item["second_zero"] for item in day_stats.values() if item["day"] == "Monday"
    )
    other_zero = sum(
        item["second_zero"] for item in day_stats.values() if item["day"] != "Monday"
    )
    unsorted_files = [
        (name, item["inversions"])
        for name, item in sorted(file_stats.items())
        if item["inversions"] > 0
    ]
    file_count = len(file_stats)
    files_without_seconds = sum(item["day"] != "Monday" for item in file_stats.values())
    lines.extend(
        [
            "",
            "## Limites",
            "",
            f"- {files_without_seconds} fichier(s) sur {file_count} n’ont pas de secondes dans le format source (résolution d’une minute).",
            f"- Flux dont la seconde de l’heure de début corrigée vaut 0 : Monday {monday_zero}/{monday_rows} "
            f"({100 * monday_zero / monday_rows if monday_rows else 0:.2f} %), "
            f"autres jours {other_zero}/{other_rows} "
            f"({100 * other_zero / other_rows if other_rows else 0:.2f} %).",
            "- Fichiers d’origine dont les heures de début ne sont pas triées : "
            + (
                "; ".join(f"{name} ({count} inversion(s))" for name, count in unsorted_files)
                if unsorted_files
                else "aucun"
            )
            + ".",
            f"- Durée maximale observée : {maximum_duration_seconds:.6f} seconde(s) "
            f"({maximum_duration_seconds * 1_000_000:.0f} microsecondes).",
            "- Les labels d’origine sont conservés ; les écarts aux fenêtres ne sont pas corrigés.",
        ]
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_clean_dataset(
    config: dict[str, Any] | None = None,
    *,
    input_path: str | Path | None = None,
    report_path: str | Path | None = None,
    attack_windows_path: str | Path | None = None,
    sample_size: int = 5_000,
    batch_size: int = _ROW_GROUP_SIZE,
) -> tuple[Path, Path, Path]:
    """Construit clean.parquet, son échantillon stratifié et le rapport."""
    project_config = load_config() if config is None else config
    interim = Path(project_config["paths"]["interim"])
    source_path = (
        Path(input_path)
        if input_path is not None
        else interim / "clean_raw.parquet"
    )
    output_path = interim / "clean.parquet"
    sample_path = interim / "clean_sample.parquet"
    if report_path is None:
        report_path = interim.resolve().parents[1] / "reports" / "timestamps_check.md"
    report_path = Path(report_path)
    if sample_size < 1 or batch_size < 1:
        raise ValueError("sample_size et batch_size doivent être positifs.")
    if not source_path.exists():
        raise FileNotFoundError(f"Parquet source introuvable : {source_path}.")

    attack_config = load_attack_windows(attack_windows_path)
    parsed_file = pq.ParquetFile(source_path)
    day_stats: dict[str, dict[str, Any]] = {}
    file_stats: dict[str, dict[str, Any]] = {}
    parse_failures: Counter[str] = Counter()
    weekday_mismatches = 0
    nonpositive_by_day: Counter[str] = Counter()
    maximum_duration_seconds = float("-inf")
    attack_counts: Counter[tuple[str, str]] = Counter()
    attack_in_window: Counter[tuple[str, str]] = Counter()
    stratum_counts: Counter[tuple[str, str]] = Counter()

    with TemporaryDirectory(prefix="horodatages-", dir=interim) as temporary:
        temp_dir = Path(temporary)
        day_writers: dict[str, pq.ParquetWriter] = {}
        day_files: dict[str, Path] = {}
        last_start_by_file: dict[str, pd.Timestamp] = {}
        try:
            for batch in parsed_file.iter_batches(batch_size=batch_size):
                frame = batch.to_pandas()
                starts = correct_start_times(
                    frame, project_config, afficher_resultats=False
                )
                starts, diagnostics = add_ts_end(
                    frame,
                    project_config,
                    corrected_starts=starts,
                    afficher_resultats=False,
                )
                nonpositive_by_day.update(diagnostics.nonpositive_durations)
                durations = frame["Flow Duration"].to_numpy(dtype=np.float64) / 1_000_000
                maximum_duration_seconds = max(
                    maximum_duration_seconds, float(durations.max())
                )
                for day, group_indexes in frame.groupby("day", sort=False).groups.items():
                    day = str(day)
                    positions = frame.index.get_indexer(group_indexes)
                    day_duration_seconds = durations[positions]
                    day_starts = starts.loc[group_indexes]
                    day_stats.setdefault(
                        day,
                        {
                            "day": day,
                            "rows": 0,
                            "ts_min": float("inf"),
                            "ts_max": float("-inf"),
                            "duration_sum_seconds": 0.0,
                            "nonpositive": 0,
                            "second_zero": 0,
                        },
                    )
                    stats = day_stats[day]
                    ts_values = frame.loc[group_indexes, "ts_end"].to_numpy()
                    stats["rows"] += len(group_indexes)
                    stats["ts_min"] = min(stats["ts_min"], float(ts_values.min()))
                    stats["ts_max"] = max(stats["ts_max"], float(ts_values.max()))
                    stats["duration_sum_seconds"] += float(day_duration_seconds.sum())
                    stats["nonpositive"] += diagnostics.nonpositive_durations.get(day, 0)
                    zero_seconds = int(day_starts.dt.second.eq(0).sum())
                    stats["second_zero"] += zero_seconds

                for source_file, group_indexes in frame.groupby(
                    "source_file", sort=False
                ).groups.items():
                    source_file = str(source_file)
                    indexes = frame.index.get_indexer(group_indexes)
                    file_days = frame.loc[group_indexes, "day"].unique()
                    if len(file_days) != 1:
                        raise ValueError(
                            f"{source_file} est associé à plusieurs jours."
                        )
                    file_day = str(file_days[0])
                    info = file_stats.setdefault(
                        source_file,
                        {"day": file_day, "rows": 0, "inversions": 0},
                    )
                    ordered_starts = starts.iloc[indexes]
                    start_values = ordered_starts.to_numpy(dtype="datetime64[ns]")
                    if source_file in last_start_by_file and len(start_values):
                        if pd.Timestamp(start_values[0]) < last_start_by_file[source_file]:
                            info["inversions"] += 1
                    if len(start_values) > 1:
                        info["inversions"] += int(
                            np.count_nonzero(np.diff(start_values) < np.timedelta64(0, "ns"))
                        )
                    if len(start_values):
                        last_start_by_file[source_file] = pd.Timestamp(start_values[-1])
                    info["rows"] += len(group_indexes)

                window_diagnostics = check_attack_windows(
                    frame, starts, attack_config
                )
                for row in window_diagnostics.rows:
                    key = (row["day"], row["label_multi"])
                    attack_counts[key] += row["flows"]
                    if row["in_window"] is not None:
                        attack_in_window[key] += row["in_window"]
                stratum_counts.update(
                    Counter(
                        (
                            str(day),
                            str(label),
                        )
                        for day, label in zip(frame["day"], frame["label_multi"])
                    )
                )

                frame = frame.drop(columns="Timestamp")
                for day, group_indexes in frame.groupby("day", sort=False).groups.items():
                    day = str(day)
                    day_frame = frame.loc[group_indexes]
                    table = pa.Table.from_pandas(day_frame, preserve_index=False)
                    if day not in day_writers:
                        day_files[day] = temp_dir / f"{day}.parquet"
                        day_writers[day] = pq.ParquetWriter(
                            day_files[day], table.schema
                        )
                    else:
                        table = table.cast(day_writers[day].schema)
                    day_writers[day].write_table(table, row_group_size=batch_size)
        finally:
            for writer in day_writers.values():
                writer.close()

        print(f"Échecs de parsing Timestamp : {sum(parse_failures.values())}.")
        print(f"Écarts entre date parsée et day : {weekday_mismatches}.")
        print(
            "Durees Flow Duration <= 0 par jour : "
            f"{dict(sorted(nonpositive_by_day.items()))}"
        )

        if not day_files:
            raise ValueError("Aucune donnée ne subsiste dans le Parquet source.")
        quotas = _allocate_stratified_quotas(stratum_counts, sample_size)
        seed = int(project_config["seeds"]["global"])
        sample_parts: list[pd.DataFrame] = []
        output_writer: pq.ParquetWriter | None = None
        try:
            for day in _JOURS:
                if day not in day_files:
                    continue
                day_frame = pd.read_parquet(day_files[day])
                day_frame = day_frame.sort_values(
                    "ts_end", kind="stable", ignore_index=True
                )
                if not day_frame["ts_end"].is_monotonic_increasing:
                    raise ValueError(f"ts_end n’est pas croissant pour {day}.")
                validate_schema(day_frame, stage="clean")
                print(
                    f"validate_schema(stage='clean') : {day}, "
                    f"{len(day_frame)} lignes, OK."
                )

                for label, group in day_frame.groupby(
                    "label_multi", sort=False, observed=True
                ):
                    key = (day, str(label))
                    quota = quotas.get(key, 0)
                    if quota:
                        sample_parts.append(
                            group.sample(n=quota, random_state=seed)
                        )

                table = pa.Table.from_pandas(day_frame, preserve_index=False)
                if output_writer is None:
                    output_writer = pq.ParquetWriter(output_path, table.schema)
                else:
                    table = table.cast(output_writer.schema)
                output_writer.write_table(table, row_group_size=batch_size)
        finally:
            if output_writer is not None:
                output_writer.close()

        if output_writer is None:
            raise ValueError("Aucun flux final à écrire.")
        output_table = pq.ParquetFile(output_path)
        if output_table.metadata.num_rows != sum(
            item["rows"] for item in day_stats.values()
        ):
            raise ValueError("Le nombre de lignes écrit ne correspond pas au nombre lu.")

        sample = pd.concat(sample_parts, ignore_index=True)
        sample = sample.sort_values("ts_end", kind="stable", ignore_index=True)
        if len(sample) != sample_size:
            raise ValueError(
                f"Taille d’échantillon incorrecte : {len(sample)} au lieu de {sample_size}."
            )
        validate_schema(sample, stage="clean")
        pq.write_table(
            pa.Table.from_pandas(sample, preserve_index=False),
            sample_path,
            row_group_size=batch_size,
        )

    all_data_classes = {label for _, label in stratum_counts}
    configured_classes = {
        str(class_name)
        for day_windows in attack_config["windows"].values()
        for class_name in day_windows
    }
    data_days = [day for day in _JOURS if day in day_stats]
    attack_rows: list[dict[str, Any]] = []
    for day in data_days:
        for class_name in dict.fromkeys(
            class_name
            for class_windows in attack_config["windows"].values()
            for class_name in class_windows
        ):
            windows = attack_config["windows"].get(day, {}).get(class_name)
            key = (day, str(class_name))
            attack_rows.append(
                {
                    "day": day,
                    "label_multi": str(class_name),
                    "windows": windows,
                    "flows": attack_counts[key],
                    "tolerance": float(attack_config["tolerance_minutes"]),
                }
            )
    attack_diagnostics = AttackWindowDiagnostics(
        rows=attack_rows,
        classes_missing_from_data=sorted(configured_classes - all_data_classes),
        classes_missing_from_windows=sorted(all_data_classes - configured_classes),
    )
    for day in day_stats:
        day_stats[day]["nonpositive"] = nonpositive_by_day[day]
    _write_timestamp_report(
        report_path,
        day_stats,
        file_stats,
        attack_diagnostics,
        attack_counts,
        attack_in_window,
        parse_failures,
        weekday_mismatches,
        maximum_duration_seconds,
        sample_size,
    )
    return output_path, sample_path, report_path


if __name__ == "__main__":
    clean_path, sample_path, report = build_clean_dataset()
    print(f"Données horodatées : {clean_path}")
    print(f"Échantillon de développement : {sample_path}")
    print(f"Rapport : {report}")
