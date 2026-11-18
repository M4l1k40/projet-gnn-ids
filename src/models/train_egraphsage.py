"""M1 (T7) : entraînement d'E-GraphSAGE sur snapshots causaux, multi-graines.

Usage (depuis la racine du dépôt) :
    python -m src.models.train_egraphsage --plan                 # coût de chaque (W, pas)
    python -m src.models.train_egraphsage --source fake --epochs 2 --seeds 42   # test rapide
    python -m src.models.train_egraphsage --window 60 --step 15 --seeds 42

Un snapshot = un lot. Les snapshots sont parcourus dans un ordre ALÉATOIRE à chaque époque et le
gradient est cumulé sur `--accum` snapshots (sinon le modèle voit de longues séries d'un même segment
d'attaque et oublie le reste). Perte = cross-entropy pondérée (inverse des fréquences du train).
Early stopping sur la PR-AUC de validation. Sortie : data/predictions/e_graphsage_seed{seed}.parquet
au format commun (flow_id, y_true, y_pred, score, recon_error, seed) + poids dans models/.

Rappels de validité :
 - step > 0 : un flux peut voir des flux jusqu'à `step` secondes plus tardifs dans son pas (fuite bornée,
   à documenter). Seuil 0.5 par défaut : M2 recalcule seuils / FPR@TPR depuis `score`.
 - keep_prob < 1 et shuffle ne s'appliquent qu'à l'entraînement ; val et test sont prédits en entier.
"""
from __future__ import annotations

import argparse
import copy
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import average_precision_score, f1_score, recall_score, roc_auc_score

from src.graph.build import build_graph, causal_snapshots, feature_columns, target_flow_ids
from src.models.e_graphsage import EGraphSAGE

ID_COLS_LOAD = ["flow_id", "src_ip", "dst_ip", "src_port", "dst_port", "ts_end", "label_bin", "split"]


def load_all(source: str):
    if source == "fake":
        df = pd.read_parquet("data/interim/fake_flows.parquet")
        return df, feature_columns(df)
    from src.data.access import feature_names, load_split  # interface de M4

    feats = feature_names()
    cols = ID_COLS_LOAD + feats
    df = pd.concat([load_split(s, columns=cols) for s in ("train", "val", "test")], ignore_index=True)
    return df, feats


def plan(df: pd.DataFrame, windows=(60, 300), steps=(5, 15, 30)) -> None:
    """Coût des snapshots de test pour chaque (W, pas) : calcul sur ts_end seulement."""
    d = df[["ts_end", "split"]].copy()
    d["split"] = d["split"].astype(str)
    d = d.sort_values("ts_end", kind="mergesort")
    ts, tt = d["ts_end"].to_numpy(), d.loc[d["split"] == "test", "ts_end"].to_numpy()
    print(f"flux test : {len(tt):,}")
    print(f"{'W':>5} {'pas':>4} {'snapshots':>10} {'arêtes/snap (méd)':>18} {'p95':>8} {'max':>8} {'total arêtes':>16}")
    for W in windows:
        for step in steps:
            key = np.floor(tt / step)
            first = np.r_[0, np.flatnonzero(np.diff(key)) + 1]
            last = np.r_[first[1:] - 1, len(tt) - 1]
            hi = np.searchsorted(ts, tt[last], side="right")
            lo = np.searchsorted(ts, tt[first] - W, side="left")
            n = hi - lo
            print(f"{W:>5} {step:>4} {len(n):>10,} {np.median(n):>18,.0f} {np.percentile(n, 95):>8,.0f} "
                  f"{n.max():>8,} {n.sum():>16,}")


@torch.no_grad()
def predict(model, g, split, step, window):
    model.eval()
    ids, ys, ps = [], [], []
    for snap in causal_snapshots(g, split, step, window):
        m = snap.target_mask
        ps.append(F.softmax(model(snap)[m], dim=-1)[:, 1].numpy())
        ys.append(snap.y[m].numpy())
        ids.append(target_flow_ids(g, snap))
    return np.concatenate(ids), np.concatenate(ys), np.concatenate(ps)


def val_score(y, p) -> float:
    return average_precision_score(y, p) if len(np.unique(y)) == 2 else -float("inf")


