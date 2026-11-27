# TreeSHAP — XGBoost V3 b0, graine 42

- Les contributions sont calculées par `Booster.predict(pred_contribs=True)` en log-odds; la dernière colonne de sortie est la valeur de base et n’est pas incluse dans les classements.
- Échantillonnage stratifié reproductible (graine 42) : BENIGN=15,000, Bot=476, DDoS=1,500, DoS Hulk=1,500, DoS Slowhttptest=1,205, DoS slowloris=714, FTP-Patator=1,500, Infiltration=9, PortScan=1,500, SSH-Patator=1,192, Web Attack - Brute Force=260, Web Attack - XSS=66; total 24,922.
- Contrôle croisé : shap.TreeExplainer(model_output='raw'), 200 lignes, écart absolu max 0, moyen 0.

## Top 20 global par moyenne de |SHAP|

| Rang | Feature | Moyenne |SHAP| | SHAP moyen (log-odds) |
|---:|---|---:|---:|
| 1 | Init_Win_bytes_forward | 1.29256 | -0.664072 |
| 2 | Bwd Packet Length Min | 1.16372 | 0.00439493 |
| 3 | Init_Win_bytes_backward | 1.02417 | -0.330207 |
| 4 | Average Packet Size | 0.722312 | -0.417154 |
| 5 | Bwd Packet Length Std | 0.579748 | -0.100823 |
| 6 | Fwd Packet Length Max | 0.450901 | -0.169909 |
| 7 | Protocol | 0.409774 | -0.279025 |
| 8 | Fwd Packet Length Min | 0.343674 | 0.0273384 |
| 9 | min_seg_size_forward | 0.335072 | -0.0467396 |
| 10 | Total Length of Bwd Packets | 0.266463 | -0.262376 |
| 11 | Max Packet Length | 0.228491 | 0.0963623 |
| 12 | Bwd Header Length | 0.219815 | -0.0906938 |
| 13 | Packet Length Std | 0.215449 | 0.0637869 |
| 14 | Flow IAT Min | 0.214223 | -0.16209 |
| 15 | Fwd Packet Length Std | 0.204614 | -0.109866 |
| 16 | Bwd Packet Length Mean | 0.203814 | -0.0835617 |
| 17 | Fwd Header Length | 0.190562 | -0.0457787 |
| 18 | Fwd IAT Min | 0.166199 | -0.0350515 |
| 19 | PSH Flag Count | 0.150076 | -0.0496784 |
| 20 | Bwd Packets/s | 0.147339 | -0.0513052 |

## Top 10 par classe d’attaque

