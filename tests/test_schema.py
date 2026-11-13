import numpy as np
import pandas as pd
import pytest

from src.data.fake import generate_fake_flows
from src.data.schema import ID_COLS, META_COLS, TARGET_COLS, validate_schema
from src.utils.config import load_config


@pytest.fixture(scope="module")
def fake_flows() -> pd.DataFrame:
    return generate_fake_flows()


def test_validate_schema_accepte_les_flux_factices(
    fake_flows: pd.DataFrame,
) -> None:
    validate_schema(fake_flows, stage="final")


def test_validate_schema_signale_une_colonne_manquante(
    fake_flows: pd.DataFrame,
) -> None:
    with pytest.raises(ValueError, match="day"):
        validate_schema(fake_flows.drop(columns="day"))


def test_validate_schema_signale_nan_dans_une_feature(
    fake_flows: pd.DataFrame,
) -> None:
    features = [
        column
        for column in fake_flows.select_dtypes(include="number").columns
        if column not in ID_COLS + TARGET_COLS + META_COLS
    ]
    flux = fake_flows.copy()
    flux.loc[flux.index[0], features[0]] = np.nan

    with pytest.raises(ValueError, match=features[0]):
        validate_schema(flux)


def test_validate_schema_signale_un_split_invalide(
    fake_flows: pd.DataFrame,
) -> None:
    flux = fake_flows.copy()
    valeurs_split = flux["split"].astype(object)
    valeurs_split.iloc[0] = "foo"
    flux["split"] = pd.Categorical(
        valeurs_split, categories=["train", "val", "test", "foo"], ordered=True
    )

    with pytest.raises(ValueError, match="split"):
        validate_schema(flux)


def test_validate_schema_signale_un_flow_id_duplique(
    fake_flows: pd.DataFrame,
) -> None:
    flux = fake_flows.copy()
    flux.loc[flux.index[1], "flow_id"] = flux.loc[flux.index[0], "flow_id"]

    with pytest.raises(ValueError, match="flow_id"):
        validate_schema(flux)


def test_validate_schema_signale_une_cible_incoherente(
    fake_flows: pd.DataFrame,
) -> None:
    flux = fake_flows.copy()
    index_benign = flux.index[flux["label_multi"] == "BENIGN"][0]
    flux.loc[index_benign, "label_bin"] = 1

    with pytest.raises(ValueError, match="label_bin/label_multi"):
        validate_schema(flux)


def test_split_est_chronologique_et_respecte_les_gaps(
    fake_flows: pd.DataFrame,
) -> None:
    gap_seconds = load_config()["split"]["gap_minutes"] * 60

    for _, jour in fake_flows.groupby("day", observed=True):
        horodatages = {
            nom: jour.loc[jour["split"] == nom, "ts_end"]
            for nom in ("train", "val", "test")
        }
        assert horodatages["train"].max() < horodatages["val"].min()
        assert horodatages["val"].max() < horodatages["test"].min()
        assert horodatages["val"].min() - horodatages["train"].max() >= gap_seconds
        assert horodatages["test"].min() - horodatages["val"].max() >= gap_seconds


def test_split_clean_ne_requiert_pas_la_colonne_split(
    fake_flows: pd.DataFrame,
) -> None:
    validate_schema(fake_flows.drop(columns="split"), stage="clean")
