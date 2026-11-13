# Répartition des classes par bloc chronologique

- Mode : `count`.
- Ratios : train 60%, val 15%, test 25%.
- Gap : 5 minute(s).
- Seuil d’exploitabilité : au moins 100 flux dans chacun des blocs train, val et test.

Les pourcentages sont calculés sur l’effectif total de chaque classe dans la portée concernée. Les flux du bloc gap restent visibles et les classes ne sont ni supprimées ni regroupées dans l’analyse multiclasse.

## Vue globale — multiclasse

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable |
|---|---:|---:|---:|---:|:---:|
| BENIGN | 1294054 (56.98 %) | 351979 (15.50 %) | 561635 (24.73 %) | 63454 (2.79 %) | oui |
| Bot | 1956 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DDoS | 0 (0.00 %) | 22363 (17.47 %) | 73011 (57.03 %) | 32651 (25.50 %) | non |
| DoS GoldenEye | 10293 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DoS Hulk | 230123 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DoS Slowhttptest | 5499 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DoS slowloris | 5791 (99.91 %) | 0 (0.00 %) | 5 (0.09 %) | 0 (0.00 %) | non |
| FTP-Patator | 7935 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| Heartbleed | 0 (0.00 %) | 0 (0.00 %) | 11 (100.00 %) | 0 (0.00 %) | non |
| Infiltration | 18 (50.00 %) | 9 (25.00 %) | 7 (19.44 %) | 2 (5.56 %) | non |
| PortScan | 138758 (87.38 %) | 20046 (12.62 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| SSH-Patator | 0 (0.00 %) | 4768 (80.85 %) | 539 (9.14 %) | 590 (10.01 %) | non |
| Web Attack - Brute Force | 1507 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| Web Attack - Sql Injection | 21 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| Web Attack - XSS | 652 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |

## Vue par jour — multiclasse

### Friday

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable |
|---|---:|---:|---:|---:|:---:|
| BENIGN | 280914 (67.87 %) | 58060 (14.03 %) | 59894 (14.47 %) | 15060 (3.64 %) | oui |
| Bot | 1956 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DDoS | 0 (0.00 %) | 22363 (17.47 %) | 73011 (57.03 %) | 32651 (25.50 %) | non |
| PortScan | 138758 (87.38 %) | 20046 (12.62 %) | 0 (0.00 %) | 0 (0.00 %) | non |

### Monday

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable |
|---|---:|---:|---:|---:|:---:|
| BENIGN | 317670 (60.00 %) | 73967 (13.97 %) | 124171 (23.45 %) | 13642 (2.58 %) | oui |

### Thursday

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable |
|---|---:|---:|---:|---:|:---:|
| BENIGN | 272892 (59.81 %) | 60371 (13.23 %) | 102060 (22.37 %) | 20944 (4.59 %) | oui |
| Infiltration | 18 (50.00 %) | 9 (25.00 %) | 7 (19.44 %) | 2 (5.56 %) | non |
| Web Attack - Brute Force | 1507 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| Web Attack - Sql Injection | 21 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| Web Attack - XSS | 652 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |

### Tuesday

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable |
|---|---:|---:|---:|---:|:---:|
| BENIGN | 259450 (60.08 %) | 57728 (13.37 %) | 106914 (24.76 %) | 7717 (1.79 %) | oui |
| FTP-Patator | 7935 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| SSH-Patator | 0 (0.00 %) | 4768 (80.85 %) | 539 (9.14 %) | 590 (10.01 %) | non |

### Wednesday

| Classe | Train (n, %) | Val (n, %) | Test (n, %) | Gap (n, %) | Exploitable |
|---|---:|---:|---:|---:|:---:|
| BENIGN | 163128 (37.10 %) | 101853 (23.17 %) | 168596 (38.35 %) | 6091 (1.39 %) | oui |
| DoS GoldenEye | 10293 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DoS Hulk | 230123 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DoS Slowhttptest | 5499 (100.00 %) | 0 (0.00 %) | 0 (0.00 %) | 0 (0.00 %) | non |
| DoS slowloris | 5791 (99.91 %) | 0 (0.00 %) | 5 (0.09 %) | 0 (0.00 %) | non |
| Heartbleed | 0 (0.00 %) | 0 (0.00 %) | 11 (100.00 %) | 0 (0.00 %) | non |

## Exploitabilité binaire

- Classes exploitables : 2/2 (ATTACK, BENIGN).

## Classes multiclasse non exploitables et heures observées

- Multiclasse **Bot** (global) — train: 1956 flux, 09:34:00–12:59:00; val: absent; test: absent; gap: absent.
- Multiclasse **DDoS** (global) — train: absent; val: 22363 flux, 15:56:00–15:59:00; test: 73011 flux, 16:03:00–16:16:00; gap: 32651 flux, 15:58:00–16:04:00.
- Multiclasse **DoS GoldenEye** (global) — train: 10293 flux, 11:10:00–11:19:00; val: absent; test: absent; gap: absent.
- Multiclasse **DoS Hulk** (global) — train: 230123 flux, 10:43:00–11:07:00; val: absent; test: absent; gap: absent.
- Multiclasse **DoS Slowhttptest** (global) — train: 5499 flux, 10:15:00–10:37:00; val: absent; test: absent; gap: absent.
- Multiclasse **DoS slowloris** (global) — train: 5791 flux, 09:01:00–10:11:00; val: absent; test: 5 flux, 14:24:00–14:25:00; gap: absent.
- Multiclasse **FTP-Patator** (global) — train: 7935 flux, 09:17:00–10:30:00; val: absent; test: absent; gap: absent.
- Multiclasse **Heartbleed** (global) — train: absent; val: absent; test: 11 flux, 15:12:00–15:32:00; gap: absent.
- Multiclasse **Infiltration** (global) — train: 18 flux, 14:19:00–14:42:00; val: 9 flux, 15:04:00–15:23:00; test: 7 flux, 15:31:00–15:45:00; gap: 2 flux, 15:26:00–15:28:00.
- Multiclasse **PortScan** (global) — train: 138758 flux, 13:05:00–14:56:00; val: 20046 flux, 15:03:00–15:23:00; test: absent; gap: absent.
- Multiclasse **SSH-Patator** (global) — train: absent; val: 4768 flux, 14:10:00–14:59:00; test: 539 flux, 15:05:00–15:11:00; gap: 590 flux, 14:09:00–15:04:00.
- Multiclasse **Web Attack - Brute Force** (global) — train: 1507 flux, 09:15:00–10:00:00; val: absent; test: absent; gap: absent.
- Multiclasse **Web Attack - Sql Injection** (global) — train: 21 flux, 10:40:00–10:42:00; val: absent; test: absent; gap: absent.
- Multiclasse **Web Attack - XSS** (global) — train: 652 flux, 10:15:00–10:35:00; val: absent; test: absent; gap: absent.
- Multiclasse **Bot** (Friday) — train: 1956 flux, 09:34:00–12:59:00; val: absent; test: absent; gap: absent.
- Multiclasse **DDoS** (Friday) — train: absent; val: 22363 flux, 15:56:00–15:59:00; test: 73011 flux, 16:03:00–16:16:00; gap: 32651 flux, 15:58:00–16:04:00.
- Multiclasse **PortScan** (Friday) — train: 138758 flux, 13:05:00–14:56:00; val: 20046 flux, 15:03:00–15:23:00; test: absent; gap: absent.
- Multiclasse **Infiltration** (Thursday) — train: 18 flux, 14:19:00–14:42:00; val: 9 flux, 15:04:00–15:23:00; test: 7 flux, 15:31:00–15:45:00; gap: 2 flux, 15:26:00–15:28:00.
- Multiclasse **Web Attack - Brute Force** (Thursday) — train: 1507 flux, 09:15:00–10:00:00; val: absent; test: absent; gap: absent.
- Multiclasse **Web Attack - Sql Injection** (Thursday) — train: 21 flux, 10:40:00–10:42:00; val: absent; test: absent; gap: absent.
- Multiclasse **Web Attack - XSS** (Thursday) — train: 652 flux, 10:15:00–10:35:00; val: absent; test: absent; gap: absent.
- Multiclasse **FTP-Patator** (Tuesday) — train: 7935 flux, 09:17:00–10:30:00; val: absent; test: absent; gap: absent.
- Multiclasse **SSH-Patator** (Tuesday) — train: absent; val: 4768 flux, 14:10:00–14:59:00; test: 539 flux, 15:05:00–15:11:00; gap: 590 flux, 14:09:00–15:04:00.
- Multiclasse **DoS GoldenEye** (Wednesday) — train: 10293 flux, 11:10:00–11:19:00; val: absent; test: absent; gap: absent.
- Multiclasse **DoS Hulk** (Wednesday) — train: 230123 flux, 10:43:00–11:07:00; val: absent; test: absent; gap: absent.
- Multiclasse **DoS Slowhttptest** (Wednesday) — train: 5499 flux, 10:15:00–10:37:00; val: absent; test: absent; gap: absent.
- Multiclasse **DoS slowloris** (Wednesday) — train: 5791 flux, 09:01:00–10:11:00; val: absent; test: 5 flux, 14:24:00–14:25:00; gap: absent.
- Multiclasse **Heartbleed** (Wednesday) — train: absent; val: absent; test: 11 flux, 15:12:00–15:32:00; gap: absent.

## Classes binaires non exploitables et heures observées

- Binaire **ATTACK** (Thursday) — train: 2198 flux, 09:15:00–14:42:00; val: 9 flux, 15:04:00–15:23:00; test: 7 flux, 15:31:00–15:45:00; gap: 2 flux, 15:26:00–15:28:00.
- Binaire **ATTACK** (Wednesday) — train: 251706 flux, 09:01:00–11:19:00; val: absent; test: 16 flux, 14:24:00–15:32:00; gap: absent.
