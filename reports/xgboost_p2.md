# Évaluation XGBoost binaire — généralisation P2 / E5

- Labels d’origine `label_bin`; paramètres de l’essai 24 conservés, 199 rounds fixes, sans early stopping ni nouvelle recherche.
- Un modèle, graine 42, par pli; `scale_pos_weight` recalculé sur le train de ce pli; 69 features.
- Le seuil de chaque pli est choisi sur les scores de validation BENIGN pour atteindre un FPR ≤ 1 %.
- Les données test ne sont chargées qu’après la fin des entraînements des neuf plis.
- Les vues v2 comptent `label_v2_bin == 1 OR attempted == True` comme positif.

## Résultats par pli et vérité

| Pli | Vérité | Train | Val | Test | Prévalence | Classes test (présentes dans train) | ROC-AUC | PR-AUC | TPR@FPR≤0,1 % | TPR@FPR≤1 % | Seuil val | TPR/FPR au seuil | FP/FN au seuil |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| day_Tuesday | labels origine | 2,274,705 | 61,770 | 445,641 | 3.1038% | BENIGN (train), FTP-Patator (zéro-shot), SSH-Patator (zéro-shot) | 0.88034 | 0.19992 | 0.0012 | 0.1957 | 0.0060776547 | 0.2770/0.0190 | 8,204/10,001 |
| day_Tuesday | v2 Attempted comptés | 2,274,705 | 61,770 | 445,641 | 3.4627% | BENIGN (train), FTP-Patator (zéro-shot), SSH-Patator (zéro-shot) | 0.88432 | 0.20436 | 0.0010 | 0.1778 | 0.0060776547 | 0.2507/0.0190 | 8,167/11,563 |
| day_Wednesday | labels origine | 2,017,856 | 72,487 | 691,379 | 36.4071% | BENIGN (train), DoS GoldenEye (zéro-shot), DoS Hulk (zéro-shot), DoS Slowhttptest (zéro-shot), DoS slowloris (zéro-shot) | 0.97380 | 0.94017 | 0.0707 | 0.4319 | 0.0047802716 | 0.4356/0.0103 | 4,544/142,068 |
| day_Wednesday | v2 Attempted comptés | 2,017,856 | 72,487 | 691,379 | 37.3877% | BENIGN (train), DoS GoldenEye (zéro-shot), DoS Hulk (zéro-shot), DoS Slowhttptest (zéro-shot), DoS slowloris (zéro-shot) | 0.97617 | 0.94797 | 0.0930 | 0.4599 | 0.0047802716 | 0.4278/0.0083 | 3,596/147,900 |
| day_Thursday | labels origine | 2,279,506 | 51,947 | 458,447 | 0.4755% | BENIGN (train), Web Attack - Brute Force (zéro-shot), Web Attack - Sql Injection (zéro-shot), Web Attack - XSS (zéro-shot) | 0.88482 | 0.01925 | 0.0000 | 0.0000 | 0.0065155691 | 0.9161/0.1471 | 67,125/183 |
| day_Thursday | v2 Attempted comptés | 2,279,506 | 51,947 | 458,447 | 15.1645% | BENIGN (train), Web Attack - Brute Force (zéro-shot), Web Attack - Sql Injection (zéro-shot), Web Attack - XSS (zéro-shot) | 0.99546 | 0.98216 | 0.9329 | 0.9475 | 0.0065155691 | 0.9463/0.0086 | 3,334/3,733 |
| day_Friday | labels origine | 2,036,860 | 40,545 | 702,713 | 41.0957% | BENIGN (train), Bot (zéro-shot), DDoS (zéro-shot), PortScan (zéro-shot) | 0.80540 | 0.75307 | 0.2824 | 0.2848 | 0.0030422504 | 0.2850/0.0203 | 8,404/206,469 |
| day_Friday | v2 Attempted comptés | 2,036,860 | 40,545 | 702,713 | 45.6948% | BENIGN (train), Bot (zéro-shot), DDoS (zéro-shot), PortScan (zéro-shot) | 0.84028 | 0.81551 | 0.2535 | 0.2665 | 0.0030422504 | 0.2666/0.0134 | 5,114/235,497 |
| family_bruteforce | labels origine | 2,682,068 | 74,166 | 13,832 | 100.0000% | FTP-Patator (zéro-shot), SSH-Patator (zéro-shot) | nan | 1.00000 | nan | nan | 0.0053293505 | 0.3244/nan | 0/9,345 |
| family_bruteforce | v2 Attempted comptés | 2,682,068 | 74,166 | 13,832 | 99.9928% | FTP-Patator (zéro-shot), SSH-Patator (zéro-shot) | 0.00000 | 0.99944 | 0.0000 | 0.0000 | 0.0053293505 | 0.3243/1.0000 | 1/9,345 |
| family_dos | labels origine | 2,315,027 | 75,454 | 379,736 | 100.0000% | DDoS (zéro-shot), DoS GoldenEye (zéro-shot), DoS Hulk (zéro-shot), DoS Slowhttptest (zéro-shot), DoS slowloris (zéro-shot) | nan | 1.00000 | nan | nan | 0.0032004716 | 0.3386/nan | 0/251,169 |
| family_dos | v2 Attempted comptés | 2,315,027 | 75,454 | 379,736 | 99.9984% | DDoS (zéro-shot), DoS GoldenEye (zéro-shot), DoS Hulk (zéro-shot), DoS Slowhttptest (zéro-shot), DoS slowloris (zéro-shot) | 0.59749 | 0.99997 | 0.0000 | 0.0000 | 0.0032004716 | 0.3386/0.1667 | 1/251,164 |
| family_web | labels origine | 2,691,513 | 75,475 | 2,180 | 100.0000% | Web Attack - Brute Force (zéro-shot), Web Attack - Sql Injection (zéro-shot), Web Attack - XSS (zéro-shot) | nan | 1.00000 | nan | nan | 0.0048908214 | 0.9170/nan | 0/181 |
| family_web | v2 Attempted comptés | 2,691,513 | 75,475 | 2,180 | 100.0000% | Web Attack - Brute Force (zéro-shot), Web Attack - Sql Injection (zéro-shot), Web Attack - XSS (zéro-shot) | nan | 1.00000 | nan | nan | 0.0048908214 | 0.9170/nan | 0/181 |
| family_recon | labels origine | 2,534,355 | 75,583 | 158,804 | 100.0000% | PortScan (zéro-shot) | nan | 1.00000 | nan | nan | 0.005824381 | 0.0063/nan | 0/157,811 |
| family_recon | v2 Attempted comptés | 2,534,355 | 75,583 | 158,804 | 99.9912% | PortScan (zéro-shot) | 0.03816 | 0.99953 | 0.0002 | 0.0002 | 0.005824381 | 0.0062/0.8571 | 12/157,809 |
| family_bot | labels origine | 2,691,509 | 75,475 | 1,956 | 100.0000% | Bot (zéro-shot) | nan | 1.00000 | nan | nan | 0.0043788678 | 0.0046/nan | 0/1,947 |
| family_bot | v2 Attempted comptés | 2,691,509 | 75,475 | 1,956 | 99.7955% | Bot (zéro-shot) | 0.85284 | 0.99967 | 0.7710 | 0.7710 | 0.0043788678 | 0.0046/0.0000 | 0/1,943 |

