"""Affectation chronologique des flux aux blocs train, val, test et gap."""

from collections import Counter
from typing import Mapping

import numpy as np
import pandas as pd


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
