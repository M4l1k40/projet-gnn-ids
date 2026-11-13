# Diagnostic de fuite entre splits

- Features comparées : 69 ; les ports, identifiants, `ts_end` et labels sont exclus.
- Échantillonnage stratifié : train 300000/300000, test 50000/50000, val 50000/50000.
- Les vecteurs identiques sont comparés après arrondi à 6 décimales et uniquement au sein de la même classe.
- Les distances sont euclidiennes dans l’espace des features normalisées ; les voisins sont recherchés dans l’échantillon train stratifié.

## Vecteurs test identiques au train par classe

| Classe | Flux test | Flux train même classe | Vecteurs identiques | Part du test |
|---|---:|---:|---:|---:|
| BENIGN | 840429 | 1193282 | 179928 | 21.4091 % |
| Bot | 476 | 1174 | 0 | 0.0000 % |
| DDoS | 12501 | 76815 | 5 | 0.0400 % |
| DoS GoldenEye | 0 | 6176 | 0 | 0.0000 % |
| DoS Hulk | 14152 | 138074 | 2508 | 17.7219 % |
| DoS Slowhttptest | 1205 | 3300 | 0 | 0.0000 % |
| DoS slowloris | 714 | 3478 | 0 | 0.0000 % |
| FTP-Patator | 1579 | 4764 | 478 | 30.2723 % |
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
| test_vers_train | BENIGN | 47076 | 300000 | 0 | 0 | 1.4025089e-05 | 0.0010124128 | 12.5712 % |
| test_vers_train | Bot | 27 | 300000 | 1.482396e-05 | 1.6240025e-05 | 3.3747499e-05 | 5.8012528e-05 | 0.0000 % |
| test_vers_train | DDoS | 700 | 300000 | 1.0837655e-05 | 5.0850798e-05 | 0.00022469382 | 0.00075593551 | 0.0000 % |
| test_vers_train | DoS Hulk | 793 | 300000 | 0 | 0 | 0.00013110948 | 0.0018132859 | 17.5284 % |
| test_vers_train | DoS Slowhttptest | 67 | 300000 | 1.2974062e-05 | 2.8397552e-05 | 0.00015502268 | 0.00042371889 | 0.0000 % |
| test_vers_train | DoS slowloris | 40 | 300000 | 3.9319591e-06 | 1.175599e-05 | 0.0061581947 | 3.2275541 | 0.0000 % |
| test_vers_train | FTP-Patator | 88 | 300000 | 0 | 0 | 1.4641907e-06 | 0.0018984751 | 15.9091 % |
| test_vers_train | Infiltration | 1 | 300000 | 0.56700044 | 0.56700044 | 0.56700044 | 0.56700044 | 0.0000 % |
| test_vers_train | PortScan | 1123 | 300000 | 0 | 0 | 0 | 0 | 98.1300 % |
| test_vers_train | SSH-Patator | 67 | 300000 | 0 | 0 | 0 | 0 | 53.7313 % |
| test_vers_train | Web Attack - Brute Force | 14 | 300000 | 1.0251018e-05 | 1.3246787e-05 | 7.2854499e-05 | 0.00019168424 | 0.0000 % |
| test_vers_train | Web Attack - XSS | 4 | 300000 | 0.00013090784 | 0.00016894447 | 0.00035912758 | 0.00070082217 | 0.0000 % |
| val_vers_train | BENIGN | 49425 | 300000 | 0 | 0 | 1.0416762e-05 | 0.0008279616 | 14.3207 % |
| val_vers_train | Bot | 35 | 300000 | 0 | 0 | 1.3003378e-05 | 3.41739e-05 | 22.8571 % |
| val_vers_train | DoS slowloris | 42 | 300000 | 0 | 0 | 4.3439831e-06 | 9.5401695e-06 | 14.2857 % |
| val_vers_train | FTP-Patator | 267 | 300000 | 0 | 0 | 1.0946416e-06 | 0.0026771341 | 18.7266 % |
| val_vers_train | Heartbleed | 1 | 300000 | 3.6837819 | 3.6837819 | 3.6837819 | 3.6837819 | 0.0000 % |
| val_vers_train | Infiltration | 1 | 300000 | 3.31946 | 3.31946 | 3.31946 | 3.31946 | 0.0000 % |
| val_vers_train | SSH-Patator | 194 | 300000 | 0 | 0 | 0 | 0.0020381517 | 46.9072 % |
| val_vers_train | Web Attack - Brute Force | 34 | 300000 | 4.4716669e-05 | 7.7709301e-05 | 0.00017859426 | 0.00043901738 | 0.0000 % |
| val_vers_train | Web Attack - XSS | 1 | 300000 | 0.0003320505 | 0.0003320505 | 0.0003320505 | 0.0003320505 | 0.0000 % |

## Résumé

- Flux test identiques au train, même classe : 203167/892629 (22.7605 %).
- Médiane de distance test→train : 0.00089558194.
- Distances test→train nulles dans l’échantillon : 14.4180 %.