| Classe | Support échantillonné | Rang | Feature | Moyenne |SHAP| | SHAP moyen |
|---|---:|---:|---|---:|---:|
| Bot | 476 | 1 | Fwd IAT Min | 1.12262 | -1.12262 |
| Bot | 476 | 2 | Bwd Header Length | 1.06998 | -1.06998 |
| Bot | 476 | 3 | Total Length of Bwd Packets | 0.937296 | -0.937296 |
| Bot | 476 | 4 | Init_Win_bytes_forward | 0.88495 | -0.88495 |
| Bot | 476 | 5 | Flow IAT Min | 0.740631 | -0.740514 |
| Bot | 476 | 6 | Init_Win_bytes_backward | 0.603536 | -0.603536 |
| Bot | 476 | 7 | Bwd Packet Length Min | 0.573683 | 0.573683 |
| Bot | 476 | 8 | Subflow Bwd Bytes | 0.470139 | -0.470139 |
| Bot | 476 | 9 | Bwd Packet Length Std | 0.427034 | -0.427034 |
| Bot | 476 | 10 | min_seg_size_forward | 0.409533 | -0.408276 |
| DDoS | 1,500 | 1 | Bwd Packet Length Std | 2.09676 | 2.09191 |
| DDoS | 1,500 | 2 | Bwd Packet Length Min | 1.20892 | 1.20892 |
| DDoS | 1,500 | 3 | Init_Win_bytes_forward | 1.1831 | 1.1157 |
| DDoS | 1,500 | 4 | Average Packet Size | 0.755936 | 0.559713 |
| DDoS | 1,500 | 5 | Init_Win_bytes_backward | 0.66163 | 0.476172 |
| DDoS | 1,500 | 6 | Bwd Packet Length Mean | 0.587935 | 0.497288 |
| DDoS | 1,500 | 7 | Max Packet Length | 0.532103 | 0.532103 |
| DDoS | 1,500 | 8 | Packet Length Std | 0.424042 | 0.421589 |
| DDoS | 1,500 | 9 | Fwd Packet Length Min | 0.353334 | 0.353334 |
| DDoS | 1,500 | 10 | Total Length of Fwd Packets | 0.299732 | 0.299722 |
| DoS Hulk | 1,500 | 1 | Init_Win_bytes_forward | 2.01316 | 1.74721 |
| DoS Hulk | 1,500 | 2 | Bwd Packet Length Std | 1.39058 | 1.28514 |
| DoS Hulk | 1,500 | 3 | Bwd Packet Length Min | 1.08988 | 1.08988 |
| DoS Hulk | 1,500 | 4 | Init_Win_bytes_backward | 1.00142 | 0.660008 |
| DoS Hulk | 1,500 | 5 | Average Packet Size | 0.388769 | 0.195062 |
| DoS Hulk | 1,500 | 6 | Bwd Packet Length Mean | 0.35997 | 0.204012 |
| DoS Hulk | 1,500 | 7 | Fwd Packet Length Min | 0.347215 | 0.347215 |
| DoS Hulk | 1,500 | 8 | Fwd Packet Length Max | 0.298429 | 0.161411 |
| DoS Hulk | 1,500 | 9 | Fwd Header Length | 0.274064 | 0.238822 |
| DoS Hulk | 1,500 | 10 | min_seg_size_forward | 0.238211 | 0.0274251 |
| DoS Slowhttptest | 1,205 | 1 | Bwd Packet Length Min | 0.953021 | 0.948284 |
| DoS Slowhttptest | 1,205 | 2 | Init_Win_bytes_backward | 0.771517 | 0.388457 |
| DoS Slowhttptest | 1,205 | 3 | Fwd IAT Mean | 0.418973 | 0.401138 |
| DoS Slowhttptest | 1,205 | 4 | min_seg_size_forward | 0.403259 | 0.401941 |
| DoS Slowhttptest | 1,205 | 5 | Fwd Packet Length Min | 0.385494 | 0.224567 |
| DoS Slowhttptest | 1,205 | 6 | Fwd Packet Length Max | 0.288753 | -0.0276308 |
| DoS Slowhttptest | 1,205 | 7 | Average Packet Size | 0.273665 | 0.0769091 |
| DoS Slowhttptest | 1,205 | 8 | Bwd Packet Length Std | 0.233723 | -0.0794171 |
| DoS Slowhttptest | 1,205 | 9 | Flow IAT Mean | 0.218092 | 0.2034 |
| DoS Slowhttptest | 1,205 | 10 | Fwd IAT Min | 0.215311 | -0.0548553 |
| DoS slowloris | 714 | 1 | Init_Win_bytes_backward | 1.25633 | 0.950101 |
| DoS slowloris | 714 | 2 | Bwd Packet Length Min | 1.00325 | 1.00325 |
| DoS slowloris | 714 | 3 | Init_Win_bytes_forward | 0.619365 | 0.595606 |
| DoS slowloris | 714 | 4 | Bwd IAT Mean | 0.431889 | 0.363229 |
| DoS slowloris | 714 | 5 | min_seg_size_forward | 0.397881 | 0.386888 |
| DoS slowloris | 714 | 6 | Fwd Packet Length Min | 0.351136 | 0.264756 |
| DoS slowloris | 714 | 7 | Bwd IAT Min | 0.310617 | 0.272371 |
| DoS slowloris | 714 | 8 | Flow IAT Mean | 0.308658 | 0.303093 |
| DoS slowloris | 714 | 9 | Packet Length Std | 0.291372 | 0.286601 |
| DoS slowloris | 714 | 10 | Fwd Packet Length Std | 0.270896 | -0.165608 |
| FTP-Patator | 1,500 | 1 | Init_Win_bytes_backward | 1.33204 | 1.18543 |
| FTP-Patator | 1,500 | 2 | Bwd Packet Length Min | 1.01471 | 1.01471 |
| FTP-Patator | 1,500 | 3 | Packet Length Std | 0.821531 | 0.817703 |
| FTP-Patator | 1,500 | 4 | min_seg_size_forward | 0.727999 | 0.727999 |
| FTP-Patator | 1,500 | 5 | Init_Win_bytes_forward | 0.648517 | 0.638393 |
| FTP-Patator | 1,500 | 6 | Fwd Packet Length Max | 0.640082 | 0.609884 |
| FTP-Patator | 1,500 | 7 | act_data_pkt_fwd | 0.468277 | 0.421693 |
| FTP-Patator | 1,500 | 8 | Packet Length Variance | 0.374039 | 0.371545 |
| FTP-Patator | 1,500 | 9 | Fwd Packet Length Min | 0.356948 | 0.356948 |
| FTP-Patator | 1,500 | 10 | Max Packet Length | 0.271755 | 0.268423 |
| Infiltration | 9 | 1 | Init_Win_bytes_backward | 0.923582 | -0.923582 |
| Infiltration | 9 | 2 | Average Packet Size | 0.625737 | -0.625737 |
| Infiltration | 9 | 3 | Bwd Packet Length Min | 0.625498 | 0.625498 |
| Infiltration | 9 | 4 | Fwd Packet Length Max | 0.540548 | -0.540548 |
| Infiltration | 9 | 5 | Bwd Packet Length Mean | 0.510879 | 0.492358 |
| Infiltration | 9 | 6 | Fwd Packet Length Std | 0.349476 | -0.349476 |
| Infiltration | 9 | 7 | min_seg_size_forward | 0.33441 | -0.33441 |
| Infiltration | 9 | 8 | Bwd Packet Length Std | 0.326062 | -0.326062 |
| Infiltration | 9 | 9 | Fwd Packet Length Mean | 0.299479 | 0.275511 |
| Infiltration | 9 | 10 | Total Length of Bwd Packets | 0.256363 | -0.256363 |
| PortScan | 1,500 | 1 | Bwd Packet Length Min | 1.12307 | 1.12307 |
| PortScan | 1,500 | 2 | Average Packet Size | 1.10971 | 1.10577 |
| PortScan | 1,500 | 3 | Max Packet Length | 0.980555 | 0.978469 |
| PortScan | 1,500 | 4 | Packet Length Std | 0.450535 | 0.448213 |
| PortScan | 1,500 | 5 | Fwd Packet Length Min | 0.399116 | 0.399116 |
| PortScan | 1,500 | 6 | Bwd Packet Length Std | 0.380947 | 0.372579 |
| PortScan | 1,500 | 7 | Fwd Packet Length Max | 0.359265 | 0.357584 |
| PortScan | 1,500 | 8 | Init_Win_bytes_backward | 0.304033 | -0.284817 |
| PortScan | 1,500 | 9 | Bwd Header Length | 0.292663 | 0.287233 |
| PortScan | 1,500 | 10 | Fwd Header Length | 0.261665 | -0.256279 |
| SSH-Patator | 1,192 | 1 | Init_Win_bytes_backward | 2.34802 | 2.32626 |
| SSH-Patator | 1,192 | 2 | Init_Win_bytes_forward | 1.28307 | 1.26589 |
| SSH-Patator | 1,192 | 3 | Bwd Packet Length Min | 0.9798 | 0.9798 |
| SSH-Patator | 1,192 | 4 | min_seg_size_forward | 0.528811 | 0.528811 |
| SSH-Patator | 1,192 | 5 | Flow Duration | 0.357476 | 0.264096 |
| SSH-Patator | 1,192 | 6 | Fwd Packet Length Min | 0.347406 | 0.343903 |
| SSH-Patator | 1,192 | 7 | Fwd Packet Length Max | 0.331573 | -0.0560484 |
| SSH-Patator | 1,192 | 8 | Bwd IAT Total | 0.292155 | 0.27603 |
| SSH-Patator | 1,192 | 9 | Bwd Packets/s | 0.264326 | 0.204772 |
| SSH-Patator | 1,192 | 10 | Fwd Packet Length Std | 0.257536 | -0.180686 |
| Web Attack - Brute Force | 260 | 1 | Fwd IAT Min | 1.5361 | 1.53535 |
| Web Attack - Brute Force | 260 | 2 | Bwd Packet Length Min | 0.955831 | 0.955831 |
| Web Attack - Brute Force | 260 | 3 | Fwd Header Length | 0.7379 | 0.705305 |
| Web Attack - Brute Force | 260 | 4 | Init_Win_bytes_backward | 0.565547 | 0.534788 |
| Web Attack - Brute Force | 260 | 5 | Init_Win_bytes_forward | 0.443733 | 0.443733 |
| Web Attack - Brute Force | 260 | 6 | Fwd Packet Length Min | 0.32706 | 0.32706 |
| Web Attack - Brute Force | 260 | 7 | min_seg_size_forward | 0.322434 | 0.322434 |
| Web Attack - Brute Force | 260 | 8 | Fwd Packet Length Max | 0.298327 | 0.209441 |
| Web Attack - Brute Force | 260 | 9 | PSH Flag Count | 0.295661 | 0.258697 |
| Web Attack - Brute Force | 260 | 10 | Bwd Packet Length Std | 0.28273 | -0.28273 |
| Web Attack - XSS | 66 | 1 | Fwd IAT Min | 1.57963 | 1.57864 |
| Web Attack - XSS | 66 | 2 | Bwd Packet Length Min | 0.92765 | 0.92765 |
| Web Attack - XSS | 66 | 3 | Fwd Header Length | 0.772142 | 0.733899 |
| Web Attack - XSS | 66 | 4 | Init_Win_bytes_backward | 0.449301 | 0.200817 |
| Web Attack - XSS | 66 | 5 | Init_Win_bytes_forward | 0.444226 | 0.345315 |
| Web Attack - XSS | 66 | 6 | Fwd Packet Length Max | 0.318638 | 0.189632 |
| Web Attack - XSS | 66 | 7 | Fwd Packet Length Min | 0.313542 | 0.313542 |
| Web Attack - XSS | 66 | 8 | min_seg_size_forward | 0.308225 | 0.308225 |
| Web Attack - XSS | 66 | 9 | PSH Flag Count | 0.306614 | 0.271982 |
| Web Attack - XSS | 66 | 10 | Flow IAT Min | 0.279784 | 0.225059 |

