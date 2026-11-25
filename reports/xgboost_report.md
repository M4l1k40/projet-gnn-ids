# Évaluation XGBoost binaire — CIC-IDS2017

- Seuil OOF FPR 1 % : `0.478321` ; FPR OOF observée : 0.9631%.
- Hyperparamètres : essai 24, 199 rounds, 10 graines (42, 43, 44, 45, 46, 47, 48, 49, 50, 51).
- Les métriques sont calculées sur les scores de chaque graine; les agrégats donnent moyenne ± écart-type (échantillon) / médiane.

## Métriques globales

Chaque cellule numérique indique moyenne ± écart-type / médiane.

| Évaluation | Flux | PR-AUC | ROC-AUC | MCC | F1 | Précision | Recall | FPR au seuil OOF | TPR au seuil OOF | TPR à FPR ≤ 1 % | FP / bénins |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| test complet | 882,784 | 0.9920 ± 0.0004 / 0.9921 | 0.9987 ± 0.0002 / 0.9988 | 0.9770 ± 0.0125 / 0.9848 | 0.9783 ± 0.0119 / 0.9857 | 0.9744 ± 0.0233 / 0.9894 | 0.9825 ± 0.0006 / 0.9824 | 0.0017 ± 0.0015 / 0.0007 | 0.9825 ± 0.0006 / 0.9824 | 0.9875 ± 0.0001 / 0.9875 | 1377.4 ± 1283.7 / 550.0 / 830,584 (0.001658 ± 0.001546 / 0.000662) |
| test strict | 682,136 | 0.9837 ± 0.0006 / 0.9838 | 0.9979 ± 0.0002 / 0.9980 | 0.9602 ± 0.0214 / 0.9737 | 0.9617 ± 0.0208 / 0.9748 | 0.9559 ± 0.0403 / 0.9820 | 0.9684 ± 0.0010 / 0.9682 | 0.0021 ± 0.0020 / 0.0008 | 0.9684 ± 0.0010 / 0.9682 | 0.9769 ± 0.0002 / 0.9770 | 1341.3 ± 1283.3 / 513.5 / 653,197 (0.002053 ± 0.001965 / 0.000786) |
| test sans signalés | 828,488 | 0.9990 ± 0.0000 / 0.9990 | 0.9998 ± 0.0000 / 0.9998 | 0.9902 ± 0.0002 / 0.9902 | 0.9906 ± 0.0002 / 0.9906 | 0.9869 ± 0.0003 / 0.9870 | 0.9944 ± 0.0007 / 0.9942 | 0.0007 ± 0.0000 / 0.0006 | 0.9944 ± 0.0007 / 0.9942 | 0.9991 ± 0.0000 / 0.9991 | 514.2 ± 13.1 / 512.0 / 789,455 (0.000651 ± 0.000017 / 0.000649) |
| test complet sans Bot | 882,308 | 0.9976 ± 0.0001 / 0.9976 | 0.9996 ± 0.0000 / 0.9996 | 0.9818 ± 0.0126 / 0.9897 | 0.9827 ± 0.0120 / 0.9903 | 0.9744 ± 0.0233 / 0.9894 | 0.9915 ± 0.0006 / 0.9914 | 0.0017 ± 0.0015 / 0.0007 | 0.9915 ± 0.0006 / 0.9914 | 0.9965 ± 0.0001 / 0.9965 | 1377.4 ± 1283.7 / 550.0 / 830,584 (0.001658 ± 0.001546 / 0.000662) |

La colonne TPR à FPR ≤ 1 % utilise le point ROC atteignable de TPR maximal dont le FPR ne dépasse pas 1 %.

## Test complet par graine

| Graine/statistique | TP | FP | FN | FPR | Recall | PR-AUC | F1 | TPR à FPR ≤ 1 % |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 42 | 51,251 | 535 | 949 | 0.000644 | 0.981820 | 0.992238 | 0.985729 | 0.987452 |
| 43 | 51,280 | 2,905 | 920 | 0.003498 | 0.982375 | 0.991626 | 0.964046 | 0.987490 |
| 44 | 51,264 | 532 | 936 | 0.000641 | 0.982069 | 0.992087 | 0.985884 | 0.987567 |
| 45 | 51,260 | 3,527 | 940 | 0.004246 | 0.981992 | 0.992378 | 0.958247 | 0.987490 |
| 46 | 51,282 | 546 | 918 | 0.000657 | 0.982414 | 0.991916 | 0.985927 | 0.987356 |
| 47 | 51,301 | 542 | 899 | 0.000653 | 0.982778 | 0.992099 | 0.986150 | 0.987356 |
| 48 | 51,265 | 550 | 935 | 0.000662 | 0.982088 | 0.992127 | 0.985723 | 0.987452 |
| 49 | 51,302 | 550 | 898 | 0.000662 | 0.982797 | 0.992388 | 0.986084 | 0.987375 |
| 50 | 51,310 | 3,228 | 890 | 0.003886 | 0.982950 | 0.991174 | 0.961420 | 0.987471 |
| 51 | 51,350 | 859 | 850 | 0.001034 | 0.983716 | 0.992349 | 0.983632 | 0.987490 |
| Moyenne | 51286.5 | 1377.4 | 913.5 | 0.001658 | 0.982500 | 0.992038 | 0.978284 | 0.987450 |
| Médiane | 51281.0 | 550.0 | 919.0 | 0.000662 | 0.982395 | 0.992113 | 0.985726 | 0.987462 |

