# Comparaison des variantes de split

- Seuil d’exploitabilité : 100 flux minimum dans chacun des blocs train, val et test.
- Les effectifs et pourcentages sont calculés séparément dans chaque classe.
- Les labels multiclasse sont laissés inchangés ; aucune classe n’est regroupée.
- V1 à 4 min sert de référence pour comparer les flux perdus ; V1 à 5 min est affichée séparément.
- Pour V2/V3, « test postérieur à train » mesure les flux test dont `ts_end` est supérieur au minimum `ts_end` train de la même classe, tous jours confondus.
- V3 répartit d’abord les blocs pour couvrir les splits des classes présentes dans au moins trois blocs, puis retire les flux des gaps ; le gap peut donc éliminer les derniers flux d’une classe dans un split, ce qui est reflété dans l’exploitabilité mesurée.

## Résumé comparatif

| Variante | Classes exploitables | Flux gap | BENIGN dans test | Part des BENIGN en test |
|---|---:|---:|---:|---:|
| V1 — assign_split, gap 4 min (référence) | 1/15 | 78288 | 569499/2271122 | 25.08 % |
| V1 — assign_split, gap 5 min | 1/15 | 96697 | 561635/2271122 | 24.73 % |
| V2 — segments d’attaque | 3/15 | 299025 | 826900/2271122 | 36.41 % |
| V3 — blocs stratifiés | 6/15 | 1414364 | 251342/2271122 | 11.07 % |