Les PR-AUC sont des average precision et doivent être lues avec la prévalence affichée.
Avec les labels d’origine, les plis famille ne contiennent aucun BENIGN en test : ROC-AUC et points TPR@FPR ne sont pas définis; la PR-AUC de 1,0 est dégénérée (prévalence 100 %) et n’indique pas de séparation. Dans certaines vues v2, quelques négatifs subsistent (prévalence légèrement inférieure à 100 % dans le tableau); les métriques ROC et TPR@FPR correspondantes reposent alors sur très peu de négatifs et sont instables.

## Recall par classe d’origine

Le BENIGN est présenté en spécificité; les classes d’attaque sont présentées en recall avec support.

| Pli | Vérité | Classe d’origine | Effectif positif | Présente dans train | Mesure |
|---|---|---|---:|---|---:|
| day_Tuesday | labels origine | BENIGN | 431,809 | oui | specificity 0.9810 |
| day_Tuesday | labels origine | FTP-Patator | 7,935 | non | recall 0.1306 |
| day_Tuesday | labels origine | SSH-Patator | 5,897 | non | recall 0.4740 |
| day_Tuesday | v2 Attempted comptés | BENIGN | 430,209 | oui | specificity 0.9810 |
| day_Tuesday | v2 Attempted comptés | FTP-Patator | 7,934 | non | recall 0.1305 |
| day_Tuesday | v2 Attempted comptés | SSH-Patator | 5,897 | non | recall 0.4740 |
| day_Wednesday | labels origine | BENIGN | 439,668 | oui | specificity 0.9897 |
| day_Wednesday | labels origine | DoS GoldenEye | 10,293 | non | recall 0.6389 |
| day_Wednesday | labels origine | DoS Hulk | 230,123 | non | recall 0.4329 |
| day_Wednesday | labels origine | DoS Slowhttptest | 5,499 | non | recall 0.2253 |
| day_Wednesday | labels origine | DoS slowloris | 5,796 | non | recall 0.3825 |
| day_Wednesday | v2 Attempted comptés | BENIGN | 432,882 | oui | specificity 0.9897 |
| day_Wednesday | v2 Attempted comptés | DoS GoldenEye | 10,293 | non | recall 0.6389 |
| day_Wednesday | v2 Attempted comptés | DoS Hulk | 230,123 | non | recall 0.4329 |
| day_Wednesday | v2 Attempted comptés | DoS Slowhttptest | 5,499 | non | recall 0.2253 |
| day_Wednesday | v2 Attempted comptés | DoS slowloris | 5,790 | non | recall 0.3826 |
| day_Thursday | labels origine | BENIGN | 456,267 | oui | specificity 0.8529 |
| day_Thursday | labels origine | Web Attack - Brute Force | 1,507 | non | recall 0.9044 |
| day_Thursday | labels origine | Web Attack - Sql Injection | 21 | non | recall 0.9524 |
| day_Thursday | labels origine | Web Attack - XSS | 652 | non | recall 0.9417 |
| day_Thursday | v2 Attempted comptés | BENIGN | 388,926 | oui | specificity 0.8529 |
| day_Thursday | v2 Attempted comptés | Web Attack - Brute Force | 1,507 | non | recall 0.9044 |
| day_Thursday | v2 Attempted comptés | Web Attack - Sql Injection | 21 | non | recall 0.9524 |
| day_Thursday | v2 Attempted comptés | Web Attack - XSS | 652 | non | recall 0.9417 |
| day_Friday | labels origine | BENIGN | 413,928 | oui | specificity 0.9797 |
| day_Friday | labels origine | Bot | 1,956 | non | recall 0.0000 |
| day_Friday | labels origine | DDoS | 128,025 | non | recall 0.6357 |
| day_Friday | labels origine | PortScan | 158,804 | non | recall 0.0058 |
| day_Friday | v2 Attempted comptés | BENIGN | 381,592 | oui | specificity 0.9797 |
| day_Friday | v2 Attempted comptés | Bot | 1,952 | non | recall 0.0000 |
| day_Friday | v2 Attempted comptés | DDoS | 128,025 | non | recall 0.6357 |
| day_Friday | v2 Attempted comptés | PortScan | 158,790 | non | recall 0.0057 |
| family_bruteforce | labels origine | FTP-Patator | 7,935 | non | recall 0.2205 |
| family_bruteforce | labels origine | SSH-Patator | 5,897 | non | recall 0.4641 |
| family_bruteforce | v2 Attempted comptés | FTP-Patator | 7,934 | non | recall 0.2204 |
| family_bruteforce | v2 Attempted comptés | SSH-Patator | 5,897 | non | recall 0.4641 |
| family_dos | labels origine | DDoS | 128,025 | non | recall 0.4814 |
| family_dos | labels origine | DoS GoldenEye | 10,293 | non | recall 0.5403 |
| family_dos | labels origine | DoS Hulk | 230,123 | non | recall 0.2551 |
| family_dos | labels origine | DoS Slowhttptest | 5,499 | non | recall 0.0946 |
| family_dos | labels origine | DoS slowloris | 5,796 | non | recall 0.3689 |
| family_dos | v2 Attempted comptés | DDoS | 128,025 | non | recall 0.4814 |
| family_dos | v2 Attempted comptés | DoS GoldenEye | 10,293 | non | recall 0.5403 |
| family_dos | v2 Attempted comptés | DoS Hulk | 230,123 | non | recall 0.2551 |
| family_dos | v2 Attempted comptés | DoS Slowhttptest | 5,499 | non | recall 0.0946 |
| family_dos | v2 Attempted comptés | DoS slowloris | 5,790 | non | recall 0.3691 |
| family_web | labels origine | Web Attack - Brute Force | 1,507 | non | recall 0.9038 |
| family_web | labels origine | Web Attack - Sql Injection | 21 | non | recall 1.0000 |
| family_web | labels origine | Web Attack - XSS | 652 | non | recall 0.9448 |
| family_web | v2 Attempted comptés | Web Attack - Brute Force | 1,507 | non | recall 0.9038 |
| family_web | v2 Attempted comptés | Web Attack - Sql Injection | 21 | non | recall 1.0000 |
| family_web | v2 Attempted comptés | Web Attack - XSS | 652 | non | recall 0.9448 |
| family_recon | labels origine | PortScan | 158,804 | non | recall 0.0063 |
| family_recon | v2 Attempted comptés | PortScan | 158,790 | non | recall 0.0062 |
| family_bot | labels origine | Bot | 1,956 | non | recall 0.0046 |
| family_bot | v2 Attempted comptés | Bot | 1,952 | non | recall 0.0046 |

