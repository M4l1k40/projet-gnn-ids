from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.clean import clean_raw


@pytest.fixture
def resultat_nettoyage(tmp_path: Path) -> tuple[pd.DataFrame, str]:
    dossier_csv = tmp_path / "raw" / "TrafficLabelling"
    dossier_csv.mkdir(parents=True)
    contenu = "\n".join(
        [
            " Flow ID , Source IP , Source Port , Destination IP , Destination Port , Timestamp , Feature , Constant , Fwd Header Length.1 , Label ",
            "repeat,10.0.0.1,1000,10.0.0.50,80,7/7/2017 10:00,1.5,7,9, BENIGN ",
            "repeat,10.0.0.1,1000,10.0.0.50,80,7/7/2017 10:00,1.5,7,9, BENIGN ",
            "repeat,10.0.0.2,1001,10.0.0.50,443,7/7/2017 10:01,2.5,7,9, Intrusion\u00e9 ",
            "flow-inf,10.0.0.3,1002,10.0.0.50,80,7/7/2017 10:02,inf,7,9,DoS",
            "flow-nan,10.0.0.4,1003,10.0.0.50,80,7/7/2017 10:03,,7,9,PortScan",
            "",
            "",
        ]
    )
    (dossier_csv / "Monday-mini.csv").write_text(contenu, encoding="latin-1")

    configuration = {
        "paths": {
            "raw": tmp_path / "raw",
            "interim": tmp_path / "interim",
        },
        "raw_subdir": "TrafficLabelling",
    }
    chemin_rapport = tmp_path / "reports" / "cleaning_report.md"
    chemin_parquet = clean_raw(
        configuration,
        chunksize=1,
        report_path=chemin_rapport,
    )
    return pd.read_parquet(chemin_parquet), chemin_rapport.read_text(encoding="utf-8")


def test_nettoyage_respecte_les_regles_et_les_types(
    resultat_nettoyage: tuple[pd.DataFrame, str],
) -> None:
    flux, _ = resultat_nettoyage

    assert len(flux) == 2
    assert flux["orig_flow_id"].tolist() == ["repeat", "repeat"]
    assert flux["flow_id"].tolist() == ["Monday_0", "Monday_1"]
    assert flux["label_multi"].tolist() == ["BENIGN", "Intrusion-"]
    assert flux["label_bin"].tolist() == [0, 1]
    assert flux["src_port"].dtype == np.dtype("int32")
    assert flux["dst_port"].dtype == np.dtype("int32")
    assert flux["Feature"].dtype == np.dtype("float32")
    assert flux["Timestamp"].tolist() == ["7/7/2017 10:00", "7/7/2017 10:01"]
    assert flux["src_ip"].tolist() == ["10.0.0.1", "10.0.0.2"]
    assert flux["day"].tolist() == ["Monday", "Monday"]
    assert flux["source_file"].tolist() == ["Monday-mini.csv", "Monday-mini.csv"]
    assert "ts_end" not in flux.columns
    assert "Constant" not in flux.columns
    assert "Fwd Header Length.1" not in flux.columns


def test_rapport_compte_les_filtres_et_signale_les_classes_perdues(
    resultat_nettoyage: tuple[pd.DataFrame, str],
) -> None:
    _, rapport = resultat_nettoyage

    assert "| Monday-mini.csv | Monday | 6 | 6 | 6 | 6 | 5 | 3 | 2 | 2 | 2 | 2 | 2 |" in rapport
    assert "| Monday-mini.csv | 1 | 0 | 1 | 1 | 2 | 1 |" in rapport
    assert "| Monday | BENIGN | 1 |" in rapport
    assert "| DoS | 1 | 0 |" in rapport
    assert "| PortScan | 1 | 0 |" in rapport
    assert "ATTENTION" in rapport
    assert "Nombre final de features : 1" in rapport