### Faux positifs et chevauchement entre graines

Un FP est défini strictement par `y_pred == 1` et `label_bin == 0`. FP communs aux dix graines : 474.

| Graine | FP total | FP signalés par l'audit | FP non signalés |
|---:|---:|---:|---:|
| 42 | 535 | 40 | 495 |
| 43 | 2,905 | 2,394 | 511 |
| 44 | 532 | 26 | 506 |
| 45 | 3,527 | 3,016 | 511 |
| 46 | 546 | 30 | 516 |
| 47 | 542 | 29 | 513 |
| 48 | 550 | 44 | 506 |
| 49 | 550 | 28 | 522 |
| 50 | 3,228 | 2,711 | 517 |
| 51 | 859 | 314 | 545 |

#### FP propres aux graines 43, 45 et 50

L'union des FP de 43/45/50, après retrait de tout FP des sept autres graines, contient 2,725 flux. label_multi : BENIGN 2,725; label_bin=0 : 2,725.

| Graine | Score min | Médiane | Max | Part dans [0,40; 0,55] |
|---:|---:|---:|---:|---:|
| 43 | 0.282431 | 0.544801 | 0.699102 | 49.32% |
| 45 | 0.250815 | 0.614765 | 0.708362 | 17.72% |
| 50 | 0.309835 | 0.543100 | 0.690707 | 55.78% |

2,719/2,725 sont du mercredi; parmi eux, `src_port=80` : 2,718 (99.96%), `dst_port=80` : 0 (0.00%).
Plage mercredi (UTC) : 2017-07-05 10:44:08 à 2017-07-05 14:13:00; heures principales : 2017-07-05 10 (2,676), 2017-07-05 11 (42), 2017-07-05 14 (1).
Top IP source mercredi : 192.168.10.50 (2,718), 194.126.157.22 (1).
Protocol standardisé mercredi : -0.7524038553237915 (2,719); top dst_port : 57838 (4), 33194 (3), 53666 (3), 39430 (3), 47020 (3).
Top IP destination mercredi : 172.16.0.1 (2,718), 192.168.10.17 (1).
Vecteurs distincts parmi ces FP : 2,725/2,725; `seen_in_train=False` : 2,725; règle canonique : DoS Hulk (2,718), BENIGN (7).
Comparaison TP DoS Hulk graine 42 : 13,968 TP, 13,968 le mercredi; `dst_port=80` pour 13,968. Adresse source/destination inversée observée : 2,718 FP 192.168.10.50→172.16.0.1 contre 13,968 TP 172.16.0.1→192.168.10.50.

## Analyse de sensibilité — Bot exclu

Ces résultats complémentaires ne remplacent pas le test principal complet.

| Sous-ensemble | Flux | TP moyen | Recall moyen ± écart-type | Recall médian |
|---|---:|---:|---:|---:|
| Test complet sans Bot | 882,308 | — | 0.9915 ± 0.0006 / 0.9914 | — |
| Attaques hors Bot seulement | 51,724 | 51286.5 | 0.9915 ± 0.0006 | 0.991435 |


## Métriques hors-pli recalculées

| Pli | Effectif | Attaques | Taux d'attaque | PR-AUC | FPR au seuil OOF | TPR au seuil OOF | TPR max à FPR ≤ 1 % | best_iteration | Fit (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 303,157 | 66,876 | 22.0599% | 0.925473 | 1.2434% | 70.2689% | 69.6453% | 2 | 33.96 |
| 1 | 303,155 | 66,875 | 22.0597% | 0.998219 | 0.0533% | 72.4680% | 99.9163% | 198 | 95.20 |
| 2 | 303,151 | 66,872 | 22.0590% | 0.998176 | 0.0482% | 80.5973% | 99.6082% | 287 | 123.56 |
| 3 | 303,148 | 66,869 | 22.0582% | 0.958840 | 3.3833% | 88.6106% | 68.4054% | 1 | 32.56 |
| 4 | 303,144 | 66,865 | 22.0572% | 0.965966 | 0.0872% | 90.3372% | 90.5720% | 64 | 53.53 |

