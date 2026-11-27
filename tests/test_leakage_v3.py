import numpy as np
import pandas as pd

from src.data.leakage_v3 import (
    _distance_bands,
    _nearest_statistics,
    _stratified_test_sample,
)


def test_stratified_test_sample_caps_benign_and_each_attack_reproducibly():
    frame = pd.DataFrame(
        {
            "flow_id": [f"id-{index}" for index in range(20)],
            "label_multi": ["BENIGN"] * 10 + ["AttackA"] * 6 + ["AttackB"] * 4,
            "label_bin": [0] * 10 + [1] * 10,
            "feature_a": np.arange(20, dtype=np.float32),
        }
    )
    first = _stratified_test_sample(frame, ["feature_a"], 42, 3, 2)
    second = _stratified_test_sample(frame, ["feature_a"], 42, 3, 2)
    assert first["flow_id"].tolist() == second["flow_id"].tolist()
    assert first["label_multi"].value_counts().to_dict() == {
        "BENIGN": 3,
        "AttackA": 2,
        "AttackB": 2,
    }
    assert first["feature_a"].dtype == np.float32


def test_distance_bands_are_disjoint_and_separate_exact_zero():
    distances = np.array([0, 0, 1, 2, 3, 4, 5, 6], dtype=np.float64)
    bands, p25, p75 = _distance_bands(distances)
    assert p25 == 0.75
    assert p75 == 4.25
    assert np.count_nonzero(bands == "distance nulle") == 2
    assert np.count_nonzero(bands == "0 < distance ≤ p25") == 0
    assert np.count_nonzero(bands == "p25–p75") == 4
    assert np.count_nonzero(bands == "> p75") == 2


def test_nearest_statistics_separates_label_matches_and_xgb_recall():
    frame = pd.DataFrame(
        {
            "label_multi": ["BENIGN", "Attack", "Attack"],
            "label_bin": np.array([0, 1, 1], dtype=np.int8),
        }
    )
    result = _nearest_statistics(
        frame,
        np.array([0.0, 0.1, 0.2]),
        np.array(["BENIGN", "BENIGN", "Attack"]),
        np.array([True, False, False]),
        np.array([0, 1, 0], dtype=np.int8),
    ).set_index("label_multi")
    assert result.loc["Attack", "same_label_neighbor_count"] == 1
    assert result.loc["Attack", "different_label_neighbor_count"] == 1
    assert result.loc["Attack", "different_label_bin_count"] == 1
    assert result.loc["Attack", "xgb_recall"] == 0.5
