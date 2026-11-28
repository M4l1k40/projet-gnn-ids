"""Prépare le split V3 avec signed_log1p et standardisation train-only."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterator

import joblib
import cloudpickle
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy.stats import spearmanr
from sklearn.preprocessing import StandardScaler

from src.data.schema import ID_COLS, META_COLS, TARGET_COLS, validate_schema
from src.utils.config import load_config

_SPLITS = ("train", "val", "test")
_COPY_FILES = ("meta.parquet", "folds.parquet", "p2_folds.parquet")


class LogZTransformer:
    """Transformeur autonome dont l'état contient médianes et stats train."""

    def __init__(
        self,
        feature_names: list[str],
        imputation_medians: np.ndarray,
        invalid_indices: np.ndarray,
        mean: np.ndarray,
        scale: np.ndarray,
    ) -> None:
        self.feature_names = list(feature_names)
        self.imputation_medians = np.asarray(imputation_medians, dtype=np.float64)
        self.invalid_indices = np.asarray(invalid_indices, dtype=np.int64)
        self.mean_ = np.asarray(mean, dtype=np.float64)
        self.scale_ = np.asarray(scale, dtype=np.float64)
        self.n_features_in_ = len(self.feature_names)

    def transform(self, values: pd.DataFrame | np.ndarray) -> np.ndarray:
        """Transforme un DataFrame ordonné par nom ou un ndarray déjà ordonné."""
        if isinstance(values, pd.DataFrame):
            missing = [name for name in self.feature_names if name not in values]
            if missing:
                raise ValueError("Features manquantes : " + ", ".join(missing) + ".")
            matrix = values.loc[:, self.feature_names].to_numpy(
                dtype=np.float64,
                copy=True,
            )
        else:
            matrix = np.asarray(values, dtype=np.float64)
            if matrix.ndim != 2 or matrix.shape[1] != self.n_features_in_:
                raise ValueError(
                    f"Entrée attendue avec {self.n_features_in_} features."
                )
            matrix = matrix.copy()
        if not np.isfinite(matrix).all():
            raise ValueError("Les features brutes contiennent NaN ou infini.")
        for index in self.invalid_indices:
            negative = matrix[:, index] < 0
            matrix[negative, index] = self.imputation_medians[index]
        transformed = np.sign(matrix) * np.log1p(np.abs(matrix))
        transformed = (transformed - self.mean_) / self.scale_
        if not np.isfinite(transformed).all():
            raise ValueError("La transformation a produit NaN ou infini.")
        return transformed.astype(np.float32)


LogZTransformer.__module__ = "src.data.normalize_logz"
sys.modules.setdefault("src.data.normalize_logz", sys.modules[__name__])


def _dump_transformer(transformer: LogZTransformer, path: Path) -> None:
    module = sys.modules["src.data.normalize_logz"]
    cloudpickle.register_pickle_by_value(module)
    try:
        with path.open("wb") as stream:
            cloudpickle.dump(transformer, stream, protocol=5)
    finally:
        cloudpickle.unregister_pickle_by_value(module)


def _configured_path(config: dict[str, Any], name: str) -> Path:
    value = config["paths"].get(name)
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(f"Chemin de configuration manquant : paths.{name}.")
    return Path(value).resolve()


def _feature_names(config: dict[str, Any]) -> list[str]:
    path = _configured_path(config, "feature_list")
    features = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(features, list) or not features or not all(
        isinstance(feature, str) for feature in features
    ):
        raise ValueError(f"{path} doit contenir une liste JSON de features.")
    excluded = set(ID_COLS + TARGET_COLS + META_COLS)
    forbidden = sorted(set(features) & excluded)
    if forbidden:
        raise ValueError("Features identifiantes interdites : " + ", ".join(forbidden))
    return features


def _flow_ids(path: Path) -> list[str]:
    values = pq.read_table(path, columns=["flow_id"])["flow_id"].to_pylist()
    if len(values) != len(set(values)):
        raise ValueError(f"flow_id non uniques dans {path}.")
    return values


