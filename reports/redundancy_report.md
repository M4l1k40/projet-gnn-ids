# Redondance des vecteurs de features

Les vecteurs sont comparés après arrondi de chaque feature à 6 décimales, comme dans le diagnostic de fuite. Le même vecteur est défini par ses octets contigus et les zéros signés sont normalisés.

- `seen_in_train_any_label` : un vecteur identique existe dans train, quelle que soit sa classe.
- `conflict_in_train` : le vecteur existe dans train sous une classe différente.
- `train_dup_count` : nombre d’occurrences de ce vecteur dans le split train (0 si absent).

- Contrôle test/same-class : 200,648 flux (attendu : 200,648).

| Split | Classe | Flux | Vecteur présent train | % présent | Conflit de classe | % conflit | Même classe | Train occurrences cumulées | Lignes avec doublon train |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| test | BENIGN | 830584 | 177466 | 21.3664 % | 103 | 0.0124 % | 177387 | 44931391 | 139608 |
| test | Bot | 476 | 0 | 0.0000 % | 0 | 0.0000 % | 0 | 0 | 0 |
| test | DDoS | 12501 | 8 | 0.0640 % | 0 | 0.0000 % | 8 | 8 | 0 |
| test | DoS Hulk | 14152 | 2525 | 17.8420 % | 146 | 1.0317 % | 2525 | 5276190 | 2398 |
| test | DoS Slowhttptest | 1205 | 0 | 0.0000 % | 0 | 0.0000 % | 0 | 0 | 0 |
| test | DoS slowloris | 714 | 2 | 0.2801 % | 2 | 0.2801 % | 0 | 2 | 0 |
| test | FTP-Patator | 1579 | 480 | 30.3990 % | 0 | 0.0000 % | 480 | 62479 | 351 |
| test | Infiltration | 9 | 0 | 0.0000 % | 0 | 0.0000 % | 0 | 0 | 0 |
| test | PortScan | 20046 | 19699 | 98.2690 % | 19083 | 95.1960 % | 19699 | 28745207 | 19692 |
| test | SSH-Patator | 1192 | 541 | 45.3859 % | 0 | 0.0000 % | 541 | 14398 | 530 |
| test | Web Attack - Brute Force | 260 | 8 | 3.0769 % | 0 | 0.0000 % | 8 | 11 | 2 |
| test | Web Attack - XSS | 66 | 0 | 0.0000 % | 0 | 0.0000 % | 0 | 0 | 0 |
| train | BENIGN | 1181398 | 1181398 | 100.0000 % | 1072 | 0.0907 % | 1181398 | 40745988 | 248197 |
| train | Bot | 1174 | 1174 | 100.0000 % | 91 | 7.7513 % | 1174 | 4818 | 503 |
| train | DDoS | 76815 | 76815 | 100.0000 % | 1 | 0.0013 % | 76815 | 76850 | 32 |
| train | DoS GoldenEye | 6176 | 6176 | 100.0000 % | 0 | 0.0000 % | 6176 | 6316 | 122 |
| train | DoS Hulk | 138074 | 138074 | 100.0000 % | 2842 | 2.0583 % | 138074 | 94836201 | 34735 |
| train | DoS Slowhttptest | 3300 | 3300 | 100.0000 % | 1 | 0.0303 % | 3300 | 3801 | 143 |
| train | DoS slowloris | 3478 | 3478 | 100.0000 % | 1 | 0.0288 % | 3478 | 4607 | 348 |
| train | FTP-Patator | 4764 | 4764 | 100.0000 % | 0 | 0.0000 % | 4764 | 252014 | 1597 |
| train | Heartbleed | 7 | 7 | 100.0000 % | 0 | 0.0000 % | 7 | 7 | 0 |
| train | Infiltration | 22 | 22 | 100.0000 % | 0 | 0.0000 % | 22 | 22 | 0 |
| train | PortScan | 95698 | 95698 | 100.0000 % | 56232 | 58.7598 % | 95698 | 114955038 | 94757 |
| train | SSH-Patator | 3539 | 3539 | 100.0000 % | 0 | 0.0000 % | 3539 | 47625 | 1699 |
| train | Web Attack - Brute Force | 905 | 905 | 100.0000 % | 0 | 0.0000 % | 905 | 941 | 27 |
| train | Web Attack - Sql Injection | 13 | 13 | 100.0000 % | 0 | 0.0000 % | 13 | 13 | 0 |
| train | Web Attack - XSS | 392 | 392 | 100.0000 % | 0 | 0.0000 % | 392 | 392 | 0 |
| val | BENIGN | 149947 | 35082 | 23.3963 % | 17 | 0.0113 % | 35067 | 11760396 | 28555 |
| val | Bot | 108 | 38 | 35.1852 % | 7 | 6.4815 % | 38 | 298 | 38 |
| val | DoS slowloris | 129 | 21 | 16.2791 % | 0 | 0.0000 % | 21 | 83 | 16 |
| val | FTP-Patator | 820 | 282 | 34.3902 % | 0 | 0.0000 % | 282 | 38989 | 201 |
| val | Heartbleed | 1 | 0 | 0.0000 % | 0 | 0.0000 % | 0 | 0 | 0 |
| val | Infiltration | 4 | 0 | 0.0000 % | 0 | 0.0000 % | 0 | 0 | 0 |
| val | SSH-Patator | 597 | 288 | 48.2412 % | 0 | 0.0000 % | 288 | 8689 | 284 |
| val | Web Attack - Brute Force | 105 | 6 | 5.7143 % | 0 | 0.0000 % | 6 | 10 | 3 |
| val | Web Attack - XSS | 3 | 0 | 0.0000 % | 0 | 0.0000 % | 0 | 0 | 0 |

Les indicateurs sont des annotations de diagnostic : aucun flux n’est supprimé ni modifié. `train_dup_count` peut être utilisé pour pondérer ou dédupliquer l’entraînement au niveau de l’expérience.
