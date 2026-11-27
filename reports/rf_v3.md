# Random Forest binaire — split V3

- Labels d’origine, 69 features, folds V3 purgés; paramètres fixes après grille de quatre configurations.
- Configuration retenue : `max_samples=0.5`, `min_samples_leaf=5`, 100 arbres, `max_features=sqrt`, `class_weight=balanced_subsample`.
- Sélection : meilleure PR-AUC moyenne des plis 0–2; PR-AUC moyenne plis 0–2 0.949332 (baseline (0,3 ; 5): 0.913327; meilleure observée 0.949332).
- Seuil hors-pli FPR 1 % : 0.17716859; FPR atteinte 0.9995%; scores OOF égaux au seuil : 3.
- Graines 42–51; cellules : moyenne ± écart-type / médiane.

## Recherche (PR-AUC validation)

| max_samples | min_samples_leaf | pli | PR-AUC | TPR@FPR≤1% | Fit (s) | Modèle mémoire (octets) | Modèle compressé (octets) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.3 | 1 | 0 | 0.774447 | 0.710330 | 106.1 | 9,946,800 | 3,318,632 |
| 0.3 | 1 | 1 | 0.977756 | 0.833346 | 95.0 | 8,458,992 | 2,855,877 |
| 0.3 | 1 | 2 | 0.965472 | 0.825831 | 93.1 | 9,499,248 | 3,185,973 |
| 0.3 | 5 | 0 | 0.795447 | 0.709866 | 114.6 | 5,697,792 | 2,392,137 |
| 0.3 | 5 | 1 | 0.976697 | 0.829383 | 113.9 | 5,101,920 | 2,142,682 |
| 0.3 | 5 | 2 | 0.967838 | 0.832785 | 104.0 | 5,565,888 | 2,319,631 |
| 0.5 | 1 | 0 | 0.775706 | 0.710165 | 141.8 | 12,381,120 | 4,138,727 |
| 0.5 | 1 | 1 | 0.979079 | 0.833196 | 148.8 | 10,225,872 | 3,491,400 |
| 0.5 | 1 | 2 | 0.969283 | 0.866491 | 134.8 | 11,852,064 | 4,001,679 |
| 0.5 | 5 | 0 | 0.892288 | 0.710135 | 152.5 | 7,039,296 | 2,952,740 |
| 0.5 | 5 | 1 | 0.978614 | 0.832523 | 160.0 | 6,073,488 | 2,559,738 |
| 0.5 | 5 | 2 | 0.977094 | 0.838453 | 135.8 | 6,832,656 | 2,844,925 |

## RF contre XGBoost V3 b0

Valeurs par graine : moyenne ± écart-type / médiane. Les deux modèles utilisent leur seuil calibré sur plis hors-pli.

| Modèle | Vérité test | PR-AUC | ROC-AUC | TPR@FPR≤0,1% | TPR@FPR≤1% | FP min–max | FN | TPR/FPR au seuil | Part FP signalés |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RF V3 b0 | labels d'origine | 0.9885 ± 0.0002 / 0.9886 | 0.9940 ± 0.0001 / 0.9940 | 0.9609 ± 0.0048 / 0.9598 | 0.9818 ± 0.0013 / 0.9820 | 4001–7253 | 902.6 ± 20.0 / 901.0 | 0.9827 ± 0.0004 / 0.9827 / 0.0107 ± 0.0015 / 0.0109 | 0.007 ± 0.001 / 0.007 |
| RF V3 b0 | v2 — Attempted comptés | 0.6638 ± 0.0107 / 0.6602 | 0.7743 ± 0.0193 / 0.7689 | 0.5725 ± 0.0026 / 0.5718 | 0.5853 ± 0.0009 / 0.5853 | 3963–7206 | 36247.6 ± 18.4 / 36246.0 | 0.5862 ± 0.0002 / 0.5862 / 0.0113 ± 0.0016 / 0.0115 | 0.000 ± 0.000 / 0.000 |
| RF V3 b0 | v2 — Attempted exclus | 0.6048 ± 0.0112 / 0.6014 | 0.7397 ± 0.0233 / 0.7336 | 0.5309 ± 0.0001 / 0.5310 | 0.5324 ± 0.0003 / 0.5324 | 3963–7206 | 34089.0 ± 11.0 / 34094.0 | 0.5327 ± 0.0002 / 0.5327 / 0.0113 ± 0.0016 / 0.0115 | 0.000 ± 0.000 / 0.000 |
| XGBoost V3 b0 | labels d'origine | 0.9936 ± 0.0004 / 0.9938 | 0.9987 ± 0.0002 / 0.9988 | 0.9851 ± 0.0009 / 0.9856 | 0.9881 ± 0.0003 / 0.9880 | 2313–2547 | 665.6 ± 3.0 / 666.5 | 0.9872 ± 0.0001 / 0.9872 / 0.0041 ± 0.0001 / 0.0041 | 0.049 ± 0.005 / 0.049 |
| XGBoost V3 b0 | v2 — Attempted comptés | 0.8011 ± 0.0062 / 0.8020 | 0.9450 ± 0.0039 / 0.9457 | 0.5874 ± 0.0006 / 0.5876 | 0.5921 ± 0.0005 / 0.5921 | 2198–2423 | 35937.1 ± 12.1 / 35941.0 | 0.5897 ± 0.0001 / 0.5897 / 0.0042 ± 0.0001 / 0.0042 | 0.000 ± 0.000 / 0.000 |
| XGBoost V3 b0 | v2 — Attempted exclus | 0.7476 ± 0.0073 / 0.7485 | 0.9369 ± 0.0047 / 0.9378 | 0.5336 ± 0.0006 / 0.5339 | 0.5379 ± 0.0005 / 0.5379 | 2198–2423 | 33869.1 ± 11.5 / 33872.5 | 0.5357 ± 0.0002 / 0.5357 / 0.0042 ± 0.0001 / 0.0042 | 0.000 ± 0.000 / 0.000 |

