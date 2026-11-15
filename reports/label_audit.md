# Audit de sensibilité des labels CIC-IDS2017

Cet audit réapplique, à titre d’analyse, les règles publiées par Liu, Engelen et al. (CNS 2022), en tenant compte des travaux de Lanvin et al. (CRiSIS 2022). Il ne modifie ni `label_multi` ni les Parquets finaux.

## Méthode et fuseau horaire

- Les règles du notebook définissent des fenêtres UTC et s’appliquent à l’heure de début du flux.
- `clean.parquet` stocke `ts_end` comme epoch en secondes à partir de l’heure locale naïve. Le début est calculé par `ts_end - Flow Duration / 1e6`, puis on ajoute 3 h pour UTC.
- Contrôle simple : 4 juillet 2017, 10:00 heure locale devient 13:00 UTC.
- Le début de chaque fenêtre est arrondi à la minute inférieure, comme dans la règle publiée; la borne de fin est inclusive.
- Les appels sont appliqués dans leur ordre d’origine : les catégories Attempted et filtres de paquets peuvent donc remplacer une règle antérieure.
- Le lundi ne comporte pas de bloc d’attaque explicite dans le notebook consulté : ses flux restent BENIGN selon la règle de repli.

## Matrice par jour : label d’origine × règle

Le pourcentage indique la part de la classe d’origine de ce jour attribuée à cette règle.

