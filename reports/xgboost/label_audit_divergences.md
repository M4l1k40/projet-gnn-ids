# Divergences réelles de l’audit des labels

- `label_rule` est d’abord converti en label CIC-IDS2017 canonique via `configs/xgboost.yaml` ; les labels originaux ne sont pas modifiés.
- Un flux est « signalé » si `label_rule` canonique diffère de `label_multi` ou si `attempted_category >= 0`.
- Les effectifs portent uniquement sur les lignes des splits finaux ; les flux du gap ne sont pas inclus.

| Bloc | Flux | Divergences réelles | Règle Attempted | Signalés (union) |
|---|---:|---:|---:|---:|
| train | 1515755 | 35405 | 51124 | 83629 |
| val | 151714 | 11754 | 1274 | 12672 |
| test | 882784 | 41157 | 16451 | 54296 |

## Divergences et signalements par classe

| Bloc | Classe | Effectif | Divergences réelles | Attempted | Signalés (union) |
|---|---|---:|---:|---:|---:|
| train | BENIGN | 1181398 | 35388 | 2900 | 35388 |
| train | Bot | 1174 | 2 | 0 | 2 |
| train | DDoS | 76815 | 0 | 0 | 0 |
| train | DoS GoldenEye | 6176 | 0 | 1725 | 1725 |
| train | DoS Hulk | 138074 | 0 | 38303 | 38303 |
| train | DoS Slowhttptest | 3300 | 0 | 1706 | 1706 |
| train | DoS slowloris | 3478 | 1 | 1103 | 1104 |
| train | FTP-Patator | 4764 | 0 | 2380 | 2380 |
| train | Heartbleed | 7 | 0 | 0 | 0 |
| train | Infiltration | 22 | 0 | 1 | 1 |
| train | PortScan | 95698 | 14 | 0 | 14 |
| train | SSH-Patator | 3539 | 0 | 1761 | 1761 |
| train | Web Attack - Brute Force | 905 | 0 | 862 | 862 |
| train | Web Attack - Sql Injection | 13 | 0 | 0 | 0 |
| train | Web Attack - XSS | 392 | 0 | 383 | 383 |
| val | BENIGN | 149947 | 11754 | 356 | 11754 |
| val | Bot | 108 | 0 | 3 | 3 |
| val | DoS slowloris | 129 | 0 | 84 | 84 |
| val | FTP-Patator | 820 | 0 | 429 | 429 |
| val | Heartbleed | 1 | 0 | 0 | 0 |
| val | Infiltration | 4 | 0 | 0 | 0 |
| val | SSH-Patator | 597 | 0 | 299 | 299 |
| val | Web Attack - Brute Force | 105 | 0 | 100 | 100 |
| val | Web Attack - XSS | 3 | 0 | 3 | 3 |
| test | BENIGN | 830584 | 41129 | 3293 | 41129 |
| test | Bot | 476 | 2 | 474 | 476 |
| test | DDoS | 12501 | 0 | 0 | 0 |
| test | DoS Hulk | 14152 | 0 | 10052 | 10052 |
| test | DoS Slowhttptest | 1205 | 0 | 806 | 806 |
| test | DoS slowloris | 714 | 5 | 151 | 156 |
| test | FTP-Patator | 1579 | 1 | 772 | 773 |
| test | Infiltration | 9 | 0 | 0 | 0 |
| test | PortScan | 20046 | 0 | 0 | 0 |
| test | SSH-Patator | 1192 | 0 | 593 | 593 |
| test | Web Attack - Brute Force | 260 | 0 | 247 | 247 |
| test | Web Attack - XSS | 66 | 20 | 63 | 64 |
