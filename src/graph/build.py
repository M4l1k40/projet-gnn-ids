"""M1 : construction du graphe de flux (représentations A/B) et snapshots causaux.

Principe
--------
1. `build_graph` construit UN graphe global (tous les splits) trié par (ts_end, flow_id).
   Chaque flux = une arête orientée src -> dst, avec ses features (edge_attr), son label (y),
   son ts_end (ts) et son split (split_id : 0 train, 1 val, 2 test).
2. `causal_snapshots` découpe ce graphe en snapshots : pour prédire les flux dont le
   ts_end vaut t, le snapshot ne contient que les arêtes de l'univers avec ts_end <= t
   (règle du guide §5.2 ; les ex-aequo sont considérés simultanés donc visibles).
   Univers : train -> {train} ; val -> {train, val} ; test -> {train, val, test}.
3. `assert_causal` vérifie la règle (à appeler dans les tests ET dans la boucle de données).

Adapter `GraphCols` aux noms réels de src/data/schema.py.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence

import numpy as np
import pandas as pd
import torch
from torch_geometric.data import Data

SPLIT_IDS = {"train": 0, "val": 1, "test": 2}

try:  # constantes officielles de M4
    from src.data.schema import ID_COLS, META_COLS, TARGET_COLS
except ImportError:  # repli (tests hors dépôt)
    ID_COLS = ["flow_id", "src_ip", "dst_ip", "src_port", "dst_port", "ts_end"]
    TARGET_COLS = ["label_bin", "label_multi"]
    META_COLS = ["split", "day"]


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Features = toutes les colonnes hors ID / cibles / méta (jamais de liste en dur)."""
    excluded = set(ID_COLS + TARGET_COLS + META_COLS)
    return [c for c in df.columns if c not in excluded]


@dataclass
class GraphCols:
    """Noms de colonnes du Parquet (à aligner sur schema.py)."""
    flow_id: str = "flow_id"
    src_ip: str = "src_ip"
    src_port: str = "src_port"
    dst_ip: str = "dst_ip"
    dst_port: str = "dst_port"
    ts: str = "ts_end"
    label: str = "label_bin"
    split: str = "split"


def _ts_seconds(s: pd.Series) -> np.ndarray:
    if np.issubdtype(s.dtype, np.datetime64):
        return s.astype("int64").to_numpy() / 1e9
    return s.to_numpy(dtype=np.float64)


def make_node_ids(df: pd.DataFrame, cols: GraphCols, mode: str = "host",
                  remap_seed: int | None = 0):
    """Retourne (src_idx, dst_idx, n_nodes).

    mode "host"    : nœud = IP                (représentation A, noyau)
    mode "ip_port" : nœud = (IP, port)        (représentation B, comme l'article)
    remap_seed     : permutation aléatoire fixée des identifiants (None = sans remappage,
                     pour l'ablation E6). Les features des nœuds étant constantes, le
                     remappage ne change pas le modèle ; il garantit surtout qu'aucun
                     identifiant exploitable ne circule (ordre d'apparition, etc.).
    """
    if mode == "host":
        ks = df[cols.src_ip].astype(str)
        kd = df[cols.dst_ip].astype(str)
    elif mode == "ip_port":
        ks = df[cols.src_ip].astype(str) + ":" + df[cols.src_port].astype(str)
        kd = df[cols.dst_ip].astype(str) + ":" + df[cols.dst_port].astype(str)
    else:
        raise ValueError(f"mode inconnu: {mode}")
    codes, uniques = pd.factorize(pd.concat([ks, kd], ignore_index=True))
    n = len(df)
    src, dst = codes[:n], codes[n:]
    if remap_seed is not None:
        perm = np.random.default_rng(remap_seed).permutation(len(uniques))
        src, dst = perm[src], perm[dst]
    return src.astype(np.int64), dst.astype(np.int64), len(uniques)


