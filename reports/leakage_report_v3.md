# Diagnostic de voisinage et de fuite — split V3

- Test V3 échantillonné avec la graine 42 : 31,501 flux; 69 features déjà normalisées.
- Recherche 1-NN sur tout le train V3 (1,649,128 lignes), requêtes par blocs de 1000, workers=4.
- Scaler propre à cette version : `D:\AI\projet-gnn-ids\models\scaler_v3.joblib`; ses features sont vérifiées, mais il n’est pas réappliqué aux Parquets déjà normalisés.
- XGBoost V3 b0 : seed 42, seuil 0.01539807.

## Distances, seen_in_train et 1-NN par classe

| Classe | n | Distance nulle | seen_in_train | seen∩nulle | seen≠0 | unseen∩0 | Voisin même label | Voisin label différent | Voisin label_bin différent | Recall XGBoost | Recall 1-NN | Q1 | Q5 | Q25 | Q50 | Q75 | Q95 | Q99 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BENIGN | 20,000 | 20.71% (4,142) | 22.68% (4,535) | 4,140 | 395 | 2 | 99.94% (19,987) | 0.07% (13) | 0.07% (13) | nan | 0.9993 | 0 | 0 | 5.84748e-07 | 9.95431e-05 | 0.00724726 | 0.404435 | 1.3679 |
| Bot | 476 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 0.00% (0) | 100.00% (476) | 100.00% (476) | 0.0000 | 0.0000 | 8.49968e-06 | 1.17056e-05 | 1.99142e-05 | 3.31483e-05 | 6.35803e-05 | 0.000366271 | 0.00106202 |
| DDoS | 2,000 | 0.00% (0) | 0.15% (3) | 0 | 3 | 0 | 92.05% (1,841) | 7.95% (159) | 0.30% (6) | 0.9990 | 0.9205 | 2.14915e-06 | 1.1725e-05 | 0.000103523 | 0.000277203 | 0.00133133 | 1.62677 | 2.16974 |
| DoS Hulk | 2,000 | 16.30% (326) | 16.85% (337) | 326 | 11 | 0 | 85.95% (1,719) | 14.05% (281) | 4.75% (95) | 0.9915 | 0.8595 | 0 | 0 | 1.72758e-05 | 0.00156025 | 0.0186468 | 0.149701 | 3.73889 |
| DoS Slowhttptest | 1,205 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 79.83% (962) | 20.17% (243) | 19.34% (233) | 0.9975 | 0.7983 | 7.72776e-06 | 1.4176e-05 | 4.6814e-05 | 0.000108498 | 1.12962 | 20.9273 | 26.9332 |
| DoS slowloris | 714 | 0.28% (2) | 0.00% (0) | 0 | 0 | 2 | 40.06% (286) | 59.94% (428) | 35.99% (257) | 0.9902 | 0.4006 | 1.02969e-06 | 3.51564e-06 | 0.00578708 | 0.278915 | 3.30247 | 9.9154 | 10.6268 |
| FTP-Patator | 1,579 | 23.31% (368) | 30.78% (486) | 368 | 118 | 0 | 99.49% (1,571) | 0.51% (8) | 0.38% (6) | 0.9962 | 0.9949 | 0 | 0 | 3.68352e-07 | 0.00176702 | 0.00528792 | 0.00944236 | 0.0125341 |
| Infiltration | 9 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 44.44% (4) | 55.56% (5) | 55.56% (5) | 0.8889 | 0.4444 | 0.0961235 | 0.164316 | 0.556833 | 1.32215 | 3.18084 | 4.47624 | 4.79635 |
| PortScan | 2,000 | 98.55% (1,971) | 98.55% (1,971) | 1,971 | 0 | 0 | 99.45% (1,989) | 0.55% (11) | 0.50% (10) | 1.0000 | 0.9945 | 0 | 0 | 0 | 0 | 0 | 0 | 6.87527e-05 |
| SSH-Patator | 1,192 | 45.39% (541) | 45.39% (541) | 541 | 0 | 0 | 96.48% (1,150) | 3.52% (42) | 3.44% (41) | 0.9891 | 0.9648 | 0 | 0 | 0 | 0.00219285 | 0.00738378 | 0.0236262 | 0.345554 |
| Web Attack - Brute Force | 260 | 3.08% (8) | 3.08% (8) | 8 | 0 | 0 | 68.85% (179) | 31.15% (81) | 3.08% (8) | 1.0000 | 0.6885 | 0 | 9.65481e-06 | 3.56397e-05 | 7.46462e-05 | 0.000162399 | 0.00112708 | 0.0322655 |
| Web Attack - XSS | 66 | 0.00% (0) | 0.00% (0) | 0 | 0 | 0 | 24.24% (16) | 75.76% (50) | 10.61% (7) | 0.9697 | 0.2424 | 6.0932e-06 | 1.81739e-05 | 4.11131e-05 | 7.06893e-05 | 0.000215598 | 0.37984 | 0.910362 |

