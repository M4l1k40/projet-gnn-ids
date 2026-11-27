# Split alternatif V3

V3 conserve les coupures de chaque classe d’attaque. Seule la propriété des flux BENIGN change : ils héritent des coupures de la classe dont la fenêtre officielle, étendue de sa tolérance, les contient; en cas de chevauchement, la fenêtre la plus précoce gagne. Hors fenêtre, le split chronologique de référence du jour s’applique.

- Paramètre utilisé : `split.final.benign_ownership=official_window`; V2 garde son split d’origine.
- Lignes source : 2827677; conservées V3 : 2521796; perdues en gap V3 : 305881.
- Flux en gap V2 : 277424; checks d’ordre/gap d’attaque passés : 19.
- Artefacts V3 : `D:\AI\projet-gnn-ids\data\processed_v3`; features inchangées : 69.

## Couverture des labels v2

labels_v2 couvre 2 496 532 / 2 521 796 flow_id conservés dans V3. Les identifiants absents sont tous BENIGN. Ils ne sont pas ajoutés à `labels_v2.parquet`, qui reste inchangé.

| Bloc V3 | flow_id absents de labels_v2 | Classes d’origine |
|---|---:|---|
| train | 18 563 | BENIGN (18 563) |
| val | 71 | BENIGN (71) |
| test | 6 630 | BENIGN (6 630) |
| Total | 25 264 | BENIGN (25 264) |

## BENIGN par jour et bloc

| Jour | V2 train/val/test/gap | V3 train/val/test/gap |
|---|---:|---:|
| Friday | 227466/34930/118653/32879 | 294912/22067/66311/30638 |
| Monday | 317670/76126/127538/8116 | 317670/76126/127538/8116 |
| Thursday | 281670/23528/120514/30555 | 277983/23528/123309/31447 |
| Tuesday | 268452/12396/131941/19020 | 279276/12396/124627/15510 |
| Wednesday | 86140/2967/331938/18623 | 144930/105227/137572/51939 |
| Total | 1181398/149947/830584/109193 | 1314771/239344/579357/137650 |

## Effectifs par classe et bloc

| Classe d’origine | V2 train/val/test/gap | V3 train/val/test/gap |
|---|---:|---:|
| BENIGN | 1181398/149947/830584/109193 | 1314771/239344/579357/137650 |
| Bot | 1174/108/476/198 | 1174/108/476/198 |
| DDoS | 76815/0/12501/38709 | 76815/0/12501/38709 |
| DoS GoldenEye | 6176/0/0/4117 | 6176/0/0/4117 |
| DoS Hulk | 138074/0/14152/77897 | 138074/0/14152/77897 |
| DoS Slowhttptest | 3300/0/1205/994 | 3300/0/1205/994 |
| DoS slowloris | 3478/129/714/1475 | 3478/129/714/1475 |
| FTP-Patator | 4764/820/1579/772 | 4764/820/1579/772 |
| Heartbleed | 7/1/0/3 | 7/1/0/3 |
| Infiltration | 22/4/9/1 | 22/4/9/1 |
| PortScan | 95698/0/20046/43060 | 95698/0/20046/43060 |
| SSH-Patator | 3539/597/1192/569 | 3539/597/1192/569 |
| Web Attack - Brute Force | 905/105/260/237 | 905/105/260/237 |
| Web Attack - Sql Injection | 13/0/0/8 | 13/0/0/8 |
| Web Attack - XSS | 392/3/66/191 | 392/3/66/191 |

Classes avec au moins 50 flux train et test : BENIGN, Bot, DDoS, DoS Hulk, DoS Slowhttptest, DoS slowloris, FTP-Patator, PortScan, SSH-Patator, Web Attack - Brute Force, Web Attack - XSS.

## Paires miroir (flux test; blocs du flux aller)

| Famille/règle | Candidats V2 | V2 train/val/test/gap/introuvable | Paires inter-blocs V2 | Candidats V3 | V3 train/val/test/gap/introuvable | Paires inter-blocs V3 |
|---|---:|---:|---:|---:|---:|---:|
| server_response | 11079 | 3253/0/3888/3300/638 | 6553 | 5213 | 0/0/3722/1021/470 | 1021 |
| DoS Hulk (+ Attempted) | 19743 | 2795/0/1608/2252/13088 | 5047 | 14533 | 0/0/776/711/13046 | 711 |

## Attaques par pli de train V3

| Classe | Pli 0 | Pli 1 | Pli 2 | Pli 3 | Pli 4 | Total |
|---|---:|---:|---:|---:|---:|---:|
| Bot | 235 | 235 | 235 | 235 | 234 | 1174 |
| DDoS | 15363 | 15363 | 15363 | 15363 | 15363 | 76815 |
| DoS GoldenEye | 1236 | 1235 | 1235 | 1235 | 1235 | 6176 |
| DoS Hulk | 27615 | 27615 | 27615 | 27615 | 27614 | 138074 |
| DoS Slowhttptest | 660 | 660 | 660 | 660 | 660 | 3300 |
| DoS slowloris | 696 | 696 | 696 | 695 | 695 | 3478 |
| FTP-Patator | 953 | 953 | 953 | 953 | 952 | 4764 |
| Heartbleed | 2 | 2 | 1 | 1 | 1 | 7 |
| Infiltration | 5 | 5 | 4 | 4 | 4 | 22 |
| PortScan | 19140 | 19140 | 19140 | 19139 | 19139 | 95698 |
| SSH-Patator | 708 | 708 | 708 | 708 | 707 | 3539 |
| Web Attack - Brute Force | 181 | 181 | 181 | 181 | 181 | 905 |
| Web Attack - Sql Injection | 3 | 3 | 3 | 2 | 2 | 13 |
| Web Attack - XSS | 79 | 79 | 78 | 78 | 78 | 392 |