def _matrix(table: pa.Table, features: list[str]) -> np.ndarray:
    frame = table.select(features).to_pandas()
    matrix = frame.to_numpy(dtype=np.float32, copy=False)
    if not np.isfinite(matrix).all():
        raise ValueError("Les features de clean.parquet contiennent NaN ou infini.")
    return matrix


def _selected_raw_batches(
    clean_path: Path,
    flow_ids: set[str],
    columns: list[str],
    batch_size: int,
) -> Iterator[tuple[list[str], np.ndarray]]:
    source = pq.ParquetFile(clean_path)
    for batch in source.iter_batches(columns=["flow_id", *columns], batch_size=batch_size):
        ids = batch.column(0).to_pylist()
        positions = np.fromiter(
            (index for index, flow_id in enumerate(ids) if flow_id in flow_ids),
            dtype=np.int64,
        )
        if not len(positions):
            continue
        selected = batch.take(pa.array(positions, type=pa.int64()))
        selected_ids = selected.column(0).to_pylist()
        values = _matrix(selected.select(columns), columns)
        yield selected_ids, values


def _train_medians(
    clean_path: Path,
    train_ids: set[str],
    features: list[str],
    invalid_indices: np.ndarray,
    batch_size: int,
    expected_rows: int,
) -> tuple[np.ndarray, dict[str, int]]:
    medians = np.zeros(len(features), dtype=np.float64)
    chunks: dict[int, list[np.ndarray]] = {int(i): [] for i in invalid_indices}
    counts = {features[int(i)]: 0 for i in invalid_indices}
    rows = 0
    invalid_features = [features[int(i)] for i in invalid_indices]
    for _, values in _selected_raw_batches(
        clean_path, train_ids, invalid_features, batch_size
    ):
        rows += len(values)
        for local_index, feature_index in enumerate(invalid_indices):
            valid = values[:, local_index] >= 0
            valid_values = values[valid, local_index]
            if len(valid_values):
                chunks[int(feature_index)].append(valid_values.copy())
            counts[features[int(feature_index)]] += int(np.count_nonzero(~valid))
    if rows != expected_rows:
        raise ValueError(
            f"clean.parquet couvre {rows} lignes train au lieu de {expected_rows}."
        )
    for index in invalid_indices:
        pieces = chunks[int(index)]
        if not pieces:
            raise ValueError(f"Aucune valeur valide pour l’imputation de {features[index]}.")
        medians[int(index)] = float(np.median(np.concatenate(pieces)))
    return medians, counts


def _fit_standardizer(
    clean_path: Path,
    train_ids: set[str],
    features: list[str],
    medians: np.ndarray,
    invalid_indices: np.ndarray,
    batch_size: int,
    expected_rows: int,
) -> tuple[np.ndarray, np.ndarray]:
    scaler = StandardScaler()
    rows = 0
    for _, raw in _selected_raw_batches(clean_path, train_ids, features, batch_size):
        matrix = raw.astype(np.float64, copy=True)
        for index in invalid_indices:
            matrix[matrix[:, int(index)] < 0, int(index)] = medians[int(index)]
        transformed = np.sign(matrix) * np.log1p(np.abs(matrix))
        scaler.partial_fit(transformed)
        rows += len(matrix)
    if rows != expected_rows:
        raise ValueError(
            f"Scaler ajusté sur {rows} lignes au lieu de {expected_rows}."
        )
    scale = np.asarray(scaler.scale_, dtype=np.float64)
    scale[scale == 0] = 1.0
    return np.asarray(scaler.mean_, dtype=np.float64), scale