## Sens de l’effet selon la valeur

Les contributions moyennes sont estimées dans des bandes de rang percentile ±5 points autour de Q10, Q50 et Q90; les ex æquo restent regroupés.

| Feature | Bande | Valeur au quantile | Valeur moyenne échantillon | SHAP moyen log-odds | n |
|---|---|---:|---:|---:|---:|
| Init_Win_bytes_forward | bas (Q10) | -0.479733 | -0.479733 | -1.9925 | 6,078 |
| Init_Win_bytes_forward | médian (Q50) | -0.459563 | -0.457164 | 0.494887 | 2,002 |
| Init_Win_bytes_forward | haut (Q90) | 1.66202 | 1.66202 | 0.13267 | 4,292 |
| Bwd Packet Length Min | bas (Q10) | -0.610339 | -0.610339 | 0.770776 | 249 |
| Bwd Packet Length Min | médian (Q50) | -0.610339 | -0.560181 | 0.574769 | 249 |
| Bwd Packet Length Min | haut (Q90) | 0.98645 | 1.01751 | -2.35205 | 2,505 |
| Init_Win_bytes_backward | bas (Q10) | -0.228963 | -0.228963 | -0.52699 | 249 |
| Init_Win_bytes_backward | médian (Q50) | -0.228843 | -0.228843 | -0.452808 | 3,502 |
| Init_Win_bytes_backward | haut (Q90) | -0.154724 | 0.0930088 | -1.90746 | 2,236 |
| Average Packet Size | bas (Q10) | -0.589303 | -0.589303 | 0.0199364 | 4,473 |
| Average Packet Size | médian (Q50) | -0.499294 | -0.498431 | -0.82028 | 2,470 |
| Average Packet Size | haut (Q90) | 0.381902 | 0.597216 | -1.20183 | 2,493 |
| Bwd Packet Length Std | bas (Q10) | -0.410446 | -0.410446 | -0.236149 | 249 |
| Bwd Packet Length Std | médian (Q50) | -0.410446 | -0.410446 | -0.236149 | 249 |
| Bwd Packet Length Std | haut (Q90) | 0.337541 | 0.327886 | -0.767132 | 2,537 |
| Fwd Packet Length Max | bas (Q10) | -0.291726 | -0.291726 | 0.199331 | 5,142 |
| Fwd Packet Length Max | médian (Q50) | -0.255731 | -0.25512 | 0.00253404 | 2,519 |
| Fwd Packet Length Max | haut (Q90) | 0.45267 | 0.435011 | -0.759964 | 2,525 |
| Protocol | bas (Q10) | -0.764406 | -0.832418 | 0.0844791 | 249 |
| Protocol | médian (Q50) | -0.764406 | -0.764406 | 0.0849506 | 249 |
| Protocol | haut (Q90) | 1.3054 | 1.3054 | -1.41566 | 6,063 |
| Fwd Packet Length Min | bas (Q10) | -0.337869 | -0.337869 | 0.240584 | 249 |
| Fwd Packet Length Min | médian (Q50) | -0.337869 | -0.320237 | 0.184059 | 3 |
| Fwd Packet Length Min | haut (Q90) | 0.455579 | 0.470281 | -0.610412 | 2,431 |
| min_seg_size_forward | bas (Q10) | 0.00333811 | 0.00333811 | -0.460526 | 249 |
| min_seg_size_forward | médian (Q50) | 0.00334655 | 0.00334374 | -0.469823 | 516 |
| min_seg_size_forward | haut (Q90) | 0.00334655 | 0.00334936 | 0.167108 | 1 |
| Total Length of Bwd Packets | bas (Q10) | -0.00806534 | -0.00806534 | -0.150908 | 249 |
| Total Length of Bwd Packets | médian (Q50) | -0.00805926 | -0.00805302 | -0.740118 | 2,028 |
| Total Length of Bwd Packets | haut (Q90) | -0.00636463 | -0.00608428 | -0.310703 | 2,622 |

