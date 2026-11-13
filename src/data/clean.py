"""Nettoyage en flux des CSV CIC-IDS2017 avant construction du schéma final."""

from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from src.utils.config import load_config

_TAILLE_BLOC = 50_000
_RENOMMAGE = {
    "Flow ID": "orig_flow_id",
    "Source IP": "src_ip",
    "Destination IP": "dst_ip",
    "Source Port": "src_port",
    "Destination Port": "dst_port",
    "Label": "label_multi",
}
_COLONNES_HORS_FEATURES = {
    "orig_flow_id",
    "src_ip",
    "dst_ip",
    "src_port",
    "dst_port",
    "Timestamp",
    "label_multi",
    "day",
    "source_file",
}
_PLAGES_PORT = np.iinfo(np.int32)


def _jour_depuis_nom(nom_fichier: str) -> str:
    nom = nom_fichier.casefold()
    for jour in ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday"):
        if jour.casefold() in nom:
            return jour
    raise ValueError(f"Jour introuvable dans le nom du fichier : {nom_fichier}.")


def _compter_labels(labels: pd.Series) -> Counter[str]:
    return Counter(
        "(label manquant)" if pd.isna(label) else str(label) for label in labels
    )


def _mettre_a_jour_lignes_par_fichier(
    statistiques: dict[str, dict[str, Any]], lignes: pd.DataFrame, etape: int
) -> None:
    comptes = lignes["source_file"].value_counts()
    for nom_fichier, compte in comptes.items():
        statistiques[str(nom_fichier)]["apres"][etape] += int(compte)


def _valider_et_convertir_port(
    lignes: pd.DataFrame, colonne: str, nom_fichier: str
) -> None:
    valeurs = pd.to_numeric(lignes[colonne], errors="coerce").to_numpy(
        dtype=np.float64, na_value=np.nan
    )
    invalides = (
        ~np.isfinite(valeurs)
        | (valeurs != np.floor(valeurs))
        | (valeurs < _PLAGES_PORT.min)
        | (valeurs > _PLAGES_PORT.max)
    )
    nombre_invalide = int(invalides.sum())
    if nombre_invalide:
        raise ValueError(
            f"{nom_fichier}, {colonne} : {nombre_invalide} valeur(s) "
            "impossible(s) à convertir en int32."
        )
    lignes[colonne] = valeurs.astype(np.int32)


