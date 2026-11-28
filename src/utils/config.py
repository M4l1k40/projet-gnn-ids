from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load a YAML configuration and resolve its configured data paths."""
    path = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).resolve().parents[2] / "configs" / "data.yaml"
    )
    path = path.resolve()

    with path.open(encoding="utf-8") as config_file:
        config = yaml.safe_load(config_file)

    if not isinstance(config, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")

    paths = config.get("paths")
    if not isinstance(paths, dict):
        raise ValueError(f"Expected a 'paths' mapping in {path}")

    project_root = path.parent.parent
    required_paths = {"raw", "interim", "processed"}
    for name in (
        "raw",
        "interim",
        "processed",
        "processed_v3",
        "processed_v3_logz",
        "scaler_v3_logz",
        "p2_folds_source",
        "scaler_audit_v3",
        "normalization_v3_logz_report",
        "feature_list",
    ):
        configured_path = paths.get(name)
        if not isinstance(configured_path, str) or not configured_path:
            if name in required_paths:
                raise ValueError(f"Expected a non-empty 'paths.{name}' value in {path}")
            continue
        data_path = Path(configured_path)
        paths[name] = (
            data_path if data_path.is_absolute() else project_root / data_path
        ).resolve()

    return config