## seen_in_train V3 (proportion par classe)

| Bloc | Classe | Effectif | seen_in_train |
|---|---|---:|---:|
| test | BENIGN | 579357 | 22.583 % |
| test | Bot | 476 | 0.000 % |
| test | DDoS | 12501 | 0.056 % |
| test | DoS Hulk | 14152 | 18.026 % |
| test | DoS Slowhttptest | 1205 | 0.000 % |
| test | DoS slowloris | 714 | 0.000 % |
| test | FTP-Patator | 1579 | 30.779 % |
| test | Infiltration | 9 | 0.000 % |
| test | PortScan | 20046 | 98.264 % |
| test | SSH-Patator | 1192 | 45.386 % |
| test | Web Attack - Brute Force | 260 | 3.077 % |
| test | Web Attack - XSS | 66 | 0.000 % |
| val | BENIGN | 239344 | 22.312 % |
| val | Bot | 108 | 35.185 % |
| val | DoS slowloris | 129 | 14.729 % |
| val | FTP-Patator | 820 | 34.512 % |
| val | Heartbleed | 1 | 0.000 % |
| val | Infiltration | 4 | 0.000 % |
| val | SSH-Patator | 597 | 48.241 % |
| val | Web Attack - Brute Force | 105 | 5.714 % |
| val | Web Attack - XSS | 3 | 0.000 % |

## Fenêtre officielle contre intervalle robuste [p0,5; p99,5]

| Jour | Classe | Intervalle robuste | Officiel ± tolérance | Écart précoce/tardif (min) | Contrôle |
|---|---|---|---|---:|---|
| Friday | Bot | 10:04:00–12:57:01 | 10:00–11:04 | 0.00/113.02 | ALERTE >5 min |
| Friday | DDoS | 15:56:00–16:16:01 | 15:54–16:18 | 0.00/0.00 | OK |
| Friday | PortScan | 14:51:00–15:23:00 | 13:53–15:31 | 0.00/0.00 | OK |
| Thursday | Infiltration | 14:19:07–15:45:44 | 14:17–15:47 | 0.00/0.00 | OK |
| Thursday | Web Attack - Brute Force | 09:18:13–09:59:31 | 09:18–10:02 | 0.00/0.00 | OK |
| Thursday | Web Attack - Sql Injection | 10:40:00–10:42:05 | 10:38–10:44 | 0.00/0.00 | OK |
| Thursday | Web Attack - XSS | 10:15:03–10:35:05 | 10:13–10:37 | 0.00/0.00 | OK |
| Tuesday | FTP-Patator | 09:19:09–10:19:09 | 09:18–10:22 | 0.00/0.00 | OK |
| Tuesday | SSH-Patator | 14:09:00–15:11:00 | 13:58–15:02 | 0.00/9.00 | ALERTE >5 min |
| Wednesday | DoS GoldenEye | 11:10:10–11:19:47 | 11:08–11:25 | 0.00/0.00 | OK |
| Wednesday | DoS Hulk | 10:43:00–11:00:39 | 10:41–11:02 | 0.00/0.00 | OK |
| Wednesday | DoS Slowhttptest | 10:16:03–10:37:00 | 10:12–10:37 | 0.00/0.00 | OK |
| Wednesday | DoS slowloris | 09:48:00–10:10:04 | 09:45–10:12 | 0.00/0.00 | OK |
| Wednesday | Heartbleed | 15:14:05–15:32:23 | 15:10–15:34 | 0.00/0.00 | OK |

## Flux perdus en gap

- V2 : 277424 flux; V3 : 305881 flux.
- Répartition V3 par classe : BENIGN=137650; Bot=198; DDoS=38709; DoS GoldenEye=4117; DoS Hulk=77897; DoS Slowhttptest=994; DoS slowloris=1475; FTP-Patator=772; Heartbleed=3; Infiltration=1; PortScan=43060; SSH-Patator=569; Web Attack - Brute Force=237; Web Attack - Sql Injection=8; Web Attack - XSS=191.

| Jour | V2 en gap | V3 en gap |
|---|---:|---:|
| Friday | 114846 | 112605 |
| Monday | 8116 | 8116 |
| Thursday | 30992 | 31884 |
| Tuesday | 20361 | 16851 |
| Wednesday | 103109 | 136425 |

Les prédictions, modèles, labels v2 et artefacts V2 ne sont pas modifiés; aucun entraînement n’est réalisé.