## Gain contre TreeSHAP

| Feature | Rang gain | Rang |SHAP| | Gain | Moyenne |SHAP| |
|---|---:|---:|---:|---:|
| Init_Win_bytes_forward | 19 | 1 | 540.347 | 1.29256 |
| Bwd Packet Length Min | 1 | 2 | 30655.7 | 1.16372 |
| Init_Win_bytes_backward | 9 | 3 | 1555.35 | 1.02417 |
| Average Packet Size | 3 | 4 | 5880.46 | 0.722312 |
| Bwd Packet Length Std | 4 | 5 | 5231 | 0.579748 |
| Fwd Packet Length Max | 7 | 6 | 1996.47 | 0.450901 |
| Protocol | 33 | 7 | 201.102 | 0.409774 |
| Fwd Packet Length Min | 2 | 8 | 18824.9 | 0.343674 |
| min_seg_size_forward | 15 | 9 | 753.855 | 0.335072 |
| Total Length of Bwd Packets | 23 | 10 | 313.385 | 0.266463 |
| Max Packet Length | 13 | 11 | 935.216 | 0.228491 |
| Bwd Header Length | 6 | 12 | 2837.73 | 0.219815 |
| Packet Length Std | 10 | 13 | 1508.56 | 0.215449 |
| Flow IAT Min | 41 | 14 | 127.503 | 0.214223 |
| Fwd Packet Length Std | 11 | 15 | 1149.96 | 0.204614 |
| Bwd Packet Length Mean | 46 | 16 | 93.5685 | 0.203814 |
| Fwd Header Length | 12 | 17 | 993.632 | 0.190562 |
| Fwd IAT Min | 22 | 18 | 317.812 | 0.166199 |
| PSH Flag Count | 26 | 19 | 255.674 | 0.150076 |
| Bwd Packets/s | 34 | 20 | 196.815 | 0.147339 |

