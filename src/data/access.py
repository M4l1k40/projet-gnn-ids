"""Helpers read-only pour accéder aux jeux et métadonnées préparés."""

import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
import yaml

from src.data.folds import get_fold
from src.data.p2 import load_p2
from src.utils.config import load_config

_SPLITS = {"train", "val", "test"}


def _project_paths() -> tuple[Path, Path]:
    config = load_config()
    processed = Path(config["paths"]["processed"])
    return processed, processed.parent.parent


def _validate_split(split: str) -> None:
    if split not in _SPLITS:
        raise ValueError("split doit être 'train', 'val' ou 'test'.")


def load_split(
    split: str,
    columns: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Charge un split, éventuellement limité aux colonnes demandées.
    Exemple : `train = load_split("train", ["flow_id", "label_bin"])`.
    """
    _validate_split(split)
    processed, _ = _project_paths()
    path = processed / f"{split}.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Split introuvable : {path}.")
    return pd.read_parquet(path, columns=list(columns) if columns is not None else None)


def feature_names() -> list[str]:
    """Lit la liste ordonnée des features utilisées par le scaler final.
    Exemple : `features = feature_names()`.
    """
    _, project_root = _project_paths()
    path = project_root / "models" / "features.json"
    if not path.exists():
        raise FileNotFoundError(f"Liste de features introuvable : {path}.")
    features = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(features, list) or not all(
        isinstance(feature, str) for feature in features
    ):
        raise ValueError(f"{path} doit contenir une liste JSON de chaînes.")
    return features


def multiclass_classes() -> list[str]:
    """Lit les classes retenues pour les expériences multiclasse.
    Exemple : `classes = multiclass_classes()`.
    """
    _, project_root = _project_paths()
    path = project_root / "configs" / "classes.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Configuration des classes introuvable : {path}.")
    classes_config = yaml.safe_load(path.read_text(encoding="utf-8"))
    classes = classes_config.get("multiclass_classes") if isinstance(
        classes_config, dict
    ) else None
    if not isinstance(classes, list) or not all(
        isinstance(label, str) for label in classes
    ):
        raise ValueError(f"{path} doit définir une liste multiclass_classes.")
    return classes


def load_meta() -> pd.DataFrame:
    """Charge les métadonnées alignées par `flow_id` aux splits conservés.
    Exemple : `meta = load_meta()`.
    """
    processed, _ = _project_paths()
    path = processed / "meta.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Métadonnées introuvables : {path}.")
    return pd.read_parquet(path)


def strict_test_mask() -> pd.Series:
    """Construit le masque strict dans l'ordre des lignes de test.parquet.
    Exemple : `test_strict = test.loc[strict_test_mask()]`.
    """
    processed, _ = _project_paths()
    test_path = processed / "test.parquet"
    meta_path = processed / "meta.parquet"
    for path in (test_path, meta_path):
        if not path.exists():
            raise FileNotFoundError(f"Fichier requis introuvable : {path}.")
    test = pd.read_parquet(test_path, columns=["flow_id"])
    meta = pd.read_parquet(meta_path, columns=["flow_id", "seen_in_train"])
    if meta["flow_id"].duplicated().any():
        raise ValueError("meta.parquet contient des flow_id dupliqués.")
    if test["flow_id"].isna().any():
        raise ValueError("test.parquet contient des flow_id manquants.")
    flags_by_id = meta.set_index("flow_id")["seen_in_train"]
    flags = test["flow_id"].map(flags_by_id)
    if flags.isna().any():
        missing_count = int(flags.isna().sum())
        raise ValueError(
            f"seen_in_train absent ou nul pour {missing_count} flux du test."
        )
    if not flags.map(lambda value: isinstance(value, (bool, np.bool_))).all():
        raise TypeError("seen_in_train doit contenir des booléens pour le test.")
    return flags.eq(False).rename("strict_test")


def load_audit_labels(split: str) -> pd.DataFrame:
    """Joint les règles d'audit au split par `flow_id`, en gardant son ordre.
    Exemple : `audit = load_audit_labels("test")`.
    """
    _validate_split(split)
    processed, _ = _project_paths()
    split_path = processed / f"{split}.parquet"
    audit_path = processed / "label_audit.parquet"
    for path in (split_path, audit_path):
        if not path.exists():
            raise FileNotFoundError(f"Fichier requis introuvable : {path}.")
    split_ids = pd.read_parquet(split_path, columns=["flow_id"])
    audit = pd.read_parquet(
        audit_path,
        columns=["flow_id", "label_rule", "attempted_category"],
    )
    if audit["flow_id"].duplicated().any():
        raise ValueError("label_audit.parquet contient des flow_id dupliqués.")
    labels_by_id = audit.set_index("flow_id")
    positions = labels_by_id.index.get_indexer(split_ids["flow_id"])
    missing_count = int((positions < 0).sum())
    if missing_count:
        raise ValueError(
            f"label_audit.parquet ne couvre pas {missing_count} flux de {split}."
        )
    result = labels_by_id.take(positions)[
        ["label_rule", "attempted_category"]
    ].copy()
    result.index = split_ids.index
    return result


def get_cv_fold(k: int) -> tuple[np.ndarray, np.ndarray]:
    """Renvoie les positions train et validation du pli CV purgé `k`.
    Exemple : `train_idx, val_idx = get_cv_fold(0)`.
    """
    return get_fold(k, config=load_config())


def load_p2_fold(name: str) -> pd.DataFrame:
    """Charge les flux normalisés d'un pli P2/E5 avec leur rôle.
    Exemple : `day_test = load_p2_fold("day_Tuesday")`.
    """
    return load_p2(name, config=load_config())