## Recall par classe d'attaque

| Classe | Flux test complet | Recall complet | Flux test strict | Recall strict | Flux sans signalés | Recall sans signalés | Avertissement |
|---|---:|---:|---:|---:|---:|---:|---|
| DDoS | 12501 | 0.9963 ± 0.0001 | 12493 | 0.9963 ± 0.0001 | 12501 | 0.9963 ± 0.0001 |  |
| DoS Hulk | 14152 | 0.9877 ± 0.0006 | 11627 | 0.9850 ± 0.0007 | 4100 | 1.0000 ± 0.0000 |  |
| DoS Slowhttptest | 1205 | 0.9011 ± 0.0206 | 1205 | 0.9011 ± 0.0206 | 399 | 0.7038 ± 0.0621 |  |
| DoS slowloris | 714 | 0.9818 ± 0.0000 | 714 | 0.9818 ± 0.0000 | 558 | 0.9946 ± 0.0000 |  |
| FTP-Patator | 1579 | 0.9962 ± 0.0000 | 1099 | 0.9945 ± 0.0000 | 806 | 1.0000 ± 0.0000 |  |
| Infiltration | 9 | 0.5222 ± 0.1741 | 9 | 0.5222 ± 0.1741 | 9 | 0.5222 ± 0.1741 | ⚠ < 100 en strict |
| PortScan | 20046 | 0.9988 ± 0.0006 | 347 | 0.9311 ± 0.0355 | 20046 | 0.9988 ± 0.0006 |  |
| SSH-Patator | 1192 | 0.9661 ± 0.0013 | 651 | 0.9379 ± 0.0024 | 599 | 0.9619 ± 0.0007 |  |
| Web Attack - Brute Force | 260 | 0.9946 ± 0.0041 | 252 | 0.9944 ± 0.0043 | 13 | 1.0000 ± 0.0000 |  |
| Web Attack - XSS | 66 | 0.8773 ± 0.0167 | 66 | 0.8773 ± 0.0167 | 2 | 0.6500 ± 0.2415 | ⚠ < 100 en strict |

## Bot — diagnostic séparé

- Support Bot : 474/476 Attempted.
- Le recall Bot est séparé des autres classes; le modèle demeure un classifieur binaire.

| Groupe Bot | Flux | Score médian graine 42 | Recall graine 42 | Recall moyen ± écart-type / médiane |
|---|---:|---:|---:|---:|
| Attempted | 474 | 0.00071833 | 0.0000 | 0.0000 ± 0.0000 / 0.0000 |
| non-Attempted | 2 | 0.00067521 | 0.0000 | 0.0000 ± 0.0000 / 0.0000 |

Bot par bloc et part Attempted :

| Bloc | Bot | Attempted | Part Attempted |
|---|---:|---:|---:|
| train | 1,174 | 0 | 0.00% |
| val | 108 | 3 | 2.78% |
| test | 476 | 474 | 99.58% |

## Matrice de confusion — graine 42, test complet

| Réel \ Prédit | Bénin | Attaque |
|---|---:|---:|
| Bénin | 830049 | 535 |
| Attaque | 949 | 51251 |

## Temps

- Entraînement par graine : 94.5761 ± 1.5705 s.
- Inférence sur le test par graine : 2.7328 ± 0.1618 s.
- Le temps d'inférence mesure l'appel predict; il exclut la lecture Parquet et le chargement du modèle.

## Importance des features (gain)

Le CSV contient le gain par feature et par graine; le tableau ci-dessous classe la part moyenne du gain normalisée par modèle.

| Rang | Feature | Gain moyen | Part moyenne du gain |
|---:|---|---:|---:|
| 1 | Bwd Packet Length Min | 28746.6 | 36.7475% |
| 2 | Fwd Packet Length Min | 14866.3 | 18.7437% |
| 3 | Average Packet Size | 6285.23 | 8.0200% |
| 4 | Bwd Packet Length Std | 3971.84 | 5.0690% |
| 5 | Packet Length Variance | 2329.07 | 2.9369% |
| 6 | Bwd Header Length | 2207.52 | 2.8136% |
| 7 | Packet Length Std | 2057.37 | 2.6285% |
| 8 | Init_Win_bytes_backward | 1846.85 | 2.3615% |
| 9 | Fwd Packet Length Max | 1464.59 | 1.8722% |
| 10 | Protocol | 1470.34 | 1.8672% |
| 11 | Min Packet Length | 1096.41 | 1.3953% |
| 12 | Fwd Header Length | 1048.17 | 1.3359% |
| 13 | Max Packet Length | 1016.54 | 1.2978% |
| 14 | Fwd Packet Length Std | 774.141 | 0.9772% |
| 15 | URG Flag Count | 704.417 | 0.8886% |