### Features surveillées

| Feature | Rang gain | Rang SHAP |
|---|---:|---:|
| Fwd Header Length | 12 | 17 |
| Total Fwd Packets | 53 | 52 |
| min_seg_size_forward | 15 | 9 |
| Init_Win_bytes_forward | 19 | 1 |
| Bwd Packet Length Min | 1 | 2 |
| Fwd Packet Length Min | 2 | 8 |

## Limites

- Les labels d’origine CIC-IDS2017 contiennent du bruit et des divergences d’audit; les explications décrivent le modèle entraîné sur ces labels, pas une vérité réseau vérifiée.
- Des features corrélées peuvent se partager ou se substituer l’importance; les rangs SHAP ne démontrent pas une contribution unique.
- SHAP décrit la contribution à la sortie du modèle et n’établit aucune causalité.

CSV global : [xgboost_v3_shap_global.csv](./xgboost_v3_shap_global.csv); CSV par classe : [xgboost_v3_shap_by_class.csv](./xgboost_v3_shap_by_class.csv); sens de l’effet : [xgboost_v3_shap_direction.csv](./xgboost_v3_shap_direction.csv); comparaison gain/SHAP : [xgboost_v3_shap_gain_comparison.csv](./xgboost_v3_shap_gain_comparison.csv).

Figures : [importance globale](./figures/xgb_v3_b0_seed42_shap_global.png), [par classe](./figures/xgb_v3_b0_seed42_shap_by_class.png) et [dépendances](./figures/xgb_v3_b0_seed42_shap_dependence.png).
