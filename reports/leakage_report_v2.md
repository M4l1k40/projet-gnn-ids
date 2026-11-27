# Diagnostic de voisinage et de fuite — split V2

- Test V2 échantillonné avec la graine 42 : 31,501 flux; 69 features déjà normalisées.
- Recherche 1-NN sur tout le train V2 (1,515,755 lignes), requêtes par blocs de 1000, workers=4.
- Scaler propre à cette version : `D:\AI\projet-gnn-ids\models\scaler.joblib`; ses features sont vérifiées, mais il n’est pas réappliqué aux Parquets déjà normalisés.
- XGBoost V2 b0 : seed 42, seuil 0.47832090.

## Distances, seen_in_train et 1-NN par classe

| Classe | n | Distance nulle | seen_in_train | seen∩nulle | seen≠0 | unseen∩0 | Voisin même label | Voisin label différent | Voisin label_bin différent | Recall XGBoost | Recall 1-NN | Q1 | Q5 | Q25 | Q50 | Q75 | Q95 | Q99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BENIGN | 20,000 | 19.53% (3,906) | 21.75% (4,350) | 3,904 | 446 | 2 | 99.92% (19,984) | 0.08% (16) | 0.08% (16) | nan | 0.9992 | 0 | 0 | 1.17598e-06 | 0.000146531 | 0.0110254 | 0.489936 | 2.00486 |
| Bot | 476 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 0.00% (0) | 100.00% (476) | 100.00% (476) | 0.0000 | 0.0000 | 8.35601e-06 | 1.15437e-05 | 1.9757e-05 | 3.35367e-05 | 6.26017e-05 | 0.000362938 | 0.00105064 |
| DDoS | 2,000 | 0.00% (0) | 0.05% (1) | 0 | 1 | 0 | 92.05% (1,841) | 7.95% (159) | 0.30% (6) | 0.9965 | 0.9205 | 2.10125e-06 | 1.15656e-05 | 0.000102208 | 0.000272793 | 0.00131305 | 1.60499 | 2.12483 |
| DoS Hulk | 2,000 | 16.30% (326) | 16.65% (333) | 326 | 7 | 0 | 85.75% (1,715) | 14.25% (285) | 5.05% (101) | 0.9890 | 0.8575 | 0 | 0 | 1.70138e-05 | 0.00150537 | 0.0191727 | 0.149851 | 3.68579 |
| DoS Slowhttptest | 1,205 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 81.16% (978) | 18.84% (227) | 17.84% (215) | 0.8946 | 0.8116 | 7.35551e-06 | 1.41115e-05 | 4.80494e-05 | 0.000109178 | 1.10857 | 21.4797 | 27.6785 |
| DoS slowloris | 714 | 0.28% (2) | 0.00% (0) | 0 | 0 | 2 | 40.20% (287) | 59.80% (427) | 35.99% (257) | 0.9818 | 0.4020 | 1.01732e-06 | 3.43049e-06 | 0.00574833 | 0.27273 | 3.30606 | 9.92547 | 10.5845 |
| FTP-Patator | 1,579 | 23.31% (368) | 30.40% (480) | 368 | 112 | 0 | 99.49% (1,571) | 0.51% (8) | 0.38% (6) | 0.9962 | 0.9949 | 0 | 0 | 3.54588e-07 | 0.00178929 | 0.00530187 | 0.0094312 | 0.0123486 |
| Infiltration | 9 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 44.44% (4) | 55.56% (5) | 55.56% (5) | 0.3333 | 0.4444 | 0.0963514 | 0.16722 | 0.568855 | 1.3223 | 3.20194 | 4.48851 | 4.82695 |
| PortScan | 2,000 | 98.55% (1,971) | 98.55% (1,971) | 1,971 | 0 | 0 | 99.00% (1,980) | 1.00% (20) | 0.95% (19) | 0.9985 | 0.9900 | 0 | 0 | 0 | 0 | 0 | 0 | 6.77301e-05 |
| SSH-Patator | 1,192 | 45.39% (541) | 45.39% (541) | 541 | 0 | 0 | 96.56% (1,151) | 3.44% (41) | 3.36% (40) | 0.9648 | 0.9656 | 0 | 0 | 0 | 0.00215915 | 0.0073962 | 0.0234175 | 0.353555 |
| Web Attack - Brute Force | 260 | 3.08% (8) | 3.08% (8) | 8 | 0 | 0 | 69.23% (180) | 30.77% (80) | 1.92% (5) | 0.9885 | 0.6923 | 0 | 9.45987e-06 | 3.51289e-05 | 7.32055e-05 | 0.000159647 | 0.00113017 | 0.0323321 |
| Web Attack - XSS | 66 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 24.24% (16) | 75.76% (50) | 10.61% (7) | 0.8636 | 0.2424 | 5.99328e-06 | 1.78149e-05 | 4.04101e-05 | 6.94233e-05 | 0.000211651 | 0.40795 | 0.951248 |

