"""M1 : E-GraphSAGE (Lo et al., 2022) en PyG.

Paper : K=2, 128 unités, ReLU, dropout 0.2 entre les couches, agrégation moyenne,
x_v = vecteur de 1 (dim = nb de features d'arête), z_uv = concat(z_u, z_v), softmax.

Deux modes d'agrégation (point à noter dans la fiche de synthèse : l'éq. 4 de l'article
écrit e_uv^{k-1} mais les features d'arête ne sont pas mises à jour d'une couche à l'autre) :
 - "node_edge" (défaut) : message = ReLU(W_m [h_u ; e_uv]) -> la 2e couche voit bien 2 sauts.
 - "edge_only"          : message = e_uv, lecture littérale de l'éq. 4 -> la 2e couche
                          n'apporte pas d'information à 2 sauts. A comparer en ablation.
Les arêtes sont utilisées dans les deux sens pour la propagation (un nœud agrège ses flux
entrants ET sortants).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import MessagePassing


class EdgeSAGEConv(MessagePassing):
    def __init__(self, in_dim: int, edge_dim: int, out_dim: int, mode: str = "node_edge"):
        super().__init__(aggr="mean")
        assert mode in ("node_edge", "edge_only")
        self.mode = mode
        if mode == "node_edge":
            self.msg = nn.Linear(in_dim + edge_dim, out_dim)
            agg_dim = out_dim
        else:
            agg_dim = edge_dim
        self.upd = nn.Linear(in_dim + agg_dim, out_dim)  # W^k . CONCAT(h_v, h_N(v))

    def forward(self, h, edge_index, edge_attr):
        agg = self.propagate(edge_index, h=h, edge_attr=edge_attr, size=(h.size(0), h.size(0)))
        return self.upd(torch.cat([h, agg], dim=-1))

    def message(self, h_j, edge_attr):
        if self.mode == "node_edge":
            return F.relu(self.msg(torch.cat([h_j, edge_attr], dim=-1)))
        return edge_attr


class EGraphSAGE(nn.Module):
    def __init__(self, edge_dim: int, hidden: int = 128, n_classes: int = 2,
                 dropout: float = 0.2, mode: str = "node_edge"):
        super().__init__()
        self.conv1 = EdgeSAGEConv(edge_dim, edge_dim, hidden, mode)
        self.conv2 = EdgeSAGEConv(hidden, edge_dim, hidden, mode)
        self.head = nn.Linear(2 * hidden, n_classes)
        self.dropout = dropout

    def _edge_embed(self, data) -> torch.Tensor:
        ei = torch.cat([data.edge_index, data.edge_index.flip(0)], dim=1)
        ea = torch.cat([data.edge_attr, data.edge_attr], dim=0)
        h = F.relu(self.conv1(data.x, ei, ea))
        h = F.dropout(h, p=self.dropout, training=self.training)
        z = F.relu(self.conv2(h, ei, ea))
        src, dst = data.edge_index
        return torch.cat([z[src], z[dst]], dim=-1)  # éq. 5 : 2*hidden = 256

    def forward(self, data) -> torch.Tensor:
        """Logits par flux (appliquer le masque `data.target_mask` pour la perte / les prédictions)."""
        return self.head(self._edge_embed(data))

    @torch.no_grad()
    def encode(self, data) -> torch.Tensor:
        """Interface pour M3 : embeddings par flux [E, 2*hidden] (mode eval)."""
        was_training = self.training
        self.eval()
        out = self._edge_embed(data)
        self.train(was_training)
        return out