def train_one_seed(g, seed, args, weights):
    torch.manual_seed(seed)
    np.random.seed(seed)
    model = EGraphSAGE(edge_dim=g.num_edge_features, n_classes=2, mode=args.mode)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr)
    best, best_state, bad = -float("inf"), None, 0
    for epoch in range(args.epochs):
        model.train()
        t0, losses, n_acc = time.time(), [], 0
        opt.zero_grad()
        for i, snap in enumerate(causal_snapshots(g, "train", args.step, args.window,
                                                  keep_prob=args.keep_prob, seed=seed * 1000 + epoch,
                                                  shuffle=args.shuffle)):
            m = snap.target_mask
            loss = F.cross_entropy(model(snap)[m], snap.y[m], weight=weights)
            (loss / args.accum).backward()
            n_acc += 1
            if n_acc == args.accum:
                opt.step()
                opt.zero_grad()
                n_acc = 0
            losses.append(loss.item())
            if (i + 1) % 500 == 0:
                print(f"  seed {seed} ep {epoch} snap {i + 1}  loss {np.mean(losses[-500:]):.4f}  "
                      f"{(time.time() - t0) / (i + 1):.2f}s/snap", flush=True)
        if n_acc:
            opt.step()
            opt.zero_grad()
        _, yv, pv = predict(model, g, "val", args.step, args.window)
        score = val_score(yv, pv)
        print(f"seed {seed} epoch {epoch}: loss {np.mean(losses):.4f}  val PR-AUC {score:.4f}  "
              f"({time.time() - t0:.0f}s)", flush=True)
        if score > best:
            best, best_state, bad = score, copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= args.patience:
                print("  early stopping")
                break
    model.load_state_dict(best_state)
    return model, best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["real", "fake"], default="real")
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--seeds", type=int, nargs="+", default=[42, 43, 44, 45, 46])
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--window", type=float, default=60.0)
    ap.add_argument("--step", type=float, default=15.0)
    ap.add_argument("--keep-prob", type=float, default=1.0)
    ap.add_argument("--accum", type=int, default=8, help="snapshots par pas de gradient")
    ap.add_argument("--shuffle", action=argparse.BooleanOptionalAction, default=True,
                    help="ordre aléatoire des snapshots d'entraînement (--no-shuffle = chronologique)")
    ap.add_argument("--mode", choices=["node_edge", "edge_only"], default="node_edge")
    ap.add_argument("--node-mode", choices=["host", "ip_port"], default="host")
    ap.add_argument("--out", default="data/predictions")
    args = ap.parse_args()

    df, feats = load_all(args.source)
    if args.plan:
        plan(df)
        return
    print(f"{len(df):,} flux, {len(feats)} features")
    g = build_graph(df, feats, node_mode=args.node_mode, remap_seed=0)
    del df
    ytr = g.y[g.split_id == 0]
    cnt = torch.bincount(ytr, minlength=2).float()
    weights = cnt.sum() / (2 * cnt.clamp(min=1))
    print(f"train : {int(cnt[0]):,} bénins / {int(cnt[1]):,} attaques ; poids {weights.tolist()}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    Path("models").mkdir(exist_ok=True)
    for seed in args.seeds:
        model, best = train_one_seed(g, seed, args, weights)
        torch.save(model.state_dict(), f"models/e_graphsage_seed{seed}.pt")
        ids, y, p = predict(model, g, "test", args.step, args.window)
        pred = (p >= 0.5).astype(np.int8)
        pd.DataFrame({
            "flow_id": ids, "y_true": y.astype(np.int8), "y_pred": pred,
            "score": p.astype(np.float32), "recon_error": np.float32("nan"),
            "seed": np.int32(seed),
        }).to_parquet(out / f"e_graphsage_seed{seed}.parquet", index=False)
        fp = int(((pred == 1) & (y == 0)).sum())
        tn = int(((pred == 0) & (y == 0)).sum())
        print(f"== seed {seed} TEST (seuil 0.5) : F1 {f1_score(y, pred, zero_division=0):.4f}  "
              f"recall {recall_score(y, pred, zero_division=0):.4f}  FPR {fp / max(fp + tn, 1):.4f}  "
              f"(PR-AUC val {best:.4f})", flush=True)
        print(f"   test complet : taux d'attaques {y.mean():.3f}  PR-AUC {average_precision_score(y, p):.4f}  "
              f"ROC-AUC {roc_auc_score(y, p):.4f}", flush=True)
        if args.source == "real":  # test strict : sans jumeau dans le train (leakage_report)
            from src.data.access import load_split, strict_test_mask

            t = load_split("test", columns=["flow_id"])
            t["strict"] = strict_test_mask().to_numpy()
            t["flow_id"] = t["flow_id"].astype(str)
            sd = pd.DataFrame({"flow_id": ids.astype(str), "y": y, "p": p}).merge(t, on="flow_id")
            sd = sd[sd["strict"]]
            print(f"   test strict  : taux d'attaques {sd.y.mean():.3f}  PR-AUC "
                  f"{average_precision_score(sd.y, sd.p):.4f}  ROC-AUC {roc_auc_score(sd.y, sd.p):.4f}",
                  flush=True)


if __name__ == "__main__":
    main()
