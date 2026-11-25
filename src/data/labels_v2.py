"""Construction non destructive des labels CIC-IDS2017 version 2."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.utils.config import load_config

_BLOCKS = ("train", "val", "test")
_OUTPUT_COLUMNS = [
    "flow_id",
    "label_orig_multi",
    "label_orig_bin",
    "canonical_rule",
    "attempted",
    "changed",
    "label_v2_bin",
    "v2_family",
]


def load_labels_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Charge la configuration des labels v2 et conserve sa racine projet."""
    path = (
        Path(config_path)
        if config_path is not None
        else Path(__file__).resolve().parents[2] / "configs" / "labels.yaml"
    ).resolve()
    config = load_config(path)
    config["_project_root"] = path.parent.parent
    return config


def _configured_path(config: dict[str, Any], key: str) -> Path:
    value = config["paths"].get(key)
    if not isinstance(value, (str, Path)) or not str(value):
        raise ValueError(f"Chemin de configuration manquant : paths.{key}.")
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    root = Path(config.get("_project_root", Path(config["paths"]["processed"]).parent.parent))
    return (root / path).resolve()


def _validate_mapping(config: dict[str, Any]) -> dict[str, str]:
    mapping = config.get("label_rule_to_multi")
    if not isinstance(mapping, dict) or not mapping:
        raise ValueError("label_rule_to_multi doit définir une correspondance non vide.")
    if any(not isinstance(rule, str) or not isinstance(label, str) for rule, label in mapping.items()):
        raise TypeError("Chaque règle et classe canonique doit être une chaîne.")
    return mapping


def _family_labels(
    frame: pd.DataFrame,
    rule_labels: pd.Series,
    canonical: pd.Series,
    changed: np.ndarray,
    config: dict[str, Any],
) -> np.ndarray:
    families = config.get("families")
    if not isinstance(families, dict):
        raise ValueError("La configuration doit définir les familles de labels.")
    portscan_rule = families.get("portscan_infiltration_rule")
    server = families.get("server_response")
    if not isinstance(portscan_rule, str) or not isinstance(server, dict):
        raise ValueError("La configuration des familles de labels est invalide.")
    source_ip = str(server["source_ip"])
    destination_ip = str(server["destination_ip"])
    ftp_source_port = int(server["ftp_source_port"])

    original_benign = frame["label_multi"].eq("BENIGN").to_numpy()
    canonical_attack = canonical.ne("BENIGN").to_numpy()
    candidates = original_benign & canonical_attack
    portscan = candidates & rule_labels.eq(portscan_rule).to_numpy()
    server_response = candidates & (
        (
            frame["src_ip"].eq(source_ip)
            & frame["dst_ip"].eq(destination_ip)
        )
        | (frame["src_ip"].eq(source_ip) & frame["src_port"].eq(ftp_source_port))
    ).to_numpy()

    result = np.full(len(frame), "unchanged", dtype=object)
    result[changed] = "other_change"
    result[server_response] = "server_response"
    result[portscan] = "portscan_infiltration"
    return result


def _labels_for_frame(
    frame: pd.DataFrame,
    matched_audit: pd.DataFrame,
    mapping: dict[str, str],
    config: dict[str, Any],
) -> pd.DataFrame:
    rule_labels = matched_audit["label_rule"].astype("string").reset_index(drop=True)
    canonical = rule_labels.map(mapping).astype("string")
    original = frame["label_multi"].astype("string").reset_index(drop=True)
    changed = canonical.ne(original).to_numpy(dtype=bool)
    attempted = matched_audit["attempted_category"].to_numpy(dtype=np.float64) >= 0
    result = pd.DataFrame(
        {
            "flow_id": frame["flow_id"].astype("string").reset_index(drop=True),
            "label_orig_multi": original,
            "label_orig_bin": frame["label_bin"].astype("int8").reset_index(drop=True),
            "canonical_rule": canonical,
            "attempted": attempted,
            "changed": changed,
            "label_v2_bin": canonical.ne("BENIGN").to_numpy(dtype=np.int8),
            "v2_family": _family_labels(
                frame.reset_index(drop=True),
                rule_labels,
                canonical,
                changed,
                config,
            ),
        }
    )
    if result.isna().any().any():
        raise ValueError("Labels v2 construits avec des valeurs manquantes.")
    return result