## RF par graine — labels d’origine

| Graine | FP | FN | TPR au seuil | TPR@FPR≤0,1% | TPR@FPR≤1% |
|---:|---:|---:|---:|---:|---:|
| 42 | 6 792 | 903 | 0.982701 | 0.958755 | 0.980307 |
| 43 | 6 468 | 915 | 0.982471 | 0.964521 | 0.982433 |
| 44 | 6 602 | 899 | 0.982778 | 0.960862 | 0.980211 |
| 45 | 6 086 | 920 | 0.982375 | 0.958716 | 0.981590 |
| 46 | 5 978 | 886 | 0.983027 | 0.958238 | 0.982969 |
| 47 | 4 001 | 899 | 0.982778 | 0.967567 | 0.983716 |
| 48 | 7 253 | 941 | 0.981973 | 0.952395 | 0.980230 |
| 49 | 6 585 | 907 | 0.982625 | 0.963946 | 0.981533 |
| 50 | 5 852 | 886 | 0.983027 | 0.957146 | 0.982912 |
| 51 | 6 105 | 870 | 0.983333 | 0.966686 | 0.982433 |
| Moyenne | 6 172.2 | 902.6 | 0.982709 | 0.960883 | 0.981833 |
| Médiane | 6 286.5 | 901.0 | 0.982739 | 0.959808 | 0.982011 |

## Recall RF par famille v2 et classe d’origine

