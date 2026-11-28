import numpy as np
import pytest
import torch

from src.graph.build import build_graph, causal_snapshots
from src.models.e_graphsage import EGraphSAGE
from src.models.encoder import encode_split, load_encoder
from test_graph_causal import FEATS, fake_df


def last_snapshot(df):
    g = build_graph(df, FEATS)
    return g, list(causal_snapshots(g, "test", step=60.0))[-1]


@pytest.mark.parametrize("head", ["linear", "mlp_feat", "mlp_only"])
def test_head_roundtrip_through_load_encoder(tmp_path, head):
    torch.manual_seed(0)
    model = EGraphSAGE(edge_dim=len(FEATS), hidden=24, head=head).eval()
    torch.save(model.state_dict(), tmp_path / "w.pt")
    loaded = load_encoder(tmp_path / "w.pt")
    _, snap = last_snapshot(fake_df())
    assert loaded.head_kind == head and loaded.hidden == 24 and loaded.edge_dim == len(FEATS)
    assert model(snap).shape == (snap.edge_index.size(1), 2)
    assert torch.allclose(model(snap), loaded(snap), atol=1e-6)


def test_mlp_only_ignores_graph_but_graph_heads_use_it():
    df = fake_df()
    g, snap = last_snapshot(df)
    other = ~snap.target_mask                      # arêtes de contexte (non cibles)
    assert other.sum() > 0
    snap2 = snap.clone()
    snap2.edge_attr = snap.edge_attr.clone()
    snap2.edge_attr[other] += 5.0                  # on perturbe seulement le contexte
    tgt = snap.target_mask
    for head, depends in (("mlp_only", False), ("mlp_feat", True), ("linear", True)):
        torch.manual_seed(1)
        m = EGraphSAGE(edge_dim=len(FEATS), hidden=16, head=head).eval()
        same = torch.allclose(m(snap)[tgt], m(snap2)[tgt], atol=1e-6)
        assert same != depends, head


def test_mlp_only_has_no_embedding_and_encode_split_refuses():
    g = build_graph(fake_df(), FEATS)
    m = EGraphSAGE(edge_dim=len(FEATS), head="mlp_only")
    with pytest.raises(NotImplementedError):
        encode_split(m, g, "val")