## Diagnostic zéro-shot P2 contre V3 b0 en distribution

La ligne P2 compare le recall au seuil calibré sur val et au point de la courbe du test dont le FPR est ≤ 1 %. La référence V3 b0 utilise son seuil OOF et son propre point de courbe test. Ces comparaisons sont diagnostiques, avec des splits et supports différents.

| Pli P2 | Classe absente du train | Support P2 | Recall P2 au seuil val | Recall P2 à FPR test≤1 % | Support V3 | Recall V3 au seuil OOF | Recall V3 à FPR test≤1 % |
|---|---|---:|---:|---:|---:|---:|---:|
| day_Tuesday | FTP-Patator | 7,935 | 0.1306 | 0.0050 | 1,579 | 0.9962 | 0.9962 |
| day_Tuesday | SSH-Patator | 5,897 | 0.4740 | 0.4523 | 1,192 | 0.9891 | 0.9975 |
| day_Wednesday | DoS GoldenEye | 10,293 | 0.6389 | 0.6347 | 0 | nan | nan |
| day_Wednesday | DoS Hulk | 230,123 | 0.4329 | 0.4293 | 14,152 | 0.9911 | 0.9947 |
| day_Wednesday | DoS Slowhttptest | 5,499 | 0.2253 | 0.2164 | 1,205 | 0.9975 | 0.9983 |
| day_Wednesday | DoS slowloris | 5,796 | 0.3825 | 0.3818 | 714 | 0.9902 | 0.9916 |
| day_Thursday | Web Attack - Brute Force | 1,507 | 0.9044 | 0.0000 | 260 | 1.0000 | 1.0000 |
| day_Thursday | Web Attack - Sql Injection | 21 | 0.9524 | 0.0000 | 0 | nan | nan |
| day_Thursday | Web Attack - XSS | 652 | 0.9417 | 0.0000 | 66 | 0.9697 | 0.9697 |
| day_Friday | Bot | 1,956 | 0.0000 | 0.0000 | 476 | 0.0000 | 0.0000 |
| day_Friday | DDoS | 128,025 | 0.6357 | 0.6355 | 12,501 | 0.9978 | 0.9978 |
| day_Friday | PortScan | 158,804 | 0.0058 | 0.0057 | 20,046 | 0.9997 | 0.9999 |
| family_bruteforce | FTP-Patator | 7,935 | 0.2205 | nan | 1,579 | 0.9962 | 0.9962 |
| family_bruteforce | SSH-Patator | 5,897 | 0.4641 | nan | 1,192 | 0.9891 | 0.9975 |
| family_dos | DDoS | 128,025 | 0.4814 | nan | 12,501 | 0.9978 | 0.9978 |
| family_dos | DoS GoldenEye | 10,293 | 0.5403 | nan | 0 | nan | nan |
| family_dos | DoS Hulk | 230,123 | 0.2551 | nan | 14,152 | 0.9911 | 0.9947 |
| family_dos | DoS Slowhttptest | 5,499 | 0.0946 | nan | 1,205 | 0.9975 | 0.9983 |
| family_dos | DoS slowloris | 5,796 | 0.3689 | nan | 714 | 0.9902 | 0.9916 |
| family_web | Web Attack - Brute Force | 1,507 | 0.9038 | nan | 260 | 1.0000 | 1.0000 |
| family_web | Web Attack - Sql Injection | 21 | 1.0000 | nan | 0 | nan | nan |
| family_web | Web Attack - XSS | 652 | 0.9448 | nan | 66 | 0.9697 | 0.9697 |
| family_recon | PortScan | 158,804 | 0.0063 | nan | 20,046 | 0.9997 | 0.9999 |
| family_bot | Bot | 1,956 | 0.0046 | nan | 476 | 0.0000 | 0.0000 |