class _RawCursor:
    def __init__(
        self,
        batches: Iterator[tuple[list[str], np.ndarray]],
    ) -> None:
        self._batches = batches
        self._ids: list[str] = []
        self._values: np.ndarray | None = None
        self._offset = 0
        self.rows_read = 0

    def take(self, count: int, feature_count: int) -> tuple[list[str], np.ndarray]:
        output_ids: list[str] = []
        output = np.empty((count, feature_count), dtype=np.float32)
        written = 0
        while written < count:
            if self._values is None or self._offset == len(self._ids):
                try:
                    self._ids, self._values = next(self._batches)
                except StopIteration as error:
                    raise ValueError("clean.parquet ne couvre pas tous les flow_id.") from error
                self._offset = 0
            available = len(self._ids) - self._offset
            take_count = min(count - written, available)
            end = self._offset + take_count
            output_ids.extend(self._ids[self._offset:end])
            output[written : written + take_count] = self._values[self._offset:end]
            self._offset = end
            written += take_count
            self.rows_read += take_count
        return output_ids, output

    def ensure_exhausted(self) -> None:
        if self._values is not None and self._offset < len(self._ids):
            raise ValueError("clean.parquet contient des flow_id V3 en trop.")
        try:
            next(self._batches)
        except StopIteration:
            return
        raise ValueError("clean.parquet contient des flow_id V3 en trop.")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_reference_files(
    config: dict[str, Any],
    source_dir: Path,
    staged_dir: Path,
) -> dict[str, str]:
    sources = {
        "meta.parquet": source_dir / "meta.parquet",
        "folds.parquet": source_dir / "folds.parquet",
        "p2_folds.parquet": _configured_path(config, "p2_folds_source"),
    }
    hashes: dict[str, str] = {}
    for name, source in sources.items():
        if not source.is_file():
            raise FileNotFoundError(f"Parquet de référence introuvable : {source}.")
        destination = staged_dir / name
        shutil.copy2(source, destination)
        source_hash = _sha256(source)
        if _sha256(destination) != source_hash:
            raise IOError(f"Copie non identique : {name}.")
        hashes[name] = source_hash
    return hashes


