"""M1 : E-GraphSAGE (Lo et al., 2022) en PyG, avec variantes de tête pour l'expérience E3.

Paper : K=2, 128 unités, ReLU, dropout 0.2 entre les couches, agrégation moyenne,
x_v = vecteur de 1 (dim = nb de features d'arête), z_uv = concat(z_u, z_v), softmax.

Deux modes d'agrégation (point à noter dans la fiche de synthèse : l'éq. 4 de l'article
écrit e_uv^{k-1} mais les features d'arête ne sont pas mises à jour d'une couche à l'autre) :
 - "node_edge" (défaut) : message = ReLU(W_m [h_u ; e_uv]) -> la 2e couche voit bien 2 sauts.
 - "edge_only"          : message = e_uv, lecture littérale de l'éq. 4 -> la 2e couche
                          n'apporte pas d'information à 2 sauts. A comparer en ablation.
Les arêtes sont utilisées dans les deux sens pour la propagation.

Têtes de classification (`head`) pour isoler l'apport du graphe (E3) :
 - "linear"   (défaut, article) : Linear(emb)               -> embeddings de graphe seuls
 - "mlp_feat" (extension)       : MLP([emb ; features flux]) -> graphe + flux
 - "mlp_only" (référence)       : MLP(features flux)         -> AUCUN graphe
L'apport du graphe = mlp_feat contre mlp_only (même MLP). "linear" n'est pas comparable à ces deux-là.
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
    HEADS = ("linear", "mlp_feat", "mlp_only")

    def __init__(self, edge_dim: int, hidden: int = 128, n_classes: int = 2,
                 dropout: float = 0.2, mode: str = "node_edge", head: str = "linear"):
        super().__init__()
        assert head in self.HEADS, head
        self.edge_dim, self.hidden, self.dropout, self.head_kind = edge_dim, hidden, dropout, head
        self.emb_dim = 2 * hidden
        if head != "mlp_only":
            self.conv1 = EdgeSAGEConv(edge_dim, edge_dim, hidden, mode)
            self.conv2 = EdgeSAGEConv(hidden, edge_dim, hidden, mode)
        if head == "linear":
            self.head = nn.Linear(2 * hidden, n_classes)
        else:
            d_in = edge_dim + (2 * hidden if head == "mlp_feat" else 0)
            self.head = nn.Sequential(nn.Linear(d_in, hidden), nn.ReLU(), nn.Linear(hidden, n_classes))

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
        if self.head_kind == "mlp_only":
            return self.head(data.edge_attr)
        z = self._edge_embed(data)
        if self.head_kind == "mlp_feat":
            z = torch.cat([z, data.edge_attr], dim=-1)
        return self.head(z)

    @torch.no_grad()
    def encode(self, data) -> torch.Tensor:
        """Interface pour M3 : embeddings de graphe par flux [E, 2*hidden] (mode eval)."""
        if self.head_kind == "mlp_only":
            raise NotImplementedError("la variante mlp_only n'a pas d'embedding de graphe")
        was_training = self.training
        self.eval()
        out = self._edge_embed(data)
        self.train(was_training)
        return out