## Tableau de décision par classe

| Classe | Voisin de même label | Voisin de label différent | Distance nulle |
|---|---:|---:|---:|
| BENIGN | 99.92% (19,984/20,000) | 0.08% (16/20,000) | 19.53% (3,906/20,000) |
| Bot | 0.00% (0/476) | 100.00% (476/476) | 0.00% (0/476) |
| DDoS | 92.05% (1,841/2,000) | 7.95% (159/2,000) | 0.00% (0/2,000) |
| DoS Hulk | 85.75% (1,715/2,000) | 14.25% (285/2,000) | 16.30% (326/2,000) |
| DoS Slowhttptest | 81.16% (978/1,205) | 18.84% (227/1,205) | 0.00% (0/1,205) |
| DoS slowloris | 40.20% (287/714) | 59.80% (427/714) | 0.28% (2/714) |
| FTP-Patator | 99.49% (1,571/1,579) | 0.51% (8/1,579) | 23.31% (368/1,579) |
| Infiltration | 44.44% (4/9) | 55.56% (5/9) | 0.00% (0/9) |
| PortScan | 99.00% (1,980/2,000) | 1.00% (20/2,000) | 98.55% (1,971/2,000) |
| SSH-Patator | 96.56% (1,151/1,192) | 3.44% (41/1,192) | 45.39% (541/1,192) |
| Web Attack - Brute Force | 69.23% (180/260) | 30.77% (80/260) | 3.08% (8/260) |
| Web Attack - XSS | 24.24% (16/66) | 75.76% (50/66) | 0.00% (0/66) |

## Classes d’attaque avec recall XGBoost < 0,95

| Classe | Recall XGBoost | Voisins de label différent |
|---|---:|---:|
| Bot | 0.0000 | 100.00% (476/476) |
| DoS Slowhttptest | 0.8946 | 18.84% (227/1,205) |
| Infiltration | 0.3333 | 55.56% (5/9) |
| Web Attack - XSS | 0.8636 | 75.76% (50/66) |

## XGBoost b0 par tranche de distance

Quantiles globaux de l’échantillon : p25=3.8728688e-07, p75=0.0069822404; la distance exactement nulle forme une catégorie séparée.

| Tranche | n | Positifs | Recall XGBoost | Faux positifs XGBoost |
|---|---:|---:|---:|---:|
| distance nulle | 7,122 | 3,216 | 0.9994 | 5 |
| 0 < distance ≤ p25 | 756 | 161 | 1.0000 | 0 |
| p25–p75 | 15,748 | 5,664 | 0.9115 | 4 |
| > p75 | 7,875 | 2,460 | 0.9142 | 6 |

## Limites

- Les distances euclidiennes peuvent être dominées par les features de grande échelle malgré la standardisation.
- Un voisin très proche n’établit pas une fuite : plusieurs flux peuvent provenir du même outil d’attaque et d’un même épisode.
- Les statistiques décrivent un échantillon stratifié du test, pas une mesure exhaustive.

Table classe : `D:\AI\projet-gnn-ids\reports\leakage_v2_by_class.csv`. Tranches XGBoost : `D:\AI\projet-gnn-ids\reports\leakage_v2_distance_bands.csv`.

## Comparaison V3 contre V2 — distance nulle

Part de l’échantillon dont la distance minimale est exactement nulle; variation exprimée en points de pourcentage (V3 − V2).

| Classe | Part V2 | Part V3 | Variation (pp) |
|---|---:|---:|---:|
| BENIGN | 19.53% | 20.71% | +1.18 |
| Bot | 0.00% | 0.00% | +0.00 |
| DDoS | 0.00% | 0.00% | +0.00 |
| DoS Hulk | 16.30% | 16.30% | +0.00 |
| DoS Slowhttptest | 0.00% | 0.00% | +0.00 |
| DoS slowloris | 0.28% | 0.28% | +0.00 |
| FTP-Patator | 23.31% | 23.31% | +0.00 |
| Infiltration | 0.00% | 0.00% | +0.00 |
| PortScan | 98.55% | 98.55% | +0.00 |
| SSH-Patator | 45.39% | 45.39% | +0.00 |
| Web Attack - Brute Force | 3.08% | 3.08% | +0.00 |
| Web Attack - XSS | 0.00% | 0.00% | +0.00 |
