# Normalisation signed-log standardisée — split V3

- Les valeurs brutes sont lues dans `data/interim/clean.parquet` et réalignées sur les splits V3 par `flow_id`.
- Signed-log1p puis centrage/réduction ajustés exclusivement sur le train après imputation des négatifs invalides.
- Les colonnes autres que les 69 features sont conservées depuis les Parquets V3; `meta.parquet`, `folds.parquet` et `p2_folds.parquet` sont des copies binaires.
- `meta.parquet` et `folds.parquet` viennent du split V3; `p2_folds.parquet` est copié sans modification depuis la source P2 configurée (`data/processed/p2_folds.parquet`).
- Train utilisé pour ajuster le transformeur : 1,649,128 lignes; features dans l’ordre de `models/features.json`.

## Features hors [0,3 ; 1,5]

| Feature | Écart-type central après log-z | Cause |
|---|---:|---|
| Fwd URG Flags | 0 | indicateur rare (p99=0; les valeurs p1–p99 sont constantes) |
| RST Flag Count | 0 | indicateur rare (p99=0; les valeurs p1–p99 sont constantes) |
| CWE Flag Count | 0 | indicateur rare (p99=0; les valeurs p1–p99 sont constantes) |
| ECE Flag Count | 0 | indicateur rare (p99=0; les valeurs p1–p99 sont constantes) |

Les indicateurs rares ont p99=0 et des valeurs identiques dans l’intervalle p1–p99; une transformation monotone ne peut pas augmenter l’écart-type central sans changer leur représentation.

## Imputations par bloc

| Bloc | Lignes | Négatifs imputés (feature: effectif) |
|---|---:|---|
| train | 1,649,128 | Flow Duration: 76, Flow Bytes/s: 60, Flow Packets/s: 76, Flow IAT Mean: 76, Flow IAT Max: 76, Flow IAT Min: 1,818, Fwd IAT Min: 11, Fwd Header Length: 35, Bwd Header Length: 22, min_seg_size_forward: 35 |
| val | 241,111 | Flow Duration: 7, Flow Bytes/s: 4, Flow Packets/s: 7, Flow IAT Mean: 7, Flow IAT Max: 7, Flow IAT Min: 230 |
| test | 631,557 | Flow Duration: 26, Flow Bytes/s: 15, Flow Packets/s: 26, Flow IAT Mean: 26, Flow IAT Max: 26, Flow IAT Min: 613 |

## Contrôles

- Écart-type central calculé sur les valeurs transformées des lignes entre p1 et p99 bruts du train (quantiles issus de `scaler_audit_v3`): 69 features.
- Spearman sur un échantillon fixe de 200,000 lignes train (graine 42), exclusions des valeurs imputées feature par feature : 69/69 features à 1 ± 1e-6.
- Le contrôle `validate_schema(stage='final')` est appliqué aux batches relus après écriture; flow_id et ordre sont comparés aux sources.
- Les contrôles de valeurs non finies sont effectués sur chaque batch avant écriture.
- `scaler_v3_logz.joblib` contient les opérations et statistiques de transformation; le fichier se charge avec `joblib.load` sans importer le code `src` (dépendances d’exécution : Python, NumPy et pandas).

### Copies identiques

| Fichier | SHA-256 |
|---|---|
| meta.parquet | `e6f92d84c52b0c91e1422516e348a195eec19155ced740415100054f945fa356` |
| folds.parquet | `0ede3142600b10be506d261afa9cb3abf5c231b7cc8f57b3ec6a42c503c056d0` |
| p2_folds.parquet | `e80fc9aa1738584877dee27a46e3dc2addc5575f88d81f0607d48e68d5c5c899` |

Aucun artefact existant n’a été remplacé. L’ancien jeu `data/processed_v3` reste le défaut; cette variante est optionnelle.

## Réentraînement seed 42 — comparaison log-z

- XGBoost : essai 24, 199 rounds fixes, graine 42; RF : configuration sélectionnée en V3 (100 arbres, max_samples=0,5, min_samples_leaf=5).
- Les seuils restent ceux des modèles b0 existants (XGBoost et RF respectivement); le test n’a servi qu’à l’évaluation.
- Comparaison XGBoost des scores test : Pearson r=0.99994767, Spearman ρ=0.99813649.

| Modèle | PR-AUC | ROC-AUC | TPR@FPR≤0,1 % | TPR@FPR≤1 % | FP | FN | TPR au seuil | FPR au seuil | Fit (s) | Inférence (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| XGBoost V3 b0 original | 0.992944 | 0.998368 | 0.985651 | 0.988525 | 2382 | 667 | 0.987222 | 0.004111 | repris | repris |
| XGBoost V3 b0 log-z | 0.993644 | 0.998725 | 0.985326 | 0.987989 | 2373 | 667 | 0.987222 | 0.004096 | 118.44467840000016 | 2.3935519000001477 |
| RF V3 b0 original | 0.988107 | 0.994015 | 0.958755 | 0.980307 | 6792 | 903 | 0.982701 | 0.011723 | repris | repris |
| RF V3 b0 log-z | 0.988829 | 0.994089 | 0.968506 | 0.983506 | 3220 | 927 | 0.982241 | 0.005558 | 275.8591693000003 | 4.308701699999801 |

### Artefacts de comparaison

- XGBoost log-z : modèle `D:\AI\projet-gnn-ids\models\xgboost_v3_logz\xgb_bin_b0_seed42_logz_v3.json`; prédictions `D:\AI\projet-gnn-ids\predictions\xgboost_v3_logz\xgb_bin_b0_seed42_logz_v3.parquet`.
- Random Forest log-z : modèle `D:\AI\projet-gnn-ids\models\rf_v3_logz\rf_bin_b0_seed42_logz_v3.joblib`; prédictions `D:\AI\projet-gnn-ids\predictions\xgboost_v3_logz\rf_bin_b0_seed42_logz_v3.parquet`.

Les seuils sont des seuils de validation hors-pli appris sur les modèles b0; les métriques ROC/PR et TPR à FPR fixé sont calculées sur le test. Le test n’a pas été utilisé pour l’ajustement du transformeur.