## Seuils et temps

| Pli | Seuil val | FPR val BENIGN atteint | Fit (s) | Inférence (s) |
|---|---:|---:|---:|---:|
| day_Tuesday | 0.0060776547 | 0.9996% | 163.9 | 2.172 |
| day_Wednesday | 0.0047802716 | 0.9992% | 163.6 | 2.333 |
| day_Thursday | 0.0065155691 | 0.9962% | 264.8 | 2.196 |
| day_Friday | 0.0030422504 | 0.9977% | 166.1 | 3.396 |
| family_bruteforce | 0.0053293505 | 0.9997% | 219.3 | 0.121 |
| family_dos | 0.0032004716 | 0.9970% | 166.1 | 1.473 |
| family_web | 0.0048908214 | 0.9970% | 190.2 | 0.023 |
| family_recon | 0.005824381 | 0.9997% | 170.0 | 0.714 |
| family_bot | 0.0043788678 | 0.9997% | 195.2 | 0.010 |

## Limites

- Plusieurs classes d’attaque du test sont absentes du train : ces recalls mesurent une généralisation zéro-shot, pas une classification apprise de ces classes.
- Les hyperparamètres de l’essai 24 ont été choisis sur des plis V2 qui contenaient ces classes; le protocole P2 n’est donc pas une sélection entièrement indépendante.
- Une seule graine (42) a été exécutée; la dispersion entre graines n’est pas estimée.
- Le seuil est calibré sur val, et les TPR à FPR 0,1 %/1 % sont des points descriptifs de la courbe test, pas des seuils de déploiement.
- Heartbleed et Infiltration sont exclus des plis P2 faute d’effectif suffisant.
- Les règles v2 sont des heuristiques d’audit, pas une vérité terrain; la vue v2 est une analyse secondaire.

Métriques par pli : [xgboost_p2_metrics.csv](./xgboost_p2_metrics.csv).
Recall par classe : [xgboost_p2_class_recall.csv](./xgboost_p2_class_recall.csv).
Comparaison zéro-shot : [xgboost_p2_comparison.csv](./xgboost_p2_comparison.csv).