def _write_transformed_split(
    source_path: Path,
    destination_path: Path,
    clean_path: Path,
    flow_ids: list[str],
    feature_names: list[str],
    transformer: LogZTransformer,
    invalid_indices: np.ndarray,
    batch_size: int,
    *,
    train_sample_positions: np.ndarray | None = None,
    central_bounds: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    id_set = set(flow_ids)
    raw_cursor = _RawCursor(
        _selected_raw_batches(clean_path, id_set, feature_names, batch_size)
    )
    source_file = pq.ParquetFile(source_path)
    source_schema = source_file.schema_arrow
    feature_indexes = [source_schema.get_field_index(name) for name in feature_names]
    if any(index < 0 for index in feature_indexes):
        raise ValueError(f"Features absentes de {source_path}.")
    writer: pq.ParquetWriter | None = None
    counts = {feature_names[int(i)]: 0 for i in invalid_indices}
    central_sum = np.zeros(len(feature_names), dtype=np.float64)
    central_squared = np.zeros(len(feature_names), dtype=np.float64)
    central_count = np.zeros(len(feature_names), dtype=np.int64)
    central_min = np.full(len(feature_names), np.inf, dtype=np.float64)
    central_max = np.full(len(feature_names), -np.inf, dtype=np.float64)
    sample_raw: list[np.ndarray] = []
    sample_transformed: list[np.ndarray] = []
    sample_imputed: list[np.ndarray] = []
    row_offset = 0
    try:
        for batch in source_file.iter_batches(batch_size=batch_size):
            table = pa.Table.from_batches([batch])
            expected_ids = table.column("flow_id").to_pylist()
            raw_ids, raw = raw_cursor.take(len(expected_ids), len(feature_names))
            if raw_ids != expected_ids:
                raise ValueError(
                    f"Ordre ou flow_id différent entre clean.parquet et {source_path.name}."
                )
            matrix = raw.astype(np.float64, copy=True)
            imputed = np.zeros(matrix.shape, dtype=bool)
            for index in invalid_indices:
                index = int(index)
                invalid = matrix[:, index] < 0
                imputed[:, index] = invalid
                counts[feature_names[index]] += int(np.count_nonzero(invalid))
                matrix[invalid, index] = transformer.imputation_medians[index]
            signed_log = np.sign(matrix) * np.log1p(np.abs(matrix))
            transformed = ((signed_log - transformer.mean_) / transformer.scale_).astype(
                np.float32
            )
            if not np.isfinite(transformed).all():
                raise ValueError(f"Transformation non finie dans {source_path.name}.")

            if central_bounds is not None:
                for index, feature in enumerate(feature_names):
                    low, high = central_bounds[feature]
                    central = (raw[:, index] >= low) & (raw[:, index] <= high)
                    values = transformed[central, index].astype(np.float64)
                    central_sum[index] += values.sum()
                    central_squared[index] += np.square(values).sum()
                    central_count[index] += len(values)
                    if len(values):
                        central_min[index] = min(central_min[index], float(values.min()))
                        central_max[index] = max(central_max[index], float(values.max()))

            if train_sample_positions is not None:
                start = row_offset
                end = start + len(raw)
                first = int(np.searchsorted(train_sample_positions, start, side="left"))
                last = int(np.searchsorted(train_sample_positions, end, side="left"))
                if last > first:
                    local = train_sample_positions[first:last] - start
                    sample_raw.append(raw[local].copy())
                    sample_transformed.append(transformed[local].copy())
                    sample_imputed.append(imputed[local].copy())
            for feature_position, (index, feature) in enumerate(
                zip(feature_indexes, feature_names)
            ):
                table = table.set_column(
                    index,
                    feature,
                    pa.array(transformed[:, feature_position], type=pa.float32()),
                )
            if writer is None:
                writer = pq.ParquetWriter(destination_path, table.schema)
            writer.write_table(table, row_group_size=batch_size)
            row_offset += len(raw)
    finally:
        if writer is not None:
            writer.close()

    raw_cursor.ensure_exhausted()
    if row_offset != len(flow_ids):
        raise ValueError(f"Nombre de lignes modifié dans {source_path.name}.")
    return {
        "rows": row_offset,
        "imputed": counts,
        "central_sum": central_sum,
        "central_squared": central_squared,
        "central_count": central_count,
        "central_min": central_min,
        "central_max": central_max,
        "sample_raw": (
            np.concatenate(sample_raw) if sample_raw else None
        ),
        "sample_transformed": (
            np.concatenate(sample_transformed) if sample_transformed else None
        ),
        "sample_imputed": (
            np.concatenate(sample_imputed) if sample_imputed else None
        ),
    }


def _validate_written_split(
    source_path: Path,
    output_path: Path,
    feature_names: list[str],
    batch_size: int,
) -> None:
    source = pq.ParquetFile(source_path)
    output = pq.ParquetFile(output_path)
    if source.metadata.num_rows != output.metadata.num_rows:
        raise ValueError(f"Nombre de lignes différent après écriture : {output_path}.")
    if source.schema_arrow.names != output.schema_arrow.names:
        raise ValueError(f"Colonnes différentes après écriture : {output_path}.")
    expected_nonfeatures = [
        name for name in source.schema_arrow.names if name not in feature_names
    ]
    source_batches = source.iter_batches(batch_size=batch_size)
    output_batches = output.iter_batches(batch_size=batch_size)
    for source_batch, output_batch in zip(source_batches, output_batches):
        source_table = pa.Table.from_batches([source_batch])
        output_table = pa.Table.from_batches([output_batch])
        frame = output_table.to_pandas()
        validate_schema(frame, stage="final")
        if not source_table["flow_id"].equals(output_table["flow_id"]):
            raise ValueError(f"flow_id ou ordre modifié après écriture : {output_path}.")
        for column in expected_nonfeatures:
            if not source_table[column].equals(output_table[column]):
                raise ValueError(f"La colonne non-feature {column} a changé.")
    try:
        next(source_batches)
        raise ValueError(f"Nombre de batches différent dans {output_path}.")
    except StopIteration:
        pass
    try:
        next(output_batches)
        raise ValueError(f"Nombre de batches différent dans {output_path}.")
    except StopIteration:
        pass


def _spearman_table(
    feature_names: list[str],
    raw: np.ndarray,
    transformed: np.ndarray,
    imputed: np.ndarray,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, feature in enumerate(feature_names):
        keep = ~imputed[:, index]
        if np.count_nonzero(keep) < 2:
            correlation = float("nan")
        else:
            correlation = float(
                spearmanr(raw[keep, index], transformed[keep, index]).statistic
            )
        rows.append(
            {
                "feature": feature,
                "sample_non_imputed": int(np.count_nonzero(keep)),
                "spearman_raw_vs_logz": correlation,
                "spearman_one_within_1e-6": bool(
                    np.isfinite(correlation) and abs(correlation - 1.0) <= 1e-6
                ),
            }
        )
    return rows


def _write_report(
    report_path: Path,
    feature_names: list[str],
    split_results: dict[str, dict[str, Any]],
    central_bounds: dict[str, tuple[float, float]],
    central_values: dict[str, float],
    spearman_rows: list[dict[str, Any]],
    copy_hashes: dict[str, str],
    train_count: int,
    sample_count: int,
) -> None:
    lines = [
        "# Normalisation signed-log standardisée — split V3",
        "",
        "- Les valeurs brutes sont lues dans `data/interim/clean.parquet` et réalignées sur les splits V3 par `flow_id`.",
        "- Signed-log1p puis centrage/réduction ajustés exclusivement sur le train après imputation des négatifs invalides.",
        "- Les colonnes autres que les 69 features sont conservées depuis les Parquets V3; `meta.parquet`, `folds.parquet` et `p2_folds.parquet` sont des copies binaires.",
        f"- Train utilisé pour ajuster le transformeur : {train_count:,} lignes; features dans l’ordre de `models/features.json`.",
        "",
        "## Features hors [0,3 ; 1,5]",
        "",
        "| Feature | Écart-type central après log-z | Cause |",
        "|---|---:|---|",
    ]
    for row in central_values.values():
        if 0.3 <= row["central_std"] <= 1.5:
            continue
        lines.append(
            f"| {row['feature']} | {row['central_std']:.6g} | {row['cause']} |"
        )
    lines.extend(
        [
            "",
            (
                "Les indicateurs rares ont p99=0 et des valeurs identiques dans "
                "l’intervalle p1–p99; une transformation monotone ne peut pas "
                "augmenter l’écart-type central sans changer leur représentation."
            ),
            "",
            "## Imputations par bloc",
            "",
            "| Bloc | Lignes | Négatifs imputés (feature: effectif) |",
            "|---|---:|---|",
        ]
    )
    for split, result in split_results.items():
        summary = ", ".join(
            f"{feature}: {count:,}"
            for feature, count in result["imputed"].items()
            if count
        ) or "aucune"
        lines.append(f"| {split} | {result['rows']:,} | {summary} |")
    spearman_count = sum(row["spearman_one_within_1e-6"] for row in spearman_rows)
    lines.extend(
        [
            "",
            f"## Contrôles",
            "",
            (
                "- Écart-type central calculé sur les valeurs transformées des lignes "
                "entre p1 et p99 bruts du train (quantiles issus de "
                f"`scaler_audit_v3`): {len(central_values)} features."
            ),
            (
                f"- Spearman sur un échantillon fixe de {sample_count:,} lignes train "
                "(graine 42), exclusions des valeurs imputées feature par feature : "
                f"{spearman_count}/{len(feature_names)} features à 1 ± 1e-6."
            ),
            (
                "- Le contrôle `validate_schema(stage='final')` est appliqué aux "
                "batches relus après écriture; flow_id et ordre sont comparés aux sources."
            ),
            "- Les contrôles de valeurs non finies sont effectués sur chaque batch avant écriture.",
            "",
            "### Copies identiques",
            "",
            "| Fichier | SHA-256 |",
            "|---|---|",
        ]
    )
    for name, digest in copy_hashes.items():
        lines.append(f"| {name} | `{digest}` |")
    lines.extend(
        [
            "",
            "Aucun artefact existant n’a été remplacé. L’ancien jeu `data/processed_v3` reste le défaut; cette variante est optionnelle.",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


def prepare_logz_data(
    config: dict[str, Any] | None = None,
    *,
    batch_size: int | None = None,
    sample_size: int | None = None,
    sample_seed: int | None = None,
) -> dict[str, Any]:
    """Construit les Parquets log-z dans un chemin neuf, sans écrasement."""
    project = load_config() if config is None else config
    paths = project["paths"]
    settings = project["normalization_logz"]
    source_dir = _configured_path(project, "processed_v3")
    destination_dir = _configured_path(project, "processed_v3_logz")
    clean_path = Path(paths["interim"]) / "clean.parquet"
    scaler_path = _configured_path(project, "scaler_v3_logz")
    report_path = _configured_path(project, "normalization_v3_logz_report")
    feature_names = _feature_names(project)
    batch_size = int(batch_size or settings["batch_size"])
    sample_size = int(sample_size or settings["sample_size"])
    sample_seed = int(settings["sample_seed"] if sample_seed is None else sample_seed)
    if batch_size < 1 or sample_size < 1:
        raise ValueError("batch_size et sample_size doivent être positifs.")
    for path in (destination_dir, scaler_path, report_path):
        if path.exists():
            raise FileExistsError(f"Refus d’écraser un artefact existant : {path}.")
    if not clean_path.is_file():
        raise FileNotFoundError(f"Données brutes nettoyées introuvables : {clean_path}.")

    source_paths = {split: source_dir / f"{split}.parquet" for split in _SPLITS}
    flow_ids = {split: _flow_ids(path) for split, path in source_paths.items()}
    if set.intersection(*(set(ids) for ids in flow_ids.values())):
        raise ValueError("Les splits V3 partagent des flow_id.")
    train_count = len(flow_ids["train"])
    invalid_names = list(settings["invalid_negative_features"])
    invalid_unknown = sorted(set(invalid_names) - set(feature_names))
    if invalid_unknown:
        raise ValueError("Features d’imputation absentes : " + ", ".join(invalid_unknown))
    invalid_indices = np.asarray(
        [feature_names.index(name) for name in invalid_names],
        dtype=np.int64,
    )
    train_ids = set(flow_ids["train"])
    medians, _ = _train_medians(
        clean_path,
        train_ids,
        feature_names,
        invalid_indices,
        batch_size,
        train_count,
    )
    mean, scale = _fit_standardizer(
        clean_path,
        train_ids,
        feature_names,
        medians,
        invalid_indices,
        batch_size,
        train_count,
    )
    transformer = LogZTransformer(feature_names, medians, invalid_indices, mean, scale)

    audit_path = _configured_path(project, "scaler_audit_v3")
    audit = pd.read_csv(audit_path, encoding="utf-8-sig")
    if set(audit["feature"]) != set(feature_names) or len(audit) != len(feature_names):
        raise ValueError("L’audit scaler n’est pas aligné sur features.json.")
    central_bounds = {
        row["feature"]: (float(row["raw_p1"]), float(row["raw_p99"]))
        for _, row in audit.iterrows()
    }
    destination_dir.parent.mkdir(parents=True, exist_ok=True)
    scaler_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(
        tempfile.mkdtemp(prefix=".normalization-v3-logz-", dir=destination_dir.parent)
    )
    staged_dir = temporary_root / "processed_v3_logz"
    staged_dir.mkdir()
    staged_scaler = temporary_root / scaler_path.name
    staged_report = temporary_root / report_path.name
    sample_count = min(sample_size, train_count)
    sample_positions = np.sort(
        np.random.default_rng(sample_seed).choice(
            train_count,
            size=sample_count,
            replace=False,
        )
    )
    split_results: dict[str, dict[str, Any]] = {}
    try:
        copy_hashes = _copy_reference_files(project, source_dir, staged_dir)
        for split in _SPLITS:
            result = _write_transformed_split(
                source_paths[split],
                staged_dir / f"{split}.parquet",
                clean_path,
                flow_ids[split],
                feature_names,
                transformer,
                invalid_indices,
                batch_size,
                train_sample_positions=sample_positions if split == "train" else None,
                central_bounds=central_bounds if split == "train" else None,
            )
            _validate_written_split(
                source_paths[split],
                staged_dir / f"{split}.parquet",
                feature_names,
                batch_size,
            )
            split_results[split] = result

        central_result = split_results["train"]
        central_values: dict[str, dict[str, Any]] = {}
        for index, feature in enumerate(feature_names):
            count = int(central_result["central_count"][index])
            if count < 1:
                central_std = float("nan")
            elif central_result["central_min"][index] == central_result["central_max"][index]:
                central_std = 0.0
            else:
                avg = central_result["central_sum"][index] / count
                variance = max(
                    central_result["central_squared"][index] / count - avg * avg,
                    0.0,
                )
                central_std = float(np.sqrt(variance))
            if 0.3 <= central_std <= 1.5:
                cause = "dans la plage"
            elif central_std < 0.3:
                cause = (
                    "indicateur rare (p99=0; les valeurs p1–p99 sont constantes)"
                    if central_bounds[feature][1] == 0
                    else "faible dispersion centrale après transformation"
                )
            else:
                cause = "queue/distribution centrale encore étalée"
            central_values[feature] = {
                "feature": feature,
                "central_std": central_std,
                "cause": cause,
            }
        sample_raw = central_result["sample_raw"]
        sample_transformed = central_result["sample_transformed"]
        sample_imputed = central_result["sample_imputed"]
        if (
            sample_raw is None
            or sample_transformed is None
            or sample_imputed is None
            or len(sample_raw) != sample_count
        ):
            raise ValueError("L’échantillon Spearman n’a pas été entièrement constitué.")
        spearman_rows = _spearman_table(
            feature_names,
            sample_raw,
            sample_transformed,
            sample_imputed,
        )
        _dump_transformer(transformer, staged_scaler)
        loaded_transformer = joblib.load(staged_scaler)
        probe = loaded_transformer.transform(
            pd.DataFrame(sample_raw[:5, ::-1], columns=list(reversed(feature_names)))
        )
        expected_probe = sample_transformed[:5]
        if not np.allclose(probe, expected_probe, rtol=0, atol=1e-6):
            raise ValueError("Le transformeur joblib ne reproduit pas sa sortie.")
        _write_report(
            staged_report,
            feature_names,
            split_results,
            central_bounds,
            central_values,
            spearman_rows,
            copy_hashes,
            train_count,
            sample_count,
        )
        staged_dir.replace(destination_dir)
        staged_scaler.replace(scaler_path)
        staged_report.replace(report_path)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    shutil.rmtree(temporary_root, ignore_errors=True)
    return {
        "processed_dir": destination_dir,
        "scaler_path": scaler_path,
        "report_path": report_path,
        "central": central_values,
        "spearman": spearman_rows,
        "imputed": {split: result["imputed"] for split, result in split_results.items()},
        "copy_hashes": copy_hashes,
    }


def main() -> None:
    result = prepare_logz_data()
    print(f"Parquets log-z : {result['processed_dir']}")
    print(f"Transformeur : {result['scaler_path']}")
    print(f"Rapport : {result['report_path']}")


if __name__ == "__main__":
    main()
