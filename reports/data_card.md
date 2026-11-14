# Fiche des données finales

## Schéma final

- 6 colonnes d’identification, 69 features float32, 2 cibles et 2 colonnes de méta-données.
- Les features sont toutes les colonnes numériques hors identifiants, ports, ts_end, cibles et méta-données.

| Colonne | Type Parquet |
|---|---|
| `flow_id` | `large_string` |
| `src_ip` | `large_string` |
| `dst_ip` | `large_string` |
| `src_port` | `int32` |
| `dst_port` | `int32` |
| `ts_end` | `double` |
| `Protocol` | `float` |
| `Flow Duration` | `float` |
| `Total Fwd Packets` | `float` |
| `Total Backward Packets` | `float` |
| `Total Length of Fwd Packets` | `float` |
| `Total Length of Bwd Packets` | `float` |
| `Fwd Packet Length Max` | `float` |
| `Fwd Packet Length Min` | `float` |
| `Fwd Packet Length Mean` | `float` |
| `Fwd Packet Length Std` | `float` |
| `Bwd Packet Length Max` | `float` |
| `Bwd Packet Length Min` | `float` |
| `Bwd Packet Length Mean` | `float` |
| `Bwd Packet Length Std` | `float` |
| `Flow Bytes/s` | `float` |
| `Flow Packets/s` | `float` |
| `Flow IAT Mean` | `float` |
| `Flow IAT Std` | `float` |
| `Flow IAT Max` | `float` |
| `Flow IAT Min` | `float` |
| `Fwd IAT Total` | `float` |
| `Fwd IAT Mean` | `float` |
| `Fwd IAT Std` | `float` |
| `Fwd IAT Max` | `float` |
| `Fwd IAT Min` | `float` |
| `Bwd IAT Total` | `float` |
| `Bwd IAT Mean` | `float` |
| `Bwd IAT Std` | `float` |
| `Bwd IAT Max` | `float` |
| `Bwd IAT Min` | `float` |
| `Fwd PSH Flags` | `float` |
| `Fwd URG Flags` | `float` |
| `Fwd Header Length` | `float` |
| `Bwd Header Length` | `float` |
| `Fwd Packets/s` | `float` |
| `Bwd Packets/s` | `float` |
| `Min Packet Length` | `float` |
| `Max Packet Length` | `float` |
| `Packet Length Mean` | `float` |
| `Packet Length Std` | `float` |
| `Packet Length Variance` | `float` |
| `FIN Flag Count` | `float` |
| `SYN Flag Count` | `float` |
| `RST Flag Count` | `float` |
| `PSH Flag Count` | `float` |
| `ACK Flag Count` | `float` |
| `URG Flag Count` | `float` |
| `CWE Flag Count` | `float` |
| `ECE Flag Count` | `float` |
| `Down/Up Ratio` | `float` |
| `Average Packet Size` | `float` |
| `Avg Fwd Segment Size` | `float` |
| `Avg Bwd Segment Size` | `float` |
| `Subflow Fwd Packets` | `float` |
| `Subflow Fwd Bytes` | `float` |
| `Subflow Bwd Packets` | `float` |
| `Subflow Bwd Bytes` | `float` |
| `Init_Win_bytes_forward` | `float` |
| `Init_Win_bytes_backward` | `float` |
| `act_data_pkt_fwd` | `float` |
| `min_seg_size_forward` | `float` |
| `Active Mean` | `float` |
| `Active Std` | `float` |
| `Active Max` | `float` |
| `Active Min` | `float` |
| `Idle Mean` | `float` |
| `Idle Std` | `float` |
| `Idle Max` | `float` |
| `Idle Min` | `float` |
| `label_bin` | `int8` |
| `label_multi` | `large_string` |
| `split` | `dictionary<values=string, indices=int8, ordered=0>` |
| `day` | `large_string` |

### Features normalisées

