# Validation croisée purgée sur train

- Plis : 5.
- Les segments sont `(day, label_multi)` (BENIGN est segmenté par jour), triés par `ts_end` puis divisés en morceaux contigus de taille aussi égale que possible.
- Pour chaque pli, les lignes de son morceau sont la validation; les flux d’autres classes du même jour à moins de la purge temporelle sont exclus du train.
- Les lignes de validation ne sont jamais marquées purgées dans leur pli.

| Pli | Classe | Train | Validation | Purgés |
|---:|---|---:|---:|---:|
| 0 | BENIGN | 801613 | 236281 | 143504 |
| 0 | Bot | 848 | 235 | 91 |
| 0 | DDoS | 42100 | 15363 | 19352 |
| 0 | DoS GoldenEye | 257 | 1236 | 4683 |
| 0 | DoS Hulk | 75002 | 27615 | 35457 |
| 0 | DoS Slowhttptest | 2103 | 660 | 537 |
| 0 | DoS slowloris | 2092 | 696 | 690 |
| 0 | FTP-Patator | 1828 | 953 | 1983 |
| 0 | Heartbleed | 4 | 2 | 1 |
| 0 | Infiltration | 13 | 5 | 4 |
| 0 | PortScan | 0 | 19140 | 76558 |
| 0 | SSH-Patator | 2527 | 708 | 304 |
| 0 | Web Attack - Brute Force | 0 | 181 | 724 |
| 0 | Web Attack - Sql Injection | 0 | 3 | 10 |
| 0 | Web Attack - XSS | 158 | 79 | 155 |

- Pli 0, classes absentes de la validation : aucune.
| 1 | BENIGN | 797929 | 236280 | 147189 |
| 1 | Bot | 588 | 235 | 351 |
| 1 | DDoS | 26274 | 15363 | 35178 |
| 1 | DoS GoldenEye | 6 | 1235 | 4935 |
| 1 | DoS Hulk | 44651 | 27615 | 65808 |
| 1 | DoS Slowhttptest | 1773 | 660 | 867 |
| 1 | DoS slowloris | 1402 | 696 | 1380 |
| 1 | FTP-Patator | 531 | 953 | 3280 |
| 1 | Heartbleed | 3 | 2 | 2 |
| 1 | Infiltration | 11 | 5 | 6 |
| 1 | PortScan | 372 | 19140 | 76186 |
| 1 | SSH-Patator | 2282 | 708 | 549 |
| 1 | Web Attack - Brute Force | 493 | 181 | 231 |
| 1 | Web Attack - Sql Injection | 0 | 3 | 10 |
| 1 | Web Attack - XSS | 5 | 79 | 308 |

- Pli 1, classes absentes de la validation : aucune.
| 2 | BENIGN | 795661 | 236279 | 149458 |
| 2 | Bot | 170 | 235 | 769 |
| 2 | DDoS | 21851 | 15363 | 39601 |
| 2 | DoS GoldenEye | 6 | 1235 | 4935 |
| 2 | DoS Hulk | 33682 | 27615 | 76777 |
| 2 | DoS Slowhttptest | 1019 | 660 | 1621 |
| 2 | DoS slowloris | 1111 | 696 | 1671 |
| 2 | FTP-Patator | 3050 | 953 | 761 |
| 2 | Heartbleed | 4 | 1 | 2 |
| 2 | Infiltration | 10 | 4 | 8 |
| 2 | PortScan | 365 | 19140 | 76193 |
| 2 | SSH-Patator | 2263 | 708 | 568 |
| 2 | Web Attack - Brute Force | 495 | 181 | 229 |
| 2 | Web Attack - Sql Injection | 0 | 3 | 10 |
| 2 | Web Attack - XSS | 113 | 78 | 201 |

- Pli 2, classes absentes de la validation : aucune.
| 3 | BENIGN | 801206 | 236279 | 143913 |
| 3 | Bot | 577 | 235 | 362 |
| 3 | DDoS | 25970 | 15363 | 35482 |
| 3 | DoS GoldenEye | 29 | 1235 | 4912 |
| 3 | DoS Hulk | 45365 | 27615 | 65094 |
| 3 | DoS Slowhttptest | 1502 | 660 | 1138 |
| 3 | DoS slowloris | 1 | 695 | 2782 |
| 3 | FTP-Patator | 2999 | 953 | 812 |
| 3 | Heartbleed | 1 | 1 | 5 |
| 3 | Infiltration | 4 | 4 | 14 |
| 3 | PortScan | 7 | 19139 | 76552 |
| 3 | SSH-Patator | 2275 | 708 | 556 |
| 3 | Web Attack - Brute Force | 497 | 181 | 227 |
| 3 | Web Attack - Sql Injection | 0 | 2 | 11 |
| 3 | Web Attack - XSS | 133 | 78 | 181 |

- Pli 3, classes absentes de la validation : aucune.
| 4 | BENIGN | 882940 | 236279 | 62179 |
| 4 | Bot | 800 | 234 | 140 |
| 4 | DDoS | 0 | 15363 | 61452 |
| 4 | DoS GoldenEye | 692 | 1235 | 4249 |
| 4 | DoS Hulk | 73289 | 27614 | 37171 |
| 4 | DoS Slowhttptest | 1503 | 660 | 1137 |
| 4 | DoS slowloris | 2048 | 695 | 735 |
| 4 | FTP-Patator | 3439 | 952 | 373 |
| 4 | Heartbleed | 0 | 1 | 6 |
| 4 | Infiltration | 4 | 4 | 14 |
| 4 | PortScan | 372 | 19139 | 76187 |
| 4 | SSH-Patator | 0 | 707 | 2832 |
| 4 | Web Attack - Brute Force | 611 | 181 | 113 |
| 4 | Web Attack - Sql Injection | 0 | 2 | 11 |
| 4 | Web Attack - XSS | 211 | 78 | 103 |

- Pli 4, classes absentes de la validation : aucune.