## V1 — assign_split, gap 4 min (référence)

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable | Test postérieur à train |
|---|---:|---:|---:|---:|:---:|---:|
| BENIGN | 1294054 (56.98 %) | 355862 (15.67 %) | 569499 (25.08 %) | 51707 (2.28 %) | oui | n/a |
| Bot | 1956 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DDoS | 0 (0.00 %) | 22363 (17.47 %) | 79481 (62.08 %) | 26181 (20.45 %) | non | n/a |
| DoS GoldenEye | 10293 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DoS Hulk | 230123 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DoS Slowhttptest | 5499 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DoS slowloris | 5791 (99.91 %) | 0 (0.00 %) | 5 (0.09 %) | 0 (0.00 %) | non | n/a |
| FTP-Patator | 7935 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| Heartbleed | 0 (0.00 %) | 0 (0.00 %) | 11 (100.00 %) | 0 (0.00 %) | non | n/a |
| Infiltration | 18 (50.00 %) | 9 (25.00 %) | 7 (19.44 %) | 2 (5.56 %) | non | n/a |
| PortScan | 138758 (87.38 %) | 20046 (12.62 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| SSH-Patator | 0 (0.00 %) | 4860 (82.41 %) | 639 (10.84 %) | 398 (6.75 %) | non | n/a |
| Web Attack - Brute Force | 1507 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| Web Attack - Sql Injection | 21 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| Web Attack - XSS | 652 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |

## V1 — assign_split, gap 5 min

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable | Test postérieur à train |
|---|---:|---:|---:|---:|:---:|---:|
| BENIGN | 1294054 (56.98 %) | 351979 (15.50 %) | 561635 (24.73 %) | 63454 (2.79 %) | oui | n/a |
| Bot | 1956 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DDoS | 0 (0.00 %) | 22363 (17.47 %) | 73011 (57.03 %) | 32651 (25.50 %) | non | n/a |
| DoS GoldenEye | 10293 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DoS Hulk | 230123 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DoS Slowhttptest | 5499 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| DoS slowloris | 5791 (99.91 %) | 0 (0.00 %) | 5 (0.09 %) | 0 (0.00 %) | non | n/a |
| FTP-Patator | 7935 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| Heartbleed | 0 (0.00 %) | 0 (0.00 %) | 11 (100.00 %) | 0 (0.00 %) | non | n/a |
| Infiltration | 18 (50.00 %) | 9 (25.00 %) | 7 (19.44 %) | 2 (5.56 %) | non | n/a |
| PortScan | 138758 (87.38 %) | 20046 (12.62 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| SSH-Patator | 0 (0.00 %) | 4768 (80.85 %) | 539 (9.14 %) | 590 (10.01 %) | non | n/a |
| Web Attack - Brute Force | 1507 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| Web Attack - Sql Injection | 21 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |
| Web Attack - XSS | 652 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non | n/a |

## V2 — segments d’attaque

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable | Test postérieur à train |
|---|---:|---:|---:|---:|:---:|---:|
| BENIGN | 1193282 (52.54 %) | 141153 (6.22 %) | 826900 (36.41 %) | 109787 (4.83 %) | oui | 826900 (100.00 %) |
| Bot | 1174 (60.02 %) | 88 (4.50 %) | 472 (24.13 %) | 222 (11.35 %) | non | 472 (100.00 %) |
| DDoS | 76815 (60.00 %) | 0 (0.00 %) | 5824 (4.55 %) | 45386 (35.45 %) | non | 5824 (100.00 %) |
| DoS GoldenEye | 6176 (60.00 %) | 0 (0.00 %) | 0 (0.00 %) | 4117 (40.00 %) | non | 0 (0.00 %) |
| DoS Hulk | 138074 (60.00 %) | 0 (0.00 %) | 878 (0.38 %) | 91171 (39.62 %) | non | 878 (100.00 %) |
| DoS Slowhttptest | 3300 (60.01 %) | 0 (0.00 %) | 1200 (21.82 %) | 999 (18.17 %) | non | 1200 (100.00 %) |
| DoS slowloris | 3478 (60.01 %) | 0 (0.00 %) | 376 (6.49 %) | 1942 (33.51 %) | non | 376 (100.00 %) |
| FTP-Patator | 4764 (60.04 %) | 687 (8.66 %) | 1455 (18.34 %) | 1029 (12.97 %) | oui | 1455 (100.00 %) |
| Heartbleed | 7 (63.64 %) | 1 (9.09 %) | 0 (0.00 %) | 3 (27.27 %) | non | 0 (0.00 %) |
| Infiltration | 22 (61.11 %) | 4 (11.11 %) | 9 (25.00 %) | 1 (2.78 %) | non | 9 (100.00 %) |
| PortScan | 95698 (60.26 %) | 0 (0.00 %) | 20046 (12.62 %) | 43060 (27.12 %) | non | 20046 (100.00 %) |
| SSH-Patator | 3539 (60.01 %) | 507 (8.60 %) | 1097 (18.60 %) | 754 (12.79 %) | oui | 1097 (100.00 %) |
| Web Attack - Brute Force | 905 (60.05 %) | 68 (4.51 %) | 216 (14.33 %) | 318 (21.10 %) | non | 216 (100.00 %) |
| Web Attack - Sql Injection | 13 (61.90 %) | 0 (0.00 %) | 0 (0.00 %) | 8 (38.10 %) | non | 0 (0.00 %) |
| Web Attack - XSS | 392 (60.12 %) | 0 (0.00 %) | 32 (4.91 %) | 228 (34.97 %) | non | 32 (100.00 %) |

La dernière colonne donne l’effectif et le pourcentage des flux test dont l’horodatage est postérieur à au moins un flux train de la même classe.

## V3 — blocs stratifiés

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable | Test postérieur à train |
|---|---:|---:|---:|---:|:---:|---:|
| BENIGN | 828040 (36.46 %) | 148059 (6.52 %) | 251342 (11.07 %) | 1043681 (45.95 %) | oui | 251342 (100.00 %) |
| Bot | 1472 (75.26 %) | 49 (2.51 %) | 166 (8.49 %) | 269 (13.75 %) | non | 140 (84.34 %) |
| DDoS | 15206 (11.88 %) | 0 (0.00 %) | 12664 (9.89 %) | 100155 (78.23 %) | non | 0 (0.00 %) |
| DoS GoldenEye | 7500 (72.87 %) | 0 (0.00 %) | 0 (0.00 %) | 2793 (27.13 %) | non | 0 (0.00 %) |
| DoS Hulk | 145 (0.06 %) | 23224 (10.09 %) | 23913 (10.39 %) | 182841 (79.45 %) | oui | 0 (0.00 %) |
| DoS Slowhttptest | 128 (2.33 %) | 1070 (19.46 %) | 1098 (19.97 %) | 3203 (58.25 %) | oui | 0 (0.00 %) |
| DoS slowloris | 0 (0.00 %) | 2924 (50.45 %) | 5 (0.09 %) | 2867 (49.47 %) | non | 0 (0.00 %) |
| FTP-Patator | 3225 (40.64 %) | 247 (3.11 %) | 273 (3.44 %) | 4190 (52.80 %) | oui | 273 (100.00 %) |
| Heartbleed | 0 (0.00 %) | 1 (9.09 %) | 3 (27.27 %) | 7 (63.64 %) | non | 0 (0.00 %) |
| Infiltration | 3 (8.33 %) | 0 (0.00 %) | 5 (13.89 %) | 28 (77.78 %) | non | 2 (40.00 %) |
| PortScan | 231 (0.15 %) | 9018 (5.68 %) | 78932 (49.70 %) | 70623 (44.47 %) | oui | 78932 (100.00 %) |
| SSH-Patator | 2073 (35.15 %) | 1160 (19.67 %) | 173 (2.93 %) | 2491 (42.24 %) | oui | 173 (100.00 %) |
| Web Attack - Brute Force | 75 (4.98 %) | 78 (5.18 %) | 669 (44.39 %) | 685 (45.45 %) | non | 669 (100.00 %) |
| Web Attack - Sql Injection | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | 21 (100.00 %) | non | 0 (0.00 %) |
| Web Attack - XSS | 1 (0.15 %) | 72 (11.04 %) | 69 (10.58 %) | 510 (78.22 %) | non | 69 (100.00 %) |

La dernière colonne donne l’effectif et le pourcentage des flux test dont l’horodatage est postérieur à au moins un flux train de la même classe.

## Chevauchements de plages V2

| Jour | Première plage | Plage chevauchante | Début intersection (epoch s) | Fin intersection (epoch s) | Priorité d’affectation BENIGN |
|---|---|---|---:|---:|---|
| Wednesday | DoS slowloris | DoS Slowhttptest | 1499249700.016045 | 1499251020.000803 | DoS slowloris |
| Wednesday | DoS slowloris | DoS Hulk | 1499251380.000001 | 1499252820.004636 | DoS slowloris |
| Wednesday | DoS slowloris | DoS GoldenEye | 1499253005.004703 | 1499253587.822008 | DoS slowloris |