def _rendre_rapport(
    statistiques: dict[str, dict[str, Any]],
    classes_avant: Counter[str],
    classes_apres: Counter[str],
    doublons: Counter[tuple[str, str]],
    colonnes_nan: Counter[tuple[str, str]],
    colonnes_inf: Counter[tuple[str, str]],
    colonnes_supprimees: list[str],
    features_finales: list[str],
    chemin_sortie: Path,
) -> str:
    etapes = range(1, 11)
    lignes = [
        "# Rapport de nettoyage CIC-IDS2017",
        "",
        f"- Fichiers traités : {len(statistiques)}",
        f"- Fichier Parquet : `{chemin_sortie}`",
        f"- Nombre final de lignes : {sum(item['apres'][10] for item in statistiques.values())}",
        f"- Nombre final de features : {len(features_finales)}",
        "",
        "## Lignes par fichier et par étape",
        "",
        "| Fichier | Jour | Lues | Après étape 1 | Après étape 2 | Après étape 3 | Après étape 4 | Après étape 5 | Après étape 6 | Après étape 7 | Après étape 8 | Après étape 9 | Après étape 10 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for nom_fichier, item in statistiques.items():
        comptes = [str(item["lues"])]
        comptes.extend(str(item["apres"][etape]) for etape in etapes)
        lignes.append(
            f"| {nom_fichier} | {item['jour']} | " + " | ".join(comptes) + " |"
        )

    lignes.extend(
        [
            "",
            "## Causes de suppression de lignes",
            "",
            "| Fichier | Lignes vides | Sans Timestamp | Avec inf/-inf dans les features | Avec NaN dans les features seulement | Lignes supprimées à l’étape 5 | Doublons supprimés |",
            "|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for nom_fichier, item in statistiques.items():
        lignes.append(
            f"| {nom_fichier} | {item['vides']} | {item['sans_timestamp']} | "
            f"{item['lignes_inf']} | {item['lignes_nan_seulement']} | "
            f"{item['lignes_features_supprimees']} | {item['doublons']} |"
        )

    lignes.extend(["", "## Cellules NaN et infini par feature", ""])
    details_features = [
        (nom_fichier, colonne)
        for nom_fichier, colonne in sorted(set(colonnes_nan) | set(colonnes_inf))
    ]
    if details_features:
        lignes.extend(
            [
                "| Fichier | Feature | NaN | inf/-inf remplacés par NaN |",
                "|---|---|---:|---:|",
            ]
        )
        for nom_fichier, colonne in details_features:
            lignes.append(
                f"| {nom_fichier} | {colonne} | "
                f"{colonnes_nan[(nom_fichier, colonne)]} | "
                f"{colonnes_inf[(nom_fichier, colonne)]} |"
            )
    else:
        lignes.append("Aucune cellule NaN ni infinie dans les features.")

    lignes.extend(["", "## Doublons supprimés par jour et par classe", ""])
    doublons_positifs = {
        cle: compte for cle, compte in doublons.items() if compte > 0
    }
    if doublons_positifs:
        lignes.extend(
            [
                "| Jour | Classe | Doublons supprimés |",
                "|---|---|---:|",
            ]
        )
        for (jour, classe), compte in sorted(doublons_positifs.items()):
            lignes.append(f"| {jour} | {classe} | {compte} |")
    else:
        lignes.append("Aucun doublon exact supprimé.")

    lignes.extend(["", "## Classes avant et après nettoyage", ""])
    toutes_les_classes = sorted(set(classes_avant) | set(classes_apres))
    lignes.extend(
        [
            "| Classe | Avant suppression des lignes invalides/doublons | Après nettoyage |",
            "|---|---:|---:|",
        ]
    )
    for classe in toutes_les_classes:
        lignes.append(
            f"| {classe} | {classes_avant[classe]} | {classes_apres[classe]} |"
        )
    classes_perdues = sorted(set(classes_avant) - set(classes_apres))
    if classes_perdues:
        lignes.extend(
            [
                "",
                "**ATTENTION — classes absentes après nettoyage :** "
                + ", ".join(classes_perdues)
                + ".",
            ]
        )
    else:
        lignes.extend(["", "Aucune classe présente avant nettoyage n’a été perdue."])

    lignes.extend(["", "## Colonnes supprimées", ""])
    if colonnes_supprimees:
        lignes.extend(f"- `{colonne}`" for colonne in colonnes_supprimees)
    else:
        lignes.append("Aucune.")
    lignes.extend(["", "## Features conservées", ""])
    if features_finales:
        lignes.extend(f"- `{colonne}`" for colonne in features_finales)
    else:
        lignes.append("Aucune.")
    return "\n".join(lignes) + "\n"


def clean_raw(
    config: dict[str, Any] | None = None,
    *,
    chunksize: int = _TAILLE_BLOC,
    report_path: Path | None = None,
) -> Path:
    """Nettoie les CSV par blocs et écrit clean_raw.parquet et son rapport."""
    project_config = load_config() if config is None else config
    if chunksize < 1:
        raise ValueError("chunksize doit être supérieur à zéro.")

    raw_directory = Path(project_config["paths"]["raw"]) / project_config["raw_subdir"]
    interim_directory = Path(project_config["paths"]["interim"])
    output_path = interim_directory / "clean_raw.parquet"
    interim_directory.mkdir(parents=True, exist_ok=True)
    fichiers = sorted(raw_directory.glob("*.csv"))
    if not fichiers:
        raise FileNotFoundError(f"Aucun fichier CSV trouvé dans {raw_directory}.")

    statistiques: dict[str, dict[str, Any]] = {}
    classes_avant: Counter[str] = Counter()
    classes_apres: Counter[str] = Counter()
    doublons: Counter[tuple[str, str]] = Counter()
    colonnes_nan: Counter[tuple[str, str]] = Counter()
    colonnes_inf: Counter[tuple[str, str]] = Counter()
    empreintes_vues: set[int] = set()
    fichiers_etape: list[Path] = []
    colonnes_features: list[str] | None = None
    plages_features: dict[str, list[float]] = {}
    colonnes_dupliquees_supprimees: set[str] = set()

    with TemporaryDirectory(prefix="nettoyage-", dir=interim_directory) as dossier_temporaire:
        dossier_temporaire_path = Path(dossier_temporaire)
        for chemin_csv in fichiers:
            nom_fichier = chemin_csv.name
            jour = _jour_depuis_nom(nom_fichier)
            statistiques[nom_fichier] = {
                "jour": jour,
                "lues": 0,
                "apres": Counter(),
                "vides": 0,
                "sans_timestamp": 0,
                "lignes_inf": 0,
                "lignes_nan_seulement": 0,
                "lignes_features_supprimees": 0,
                "doublons": 0,
                "cellules_inf": Counter(),
                "cellules_nan": Counter(),
            }

            lecteur = pd.read_csv(
                chemin_csv,
                encoding="latin-1",
                dtype="string",
                chunksize=chunksize,
                skip_blank_lines=False,
            )
            for numero_bloc, bloc in enumerate(lecteur):
                stats = statistiques[nom_fichier]
                stats["lues"] += len(bloc)
                bloc["day"] = jour
                bloc["source_file"] = nom_fichier
                stats["apres"][1] += len(bloc)

                bloc.columns = [str(colonne).strip() for colonne in bloc.columns]
                if bloc.columns.duplicated().any():
                    raise ValueError(
                        f"{nom_fichier} : des colonnes sont dupliquées après str.strip()."
                    )
                if "Label" not in bloc.columns or "Timestamp" not in bloc.columns:
                    raise ValueError(
                        f"{nom_fichier} : colonnes Label et Timestamp requises."
                    )
                bloc["Label"] = bloc["Label"].str.strip().str.replace(
                    r"[^\x00-\x7F]", "-", regex=True
                )
                stats["apres"][2] += len(bloc)

                bloc = bloc.rename(columns=_RENOMMAGE)
                if "Fwd Header Length.1" in bloc.columns:
                    bloc = bloc.drop(columns="Fwd Header Length.1")
                    colonnes_dupliquees_supprimees.add("Fwd Header Length.1")
                colonnes_requises = {
                    "orig_flow_id",
                    "src_ip",
                    "dst_ip",
                    "src_port",
                    "dst_port",
                    "Timestamp",
                    "label_multi",
                    "day",
                    "source_file",
                }
                colonnes_manquantes = colonnes_requises - set(bloc.columns)
                if colonnes_manquantes:
                    raise ValueError(
                        f"{nom_fichier} : colonnes manquantes : "
                        + ", ".join(sorted(colonnes_manquantes))
                        + "."
                    )
                features_bloc = [
                    colonne
                    for colonne in bloc.columns
                    if colonne not in _COLONNES_HORS_FEATURES
                ]
                if not features_bloc:
                    raise ValueError(f"{nom_fichier} : aucune feature détectée.")
                if colonnes_features is None:
                    colonnes_features = features_bloc
                elif features_bloc != colonnes_features:
                    raise ValueError(
                        f"{nom_fichier} : les colonnes de features diffèrent des "
                        "fichiers déjà lus."
                    )
                stats["apres"][3] += len(bloc)

                colonnes_csv = [
                    colonne
                    for colonne in bloc.columns
                    if colonne not in {"day", "source_file"}
                ]
                lignes_vides = bloc[colonnes_csv].isna().all(axis=1)
                horodatage_absent = (
                    bloc["Timestamp"].isna() | bloc["Timestamp"].str.strip().eq("")
                )
                sans_timestamp = ~lignes_vides & horodatage_absent
                stats["vides"] += int(lignes_vides.sum())
                stats["sans_timestamp"] += int(sans_timestamp.sum())
                bloc = bloc.loc[~(lignes_vides | horodatage_absent)].copy()
                stats["apres"][4] += len(bloc)
                classes_avant.update(_compter_labels(bloc["label_multi"]))

                lignes_inf = np.zeros(len(bloc), dtype=bool)
                lignes_nan = np.zeros(len(bloc), dtype=bool)
                for colonne in colonnes_features:
                    valeurs = pd.to_numeric(bloc[colonne], errors="coerce").to_numpy(
                        dtype=np.float64, na_value=np.nan
                    )
                    masque_inf = np.isinf(valeurs)
                    masque_nan = np.isnan(valeurs)
                    stats["cellules_inf"][colonne] += int(masque_inf.sum())
                    stats["cellules_nan"][colonne] += int(masque_nan.sum())
                    colonnes_inf[(nom_fichier, colonne)] += int(masque_inf.sum())
                    colonnes_nan[(nom_fichier, colonne)] += int(masque_nan.sum())
                    lignes_inf |= masque_inf
                    lignes_nan |= masque_nan
                    bloc[colonne] = valeurs
                lignes_nan_seulement = lignes_nan & ~lignes_inf
                lignes_a_supprimer = lignes_inf | lignes_nan
                stats["lignes_inf"] += int(lignes_inf.sum())
                stats["lignes_nan_seulement"] += int(lignes_nan_seulement.sum())
                stats["lignes_features_supprimees"] += int(lignes_a_supprimer.sum())
                bloc = bloc.loc[~lignes_a_supprimer].copy()
                stats["apres"][5] += len(bloc)

                if not bloc.empty:
                    colonnes_deduplication = [
                        colonne
                        for colonne in bloc.columns
                        if colonne != "source_file"
                    ]
                    empreintes = pd.util.hash_pandas_object(
                        bloc[colonnes_deduplication], index=False, categorize=True
                    ).to_numpy(dtype=np.uint64, copy=False)
                    garder = np.ones(len(bloc), dtype=bool)
                    for index, empreinte in enumerate(empreintes):
                        empreinte_int = int(empreinte)
                        if empreinte_int in empreintes_vues:
                            garder[index] = False
                        else:
                            empreintes_vues.add(empreinte_int)
                    doublons_bloc = bloc.loc[~garder]
                    stats["doublons"] += len(doublons_bloc)
                    if not doublons_bloc.empty:
                        comptes_doublons = doublons_bloc.groupby(
                            ["day", "label_multi"], dropna=False
                        ).size()
                        for (jour_doublon, classe), compte in comptes_doublons.items():
                            nom_classe = (
                                "(label manquant)"
                                if pd.isna(classe)
                                else str(classe)
                            )
                            doublons[(str(jour_doublon), nom_classe)] += int(compte)
                    bloc = bloc.loc[garder].copy()
                stats["apres"][6] += len(bloc)

                if bloc.empty:
                    continue
                for colonne in colonnes_features:
                    minimum = float(bloc[colonne].min())
                    maximum = float(bloc[colonne].max())
                    if colonne not in plages_features:
                        plages_features[colonne] = [minimum, maximum]
                    else:
                        plages_features[colonne][0] = min(
                            plages_features[colonne][0], minimum
                        )
                        plages_features[colonne][1] = max(
                            plages_features[colonne][1], maximum
                        )
                fichier_etape = dossier_temporaire_path / (
                    f"bloc-{len(fichiers_etape):06d}.parquet"
                )
                bloc.to_parquet(fichier_etape, index=False)
                fichiers_etape.append(fichier_etape)

        if not fichiers_etape or colonnes_features is None:
            raise ValueError("Aucune ligne valide ne subsiste après le nettoyage.")

        colonnes_constantes = [
            colonne
            for colonne in colonnes_features
            if plages_features[colonne][0] == plages_features[colonne][1]
        ]
        features_finales = [
            colonne
            for colonne in colonnes_features
            if colonne not in colonnes_constantes
        ]
        colonnes_supprimees = sorted(
            colonnes_dupliquees_supprimees | set(colonnes_constantes)
        )
        compteurs_jour: Counter[str] = Counter()
        chemin_parquet_temporaire = dossier_temporaire_path / "clean_raw.parquet"
        ecrivain: pq.ParquetWriter | None = None
        try:
            for fichier_etape in fichiers_etape:
                bloc_final = pd.read_parquet(fichier_etape).drop(
                    columns=colonnes_constantes
                )
                for colonne_port in ("src_port", "dst_port"):
                    _valider_et_convertir_port(
                        bloc_final, colonne_port, str(bloc_final["source_file"].iloc[0])
                    )
                for colonne in features_finales:
                    valeurs = bloc_final[colonne].to_numpy(dtype=np.float64)
                    converties = valeurs.astype(np.float32)
                    if not np.isfinite(converties).all():
                        raise ValueError(
                            f"{colonne} : conversion float32 produisant NaN ou infini."
                        )
                    bloc_final[colonne] = converties

                identifiants: list[str] = []
                for jour in bloc_final["day"].astype(str):
                    identifiants.append(f"{jour}_{compteurs_jour[jour]}")
                    compteurs_jour[jour] += 1
                bloc_final["flow_id"] = identifiants
                bloc_final["label_bin"] = (
                    bloc_final["label_multi"].ne("BENIGN").astype(np.int8)
                )
                _mettre_a_jour_lignes_par_fichier(statistiques, bloc_final, 7)
                _mettre_a_jour_lignes_par_fichier(statistiques, bloc_final, 8)
                _mettre_a_jour_lignes_par_fichier(statistiques, bloc_final, 9)

                classes_apres.update(_compter_labels(bloc_final["label_multi"]))
                table = pa.Table.from_pandas(bloc_final, preserve_index=False)
                if ecrivain is None:
                    ecrivain = pq.ParquetWriter(chemin_parquet_temporaire, table.schema)
                else:
                    table = table.cast(ecrivain.schema)
                ecrivain.write_table(table)
                _mettre_a_jour_lignes_par_fichier(statistiques, bloc_final, 10)
        finally:
            if ecrivain is not None:
                ecrivain.close()

        if ecrivain is None:
            raise ValueError("Aucune ligne finale à écrire dans le Parquet.")
        chemin_parquet_temporaire.replace(output_path)

    if report_path is None:
        racine_projet = interim_directory.resolve().parents[1]
        report_path = racine_projet / "reports" / "cleaning_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    rapport = _rendre_rapport(
        statistiques,
        classes_avant,
        classes_apres,
        doublons,
        colonnes_nan,
        colonnes_inf,
        colonnes_supprimees,
        features_finales,
        output_path,
    )
    report_path.write_text(rapport, encoding="utf-8")
    return output_path


if __name__ == "__main__":
    sortie = clean_raw()
    print(f"Nettoyage terminé : {sortie}")
