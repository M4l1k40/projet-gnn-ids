# Diagnostic de fuite entre splits

- Features comparées : 69 ; les ports, identifiants, `ts_end` et labels sont exclus.
- Échantillonnage stratifié : train 300000/300000, test 50000/50000, val 50000/50000.
- Les vecteurs identiques sont comparés après arrondi à 6 décimales et uniquement au sein de la même classe.
- Les distances sont euclidiennes dans l’espace des features normalisées ; les voisins sont recherchés dans l’échantillon train stratifié.

## Vecteurs test identiques au train par classe

| Classe | Flux test | Flux train même classe | Vecteurs identiques | Part du test |
|---|---:|---:|---:|---:|
| BENIGN | 830584 | 1181398 | 177387 | 21.3569 % |
| Bot | 476 | 1174 | 0 | 0.0000 % |
| DDoS | 12501 | 76815 | 8 | 0.0640 % |
| DoS GoldenEye | 0 | 6176 | 0 | 0.0000 % |
| DoS Hulk | 14152 | 138074 | 2525 | 17.8420 % |
| DoS Slowhttptest | 1205 | 3300 | 0 | 0.0000 % |
| DoS slowloris | 714 | 3478 | 0 | 0.0000 % |
| FTP-Patator | 1579 | 4764 | 480 | 30.3990 % |
| Heartbleed | 0 | 7 | 0 | 0.0000 % |
| Infiltration | 9 | 22 | 0 | 0.0000 % |
| PortScan | 20046 | 95698 | 19699 | 98.2690 % |
| SSH-Patator | 1192 | 3539 | 541 | 45.3859 % |
| Web Attack - Brute Force | 260 | 905 | 8 | 3.0769 % |
| Web Attack - Sql Injection | 0 | 13 | 0 | 0.0000 % |
| Web Attack - XSS | 66 | 392 | 0 | 0.0000 % |

## Distances au plus proche voisin

| Comparaison | Classe | Échantillon | Train échantillonné | Q1 | Q5 | Q25 | Q50 | Distance nulle |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| test_vers_train | BENIGN | 47043 | 300000 | 0 | 0 | 1.4575576e-05 | 0.00097639682 | 12.4801 % |
| test_vers_train | Bot | 27 | 300000 | 1.1443651e-05 | 1.4920477e-05 | 2.8182198e-05 | 4.4103698e-05 | 0.0000 % |
| test_vers_train | DDoS | 708 | 300000 | 1.1065325e-05 | 5.1152126e-05 | 0.00022426202 | 0.00075415841 | 0.0000 % |
| test_vers_train | DoS Hulk | 802 | 300000 | 0 | 0 | 0.00013225498 | 0.0018078004 | 17.4564 % |
| test_vers_train | DoS Slowhttptest | 68 | 300000 | 1.3009767e-05 | 2.8533414e-05 | 0.00015042794 | 0.00043415062 | 0.0000 % |
| test_vers_train | DoS slowloris | 40 | 300000 | 3.9198854e-06 | 1.1719944e-05 | 0.0061458939 | 3.2268072 | 0.0000 % |
| test_vers_train | FTP-Patator | 89 | 300000 | 0 | 0 | 1.4576552e-06 | 0.0019065129 | 15.7303 % |
| test_vers_train | Infiltration | 1 | 300000 | 0.56885471 | 0.56885471 | 0.56885471 | 0.56885471 | 0.0000 % |
| test_vers_train | PortScan | 1135 | 300000 | 0 | 0 | 0 | 0 | 98.1498 % |
| test_vers_train | SSH-Patator | 68 | 300000 | 0 | 0 | 0 | 0 | 52.9412 % |
| test_vers_train | Web Attack - Brute Force | 15 | 300000 | 1.0287403e-05 | 1.3502091e-05 | 7.9123066e-05 | 0.00020454094 | 0.0000 % |
| test_vers_train | Web Attack - XSS | 4 | 300000 | 0.00013059835 | 0.00016853785 | 0.00035823533 | 0.00063885909 | 0.0000 % |
| val_vers_train | BENIGN | 49418 | 300000 | 0 | 0 | 1.0260761e-05 | 0.00084465742 | 14.5574 % |
| val_vers_train | Bot | 35 | 300000 | 0 | 0 | 1.2978046e-05 | 3.4116765e-05 | 22.8571 % |
| val_vers_train | DoS slowloris | 42 | 300000 | 0 | 0 | 4.3279631e-06 | 9.5096145e-06 | 14.2857 % |
| val_vers_train | FTP-Patator | 270 | 300000 | 0 | 0 | 1.093003e-06 | 0.0027116811 | 18.5185 % |
| val_vers_train | Heartbleed | 1 | 300000 | 3.6816748 | 3.6816748 | 3.6816748 | 3.6816748 | 0.0000 % |
| val_vers_train | Infiltration | 1 | 300000 | 5.9323807 | 5.9323807 | 5.9323807 | 5.9323807 | 0.0000 % |
| val_vers_train | SSH-Patator | 197 | 300000 | 0 | 0 | 0 | 0.0020358972 | 46.7005 % |
| val_vers_train | Web Attack - Brute Force | 35 | 300000 | 4.5033821e-05 | 7.7854924e-05 | 0.00018877667 | 0.00042137127 | 0.0000 % |
| val_vers_train | Web Attack - XSS | 1 | 300000 | 0.0003312166 | 0.0003312166 | 0.0003312166 | 0.0003312166 | 0.0000 % |

## Résumé

- Flux test identiques au train, même classe : 200648/882784 (22.7290 %).
- Médiane de distance test→train : 0.00086085598.
- Distances test→train nulles dans l’échantillon : 14.3500 %.