def build_graph(df: pd.DataFrame, feature_cols: Sequence[str], cols: GraphCols = GraphCols(),
                node_mode: str = "host", remap_seed: int | None = 0) -> Data:
    """Graphe global trié par (ts_end, flow_id). `df` contient train+val+test."""
    df = df.sort_values([cols.ts, cols.flow_id], kind="mergesort").reset_index(drop=True)
    src, dst, n_nodes = make_node_ids(df, cols, node_mode, remap_seed)
    feats = df[list(feature_cols)].to_numpy(dtype=np.float32)
    g = Data(
        edge_index=torch.from_numpy(np.stack([src, dst])),
        edge_attr=torch.from_numpy(feats),
        y=torch.from_numpy(df[cols.label].to_numpy(dtype=np.int64)),
        ts=torch.from_numpy(_ts_seconds(df[cols.ts])),
        split_id=torch.from_numpy(
            df[cols.split].astype(str).map(SPLIT_IDS).to_numpy(dtype=np.int64)),
        row_id=torch.arange(len(df)),            # identifiant numérique interne
        num_nodes=n_nodes,
    )
    g.flow_ids = df[cols.flow_id].astype(str).to_numpy()   # flow_id (chaînes) de M4
    g.num_edge_features = feats.shape[1]
    return g


def _subgraph(g: Data, sel: torch.Tensor, target_mask: torch.Tensor) -> Data:
    ei = g.edge_index[:, sel]
    nodes, inv = torch.unique(ei.flatten(), return_inverse=True)
    # x : vecteur de 1, dimension = nb de features d'arête (Algorithme 1, ligne 1)
    x = torch.ones(nodes.numel(), g.num_edge_features)
    return Data(x=x, edge_index=inv.view(2, -1), edge_attr=g.edge_attr[sel], y=g.y[sel],
                ts=g.ts[sel], row_id=g.row_id[sel], target_mask=target_mask,
                n_id=nodes, e_id=sel)


UNIVERSE = {"train": ("train",), "val": ("train", "val"), "test": ("train", "val", "test")}


def causal_snapshots(g: Data, target_split: str, step: float = 0.0,
                     window: float | None = None) -> Iterator[Data]:
    """Génère des snapshots causaux. Les flux de `target_split` sont les cibles (target_mask).

    step   : 0 -> un snapshot par valeur distincte de ts_end (EXACT, causal strict au sens ts<=t).
             >0 -> cibles regroupées par tranche de `step` secondes (plus rapide ; une cible peut
             voir des arêtes plus tardives de < step secondes : fuite bornée, à documenter).
    window : None -> tout le passé de l'univers ; sinon W secondes (fenêtres glissantes §5.3).
    """
    univ_ids = torch.tensor([SPLIT_IDS[s] for s in UNIVERSE[target_split]])
    idx_univ = torch.isin(g.split_id, univ_ids).nonzero().squeeze(1)  # déjà trié par ts
    ts = g.ts[idx_univ].numpy()
    is_tgt = (g.split_id[idx_univ] == SPLIT_IDS[target_split]).numpy()
    tgt_pos = np.flatnonzero(is_tgt)
    if tgt_pos.size == 0:
        return
    key = ts[tgt_pos] if step <= 0 else np.floor(ts[tgt_pos] / step)
    groups = np.split(tgt_pos, np.flatnonzero(np.diff(key)) + 1)
    for grp in groups:
        t_min, t_max = ts[grp[0]], ts[grp[-1]]
        hi = int(np.searchsorted(ts, t_max, side="right"))
        lo = 0 if window is None else int(np.searchsorted(ts, t_min - window, side="left"))
        mask = torch.zeros(hi - lo, dtype=torch.bool)
        mask[torch.from_numpy(grp - lo)] = True
        yield _subgraph(g, idx_univ[lo:hi], mask)


def target_flow_ids(g: Data, snap: Data) -> np.ndarray:
    """flow_id (chaînes) des flux cibles d'un snapshot, pour écrire les prédictions."""
    return g.flow_ids[snap.row_id[snap.target_mask].numpy()]


def assert_causal(snap: Data, step: float = 0.0) -> None:
    """Aucune arête du snapshot n'est postérieure aux cibles (à `step` près)."""
    t, tt = snap.ts, snap.ts[snap.target_mask]
    assert t.max() <= tt.max() + 1e-9, "arête postérieure aux cibles dans le snapshot"
    assert tt.max() - tt.min() <= step + 1e-9, "cibles trop étalées pour ce pas"