- `Protocol`
- `Flow Duration`
- `Total Fwd Packets`
- `Total Backward Packets`
- `Total Length of Fwd Packets`
- `Total Length of Bwd Packets`
- `Fwd Packet Length Max`
- `Fwd Packet Length Min`
- `Fwd Packet Length Mean`
- `Fwd Packet Length Std`
- `Bwd Packet Length Max`
- `Bwd Packet Length Min`
- `Bwd Packet Length Mean`
- `Bwd Packet Length Std`
- `Flow Bytes/s`
- `Flow Packets/s`
- `Flow IAT Mean`
- `Flow IAT Std`
- `Flow IAT Max`
- `Flow IAT Min`
- `Fwd IAT Total`
- `Fwd IAT Mean`
- `Fwd IAT Std`
- `Fwd IAT Max`
- `Fwd IAT Min`
- `Bwd IAT Total`
- `Bwd IAT Mean`
- `Bwd IAT Std`
- `Bwd IAT Max`
- `Bwd IAT Min`
- `Fwd PSH Flags`
- `Fwd URG Flags`
- `Fwd Header Length`
- `Bwd Header Length`
- `Fwd Packets/s`
- `Bwd Packets/s`
- `Min Packet Length`
- `Max Packet Length`
- `Packet Length Mean`
- `Packet Length Std`
- `Packet Length Variance`
- `FIN Flag Count`
- `SYN Flag Count`
- `RST Flag Count`
- `PSH Flag Count`
- `ACK Flag Count`
- `URG Flag Count`
- `CWE Flag Count`
- `ECE Flag Count`
- `Down/Up Ratio`
- `Average Packet Size`
- `Avg Fwd Segment Size`
- `Avg Bwd Segment Size`
- `Subflow Fwd Packets`
- `Subflow Fwd Bytes`
- `Subflow Bwd Packets`
- `Subflow Bwd Bytes`
- `Init_Win_bytes_forward`
- `Init_Win_bytes_backward`
- `act_data_pkt_fwd`
- `min_seg_size_forward`
- `Active Mean`
- `Active Std`
- `Active Max`
- `Active Min`
- `Idle Mean`
- `Idle Std`
- `Idle Max`
- `Idle Min`

## Effectifs

| Split | Lignes |
|---|---:|
| train | 1515755 |
| val | 151714 |
| test | 882784 |
| Gap supprimé | 277424 |
| Total clean.parquet | 2827677 |

## Classes par split

Les pourcentages sont calculés dans chaque classe, sur les flux conservés.

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Total conservé |
|---|---:|---:|---:|---:|
| BENIGN | 1181398 (54.65 %) | 149947 (6.94 %) | 830584 (38.42 %) | 2161929 |
| Bot | 1174 (66.78 %) | 108 (6.14 %) | 476 (27.08 %) | 1758 |
| DDoS | 76815 (86.00 %) | 0 (0.00 %) | 12501 (14.00 %) | 89316 |
| DoS GoldenEye | 6176 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 6176 |
| DoS Hulk | 138074 (90.70 %) | 0 (0.00 %) | 14152 (9.30 %) | 152226 |
| DoS Slowhttptest | 3300 (73.25 %) | 0 (0.00 %) | 1205 (26.75 %) | 4505 |
| DoS slowloris | 3478 (80.49 %) | 129 (2.99 %) | 714 (16.52 %) | 4321 |
| FTP-Patator | 4764 (66.51 %) | 820 (11.45 %) | 1579 (22.04 %) | 7163 |
| Heartbleed | 7 (87.50 %) | 1 (12.50 %) | 0 (0.00 %) | 8 |
| Infiltration | 22 (62.86 %) | 4 (11.43 %) | 9 (25.71 %) | 35 |
| PortScan | 95698 (82.68 %) | 0 (0.00 %) | 20046 (17.32 %) | 115744 |
| SSH-Patator | 3539 (66.42 %) | 597 (11.20 %) | 1192 (22.37 %) | 5328 |
| Web Attack - Brute Force | 905 (71.26 %) | 105 (8.27 %) | 260 (20.47 %) | 1270 |
| Web Attack - Sql Injection | 13 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 13 |
| Web Attack - XSS | 392 (85.03 %) | 3 (0.65 %) | 66 (14.32 %) | 461 |

## Classes d’expérience

- Multiclasse : BENIGN, Bot, DoS slowloris, FTP-Patator, SSH-Patator, Web Attack - Brute Force.
- Binary-only (conservées avec `label_bin=1`) : DDoS, DoS GoldenEye, DoS Hulk, DoS Slowhttptest, PortScan, Web Attack - XSS.
- Exclues des expériences : Heartbleed, Infiltration, Web Attack - Sql Injection. Les valeurs `label_multi` du Parquet restent intactes.

## Test strict

- `meta.parquet` porte le booléen `seen_in_train` : il est nul pour train et, pour val/test, vrai si un vecteur de features arrondi à 6 décimales existe dans train pour la même classe.
- Pour une évaluation stricte, filtrer le test sur `seen_in_train == false` ; cela exclut les doublons exacts intra-classe présents dans train.
- Flux test strict : 682136.

## Paramètres et limites connues

- Split final : `segment` (V2), gap 3 min ; ratios train/val/test 60%/15%/25%.
- Seuil multiclasse : 50 flux dans chaque split.
- Graine split : 42 ; globale : 42 ; modèle : 42.
- Normalisation : `standard`, ajustée uniquement sur train.
- Les labels d’origine sont conservés sans correction ni regroupement.
- Résolution d’une minute sur 7 fichier(s) sur 8.
- 115 flux de durée nulle ou négative sont conservés.
- `dst_port` est exclu des features car c’est une colonne d’identification.
- Le split V2 n’est pas chronologique globalement ; les frontières sont définies par classe et jour.
- 277424 flux marqués gap ont été supprimés des splits.
- Fuite intra-attaque observée : 200648 vecteurs test identiques au train dans la même classe ; voir `leakage_report.md`.
