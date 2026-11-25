import numpy as np

from src.models.xgb_shap import _direction_rows, _sample_indexes


def test_stratified_sample_respects_class_caps_and_seed() -> None:
    labels = np.asarray(["BENIGN"] * 100 + ["AttackA"] * 10 + ["AttackB"] * 4)

    indexes, counts = _sample_indexes(
        labels,
        benign_limit=20,
        attack_limit=5,
        seed=42,
    )
    repeated, repeated_counts = _sample_indexes(
        labels,
        benign_limit=20,
        attack_limit=5,
        seed=42,
    )

    assert counts == {"AttackA": 5, "AttackB": 4, "BENIGN": 20}
    assert repeated_counts == counts
    np.testing.assert_array_equal(indexes, repeated)
    assert len(indexes) == 29


def test_direction_rows_summarize_low_median_and_high_value_bands() -> None:
    values = np.column_stack(
        [np.arange(100, dtype=np.float32), np.arange(100, dtype=np.float32)[::-1]]
    )
    contributions = values.astype(np.float64)

    rows = _direction_rows(
        values,
        contributions,
        ["feature_a", "feature_b"],
        ["feature_a"],
    )

    assert [row["quantile"] for row in rows] == [
        "bas (Q10)",
        "médian (Q50)",
        "haut (Q90)",
    ]
    assert rows[0]["mean_shap_log_odds"] < rows[1]["mean_shap_log_odds"]
    assert rows[1]["mean_shap_log_odds"] < rows[2]["mean_shap_log_odds"]
