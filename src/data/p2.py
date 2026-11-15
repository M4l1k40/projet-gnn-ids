"""Leave-one-day/family generalization folds with fold-specific scaling."""

import re
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import joblib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.dataset as ds
import pyarrow.parquet as pq
import yaml
from sklearn.preprocessing import StandardScaler

from src.data.schema import ID_COLS, META_COLS, TARGET_COLS
from src.utils.config import load_config

_KEY_COLUMNS = ("flow_id", "day", "label_multi", "ts_end")
_DAYS_HELD_OUT = ("Tuesday", "Wednesday", "Thursday", "Friday")
_BATCH_SIZE = 50_000
_TIME_TOLERANCE_SECONDS = 1e-5


def _feature_columns(schema: pa.Schema) -> list[str]:
    excluded = set(ID_COLS + TARGET_COLS + META_COLS)
    features: list[str] = []
    for field in schema:
        if field.name in excluded:
            continue
        if pa.types.is_float32(field.type):
            features.append(field.name)
        elif (
            pa.types.is_integer(field.type)
            or pa.types.is_floating(field.type)
            or pa.types.is_decimal(field.type)
        ):
            raise ValueError(
                f"{field.name} : type numérique inattendu {field.type}; "
                "les features P2 doivent être float32."
            )
    if not features:
        raise ValueError("Aucune feature float32 dans clean.parquet.")
    return features


def _prepare_features(values: np.ndarray, method: str) -> np.ndarray:
    matrix = np.asarray(values, dtype=np.float64)
    if not np.isfinite(matrix).all():
        raise ValueError("Les features P2 contiennent des valeurs non finies.")
    if method == "log1p_standard":
        if (matrix < 0).any():
            raise ValueError("log1p_standard exige des features non négatives.")
        return np.log1p(matrix)
    if method != "standard":
        raise ValueError(f"Méthode de normalisation inconnue : {method}.")
    return matrix


