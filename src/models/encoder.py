"""M1 -> M3 (tâche T10) : interface de l'encodeur de flux d'E-GraphSAGE.

    from src.models.encoder import load_encoder, encode_split
    model = load_encoder("models/e_graphsage_seed42.pt")
    ids, emb = encode_split(model, g, "train")          # emb : [N, 256], ids : flow_id (chaînes)

`g` est le graphe global de `src.graph.build.build_graph` (mêmes features, même ordre que
l'entraînement, même remap_seed). L'ordre des lignes est chronologique par snapshot, PAS celui du
Parquet : toujours réaligner par `ids` (flow_id).

En ligne de commande (écrit {out}_emb.npy et {out}_ids.parquet) :
    python -m src.models.encoder --weights models/e_graphsage_seed42.pt --split train --out data/embeddings/train_seed42

Points de méthode à connaître (à décider avec M1) :
 - Les embeddings utilisent exactement les mêmes snapshots causaux que l'entraînement
   (fenêtre W et pas identiques : défauts 60 s / 15 s). Un autre W donnerait une distribution différente.
 - L'encodeur est ENTRAÎNÉ AVEC LES LABELS (supervisé). Les embeddings du train sont donc "vus" par
   le modèle, ceux de val/test non : un autoencodeur entraîné sur le bénin du train peut voir un
   décalage train/test dû à cela. GraphIDS entraîne l'encodeur sans labels : ici ce n'est donc qu'une
   approximation « inspirée de ».
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.graph.build import SPLIT_IDS, build_graph, causal_snapshots, target_flow_ids
from src.models.e_graphsage import EGraphSAGE


def load_encoder(weights: str | Path, device: str = "cpu") -> EGraphSAGE:
    """Recharge un modèle sauvegardé (hyperparamètres et tête déduits des poids), en mode eval."""
    sd = torch.load(weights, map_location=device, weights_only=True)
    if "head.weight" in sd:                       # tête linéaire de l'article
        head, n_classes = "linear", sd["head.weight"].shape[0]
    else:                                         # tête MLP (extensions E3)
        head = "mlp_feat" if "conv1.upd.weight" in sd else "mlp_only"
        n_classes = sd["head.2.weight"].shape[0]
    mode = "node_edge" if "conv1.msg.weight" in sd else "edge_only"
    if head == "mlp_only":
        hidden, edge_dim = sd["head.0.weight"].shape
    else:
        hidden = sd["conv1.upd.weight"].shape[0]
        key = "conv1.msg.weight" if mode == "node_edge" else "conv1.upd.weight"
        edge_dim = sd[key].shape[1] // 2
    model = EGraphSAGE(edge_dim=int(edge_dim), hidden=int(hidden), n_classes=int(n_classes), mode=mode, head=head)
    model.load_state_dict(sd)
    return model.to(device).eval()


def edge_dim(model: EGraphSAGE) -> int:
    return model.edge_dim


def encode_split(model: EGraphSAGE, g, split: str, step: float = 15.0, window: float | None = 60.0,
                 dtype=np.float32):
    """Embeddings [N, 2*hidden] de tous les flux de `split`, calculés sur snapshots causaux."""
    if g.num_edge_features != edge_dim(model):
        raise ValueError(f"le graphe a {g.num_edge_features} features, le modèle en attend "
                         f"{edge_dim(model)} : même liste et même ordre que l'entraînement (feature_names()).")
    n = int((g.split_id == SPLIT_IDS[split]).sum())
    emb = np.empty((n, model.emb_dim), dtype=dtype)
    ids = np.empty(n, dtype=object)
    pos = 0
    for snap in causal_snapshots(g, split, step, window):
        m = snap.target_mask
        z = model.encode(snap)[m].numpy()
        emb[pos:pos + len(z)] = z
        ids[pos:pos + len(z)] = target_flow_ids(g, snap)
        pos += len(z)
    assert pos == n, f"{pos} flux encodés sur {n}"
    return ids.astype(str), emb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--split", choices=["train", "val", "test"], required=True)
    ap.add_argument("--out", required=True, help="préfixe de sortie")
    ap.add_argument("--window", type=float, default=60.0)
    ap.add_argument("--step", type=float, default=15.0)
    ap.add_argument("--node-mode", choices=["host", "ip_port"], default="host")
    ap.add_argument("--fp16", action="store_true", help="embeddings en float16 (moitié moins gros)")
    args = ap.parse_args()

    from src.models.train_egraphsage import load_all

    df, feats = load_all("real")
    g = build_graph(df, feats, node_mode=args.node_mode, remap_seed=0)
    del df
    model = load_encoder(args.weights)
    ids, emb = encode_split(model, g, args.split, args.step, args.window,
                            dtype=np.float16 if args.fp16 else np.float32)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    np.save(f"{out}_emb.npy", emb)
    pd.DataFrame({"flow_id": ids}).to_parquet(f"{out}_ids.parquet", index=False)
    print(f"{len(ids):,} embeddings {emb.shape} -> {out}_emb.npy et {out}_ids.parquet")


if __name__ == "__main__":
    main()