def _report_text(labels: pd.DataFrame, block_counts: dict[str, int]) -> str:
    lines = [
        "# Labels v2 — audit et changements",
        "",
        "Ce fichier est un artefact séparé. Les Parquets train/val/test et l’audit d’origine "
        "ne sont pas modifiés.",
        "",
        "Les familles portscan_infiltration et server_response isolent respectivement les "
        "désaccords BENIGN associés à la règle Infiltration - Portscan et les réponses "
        "émises par 192.168.10.50 vers 172.16.0.1 (ou depuis le port source FTP 21). "
        "other_change regroupe les autres divergences; unchanged indique une classe canonique "
        "identique au label multi d’origine.",
        "",
        "## Changements par bloc et famille",
        "",
        "| Bloc | Famille | Flux | Changés |",
        "|---|---|---:|---:|",
    ]
    for block in _BLOCKS:
        frame = labels[labels["block"].eq(block)]
        for family in (
            "portscan_infiltration",
            "server_response",
            "other_change",
            "unchanged",
        ):
            selected = frame[frame["v2_family"].eq(family)]
            lines.append(
                f"| {block} | {family} | {len(selected)} | "
                f"{int(selected['changed'].sum())} |"
            )

    lines.extend(
        [
            "",
            "## Transitions de classe",
            "",
            "| Bloc | Classe d’origine | Classe canonique | Flux |",
            "|---|---|---|---:|",
        ]
    )
    transitions = (
        labels[labels["changed"]]
        .groupby(
            ["block", "label_orig_multi", "canonical_rule"],
            sort=True,
            observed=True,
        )
        .size()
    )
    for (block, original, canonical), count in transitions.items():
        lines.append(f"| {block} | {original} | {canonical} | {int(count)} |")

    lines.extend(
        [
            "",
            "## Flux Attempted",
            "",
            "| Bloc | Effectif | Attempted |",
            "|---|---:|---:|",
        ]
    )
    for block in _BLOCKS:
        frame = labels[labels["block"].eq(block)]
        lines.append(
            f"| {block} | {block_counts[block]} | {int(frame['attempted'].sum())} |"
        )
    lines.extend(
        [
            "",
            "Les règles sont des heuristiques d’audit, pas une vérité terrain. "
            "`attempted` indique `attempted_category >= 0`; `changed` compare la classe "
            "canonique au label multi d’origine. `label_v2_bin` vaut 1 lorsque la classe "
            "canonique n’est pas BENIGN.",
            "",
        ]
    )
    return "\n".join(lines)