def _load_families(
    project_root: Path,
    families: dict[str, list[str]] | None,
    families_path: str | Path | None,
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    if families is not None:
        raw = families
    else:
        path = (
            Path(families_path)
            if families_path is not None
            else project_root / "configs" / "attack_families.yaml"
        )
        if not path.exists():
            raise FileNotFoundError(f"Configuration des familles introuvable : {path}.")
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("attack_families.yaml doit contenir une map YAML.")
        raw = loaded

    rare = raw.get("rare_excluded", [])
    if not isinstance(rare, list) or not all(isinstance(item, str) for item in rare):
        raise ValueError("rare_excluded doit être une liste de noms de classes.")
    family_map: dict[str, tuple[str, ...]] = {}
    assigned: dict[str, str] = {}
    for family, members in raw.items():
        if family == "rare_excluded":
            continue
        if not isinstance(members, list) or not all(
            isinstance(member, str) for member in members
        ):
            raise ValueError(f"La famille {family} doit être une liste de classes.")
        family_map[str(family)] = tuple(members)
        for member in members:
            if member in assigned:
                raise ValueError(
                    f"{member} appartient à la fois à {assigned[member]} et {family}."
                )
            assigned[member] = str(family)
    if not family_map:
        raise ValueError("Aucune famille d’attaque n’est configurée.")
    return family_map, tuple(rare)


def _read_validation_ids(val_path: Path) -> set[str]:
    if not val_path.exists():
        raise FileNotFoundError(f"Split val introuvable : {val_path}.")
    val_file = pq.ParquetFile(val_path)
    result: set[str] = set()
    for batch in val_file.iter_batches(columns=["flow_id"], batch_size=_BATCH_SIZE):
        flow_ids = batch.column(0).to_pylist()
        if any(flow_id is None for flow_id in flow_ids):
            raise ValueError(f"{val_path} contient des flow_id manquants.")
        result.update(str(flow_id) for flow_id in flow_ids)
    if len(result) != val_file.metadata.num_rows:
        raise ValueError(f"{val_path} contient des flow_id dupliqués.")
    return result


def _purge_validation_neighbours(
    keys: pd.DataFrame,
    roles: np.ndarray,
    purge_seconds: float,
) -> None:
    if purge_seconds == 0:
        return
    times = pd.to_numeric(keys["ts_end"], errors="coerce").to_numpy(
        dtype=np.float64
    )
    for indexes in keys.groupby(
        ["day", "label_multi"],
        sort=False,
        observed=True,
    ).indices.values():
        indexes = np.asarray(indexes, dtype=np.int64)
        validation = indexes[roles[indexes] == "val"]
        training = indexes[roles[indexes] == "train"]
        if not len(validation) or not len(training):
            continue
        validation_times = np.sort(times[validation])
        candidate_times = times[training]
        positions = np.searchsorted(validation_times, candidate_times)
        nearest = np.full(len(training), np.inf, dtype=np.float64)
        has_left = positions > 0
        if has_left.any():
            nearest[has_left] = np.minimum(
                nearest[has_left],
                candidate_times[has_left] - validation_times[positions[has_left] - 1],
            )
        has_right = positions < len(validation_times)
        if has_right.any():
            nearest[has_right] = np.minimum(
                nearest[has_right],
                validation_times[positions[has_right]] - candidate_times[has_right],
            )
        roles[training[nearest + _TIME_TOLERANCE_SECONDS < purge_seconds]] = "purged"


def _fold_roles(
    keys: pd.DataFrame,
    validation_ids: set[str],
    family_map: dict[str, tuple[str, ...]],
    rare_classes: tuple[str, ...],
    fold_kind: str,
    held_out: str,
    purge_seconds: float,
) -> np.ndarray:
    days = keys["day"].astype(str).to_numpy()
    labels = keys["label_multi"].astype(str).to_numpy()
    flow_ids = keys["flow_id"].astype(str)
    roles = np.full(len(keys), "train", dtype=object)
    if rare_classes:
        roles[np.isin(labels, rare_classes)] = "excluded"

    if fold_kind == "day":
        test_mask = (days == held_out) & (roles != "excluded")
    elif fold_kind == "family":
        test_mask = np.isin(labels, family_map[held_out]) & (roles != "excluded")
    else:
        raise ValueError(f"Type de pli inconnu : {fold_kind}.")
    roles[test_mask] = "test"

    validation_mask = flow_ids.isin(validation_ids).to_numpy() & (roles == "train")
    monday_benign = (days == "Monday") & (labels == "BENIGN")
    validation_mask &= ~monday_benign
    roles[validation_mask] = "val"
    _purge_validation_neighbours(keys, roles, purge_seconds)
    return roles


def _fit_fold_scaler(
    clean_path: Path,
    features: list[str],
    roles: np.ndarray,
    method: str,
    batch_size: int,
) -> tuple[StandardScaler, int]:
    scaler = StandardScaler()
    train_rows = 0
    offset = 0
    for batch in pq.ParquetFile(clean_path).iter_batches(
        columns=features,
        batch_size=batch_size,
    ):
        frame = batch.to_pandas()
        stop = offset + len(frame)
        selected = roles[offset:stop] == "train"
        if selected.any():
            values = frame.loc[selected, features].to_numpy(dtype=np.float64)
            scaler.partial_fit(_prepare_features(values, method))
            train_rows += int(selected.sum())
        offset = stop
    if offset != len(roles):
        raise ValueError("Lecture des features incomplète pendant l’ajustement P2.")
    if train_rows == 0:
        raise ValueError("Le train du pli P2 est vide; scaler impossible à ajuster.")
    if int(np.asarray(scaler.n_samples_seen_).max()) != train_rows:
        raise ValueError("Scaler P2 non ajusté sur toutes les lignes train.")
    return scaler, train_rows


def _fold_summary(
    pli: str,
    roles: np.ndarray,
    labels: np.ndarray,
    train_rows: int,
) -> dict[str, Any]:
    train_classes = sorted(set(labels[roles == "train"]))
    validation_classes = sorted(set(labels[roles == "val"]))
    test_classes = sorted(set(labels[roles == "test"]))
    return {
        "pli": pli,
        "train_rows": train_rows,
        "validation_rows": int(np.count_nonzero(roles == "val")),
        "test_rows": int(np.count_nonzero(roles == "test")),
        "purged_rows": int(np.count_nonzero(roles == "purged")),
        "excluded_rows": int(np.count_nonzero(roles == "excluded")),
        "train_classes": train_classes,
        "validation_classes": validation_classes,
        "test_classes": test_classes,
        "test_classes_absent_from_train": sorted(
            set(test_classes) - set(train_classes)
        ),
    }


def _write_p2_report(
    path: Path,
    summaries: list[dict[str, Any]],
    normalization_method: str,
    purge_minutes: float,
) -> None:
    lines = [
        "# Splits de généralisation P2 / E5",
        "",
        f"- Normalisation par pli : `{normalization_method}`, ajustée uniquement sur le train non purgé.",
        f"- Purge : {purge_minutes:g} minutes entre validation et train du même jour et de la même classe.",
        "- Les plis partent de tous les flux de `clean.parquet`, y compris ceux absents des splits finaux "
        "après leurs gaps; les features ne sont pas dupliquées dans `p2_folds.parquet`.",
        "- Les flux `Heartbleed` et `Infiltration` de `rare_excluded` ont le rôle `excluded`.",
        "- Les flux BENIGN du lundi restent toujours en train, même s’ils apparaissent dans `val.parquet`.",
        "",
        "| Pli | Lignes train | Lignes val | Lignes test | Purgés | Exclus | Classes train | Classes val | Classes test | Test absent du train |",
        "|---|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary['pli']} | {summary['train_rows']} | "
            f"{summary['validation_rows']} | {summary['test_rows']} | "
            f"{summary['purged_rows']} | {summary['excluded_rows']} | "
            f"{', '.join(summary['train_classes']) or 'aucune'} | "
            f"{', '.join(summary['validation_classes']) or 'aucune'} | "
            f"{', '.join(summary['test_classes']) or 'aucune'} | "
            f"{', '.join(summary['test_classes_absent_from_train']) or 'aucune'} |"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_p2_folds(
    config: dict[str, Any] | None = None,
    *,
    clean_path: str | Path | None = None,
    val_path: str | Path | None = None,
    processed_dir: str | Path | None = None,
    output_path: str | Path | None = None,
    models_dir: str | Path | None = None,
    report_path: str | Path | None = None,
    families_path: str | Path | None = None,
    families: dict[str, list[str]] | None = None,
    batch_size: int = _BATCH_SIZE,
) -> tuple[Path, Path, list[dict[str, Any]]]:
    """Create role-only P2 mapping and train-only scaler files for every fold."""
    project_config = load_config() if config is None else config
    interim_dir = Path(project_config["paths"]["interim"])
    configured_processed = Path(project_config["paths"]["processed"])
    data_dir = Path(processed_dir) if processed_dir is not None else configured_processed
    project_root = configured_processed.parent.parent
    source_path = Path(clean_path) if clean_path is not None else interim_dir / "clean.parquet"
    validation_path = (
        Path(val_path) if val_path is not None else data_dir / "val.parquet"
    )
    mapping_path = (
        Path(output_path) if output_path is not None else data_dir / "p2_folds.parquet"
    )
    model_dir = (
        Path(models_dir)
        if models_dir is not None
        else project_root / "models" / "p2"
    )
    report = (
        Path(report_path)
        if report_path is not None
        else project_root / "reports" / "p2_report.md"
    )
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")
    if not source_path.exists():
        raise FileNotFoundError(f"clean.parquet introuvable : {source_path}.")

    family_map, rare_classes = _load_families(project_root, families, families_path)
    normalization_method = str(project_config["normalization"]["method"])
    if normalization_method not in {"standard", "log1p_standard"}:
        raise ValueError(f"Méthode de normalisation P2 inconnue : {normalization_method}.")
    cv_config = project_config["cv"]
    purge_minutes = float(cv_config["purge_minutes"])
    if not np.isfinite(purge_minutes) or purge_minutes < 0:
        raise ValueError("cv.purge_minutes doit être positif ou nul et fini.")

    source = pq.ParquetFile(source_path)
    features = _feature_columns(source.schema_arrow)
    required_keys = set(_KEY_COLUMNS)
    missing_columns = required_keys - set(source.schema_arrow.names)
    if missing_columns:
        raise ValueError(
            "Colonnes absentes de clean.parquet : "
            + ", ".join(sorted(missing_columns))
            + "."
        )
    key_batches = [
        batch.to_pandas()
        for batch in source.iter_batches(
            columns=list(_KEY_COLUMNS),
            batch_size=batch_size,
        )
    ]
    if not key_batches:
        raise ValueError(f"{source_path} est vide.")
    keys = pd.concat(key_batches, ignore_index=True)
    del key_batches
    if len(keys) != source.metadata.num_rows:
        raise ValueError("Lecture incomplète des clés de clean.parquet.")
    if keys["flow_id"].duplicated().any():
        raise ValueError("flow_id doit être unique dans clean.parquet.")
    times = pd.to_numeric(keys["ts_end"], errors="coerce").to_numpy(dtype=np.float64)
    if not np.isfinite(times).all():
        raise ValueError("ts_end de clean.parquet contient des valeurs non finies.")
    validation_ids = _read_validation_ids(validation_path)
    validation_present = keys["flow_id"].astype(str).isin(validation_ids)
    if int(validation_present.sum()) != len(validation_ids):
        raise ValueError("Certains flow_id de val.parquet sont absents de clean.parquet.")

    fold_specs = [
        (f"day_{day}", "day", day) for day in _DAYS_HELD_OUT
    ] + [
        (f"family_{family}", "family", family) for family in family_map
    ]
    mapping_path.parent.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    writer: pq.ParquetWriter | None = None

    with TemporaryDirectory(prefix=".p2-folds-", dir=mapping_path.parent) as temp_dir:
        staged_mapping = Path(temp_dir) / mapping_path.name
        try:
            for pli, fold_kind, held_out in fold_specs:
                roles = _fold_roles(
                    keys,
                    validation_ids,
                    family_map,
                    rare_classes,
                    fold_kind,
                    held_out,
                    purge_minutes * 60,
                )
                scaler, train_rows = _fit_fold_scaler(
                    source_path,
                    features,
                    roles,
                    normalization_method,
                    batch_size,
                )
                with TemporaryDirectory(prefix=".p2-scaler-", dir=model_dir) as temp_model:
                    staged_scaler = Path(temp_model) / f"{pli}.joblib"
                    joblib.dump(scaler, staged_scaler)
                    staged_scaler.replace(model_dir / f"{pli}.joblib")
                summaries.append(_fold_summary(pli, roles, keys["label_multi"].astype(str).to_numpy(), train_rows))

                for start in range(0, len(keys), batch_size):
                    stop = min(start + batch_size, len(keys))
                    output = pd.DataFrame(
                        {
                            "flow_id": keys["flow_id"]
                            .iloc[start:stop]
                            .astype("string")
                            .reset_index(drop=True),
                            "pli": pd.Series([pli] * (stop - start), dtype="string"),
                            "role": pd.Series(roles[start:stop], dtype="string"),
                        }
                    )
                    table = pa.Table.from_pandas(output, preserve_index=False)
                    if writer is None:
                        writer = pq.ParquetWriter(staged_mapping, table.schema)
                    else:
                        table = table.cast(writer.schema)
                    writer.write_table(table, row_group_size=batch_size)
        finally:
            if writer is not None:
                writer.close()

        expected_rows = len(keys) * len(fold_specs)
        mapping_rows = (
            pq.ParquetFile(staged_mapping).metadata.num_rows if staged_mapping.exists() else 0
        )
        if writer is None or mapping_rows != expected_rows:
            raise ValueError(
                f"p2_folds.parquet contient {mapping_rows} lignes au lieu de "
                f"{expected_rows}."
            )
        staged_mapping.replace(mapping_path)

    _write_p2_report(report, summaries, normalization_method, purge_minutes)
    for summary in summaries:
        missing_train = summary["test_classes_absent_from_train"]
        print(
            f"{summary['pli']}: test absent du train = "
            f"{', '.join(missing_train) if missing_train else 'aucune'}"
        )
    print(f"Écrit {len(keys) * len(fold_specs)} rôles dans {mapping_path}.")
    return mapping_path, report, summaries


def load_p2(
    pli: str,
    config: dict[str, Any] | None = None,
    *,
    clean_path: str | Path | None = None,
    processed_dir: str | Path | None = None,
    models_dir: str | Path | None = None,
    batch_size: int = _BATCH_SIZE,
) -> pd.DataFrame:
    """Load one P2 fold from clean.parquet and apply its train-only scaler."""
    if not re.fullmatch(r"(day|family)_[A-Za-z0-9_-]+", pli):
        raise ValueError(f"Identifiant de pli P2 invalide : {pli}.")
    project_config = load_config() if config is None else config
    interim_dir = Path(project_config["paths"]["interim"])
    configured_processed = Path(project_config["paths"]["processed"])
    data_dir = Path(processed_dir) if processed_dir is not None else configured_processed
    project_root = configured_processed.parent.parent
    source_path = Path(clean_path) if clean_path is not None else interim_dir / "clean.parquet"
    mapping_path = data_dir / "p2_folds.parquet"
    model_dir = (
        Path(models_dir)
        if models_dir is not None
        else project_root / "models" / "p2"
    )
    scaler_path = model_dir / f"{pli}.joblib"
    if not source_path.exists():
        raise FileNotFoundError(f"clean.parquet introuvable : {source_path}.")
    if not mapping_path.exists():
        raise FileNotFoundError(f"p2_folds.parquet introuvable : {mapping_path}.")
    if not scaler_path.exists():
        raise FileNotFoundError(f"Scaler du pli introuvable : {scaler_path}.")
    if batch_size < 1:
        raise ValueError("batch_size doit être supérieur à zéro.")

    source = pq.ParquetFile(source_path)
    features = _feature_columns(source.schema_arrow)
    scaler = joblib.load(scaler_path)
    if int(scaler.n_features_in_) != len(features):
        raise ValueError("Le scaler P2 n’a pas le même nombre de features que clean.parquet.")
    dataset = ds.dataset(mapping_path, format="parquet")
    scanner = dataset.scanner(
        columns=["flow_id", "role"],
        filter=ds.field("pli") == pli,
        batch_size=batch_size,
    )
    roles_by_flow_id: dict[str, str] = {}
    for batch in scanner.to_batches():
        frame = batch.to_pandas()
        for flow_id, role in zip(frame["flow_id"], frame["role"]):
            key = str(flow_id)
            if key in roles_by_flow_id:
                raise ValueError(f"flow_id répété dans le pli {pli} : {key}.")
            roles_by_flow_id[key] = str(role)
    if not roles_by_flow_id:
        raise ValueError(f"Aucune ligne trouvée pour le pli {pli}.")

    columns = list(dict.fromkeys(ID_COLS + TARGET_COLS + ["day"] + features))
    missing = set(columns) - set(source.schema_arrow.names)
    if missing:
        raise ValueError(
            "Colonnes absentes de clean.parquet : " + ", ".join(sorted(missing)) + "."
        )
    chunks: list[pd.DataFrame] = []
    processed_rows = 0
    method = str(project_config["normalization"]["method"])
    for batch in source.iter_batches(columns=columns, batch_size=batch_size):
        frame = batch.to_pandas()
        flow_ids = frame["flow_id"].astype(str).tolist()
        roles: list[str] = []
        for flow_id in flow_ids:
            try:
                roles.append(roles_by_flow_id.pop(flow_id))
            except KeyError as error:
                raise ValueError(
                    f"flow_id absent du mapping du pli {pli} : {flow_id}."
                ) from error
        values = _prepare_features(
            frame[features].to_numpy(dtype=np.float64, copy=False),
            method,
        )
        transformed = scaler.transform(values).astype(np.float32)
        if not np.isfinite(transformed).all():
            raise ValueError(f"Normalisation non finie pour le pli {pli}.")
        for index, feature in enumerate(features):
            frame[feature] = transformed[:, index]
        frame["role"] = pd.Series(roles, dtype="string")
        chunks.append(frame)
        processed_rows += len(frame)
    if roles_by_flow_id:
        raise ValueError(
            f"{len(roles_by_flow_id)} flow_id du mapping du pli {pli} absents de clean.parquet."
        )
    if processed_rows != source.metadata.num_rows:
        raise ValueError("load_p2 n’a pas lu toutes les lignes clean.parquet.")
    return pd.concat(chunks, ignore_index=True)


if __name__ == "__main__":
    build_p2_folds()
