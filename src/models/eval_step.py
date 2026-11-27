"""M1 : réévalue un modèle DÉJÀ ENTRAÎNÉ sur le test à plusieurs pas de snapshot (effet de la fuite du pas).

    python -m src.models.eval_step --weights models/e_graphsage_seed46.pt --steps 15 5 1 0.5

Commencer par 15 : doit retrouver les chiffres du journal d'entraînement (contrôle de cohérence).
Limite : le modèle a été entraîné à pas 15 s ; un pas plus fin réduit aussi un peu la taille moyenne du
contexte (fenêtre de W + pas secondes), donc une petite baisse ne prouve pas à elle seule une fuite.
"""
from __future__ import annotations

import argparse
import time

import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from src.graph.build import build_graph
from src.models.encoder import load_encoder
from src.models.train_egraphsage import load_all, predict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", required=True)
    ap.add_argument("--steps", type=float, nargs="+", default=[15.0, 5.0, 1.0, 0.5])
    ap.add_argument("--window", type=float, default=60.0)
    ap.add_argument("--source", choices=["real", "fake"], default="real")
    ap.add_argument("--node-mode", choices=["host", "ip_port"], default="host")
    args = ap.parse_args()

    df, feats = load_all(args.source)
    g = build_graph(df, feats, node_mode=args.node_mode, remap_seed=0)
    del df
    model = load_encoder(args.weights)
    strict = None
    if args.source == "real":  # test strict : sans jumeau dans le train
        from src.data.access import load_split, strict_test_mask

        strict = load_split("test", columns=["flow_id"])
        strict["strict"] = strict_test_mask().to_numpy()
        strict["flow_id"] = strict["flow_id"].astype(str)
    for step in args.steps:
        t0 = time.time()
        ids, y, p = predict(model, g, "test", step, args.window)
        out = (f"pas {step:>5}s : complet PR-AUC {average_precision_score(y, p):.4f} "
               f"ROC-AUC {roc_auc_score(y, p):.4f}")
        if strict is not None:
            d = pd.DataFrame({"flow_id": ids.astype(str), "y": y, "p": p}).merge(strict, on="flow_id")
            d = d[d["strict"]]
            out += (f" | strict PR-AUC {average_precision_score(d.y, d.p):.4f} "
                    f"ROC-AUC {roc_auc_score(d.y, d.p):.4f}")
        print(out + f"  ({time.time() - t0:.0f}s)", flush=True)


if __name__ == "__main__":
    main()