Features à risque de raccourci (rang/part moyenne) :
- Fwd Header Length : rang 12, 1.3359% du gain moyen.
- Total Fwd Packets : rang 58, 0.0778% du gain moyen.
- min_seg_size_forward : rang 16, 0.8732% du gain moyen.
- Init_Win_bytes_forward : rang 17, 0.7556% du gain moyen.
- Aucune des quatre features ne figure dans les cinq premières.

## Audit des labels dans le test

- BENIGN avec règle d'attaque : 41,129.
- Attaque avec règle BENIGN : 8.
- Attaque avec autre règle d'attaque : 20.
- `attempted_category >= 0` : 16,451.
- Les flux signalés sont exclus uniquement de l'analyse complémentaire; ils restent dans le test complet et le test strict.

### Sensibilité aux labels de l'audit

Analyse secondaire; les résultats principaux restent évalués sur `label_bin` d'origine. « Attempted compté » définit l'attaque par règle canonique non-BENIGN OU Attempted. « Attempted exclu » retire les lignes Attempted avant calcul et utilise règle canonique non-BENIGN comme vérité.

| Variante | Graine | n | PR-AUC | TPR à FPR ≤ 1 % | FP au seuil | FN au seuil |
|---|---:|---:|---:|---:|---:|---:|
| Attempted compté comme attaque | 42 | 882,784 | 0.771115 | 0.604633 | 496 | 42,031 |
| Attempted compté comme attaque | 43 | 882,784 | 0.776442 | 0.606144 | 512 | 39,648 |
| Attempted compté comme attaque | 44 | 882,784 | 0.781967 | 0.604087 | 507 | 42,032 |
| Attempted compté comme attaque | 45 | 882,784 | 0.780345 | 0.603519 | 512 | 39,046 |
| Attempted compté comme attaque | 46 | 882,784 | 0.776518 | 0.604098 | 517 | 42,010 |
| Attempted compté comme attaque | 47 | 882,784 | 0.779213 | 0.604001 | 514 | 41,992 |
| Attempted compté comme attaque | 48 | 882,784 | 0.769705 | 0.603615 | 507 | 42,013 |
| Attempted compté comme attaque | 49 | 882,784 | 0.773935 | 0.604483 | 523 | 41,992 |
| Attempted compté comme attaque | 50 | 882,784 | 0.783466 | 0.606112 | 518 | 39,301 |
| Attempted compté comme attaque | 51 | 882,784 | 0.777601 | 0.603530 | 546 | 41,658 |
| Attempted exclu | 42 | 866,333 | 0.715578 | 0.560479 | 496 | 38,060 |
| Attempted exclu | 43 | 866,333 | 0.722678 | 0.561129 | 512 | 35,685 |
| Attempted exclu | 44 | 866,333 | 0.729269 | 0.560271 | 507 | 38,065 |
| Attempted exclu | 45 | 866,333 | 0.727650 | 0.559906 | 512 | 35,077 |
| Attempted exclu | 46 | 866,333 | 0.723123 | 0.559984 | 517 | 38,052 |
| Attempted exclu | 47 | 866,333 | 0.727113 | 0.560323 | 514 | 38,037 |
| Attempted exclu | 48 | 866,333 | 0.715352 | 0.559490 | 507 | 38,053 |
| Attempted exclu | 49 | 866,333 | 0.720253 | 0.560674 | 523 | 38,034 |
| Attempted exclu | 50 | 866,333 | 0.732349 | 0.561077 | 518 | 35,356 |
| Attempted exclu | 51 | 866,333 | 0.723920 | 0.560075 | 546 | 37,691 |
| Attempted compté comme attaque — moyenne | — | 882,784 | 0.777031 | 0.604422 | 515.2 | 41172.3 |
| Attempted compté comme attaque — médiane | — | 882,784 | 0.777059 | 0.604092 | 513.0 | 41992.0 |
| Attempted exclu — moyenne | — | 866,333 | 0.723729 | 0.560341 | 515.2 | 37211.0 |
| Attempted exclu — médiane | — | 866,333 | 0.723522 | 0.560297 | 513.0 | 38035.5 |

