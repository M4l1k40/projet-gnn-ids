"""Correction des horodatages CIC-IDS2017 et calcul des fins de flux."""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from src.utils.config import load_config

_JOURS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


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
) -> tuple[pd.Series, TimestampDiagnostics]:
    """Ajoute ts_end en secondes epoch, sans supprimer ni modifier les durées."""
    starts = correct_start_times(frame, config)
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
