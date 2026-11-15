"""Vérification indépendante des données finales (lecture seule, ne modifie rien)."""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

ROOT = Path("data/processed")
GAP_S = 180                      # gap de 3 min
EXPECTED_TOTAL = 2_827_677       # lignes de clean.parquet
IDS = {"src_ip", "dst_ip", "src_port", "dst_port", "ts_end", "Timestamp", "flow_id",
       "orig_flow_id", "Flow ID", "source_file", "day", "split", "label_bin", "label_multi"}
ok = True


def check(name, cond, detail=""):
    global ok
    ok &= bool(cond)
    print(("OK   " if cond else "FAIL ") + name + (f"  -> {detail}" if detail else ""))


feats = json.loads(Path("models/features.json").read_text(encoding="utf-8"))
if isinstance(feats, dict):
    feats = feats.get("features", list(feats))
check("features.json lisible", len(feats) > 0, f"{len(feats)} features")
check("aucun identifiant dans les features", not (set(feats) & IDS))
suspects = [f for f in feats if "port" in f.lower() or "timestamp" in f.lower()]
check("aucun nom de feature suspect (port, timestamp)", not suspects, str(suspects))
sc = joblib.load("models/scaler.joblib")
check("scaler cohérent avec features.json",
      getattr(sc, "n_features_in_", len(feats)) == len(feats))

light, ref_cols = [], None
for s in ("train", "val", "test"):
    p = ROOT / f"{s}.parquet"
    check(f"{s}.parquet existe", p.exists())
    df = pd.read_parquet(p)
    ref_cols = ref_cols or list(df.columns)
    check(f"{s}: mêmes colonnes que train", list(df.columns) == ref_cols)
    check(f"{s}: colonne split correcte", (df["split"].astype(str) == s).all())
    check(f"{s}: ts_end trié", df["ts_end"].is_monotonic_increasing)
    X = df[feats].to_numpy()
    check(f"{s}: features en float32", X.dtype == np.float32)
    check(f"{s}: aucun NaN ni infini", np.isfinite(X).all())
    mu, sd = X.mean(axis=0, dtype=np.float64), X.std(axis=0, dtype=np.float64)
    nz = sd > 0
    if s == "train":
        check("train: moyenne ~ 0", np.abs(mu[nz]).max() < 1e-3, f"max {np.abs(mu[nz]).max():.2e}")
        check("train: écart-type ~ 1", np.abs(sd[nz] - 1).max() < 1e-2, f"max écart {np.abs(sd[nz]-1).max():.2e}")
        print(f"INFO  colonnes constantes dans le train : {int((~nz).sum())}")
    else:
        print(f"INFO  {s}: |moyenne| max = {np.abs(mu).max():.3f} (ne doit PAS être ~0 : pas de recentrage)")
    light.append(df[["flow_id", "day", "label_multi", "label_bin", "ts_end", "split"]])
    del df, X

L = pd.concat(light, ignore_index=True)
check("flow_id unique sur train+val+test", L["flow_id"].is_unique)
check("total <= lignes de clean.parquet", len(L) <= EXPECTED_TOTAL,
      f"{len(L)} lignes, {EXPECTED_TOTAL - len(L)} manquantes (doit = flux en gap)")
check("label_bin cohérent avec label_multi", ((L["label_multi"] != "BENIGN").astype("int8") == L["label_bin"]).all())
check("chaque split a BENIGN et attaques", all(L[L.split == s]["label_bin"].nunique() == 2 for s in ("train", "val", "test")))

bad = []
for (d, c), g in L[L["label_multi"] != "BENIGN"].groupby(["day", "label_multi"]):
    r = g.groupby("split")["ts_end"].agg(["min", "max"])
    seq = [s for s in ("train", "val", "test") if s in r.index]
    for a, b in zip(seq, seq[1:]):
        if r.loc[b, "min"] - r.loc[a, "max"] < GAP_S - 1:
            bad.append((d, c, a, b))
check("attaques: train < val < test avec gap >= 3 min", not bad, f"{len(bad)} violations, ex: {bad[:3]}")

print("\nClasse x bloc :")
print(pd.crosstab(L["label_multi"], L["split"])[["train", "val", "test"]].to_string())
print("\nRESULTAT GLOBAL :", "TOUT EST OK" if ok else "ÉCHECS A CORRIGER")
sys.exit(0 if ok else 1)