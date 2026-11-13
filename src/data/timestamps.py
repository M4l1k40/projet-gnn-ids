"""Correction des horodatages CIC-IDS2017 et calcul des fins de flux."""

from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from src.utils.config import load_config

_JOURS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


@dataclass(frozen=True)
class TimestampDiagnostics:
    """Comptages associés au parsing et au calcul de ts_end."""

    parse_failures: dict[str, int]
    weekday_mismatches: int
    nonpositive_durations: dict[str, int]


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