## Tableau de décision par classe

| Classe | Voisin de même label | Voisin de label différent | Distance nulle |
|---|---:|---:|---:|
| BENIGN | 99.94% (19,987/20,000) | 0.07% (13/20,000) | 20.71% (4,142/20,000) |
| Bot | 0.00% (0/476) | 100.00% (476/476) | 0.00% (0/476) |
| DDoS | 92.05% (1,841/2,000) | 7.95% (159/2,000) | 0.00% (0/2,000) |
| DoS Hulk | 85.95% (1,719/2,000) | 14.05% (281/2,000) | 16.30% (326/2,000) |
| DoS Slowhttptest | 79.83% (962/1,205) | 20.17% (243/1,205) | 0.00% (0/1,205) |
| DoS slowloris | 40.06% (286/714) | 59.94% (428/714) | 0.28% (2/714) |
| FTP-Patator | 99.49% (1,571/1,579) | 0.51% (8/1,579) | 23.31% (368/1,579) |
| Infiltration | 44.44% (4/9) | 55.56% (5/9) | 0.00% (0/9) |
| PortScan | 99.45% (1,989/2,000) | 0.55% (11/2,000) | 98.55% (1,971/2,000) |
| SSH-Patator | 96.48% (1,150/1,192) | 3.52% (42/1,192) | 45.39% (541/1,192) |
| Web Attack - Brute Force | 68.85% (179/260) | 31.15% (81/260) | 3.08% (8/260) |
| Web Attack - XSS | 24.24% (16/66) | 75.76% (50/66) | 0.00% (0/66) |

## Classes d’attaque avec recall XGBoost < 0,95

| Classe | Recall XGBoost | Voisins de label différent |
|---|---:|---:|
| Bot | 0.0000 | 100.00% (476/476) |
| Infiltration | 0.8889 | 55.56% (5/9) |

## XGBoost b0 par tranche de distance

Quantiles globaux de l’échantillon : p25=3.7787373e-07, p75=0.005828339; la distance exactement nulle forme une catégorie séparée.

| Tranche | n | Positifs | Recall XGBoost | Faux positifs XGBoost |
|---|---:|---:|---:|---:|
| distance nulle | 7,358 | 3,216 | 0.9994 | 15 |
| 0 < distance ≤ p25 | 546 | 128 | 1.0000 | 0 |
| p25–p75 | 15,722 | 5,485 | 0.9112 | 44 |
| > p75 | 7,875 | 2,672 | 0.9858 | 19 |

## Limites

- Les distances euclidiennes peuvent être dominées par les features de grande échelle malgré la standardisation.
- Un voisin très proche n’établit pas une fuite : plusieurs flux peuvent provenir du même outil d’attaque et d’un même épisode.
- Les statistiques décrivent un échantillon stratifié du test, pas une mesure exhaustive.

Table classe : `D:\AI\projet-gnn-ids\reports\leakage_v3_by_class.csv`. Tranches XGBoost : `D:\AI\projet-gnn-ids\reports\leakage_v3_distance_bands.csv`.

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