| Jour | label_multi d’origine | label_rule | Flux | Part de la classe d’origine |
|---|---|---|---:|---:|
| Friday | BENIGN | BENIGN | 381592 | 92.1880 % |
| Friday | BENIGN | Botnet - Attempted | 973 | 0.2351 % |
| Friday | BENIGN | DDoS | 31339 | 7.5711 % |
| Friday | BENIGN | DDoS - Attempted | 1 | 0.0002 % |
| Friday | BENIGN | Portscan | 23 | 0.0056 % |
| Friday | Bot | BENIGN | 4 | 0.2045 % |
| Friday | Bot | Botnet | 1462 | 74.7444 % |
| Friday | Bot | Botnet - Attempted | 490 | 25.0511 % |
| Friday | DDoS | DDoS | 128025 | 100.0000 % |
| Friday | PortScan | BENIGN | 14 | 0.0088 % |
| Friday | PortScan | Portscan | 158790 | 99.9912 % |
| Monday | BENIGN | BENIGN | 529450 | 100.0000 % |
| Thursday | BENIGN | BENIGN | 388926 | 85.2409 % |
| Thursday | BENIGN | Infiltration | 4 | 0.0009 % |
| Thursday | BENIGN | Infiltration - Attempted | 30 | 0.0066 % |
| Thursday | BENIGN | Infiltration - Portscan | 65371 | 14.3274 % |
| Thursday | BENIGN | Web Attack - Brute Force | 1 | 0.0002 % |
| Thursday | BENIGN | Web Attack - Brute Force - Attempted | 1226 | 0.2687 % |
| Thursday | BENIGN | Web Attack - SQL Injection | 3 | 0.0007 % |
| Thursday | BENIGN | Web Attack - SQL Injection - Attempted | 20 | 0.0044 % |
| Thursday | BENIGN | Web Attack - XSS | 2 | 0.0004 % |
| Thursday | BENIGN | Web Attack - XSS - Attempted | 684 | 0.1499 % |
| Thursday | Infiltration | Infiltration | 35 | 97.2222 % |
| Thursday | Infiltration | Infiltration - Attempted | 1 | 2.7778 % |
| Thursday | Web Attack - Brute Force | Web Attack - Brute Force | 73 | 4.8441 % |
| Thursday | Web Attack - Brute Force | Web Attack - Brute Force - Attempted | 1434 | 95.1559 % |
| Thursday | Web Attack - Sql Injection | Web Attack - SQL Injection | 21 | 100.0000 % |
| Thursday | Web Attack - XSS | Web Attack - SQL Injection | 1 | 0.1534 % |
| Thursday | Web Attack - XSS | Web Attack - SQL Injection - Attempted | 19 | 2.9141 % |
| Thursday | Web Attack - XSS | Web Attack - XSS | 16 | 2.4540 % |
| Thursday | Web Attack - XSS | Web Attack - XSS - Attempted | 616 | 94.4785 % |
| Tuesday | BENIGN | BENIGN | 430209 | 99.6295 % |
| Tuesday | BENIGN | FTP-Patator | 19 | 0.0044 % |
| Tuesday | BENIGN | FTP-Patator - Attempted | 1514 | 0.3506 % |
| Tuesday | BENIGN | SSH-Patator | 1 | 0.0002 % |
| Tuesday | BENIGN | SSH-Patator - Attempted | 66 | 0.0153 % |
| Tuesday | FTP-Patator | BENIGN | 1 | 0.0126 % |
| Tuesday | FTP-Patator | FTP-Patator | 3972 | 50.0567 % |
| Tuesday | FTP-Patator | FTP-Patator - Attempted | 3962 | 49.9307 % |
| Tuesday | SSH-Patator | SSH-Patator | 2960 | 50.1950 % |
| Tuesday | SSH-Patator | SSH-Patator - Attempted | 2937 | 49.8050 % |
| Wednesday | BENIGN | BENIGN | 432882 | 98.4566 % |
| Wednesday | BENIGN | DoS GoldenEye | 203 | 0.0462 % |
| Wednesday | BENIGN | DoS GoldenEye - Attempted | 3 | 0.0007 % |
| Wednesday | BENIGN | DoS Hulk | 3680 | 0.8370 % |
| Wednesday | BENIGN | DoS Hulk - Attempted | 1911 | 0.4346 % |
| Wednesday | BENIGN | DoS Slowhttptest | 164 | 0.0373 % |
| Wednesday | BENIGN | DoS Slowhttptest - Attempted | 462 | 0.1051 % |
| Wednesday | BENIGN | DoS Slowloris | 10 | 0.0023 % |
| Wednesday | BENIGN | DoS Slowloris - Attempted | 352 | 0.0801 % |
| Wednesday | BENIGN | Heartbleed | 1 | 0.0002 % |
| Wednesday | DoS GoldenEye | DoS GoldenEye | 7714 | 74.9441 % |
| Wednesday | DoS GoldenEye | DoS GoldenEye - Attempted | 2579 | 25.0559 % |
| Wednesday | DoS Hulk | DoS Hulk | 154861 | 67.2949 % |
| Wednesday | DoS Hulk | DoS Hulk - Attempted | 75262 | 32.7051 % |
| Wednesday | DoS Slowhttptest | DoS Slowhttptest | 2400 | 43.6443 % |
| Wednesday | DoS Slowhttptest | DoS Slowhttptest - Attempted | 3099 | 56.3557 % |
| Wednesday | DoS slowloris | BENIGN | 6 | 0.1035 % |
| Wednesday | DoS slowloris | DoS Slowloris | 4070 | 70.2208 % |
| Wednesday | DoS slowloris | DoS Slowloris - Attempted | 1720 | 29.6756 % |
| Wednesday | Heartbleed | Heartbleed | 11 | 100.0000 % |

## Flux d’attaque d’origine réattribués à BENIGN ou Attempted

| Jour | label_multi d’origine | Vers BENIGN | Vers Attempted |
|---|---|---:|---:|
| Friday | Bot | 4 | 490 |
| Friday | PortScan | 14 | 0 |
| Thursday | Infiltration | 0 | 1 |
| Thursday | Web Attack - Brute Force | 0 | 1434 |
| Thursday | Web Attack - XSS | 0 | 635 |
| Tuesday | FTP-Patator | 1 | 3962 |
| Tuesday | SSH-Patator | 0 | 2937 |
| Wednesday | DoS GoldenEye | 0 | 2579 |
| Wednesday | DoS Hulk | 0 | 75262 |
| Wednesday | DoS Slowhttptest | 0 | 3099 |
| Wednesday | DoS slowloris | 6 | 1720 |

## Flux BENIGN d’origine réattribués à une attaque

