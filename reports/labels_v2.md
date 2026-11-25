# Labels v2 — audit et changements

Ce fichier est un artefact séparé. Les Parquets train/val/test et l’audit d’origine ne sont pas modifiés.

Les familles portscan_infiltration et server_response isolent respectivement les désaccords BENIGN associés à la règle Infiltration - Portscan et les réponses émises par 192.168.10.50 vers 172.16.0.1 (ou depuis le port source FTP 21). other_change regroupe les autres divergences; unchanged indique une classe canonique identique au label multi d’origine.

## Changements par bloc et famille

| Bloc | Famille | Flux | Changés |
|---|---|---:|---:|
| train | portscan_infiltration | 16990 | 16990 |
| train | server_response | 17842 | 17842 |
| train | other_change | 573 | 573 |
| train | unchanged | 1480350 | 0 |
| val | portscan_infiltration | 11398 | 11398 |
| val | server_response | 230 | 230 |
| val | other_change | 126 | 126 |
| val | unchanged | 139960 | 0 |
| test | portscan_infiltration | 29787 | 29787 |
| test | server_response | 11079 | 11079 |
| test | other_change | 291 | 291 |
| test | unchanged | 841627 | 0 |

## Transitions de classe

| Bloc | Classe d’origine | Classe canonique | Flux |
|---|---|---|---:|
| test | BENIGN | Bot | 261 |
| test | BENIGN | DDoS | 3992 |
| test | BENIGN | DoS GoldenEye | 206 |
| test | BENIGN | DoS Hulk | 5591 |
| test | BENIGN | DoS Slowhttptest | 626 |
| test | BENIGN | DoS slowloris | 226 |
| test | BENIGN | FTP-Patator | 237 |
| test | BENIGN | Infiltration | 1 |
| test | BENIGN | PortScan | 29787 |
| test | BENIGN | SSH-Patator | 43 |
| test | BENIGN | Web Attack - Brute Force | 159 |
| test | Bot | BENIGN | 2 |
| test | DoS slowloris | BENIGN | 5 |
| test | FTP-Patator | BENIGN | 1 |
| test | Web Attack - XSS | Web Attack - Sql Injection | 20 |
| train | BENIGN | Bot | 523 |
| train | BENIGN | DDoS | 15448 |
| train | BENIGN | DoS slowloris | 136 |
| train | BENIGN | FTP-Patator | 1042 |
| train | BENIGN | Infiltration | 33 |
| train | BENIGN | PortScan | 17013 |
| train | BENIGN | SSH-Patator | 18 |
| train | BENIGN | Web Attack - Brute Force | 738 |
| train | BENIGN | Web Attack - Sql Injection | 2 |
| train | BENIGN | Web Attack - XSS | 435 |
| train | Bot | BENIGN | 2 |
| train | DoS slowloris | BENIGN | 1 |
| train | PortScan | BENIGN | 14 |
| val | BENIGN | Bot | 126 |
| val | BENIGN | FTP-Patator | 133 |
| val | BENIGN | PortScan | 11398 |
| val | BENIGN | Web Attack - Brute Force | 97 |

## Flux Attempted

| Bloc | Effectif | Attempted |
|---|---:|---:|
| train | 1515755 | 51124 |
| val | 151714 | 1274 |
| test | 882784 | 16451 |

Les règles sont des heuristiques d’audit, pas une vérité terrain. `attempted` indique `attempted_category >= 0`; `changed` compare la classe canonique au label multi d’origine. `label_v2_bin` vaut 1 lorsque la classe canonique n’est pas BENIGN.

## Couverture complète des labels v2

`labels_v2_all.parquet` applique les mêmes règles à tous les flow_id de `label_audit.parquet`, y compris les flux hors des blocs V2. Le fichier `labels_v2.parquet` d’origine reste inchangé.

### Familles par bloc V3

| Bloc V3 | Famille | Flux | Changés |
|---|---|---:|---:|
| train | portscan_infiltration | 16990 | 16990 |
| train | server_response | 22359 | 22359 |
| train | other_change | 582 | 582 |
| train | unchanged | 1609197 | 0 |
| val | portscan_infiltration | 11398 | 11398 |
| val | server_response | 230 | 230 |
| val | other_change | 83 | 83 |
| val | unchanged | 229400 | 0 |
| test | portscan_infiltration | 29787 | 29787 |
| test | server_response | 5312 | 5312 |
| test | other_change | 326 | 326 |
| test | unchanged | 596132 | 0 |
| gap | portscan_infiltration | 7196 | 7196 |
| gap | server_response | 13782 | 13782 |
| gap | other_change | 63 | 63 |
| gap | unchanged | 284840 | 0 |

### Flux absents de l’ancien labels_v2, par bloc V3

| Bloc V3 | Famille | Règle d’audit | Classe d’origine | Flux |
|---|---|---|---|---:|
| test | other_change | Botnet - Attempted | BENIGN | 14 |
| test | server_response | Web Attack - Brute Force - Attempted | BENIGN | 43 |
| test | server_response | Web Attack - SQL Injection - Attempted | BENIGN | 20 |
| test | server_response | Web Attack - XSS | BENIGN | 1 |
| test | server_response | Web Attack - XSS - Attempted | BENIGN | 35 |
| test | unchanged | BENIGN | BENIGN | 6517 |
| train | other_change | Botnet - Attempted | BENIGN | 9 |
| train | server_response | DDoS | BENIGN | 1184 |
| train | server_response | SSH-Patator - Attempted | BENIGN | 2 |
| train | unchanged | BENIGN | BENIGN | 17368 |
| val | unchanged | BENIGN | BENIGN | 71 |

Couverture complète de l’audit : 2827677 flux; V3 train/val/test : 2521796 flux; absents de l’ancien `labels_v2.parquet` dans ces blocs : 25264. Ces IDs étaient hors des blocs V2; leurs labels sont calculés depuis `clean.parquet` et l’audit.
