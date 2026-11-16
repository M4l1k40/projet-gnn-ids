import numpy as np
import pandas as pd
import torch

from src.graph.build import (GraphCols, SPLIT_IDS, assert_causal, build_graph, causal_snapshots,
                             feature_columns, make_node_ids, target_flow_ids)
from src.models.e_graphsage import EGraphSAGE

FEATS = [f"f{i}" for i in range(6)]


def fake_df(n=400, seed=0):
    rng = np.random.default_rng(seed)
    ts = np.sort(rng.integers(0, 40, n)) * 60.0          # résolution 60 s -> beaucoup d'ex-aequo
    df = pd.DataFrame({
        "flow_id": [f"flow_{i}" for i in range(n)],
        "src_ip": rng.integers(0, 15, n).astype(str), "src_port": rng.integers(1024, 65535, n),
        "dst_ip": rng.integers(0, 15, n).astype(str), "dst_port": rng.choice([22, 80, 443], n),
        "ts_end": ts, "label_bin": rng.integers(0, 2, n).astype("int8"),
        "label_multi": "X", "day": "mon",
    })
    for f in FEATS:
        df[f] = rng.normal(size=n).astype("float32")
    df["split"] = pd.Categorical(
        np.where(np.arange(n) < 0.6 * n, "train", np.where(np.arange(n) < 0.75 * n, "val", "test")),
        categories=["train", "val", "test"])
    return df


def test_no_future_edges_bruteforce():
    df = fake_df()
    g = build_graph(df, FEATS)
    for split in ("train", "val", "test"):
        for snap in causal_snapshots(g, split):
            assert_causal(snap)
            t_target = snap.ts[snap.target_mask].max()
            assert (snap.ts <= t_target).all()            # aucune arête vers le futur
            assert (snap.ts[snap.target_mask] == t_target).all()


def test_universe_has_no_test_edges_for_train_and_val():
    g = build_graph(fake_df(), FEATS)
    for snap in causal_snapshots(g, "train"):
        assert (g.split_id[snap.e_id] == SPLIT_IDS["train"]).all()
    for snap in causal_snapshots(g, "val"):
        assert (g.split_id[snap.e_id] != SPLIT_IDS["test"]).all()


def test_every_target_covered_once():
    g = build_graph(fake_df(), FEATS)
    seen = torch.cat([s.row_id[s.target_mask] for s in causal_snapshots(g, "test")])
    expected = g.row_id[g.split_id == SPLIT_IDS["test"]]
    assert sorted(seen.tolist()) == sorted(expected.tolist())


def test_future_perturbation_does_not_change_past_predictions():
    """Test comportemental : modifier les features des flux futurs ne change pas les sorties passées."""
    df = fake_df()
    cutoff = float(df.loc[df.split == "test", "ts_end"].median())
    df2 = df.copy()
    future = df2["ts_end"] > cutoff
    df2.loc[future, FEATS] = (np.random.default_rng(1).normal(size=(future.sum(), len(FEATS))) * 10).astype("float32")
    torch.manual_seed(0)
    model = EGraphSAGE(edge_dim=len(FEATS)).eval()

    def preds(d):
        out = {}
        g = build_graph(d, FEATS)
        for snap in causal_snapshots(g, "test", step=0.0):
            with torch.no_grad():
                lg = model(snap)[snap.target_mask]
            for fid, row in zip(target_flow_ids(g, snap), lg):
                out[fid] = row
        return out

    a, b = preds(df), preds(df2)
    past = df.loc[(df.split == "test") & (df.ts_end <= cutoff), "flow_id"]
    assert len(past) > 0
    for fid in past:
        assert torch.allclose(a[fid], b[fid], atol=1e-6)


def test_remap_deterministic_and_bijective():
    df = fake_df()
    c = GraphCols()
    s1, d1, n1 = make_node_ids(df, c, "host", 0)
    s2, d2, _ = make_node_ids(df, c, "host", 0)
    s3, _, _ = make_node_ids(df, c, "host", 1)
    assert (s1 == s2).all() and (d1 == d2).all()
    assert not (s1 == s3).all()
    assert max(s1.max(), d1.max()) == n1 - 1


def test_mode_ip_port_has_more_nodes():
    df = fake_df()
    _, _, n_host = make_node_ids(df, GraphCols(), "host")
    _, _, n_b = make_node_ids(df, GraphCols(), "ip_port")
    assert n_b > n_host


def test_model_shapes_and_encode():
    g = build_graph(fake_df(), FEATS)
    snap = next(causal_snapshots(g, "val"))
    m = EGraphSAGE(edge_dim=len(FEATS))
    assert m(snap).shape == (snap.edge_index.size(1), 2)
    assert m.encode(snap).shape == (snap.edge_index.size(1), 256)


def test_feature_columns_follow_schema_rule():
    assert feature_columns(fake_df()) == FEATS