| Vérité test | Type | Groupe | Support positif | Recall (moyenne ± écart-type / médiane) |
|---|---|---|---:|---:|
| labels d'origine | label_orig_multi | BENIGN | 0 | n.d. |
| labels d'origine | label_orig_multi | Bot | 476 | 0.0000 ± 0.0000 / 0.0000 |
| labels d'origine | label_orig_multi | DDoS | 12,501 | 0.9967 ± 0.0004 / 0.9965 |
| labels d'origine | label_orig_multi | DoS Hulk | 14,152 | 0.9863 ± 0.0010 / 0.9864 |
| labels d'origine | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9161 ± 0.0019 / 0.9154 |
| labels d'origine | label_orig_multi | DoS slowloris | 714 | 0.9817 ± 0.0010 / 0.9818 |
| labels d'origine | label_orig_multi | FTP-Patator | 1,579 | 0.9968 ± 0.0006 / 0.9968 |
| labels d'origine | label_orig_multi | Infiltration | 9 | 0.7778 ± 0.0000 / 0.7778 |
| labels d'origine | label_orig_multi | PortScan | 20,046 | 0.9983 ± 0.0004 / 0.9983 |
| labels d'origine | label_orig_multi | SSH-Patator | 1,192 | 0.9747 ± 0.0017 / 0.9748 |
| labels d'origine | label_orig_multi | Web Attack - Brute Force | 260 | 1.0000 ± 0.0000 / 1.0000 |
| labels d'origine | label_orig_multi | Web Attack - XSS | 66 | 0.9061 ± 0.0096 / 0.9091 |
| labels d'origine | v2_family | other_change | 28 | 0.5571 ± 0.0184 / 0.5714 |
| labels d'origine | v2_family | portscan_infiltration | 0 | n.d. |
| labels d'origine | v2_family | server_response | 0 | n.d. |
| labels d'origine | v2_family | unchanged | 52,172 | 0.9829 ± 0.0004 / 0.9830 |
| v2 — Attempted comptés | label_orig_multi | BENIGN | 35,397 | 0.0013 ± 0.0002 / 0.0012 |
| v2 — Attempted comptés | label_orig_multi | Bot | 474 | 0.0000 ± 0.0000 / 0.0000 |
| v2 — Attempted comptés | label_orig_multi | DDoS | 12,501 | 0.9967 ± 0.0004 / 0.9965 |
| v2 — Attempted comptés | label_orig_multi | DoS Hulk | 14,152 | 0.9863 ± 0.0010 / 0.9864 |
| v2 — Attempted comptés | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9161 ± 0.0019 / 0.9154 |
| v2 — Attempted comptés | label_orig_multi | DoS slowloris | 709 | 0.9886 ± 0.0010 / 0.9887 |
| v2 — Attempted comptés | label_orig_multi | FTP-Patator | 1,578 | 0.9968 ± 0.0006 / 0.9968 |
| v2 — Attempted comptés | label_orig_multi | Infiltration | 9 | 0.7778 ± 0.0000 / 0.7778 |
| v2 — Attempted comptés | label_orig_multi | PortScan | 20,046 | 0.9983 ± 0.0004 / 0.9983 |
| v2 — Attempted comptés | label_orig_multi | SSH-Patator | 1,192 | 0.9747 ± 0.0017 / 0.9748 |
| v2 — Attempted comptés | label_orig_multi | Web Attack - Brute Force | 260 | 1.0000 ± 0.0000 / 1.0000 |
| v2 — Attempted comptés | label_orig_multi | Web Attack - XSS | 66 | 0.9061 ± 0.0096 / 0.9091 |
| v2 — Attempted comptés | v2_family | other_change | 318 | 0.0459 ± 0.0016 / 0.0472 |
| v2 — Attempted comptés | v2_family | portscan_infiltration | 29,787 | 0.0010 ± 0.0002 / 0.0009 |
| v2 — Attempted comptés | v2_family | server_response | 5,312 | 0.0029 ± 0.0008 / 0.0030 |
| v2 — Attempted comptés | v2_family | unchanged | 52,172 | 0.9829 ± 0.0004 / 0.9830 |
| v2 — Attempted exclus | label_orig_multi | BENIGN | 33,918 | 0.0010 ± 0.0002 / 0.0010 |
| v2 — Attempted exclus | label_orig_multi | Bot | 0 | n.d. |
| v2 — Attempted exclus | label_orig_multi | DDoS | 12,501 | 0.9967 ± 0.0004 / 0.9965 |
| v2 — Attempted exclus | label_orig_multi | DoS Hulk | 4,100 | 1.0000 ± 0.0000 / 1.0000 |
| v2 — Attempted exclus | label_orig_multi | DoS Slowhttptest | 399 | 0.7491 ± 0.0057 / 0.7469 |
| v2 — Attempted exclus | label_orig_multi | DoS slowloris | 558 | 0.9952 ± 0.0009 / 0.9946 |
| v2 — Attempted exclus | label_orig_multi | FTP-Patator | 806 | 1.0000 ± 0.0000 / 1.0000 |
| v2 — Attempted exclus | label_orig_multi | Infiltration | 9 | 0.7778 ± 0.0000 / 0.7778 |
| v2 — Attempted exclus | label_orig_multi | PortScan | 20,046 | 0.9983 ± 0.0004 / 0.9983 |
| v2 — Attempted exclus | label_orig_multi | SSH-Patator | 599 | 0.9588 ± 0.0016 / 0.9591 |
| v2 — Attempted exclus | label_orig_multi | Web Attack - Brute Force | 13 | 1.0000 ± 0.0000 / 1.0000 |
| v2 — Attempted exclus | label_orig_multi | Web Attack - XSS | 3 | 0.6667 ± 0.0000 / 0.6667 |
| v2 — Attempted exclus | v2_family | other_change | 2 | 0.0000 ± 0.0000 / 0.0000 |
| v2 — Attempted exclus | v2_family | portscan_infiltration | 29,787 | 0.0010 ± 0.0002 / 0.0009 |
| v2 — Attempted exclus | v2_family | server_response | 4,130 | 0.0013 ± 0.0006 / 0.0017 |
| v2 — Attempted exclus | v2_family | unchanged | 39,033 | 0.9948 ± 0.0002 / 0.9947 |

## Temps et mémoire

- Pic Working Set du processus : 2.47 Gio (PeakWorkingSet64/psutil selon disponibilité).
- Fits finaux mesurés : 3084.8 s; inférence totale : 53.8 s.

## Limites

- La grille ne couvre que quatre configurations; l’essai de paramètres n’est pas une recherche exhaustive.
- Le meilleur candidat est à la borne haute testée pour `max_samples` (0,5); un optimum supérieur n’est pas exclu.
- Les hyperparamètres XGBoost n’ont pas été retunés pour le split V3.
- Le seuil est calibré sur les plis V3; le test reste intra-épisode et ne mesure pas une généralisation à une capture indépendante.
- Entraînement et métriques principales utilisent les labels d’origine; les vues v2 sont des analyses de sensibilité.
- Les résultats sont propres à CIC-IDS2017 et ne constituent pas une garantie de performance en production.

Recherche : `D:\AI\projet-gnn-ids\reports\rf_v3\search_rf.csv`. Métriques : `D:\AI\projet-gnn-ids\reports\rf_v3\rf_v3_metrics.csv`.
Recall : `D:\AI\projet-gnn-ids\reports\rf_v3\rf_v3_recall.csv`. Comparaison XGBoost : `D:\AI\projet-gnn-ids\reports\rf_v3\rf_vs_xgb_v3.csv`.