def build_labels_v2(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construit labels_v2.parquet sans écraser les données sources ni une sortie existante."""
    project_config = load_labels_config() if config is None else config
    mapping = _validate_mapping(project_config)
    block_paths = {block: _configured_path(project_config, block) for block in _BLOCKS}
    audit_path = _configured_path(project_config, "audit")
    output_path = _configured_path(project_config, "output")
    report_path = _configured_path(project_config, "report")
    if output_path.exists():
        raise FileExistsError(f"Refus d’écraser la sortie existante : {output_path}.")
    if report_path.exists():
        raise FileExistsError(f"Refus d’écraser le rapport existant : {report_path}.")
    for path in (*block_paths.values(), audit_path):
        if not path.exists():
            raise FileNotFoundError(f"Fichier d’entrée introuvable : {path}.")

    audit = pd.read_parquet(
        audit_path,
        columns=["flow_id", "label_rule", "attempted_category"],
    )
    if audit["flow_id"].isna().any() or audit["flow_id"].duplicated().any():
        raise ValueError("label_audit.parquet doit avoir une clé flow_id non nulle et unique.")
    if audit[["label_rule", "attempted_category"]].isna().any().any():
        raise ValueError("label_audit.parquet contient des règles ou catégories manquantes.")
    audit["attempted_category"] = pd.to_numeric(
        audit["attempted_category"], errors="coerce"
    )
    if audit["attempted_category"].isna().any():
        raise ValueError("attempted_category doit contenir des valeurs numériques.")
    unknown_rules = sorted(set(audit["label_rule"].astype(str)) - set(mapping))
    if unknown_rules:
        raise ValueError("Règles absentes de label_rule_to_multi : " + ", ".join(unknown_rules))
    audit_index = audit.set_index("flow_id")

    pieces: list[pd.DataFrame] = []
    block_counts: dict[str, int] = {}
    for block in _BLOCKS:
        frame = pd.read_parquet(
            block_paths[block],
            columns=["flow_id", "label_bin", "label_multi", "src_ip", "dst_ip", "src_port"],
        )
        required = ["flow_id", "label_bin", "label_multi", "src_ip", "dst_ip", "src_port"]
        if frame[required].isna().any().any():
            raise ValueError(f"{block}.parquet contient des valeurs manquantes requises.")
        if frame["flow_id"].duplicated().any():
            raise ValueError(f"{block}.parquet contient des flow_id dupliqués.")
        if not frame["label_bin"].isin([0, 1]).all():
            raise ValueError(f"{block}.parquet contient un label_bin hors de 0/1.")
        positions = audit_index.index.get_indexer(frame["flow_id"])
        if np.any(positions < 0):
            raise ValueError(f"label_audit.parquet ne couvre pas toutes les lignes de {block}.")
        matched = audit_index.take(positions)
        labels = _labels_for_frame(
            frame,
            matched,
            mapping,
            project_config,
        )
        labels["block"] = block
        pieces.append(labels)
        block_counts[block] = len(labels)

    combined = pd.concat(pieces, ignore_index=True)
    if combined["flow_id"].duplicated().any():
        raise ValueError("Les Parquets train/val/test contiennent des flow_id dupliqués.")
    expected_rows = sum(block_counts.values())
    if len(combined) != expected_rows:
        raise ValueError(
            "L’effectif de labels_v2 ne correspond pas à la somme des Parquets train/val/test."
        )
    if combined.isna().any().any():
        raise ValueError("labels_v2 contient des valeurs manquantes.")
    result = combined[_OUTPUT_COLUMNS].copy()
    report = combined

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output_path, index=False)
    report_path.write_text(_report_text(report, block_counts), encoding="utf-8")
    return {
        "output_path": output_path,
        "report_path": report_path,
        "rows": len(result),
        "block_counts": block_counts,
        "attempted_by_block": {
            block: int(report.loc[report["block"].eq(block), "attempted"].sum())
            for block in _BLOCKS
        },
        "changed_by_block": {
            block: int(report.loc[report["block"].eq(block), "changed"].sum())
            for block in _BLOCKS
        },
    }


def _extended_coverage_text(
    labels: pd.DataFrame,
    missing_labels: pd.DataFrame,
) -> str:
    blocks = (*_BLOCKS, "gap")
    lines = [
        "## Couverture complète des labels v2",
        "",
        "`labels_v2_all.parquet` applique les mêmes règles à tous les flow_id de "
        "`label_audit.parquet`, y compris les flux hors des blocs V2. Le fichier "
        "`labels_v2.parquet` d’origine reste inchangé.",
        "",
        "### Familles par bloc V3",
        "",
        "| Bloc V3 | Famille | Flux | Changés |",
        "|---|---|---:|---:|",
    ]
    for block in blocks:
        selected_block = labels[labels["block"].eq(block)]
        for family in (
            "portscan_infiltration",
            "server_response",
            "other_change",
            "unchanged",
        ):
            selected = selected_block[selected_block["v2_family"].eq(family)]
            lines.append(
                f"| {block} | {family} | {len(selected)} | "
                f"{int(selected['changed'].sum())} |"
            )
    lines.extend(
        [
            "",
            "### Flux absents de l’ancien labels_v2, par bloc V3",
            "",
            "| Bloc V3 | Famille | Règle d’audit | Classe d’origine | Flux |",
            "|---|---|---|---|---:|",
        ]
    )
    breakdown = (
        missing_labels.groupby(
            ["block", "v2_family", "label_rule", "label_orig_multi"],
            sort=True,
            observed=True,
        )
        .size()
    )
    for (block, family, rule, original), count in breakdown.items():
        lines.append(
            f"| {block} | {family} | {rule} | {original} | {int(count)} |"
        )
    lines.extend(
        [
            "",
            f"Couverture complète de l’audit : {len(labels)} flux; V3 train/val/test : "
            f"{int(labels['block'].ne('gap').sum())} flux; absents de l’ancien "
            f"`labels_v2.parquet` dans ces blocs : {len(missing_labels)}. Ces IDs étaient hors des "
            "blocs V2; leurs labels sont calculés depuis `clean.parquet` et l’audit.",
            "",
        ]
    )
    return "\n".join(lines)


def build_labels_v2_all(
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construit labels_v2_all pour tous les flow_id audités sans modifier labels_v2."""
    project_config = load_labels_config() if config is None else config
    mapping = _validate_mapping(project_config)
    clean_path = _configured_path(project_config, "clean")
    audit_path = _configured_path(project_config, "audit")
    old_labels_path = _configured_path(project_config, "output")
    output_path = _configured_path(project_config, "output_all")
    report_path = _configured_path(project_config, "report")
    v3_dir = _configured_path(project_config, "processed_v3")
    if output_path.exists():
        raise FileExistsError(f"Refus d’écraser la sortie existante : {output_path}.")
    for path in (clean_path, audit_path, old_labels_path, report_path):
        if not path.exists():
            raise FileNotFoundError(f"Fichier d’entrée introuvable : {path}.")
    for block in _BLOCKS:
        if not (v3_dir / f"{block}.parquet").exists():
            raise FileNotFoundError(f"Bloc V3 introuvable : {v3_dir / f'{block}.parquet'}.")

    audit = pd.read_parquet(
        audit_path,
        columns=["flow_id", "label_rule", "attempted_category"],
    )
    clean = pd.read_parquet(
        clean_path,
        columns=[
            "flow_id",
            "label_bin",
            "label_multi",
            "src_ip",
            "dst_ip",
            "src_port",
        ],
    )
    required = ["flow_id", "label_bin", "label_multi", "src_ip", "dst_ip", "src_port"]
    if clean[required].isna().any().any() or clean["flow_id"].duplicated().any():
        raise ValueError("clean.parquet contient des clés dupliquées ou des valeurs requises manquantes.")
    if not clean["label_bin"].isin([0, 1]).all():
        raise ValueError("clean.parquet contient un label_bin hors de 0/1.")
    if audit.isna().any().any() or audit["flow_id"].duplicated().any():
        raise ValueError("label_audit.parquet contient des clés dupliquées ou des valeurs manquantes.")
    audit["attempted_category"] = pd.to_numeric(
        audit["attempted_category"], errors="coerce"
    )
    if audit["attempted_category"].isna().any():
        raise ValueError("attempted_category doit contenir des valeurs numériques.")
    unknown_rules = sorted(set(audit["label_rule"].astype(str)) - set(mapping))
    if unknown_rules:
        raise ValueError("Règles absentes de label_rule_to_multi : " + ", ".join(unknown_rules))
    if len(clean) != len(audit):
        raise ValueError("clean.parquet et label_audit.parquet n’ont pas le même effectif.")
    audit_index = audit.set_index("flow_id")
    positions = audit_index.index.get_indexer(clean["flow_id"])
    if np.any(positions < 0):
        raise ValueError("label_audit.parquet ne couvre pas tous les flow_id de clean.parquet.")
    matched = audit_index.take(positions).reset_index(drop=True)
    labels = _labels_for_frame(clean, matched, mapping, project_config)
    if len(labels) != len(audit) or labels["flow_id"].duplicated().any():
        raise ValueError("La sortie étendue ne contient pas une ligne unique par flow_id audité.")

    source_ids = pd.Index(clean["flow_id"])
    blocks = np.full(len(clean), "gap", dtype=object)
    assigned = np.zeros(len(clean), dtype=bool)
    for block in _BLOCKS:
        v3_ids = pd.read_parquet(v3_dir / f"{block}.parquet", columns=["flow_id"])[
            "flow_id"
        ]
        if v3_ids.isna().any() or v3_ids.duplicated().any():
            raise ValueError(f"Le bloc V3 {block} contient des flow_id invalides.")
        v3_positions = source_ids.get_indexer(v3_ids)
        if np.any(v3_positions < 0) or assigned[v3_positions].any():
            raise ValueError(f"Les flow_id du bloc V3 {block} sont hors source ou répétés.")
        blocks[v3_positions] = block
        assigned[v3_positions] = True
    labels["block"] = blocks

    old_labels = pd.read_parquet(old_labels_path, columns=_OUTPUT_COLUMNS)
    if old_labels["flow_id"].isna().any() or old_labels["flow_id"].duplicated().any():
        raise ValueError("labels_v2.parquet contient des clés invalides.")
    old_positions = source_ids.get_indexer(old_labels["flow_id"])
    if np.any(old_positions < 0):
        raise ValueError("labels_v2_all ne couvre pas tous les flow_id de labels_v2.")
    for column in _OUTPUT_COLUMNS[1:]:
        if not np.array_equal(
            labels[column].to_numpy()[old_positions],
            old_labels[column].to_numpy(),
        ):
            raise ValueError(
                f"labels_v2_all diffère de labels_v2 sur les IDs communs, colonne {column}."
            )

    missing_mask = (~labels["flow_id"].isin(old_labels["flow_id"])) & labels[
        "block"
    ].ne("gap")
    missing_labels = pd.DataFrame(
        {
            "block": labels.loc[missing_mask, "block"].to_numpy(),
            "v2_family": labels.loc[missing_mask, "v2_family"].to_numpy(),
            "label_rule": matched.loc[missing_mask, "label_rule"].to_numpy(),
            "label_orig_multi": labels.loc[missing_mask, "label_orig_multi"].to_numpy(),
        }
    )
    coverage_text = _extended_coverage_text(labels, missing_labels)
    report = report_path.read_text(encoding="utf-8")
    marker = "\n## Couverture complète des labels v2"
    if marker in report:
        report = report.split(marker, 1)[0].rstrip()
    report = report.rstrip() + "\n\n" + coverage_text

    output_path.parent.mkdir(parents=True, exist_ok=True)
    labels[_OUTPUT_COLUMNS].to_parquet(output_path, index=False)
    report_path.write_text(report, encoding="utf-8")
    return {
        "output_path": output_path,
        "report_path": report_path,
        "rows": len(labels),
        "v2_coverage_rows": len(old_labels),
        "v3_block_counts": {
            block: int(np.count_nonzero(blocks == block))
            for block in (*_BLOCKS, "gap")
        },
        "missing_from_old_v2": int(missing_mask.sum()),
        "missing_breakdown": missing_labels.groupby(
            ["block", "v2_family", "label_rule", "label_orig_multi"],
            sort=True,
            observed=True,
        ).size(),
    }


if __name__ == "__main__":
    result = build_labels_v2()
    print(
        f"Labels v2 : {result['rows']} flux écrits dans {result['output_path']} ; "
        f"rapport : {result['report_path']}."
    )