### Part Attempted par classe d'attaque et bloc

| Bloc | Classe | Effectif | Attempted | Part Attempted |
|---|---|---:|---:|---:|
| train | Bot | 1,174 | 0 | 0.00% |
| train | DDoS | 76,815 | 0 | 0.00% |
| train | DoS GoldenEye | 6,176 | 1,725 | 27.93% |
| train | DoS Hulk | 138,074 | 38,303 | 27.74% |
| train | DoS Slowhttptest | 3,300 | 1,706 | 51.70% |
| train | DoS slowloris | 3,478 | 1,103 | 31.71% |
| train | FTP-Patator | 4,764 | 2,380 | 49.96% |
| train | Heartbleed | 7 | 0 | 0.00% |
| train | Infiltration | 22 | 1 | 4.55% |
| train | PortScan | 95,698 | 0 | 0.00% |
| train | SSH-Patator | 3,539 | 1,761 | 49.76% |
| train | Web Attack - Brute Force | 905 | 862 | 95.25% |
| train | Web Attack - Sql Injection | 13 | 0 | 0.00% |
| train | Web Attack - XSS | 392 | 383 | 97.70% |
| val | Bot | 108 | 3 | 2.78% |
| val | DoS slowloris | 129 | 84 | 65.12% |
| val | FTP-Patator | 820 | 429 | 52.32% |
| val | Heartbleed | 1 | 0 | 0.00% |
| val | Infiltration | 4 | 0 | 0.00% |
| val | SSH-Patator | 597 | 299 | 50.08% |
| val | Web Attack - Brute Force | 105 | 100 | 95.24% |
| val | Web Attack - XSS | 3 | 3 | 100.00% |
| test | Bot | 476 | 474 | 99.58% |
| test | DDoS | 12,501 | 0 | 0.00% |
| test | DoS Hulk | 14,152 | 10,052 | 71.03% |
| test | DoS Slowhttptest | 1,205 | 806 | 66.89% |
| test | DoS slowloris | 714 | 151 | 21.15% |
| test | FTP-Patator | 1,579 | 772 | 48.89% |
| test | Infiltration | 9 | 0 | 0.00% |
| test | PortScan | 20,046 | 0 | 0.00% |
| test | SSH-Patator | 1,192 | 593 | 49.75% |
| test | Web Attack - Brute Force | 260 | 247 | 95.00% |
| test | Web Attack - XSS | 66 | 63 | 95.45% |

## Limites

- Les plis train sont proches de l'interpolation : PR-AUC CV (prévalence 22.06%) n'est pas comparable directement à la PR-AUC test (prévalence 5.91%); le pli 0 s'arrête à `best_iteration=2`.
- Les cinq meilleurs essais sont difficilement distinguables : écart premier-cinquième 0.0038, contre un écart-type d'environ 0.0460.
- La recherche n'a porté que sur les plis 0–2; les plis 3–4 n'ont servi qu'au calcul OOF du seuil.
- Les plis sont non causaux, purgés à 3 minutes, et des vecteurs quasi identiques existent entre plis; une validation temporelle ne garantit pas la transférabilité à un trafic futur.
- CIC-IDS2017 est une capture de laboratoire; les labels/règles comportent des divergences mesurées ci-dessus. Les résultats ne prouvent pas les performances en production.
- Les cibles évaluées sont les labels finaux `label_bin` / `label_multi` des Parquet; l'audit compare les règles normalisées de `label_audit.parquet` à ces labels.
- Le seuil fixe est instable entre graines : les faux positifs vont de 532 à 3,527; ne pas interpréter la seule moyenne sans cette dispersion.
- Bot n'est pas mesurable par ce modèle binaire : part Attempted 0.0% en train contre 99.6% en test (474/476); recall observé nul.
- FP propres aux graines 43/45/50 : 2,725 flux au sens strict y_pred=1 et label_bin=0, dont 2,718 avec règle Hulk et 2,719 le mercredi; scores des graines instables concentrés près/au-dessus du seuil fixe.
- Les deux features de longueur minimale (Bwd Packet Length Min et Fwd Packet Length Min) représentent ensemble 55.49% du gain normalisé moyen.
- Les classes à moins de 100 flux en test strict sont Infiltration (9), Web Attack - XSS (66).

CSV des métriques par graine et scénario : `D:\AI\projet-gnn-ids\reports\xgboost_report.csv`.
CSV complet des importances par graine : `D:\AI\projet-gnn-ids\reports\xgboost_feature_importance.csv`.
