import numpy as np
import pytest
import torch

from src.graph.build import SPLIT_IDS, build_graph, causal_snapshots
from src.models.e_graphsage import EGraphSAGE
from src.models.encoder import encode_split, load_encoder
from test_graph_causal import FEATS, fake_df


@pytest.mark.parametrize("mode,hidden", [("node_edge", 128), ("node_edge", 32), ("edge_only", 16)])
def test_load_encoder_roundtrip(tmp_path, mode, hidden):
    torch.manual_seed(0)
    model = EGraphSAGE(edge_dim=len(FEATS), hidden=hidden, mode=mode).eval()
    torch.save(model.state_dict(), tmp_path / "w.pt")
    loaded = load_encoder(tmp_path / "w.pt")
    snap = next(causal_snapshots(build_graph(fake_df(), FEATS), "val"))
    assert torch.allclose(model.encode(snap), loaded.encode(snap), atol=1e-6)
    assert loaded.encode(snap).shape[1] == 2 * hidden


def test_encode_split_covers_each_flow_once_and_is_causal():
    df = fake_df()
    g = build_graph(df, FEATS)
    model = EGraphSAGE(edge_dim=len(FEATS), hidden=16).eval()
    ids, emb = encode_split(model, g, "test", step=60.0, window=300.0)
    expected = df.loc[df.split == "test", "flow_id"]
    assert sorted(ids.tolist()) == sorted(expected.tolist())
    assert emb.shape == (len(expected), 32) and np.isfinite(emb).all()
    # les flux passés ne dépendent pas des features futures
    cutoff = float(df.loc[df.split == "test", "ts_end"].median())
    df2 = df.copy()
    fut = df2["ts_end"] > cutoff + 60.0   # marge = pas
    df2.loc[fut, FEATS] = (np.random.default_rng(1).normal(size=(fut.sum(), len(FEATS))) * 10).astype("float32")
    ids2, emb2 = encode_split(model, build_graph(df2, FEATS), "test", step=60.0, window=300.0)
    past = set(df.loc[(df.split == "test") & (df.ts_end <= cutoff), "flow_id"])
    a, b = dict(zip(ids, emb)), dict(zip(ids2, emb2))
    assert past and all(np.allclose(a[f], b[f], atol=1e-5) for f in past)


def test_feature_mismatch_is_rejected():
    g = build_graph(fake_df(), FEATS)
    model = EGraphSAGE(edge_dim=len(FEATS) + 3)
    with pytest.raises(ValueError):
        encode_split(model, g, "val")