| Jour | label_rule | Flux |
|---|---|---:|
| Friday | Botnet - Attempted | 973 |
| Friday | DDoS | 31339 |
| Friday | DDoS - Attempted | 1 |
| Friday | Portscan | 23 |
| Thursday | Infiltration | 4 |
| Thursday | Infiltration - Attempted | 30 |
| Thursday | Infiltration - Portscan | 65371 |
| Thursday | Web Attack - Brute Force | 1 |
| Thursday | Web Attack - Brute Force - Attempted | 1226 |
| Thursday | Web Attack - SQL Injection | 3 |
| Thursday | Web Attack - SQL Injection - Attempted | 20 |
| Thursday | Web Attack - XSS | 2 |
| Thursday | Web Attack - XSS - Attempted | 684 |
| Tuesday | FTP-Patator | 19 |
| Tuesday | FTP-Patator - Attempted | 1514 |
| Tuesday | SSH-Patator | 1 |
| Tuesday | SSH-Patator - Attempted | 66 |
| Wednesday | DoS GoldenEye | 203 |
| Wednesday | DoS GoldenEye - Attempted | 3 |
| Wednesday | DoS Hulk | 3680 |
| Wednesday | DoS Hulk - Attempted | 1911 |
| Wednesday | DoS Slowhttptest | 164 |
| Wednesday | DoS Slowhttptest - Attempted | 462 |
| Wednesday | DoS Slowloris | 10 |
| Wednesday | DoS Slowloris - Attempted | 352 |
| Wednesday | Heartbleed | 1 |

## Part des classes et différences exactes

Une différence est comptée lorsque `label_rule` diffère textuellement de `label_multi`; les différences de casse ou de nomenclature sont donc visibles dans cette sensibilité.

| Classe d’origine | Flux | Part du jeu | Différents | Part différente |
|---|---:|---:|---:|---:|
| BENIGN | 2271122 | 80.3176 % | 108063 | 4.7581 % |
| Bot | 1956 | 0.0692 % | 1956 | 100.0000 % |
| DDoS | 128025 | 4.5276 % | 0 | 0.0000 % |
| DoS GoldenEye | 10293 | 0.3640 % | 2579 | 25.0559 % |
| DoS Hulk | 230123 | 8.1382 % | 75262 | 32.7051 % |
| DoS Slowhttptest | 5499 | 0.1945 % | 3099 | 56.3557 % |
| DoS slowloris | 5796 | 0.2050 % | 5796 | 100.0000 % |
| FTP-Patator | 7935 | 0.2806 % | 3963 | 49.9433 % |
| Heartbleed | 11 | 0.0004 % | 0 | 0.0000 % |
| Infiltration | 36 | 0.0013 % | 1 | 2.7778 % |
| PortScan | 158804 | 5.6161 % | 158804 | 100.0000 % |
| SSH-Patator | 5897 | 0.2085 % | 2937 | 49.8050 % |
| Web Attack - Brute Force | 1507 | 0.0533 % | 1434 | 95.1559 % |
| Web Attack - Sql Injection | 21 | 0.0007 % | 21 | 100.0000 % |
| Web Attack - XSS | 652 | 0.0231 % | 636 | 97.5460 % |

## Règles non reproduites et limites

- Le notebook consulté ne contient pas de bloc d’attaque pour Monday; la convention de repli BENIGN est appliquée, mais aucune règle Monday spécifique n’est inférée.
- L’audit part du Parquet nettoyé et de son `ts_end`; il ne rejoue pas le parseur CSV historique du notebook, dont le seuil de reconstruction AM/PM était différent (heure < 7 contre le seuil 8 de la configuration courante). Les règles de fenêtres, IP, ports et filtres sont appliquées aux timestamps disponibles; les cas de bord à 07:xx ne peuvent pas être garantis identiques à cette ancienne étape de parsing.
- Les catégories de flux Attempted sont émises avec leur règle, mais ne sont pas interprétées comme une correction de label.
- Cet audit ne corrige PAS les erreurs d’extraction de flux (paquets mal ordonnés ou dupliqués) : les vérifier exige les PCAP et un CICFlowMeter modifié.

CSV détaillé : `label_audit.csv`.
