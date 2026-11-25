import numpy as np
import pandas as pd

from src.models.xgb_v3 import _evaluate_predictions, _eligible_rows
from src.models.xgb import LoadedSplit


def test_v2b_excludes_attempted_rows_from_fit_population() -> None:
    split = LoadedSplit(
        name="train",
        feature_names=["feature"],
        X=np.zeros((4, 1), dtype=np.float32),
        y_bin=np.asarray([0, 1, 0, 1], dtype=np.int8),
        y_multi=np.asarray(["BENIGN", "Attack", "BENIGN", "Attack"]),
        flow_ids=np.asarray(["a", "b", "c", "d"]),
        attempted=np.asarray([False, True, False, True]),
        y_v2_bin=np.asarray([0, 1, 0, 1], dtype=np.int8),
    )

    np.testing.assert_array_equal(
        _eligible_rows(split, "v2b"),
        np.asarray([True, False, True, False]),
    )
    np.testing.assert_array_equal(
        _eligible_rows(split, "v2a"),
        np.ones(4, dtype=bool),
    )


def test_evaluation_separates_original_v2_and_attempted_excluded_truths() -> None:
    predictions = pd.DataFrame(
        {
            "score": [0.9, 0.1, 0.9, 0.9],
            "label_bin": [0, 1, 0, 1],
            "label_v2_bin": [1, 1, 0, 0],
            "attempted": [False, True, True, False],
            "audit_counted": [1, 1, 1, 0],
            "audit_signaled": [True, True, True, True],
            "v2_family": [
                "server_response",
                "other_change",
                "unchanged",
                "other_change",
            ],
            "label_multi": ["BENIGN", "AttackA", "BENIGN", "AttackB"],
        }
    )

    metrics, recalls = _evaluate_predictions(
        predictions,
        threshold=0.5,
        seed=42,
        training_variant="V3 v2a",
    )

    by_evaluation = {row["evaluation"]: row for row in metrics}
    assert by_evaluation["labels d'origine"]["false_positives"] == 2
    assert by_evaluation["labels d'origine"]["false_negatives"] == 1
    assert by_evaluation["v2 — Attempted comptés"]["false_positives"] == 1
    assert by_evaluation["v2 — Attempted comptés"]["false_negatives"] == 1
    assert by_evaluation["v2 — Attempted exclus"]["effectif"] == 2
    assert by_evaluation["v2 — Attempted exclus"]["false_positives"] == 1
    assert by_evaluation["labels d'origine"]["fp_signal_share"] == 1.0
    assert any(
        row["group_type"] == "v2_family" and row["group"] == "server_response"
        for row in recalls
    )
