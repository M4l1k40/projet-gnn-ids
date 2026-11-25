# Évaluation XGBoost binaire — split V3

- Essai 24 appris sur les plis V2; hyperparamètres fixes, 199 rounds, sans early stopping.
- Graines 42–51; les scores sont présentés moyenne ± écart-type / médiane.
- Le V2 d’origine est un point de comparaison sur un split différent; aucune prédiction V2 n’a été recalculée.
- La vérité « v2 — Attempted comptés » définit une attaque par `label_v2_bin == 1` ou `attempted`; « Attempted exclus » retire les lignes Attempted de l’évaluation.

## Comparaison 4 × 3

| Entraînement | Test labels d’origine | Test v2 Attempted comptés | Test v2 Attempted exclus |
|---|---|---|---|
| V2 origine (split différent) | PR-AUC 0.9920 ± 0.0004 / 0.9921<br>TPR@FPR≤1% 0.9875 ± 0.0001 / 0.9875<br>FP 1377.4 ± 1283.7 / 550.0 (min–max 532–3527)<br>FN 913.5 ± 29.9 / 919.0<br>TPR/FPR seuil 0.9825 ± 0.0006 / 0.9824 / 0.0017 ± 0.0015 / 0.0007<br>FP signalés 0.325 ± 0.368 / 0.077 | PR-AUC 0.7770 ± 0.0045 / 0.7771<br>TPR@FPR≤1% 0.6044 ± 0.0010 / 0.6041<br>FP 515.2 ± 13.1 / 513.0 (min–max 496–546)<br>FN 41172.3 ± 1282.8 / 41992.0<br>TPR/FPR seuil 0.5588 ± 0.0137 / 0.5500 / 0.0007 ± 0.0000 / 0.0006<br>FP signalés 0.002 ± 0.000 / 0.002 | PR-AUC 0.7237 ± 0.0056 / 0.7235<br>TPR@FPR≤1% 0.5603 ± 0.0005 / 0.5603<br>FP 515.2 ± 13.1 / 513.0 (min–max 496–546)<br>FN 37211.0 ± 1281.5 / 38035.5<br>TPR/FPR seuil 0.5159 ± 0.0167 / 0.5052 / 0.0007 ± 0.0000 / 0.0006<br>FP signalés 0.002 ± 0.000 / 0.002 |
| V3 b0 | PR-AUC 0.9936 ± 0.0004 / 0.9938<br>TPR@FPR≤1% 0.9881 ± 0.0003 / 0.9880<br>FP 2400.3 ± 71.7 / 2389.0 (min–max 2313–2547)<br>FN 665.6 ± 3.0 / 666.5<br>TPR/FPR seuil 0.9872 ± 0.0001 / 0.9872 / 0.0041 ± 0.0001 / 0.0041<br>FP signalés 0.049 ± 0.005 / 0.049 | PR-AUC 0.8011 ± 0.0062 / 0.8020<br>TPR@FPR≤1% 0.5921 ± 0.0005 / 0.5921<br>FP 2282.8 ± 68.1 / 2262.5 (min–max 2198–2423)<br>FN 35937.1 ± 12.1 / 35941.0<br>TPR/FPR seuil 0.5897 ± 0.0001 / 0.5897 / 0.0042 ± 0.0001 / 0.0042<br>FP signalés 0.000 ± 0.000 / 0.000 | PR-AUC 0.7476 ± 0.0073 / 0.7485<br>TPR@FPR≤1% 0.5379 ± 0.0005 / 0.5379<br>FP 2282.8 ± 68.1 / 2262.5 (min–max 2198–2423)<br>FN 33869.1 ± 11.5 / 33872.5<br>TPR/FPR seuil 0.5357 ± 0.0002 / 0.5357 / 0.0042 ± 0.0001 / 0.0042<br>FP signalés 0.000 ± 0.000 / 0.000 |
| V3 v2a | PR-AUC 0.7843 ± 0.0068 / 0.7857<br>TPR@FPR≤1% 0.5053 ± 0.0144 / 0.5010<br>FP 41420.5 ± 178.3 / 41411.0 (min–max 41164–41726)<br>FN 115.3 ± 15.8 / 107.0<br>TPR/FPR seuil 0.9978 ± 0.0003 / 0.9980 / 0.0715 ± 0.0003 / 0.0715<br>FP signalés 0.850 ± 0.004 / 0.850 | PR-AUC 0.9986 ± 0.0001 / 0.9986<br>TPR@FPR≤1% 0.9967 ± 0.0002 / 0.9966<br>FP 6203.0 ± 178.4 / 6195.0 (min–max 5947–6511)<br>FN 286.8 ± 16.1 / 279.0<br>TPR/FPR seuil 0.9967 ± 0.0002 / 0.9968 / 0.0114 ± 0.0003 / 0.0114<br>FP signalés 0.000 ± 0.000 / 0.000 | PR-AUC 0.9996 ± 0.0000 / 0.9996<br>TPR@FPR≤1% 0.9993 ± 0.0000 / 0.9993<br>FP 6203.0 ± 178.4 / 6195.0 (min–max 5947–6511)<br>FN 46.7 ± 2.1 / 47.0<br>TPR/FPR seuil 0.9994 ± 0.0000 / 0.9994 / 0.0114 ± 0.0003 / 0.0114<br>FP signalés 0.000 ± 0.000 / 0.000 |
| V3 v2b | PR-AUC 0.7535 ± 0.0166 / 0.7552<br>TPR@FPR≤1% 0.4868 ± 0.0331 / 0.4929<br>FP 40751.4 ± 173.0 / 40692.0 (min–max 40565–41033)<br>FN 4384.1 ± 320.2 / 4501.5<br>TPR/FPR seuil 0.9160 ± 0.0061 / 0.9138 / 0.0703 ± 0.0003 / 0.0702<br>FP signalés 0.849 ± 0.003 / 0.850 | PR-AUC 0.9828 ± 0.0013 / 0.9832<br>TPR@FPR≤1% 0.9386 ± 0.0033 / 0.9374<br>FP 6150.8 ± 169.0 / 6099.5 (min–max 5966–6429)<br>FN 5172.5 ± 320.4 / 5289.0<br>TPR/FPR seuil 0.9409 ± 0.0037 / 0.9396 / 0.0113 ± 0.0003 / 0.0112<br>FP signalés 0.000 ± 0.000 / 0.000 | PR-AUC 0.9997 ± 0.0000 / 0.9997<br>TPR@FPR≤1% 0.9994 ± 0.0000 / 0.9994<br>FP 6150.8 ± 169.0 / 6099.5 (min–max 5966–6429)<br>FN 41.0 ± 2.7 / 40.0<br>TPR/FPR seuil 0.9994 ± 0.0000 / 0.9995 / 0.0113 ± 0.0003 / 0.0112<br>FP signalés 0.000 ± 0.000 / 0.000 |

Chaque mesure est agrégée sur les dix graines; FP signalés désigne la part des FP dont le flux est divergent ou Attempted selon l’audit.

## Rappel des seuils hors-pli

| Variante | Seuil FPR 1 % | FPR hors-pli atteinte | OOF lignes |
|---|---:|---:|---:|
| V3 b0 | 0.01539807 | 0.9975% | 1,649,128 |
| V3 v2a | 0.01306097 | 0.9998% | 1,649,128 |
| V3 v2b | 0.00458237 | 0.9999% | 1,596,866 |

## Recall par famille v2 et classe d’origine

Les supports sont les flux positifs dans chaque groupe; le tableau donne la moyenne ± écart-type / médiane du recall par graine.

| Entraînement | Vérité test | Type | Groupe | Support | Recall |
|---|---|---|---|---:|---:|
| V2 origine (split différent) | labels d'origine | label_orig_multi | BENIGN | 0 | n.d. |
| V2 origine (split différent) | labels d'origine | label_orig_multi | Bot | 476 | 0.0000 ± 0.0000 / 0.0000 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | DDoS | 12,501 | 0.9963 ± 0.0001 / 0.9963 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | DoS Hulk | 14,152 | 0.9877 ± 0.0006 / 0.9875 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9011 ± 0.0206 / 0.8950 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | DoS slowloris | 714 | 0.9818 ± 0.0000 / 0.9818 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | FTP-Patator | 1,579 | 0.9962 ± 0.0000 / 0.9962 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | Infiltration | 9 | 0.5222 ± 0.1741 / 0.5000 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | PortScan | 20,046 | 0.9988 ± 0.0006 / 0.9987 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | SSH-Patator | 1,192 | 0.9661 ± 0.0013 / 0.9664 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | Web Attack - Brute Force | 260 | 0.9946 ± 0.0041 / 0.9923 |
| V2 origine (split différent) | labels d'origine | label_orig_multi | Web Attack - XSS | 66 | 0.8773 ± 0.0167 / 0.8712 |
| V2 origine (split différent) | labels d'origine | v2_family | other_change | 28 | 0.5107 ± 0.0173 / 0.5000 |
| V2 origine (split différent) | labels d'origine | v2_family | portscan_infiltration | 0 | n.d. |
| V2 origine (split différent) | labels d'origine | v2_family | server_response | 0 | n.d. |
| V2 origine (split différent) | labels d'origine | v2_family | unchanged | 52,172 | 0.9828 ± 0.0006 / 0.9826 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | BENIGN | 41,129 | 0.0210 ± 0.0312 / 0.0010 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | Bot | 474 | 0.0000 ± 0.0000 / 0.0000 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | DDoS | 12,501 | 0.9963 ± 0.0001 / 0.9963 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | DoS Hulk | 14,152 | 0.9877 ± 0.0006 / 0.9875 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9011 ± 0.0206 / 0.8950 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | DoS slowloris | 709 | 0.9887 ± 0.0000 / 0.9887 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | FTP-Patator | 1,578 | 0.9962 ± 0.0000 / 0.9962 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | Infiltration | 9 | 0.5222 ± 0.1741 / 0.5000 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | PortScan | 20,046 | 0.9988 ± 0.0006 / 0.9987 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | SSH-Patator | 1,192 | 0.9661 ± 0.0013 / 0.9664 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | Web Attack - Brute Force | 260 | 0.9946 ± 0.0041 / 0.9923 |
| V2 origine (split différent) | v2 — Attempted comptés | label_orig_multi | Web Attack - XSS | 66 | 0.8773 ± 0.0167 / 0.8712 |
| V2 origine (split différent) | v2 — Attempted comptés | v2_family | other_change | 283 | 0.0470 ± 0.0017 / 0.0459 |
| V2 origine (split différent) | v2 — Attempted comptés | v2_family | portscan_infiltration | 29,787 | 0.0003 ± 0.0000 / 0.0003 |
| V2 origine (split différent) | v2 — Attempted comptés | v2_family | server_response | 11,079 | 0.0771 ± 0.1159 / 0.0029 |
| V2 origine (split différent) | v2 — Attempted comptés | v2_family | unchanged | 52,172 | 0.9828 ± 0.0006 / 0.9826 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | BENIGN | 37,836 | 0.0223 ± 0.0339 / 0.0006 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | Bot | 0 | n.d. |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | DDoS | 12,501 | 0.9963 ± 0.0001 / 0.9963 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | DoS Hulk | 4,100 | 1.0000 ± 0.0000 / 1.0000 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | DoS Slowhttptest | 399 | 0.7038 ± 0.0621 / 0.6855 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | DoS slowloris | 558 | 0.9946 ± 0.0000 / 0.9946 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | FTP-Patator | 806 | 1.0000 ± 0.0000 / 1.0000 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | Infiltration | 9 | 0.5222 ± 0.1741 / 0.5000 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | PortScan | 20,046 | 0.9988 ± 0.0006 / 0.9987 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | SSH-Patator | 599 | 0.9619 ± 0.0007 / 0.9616 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | Web Attack - Brute Force | 13 | 1.0000 ± 0.0000 / 1.0000 |
| V2 origine (split différent) | v2 — Attempted exclus | label_orig_multi | Web Attack - XSS | 3 | 0.4333 ± 0.1610 / 0.3333 |
| V2 origine (split différent) | v2 — Attempted exclus | v2_family | other_change | 2 | 0.0000 ± 0.0000 / 0.0000 |
| V2 origine (split différent) | v2 — Attempted exclus | v2_family | portscan_infiltration | 29,787 | 0.0003 ± 0.0000 / 0.0003 |
| V2 origine (split différent) | v2 — Attempted exclus | v2_family | server_response | 8,048 | 0.1039 ± 0.1594 / 0.0017 |
| V2 origine (split différent) | v2 — Attempted exclus | v2_family | unchanged | 39,033 | 0.9944 ± 0.0007 / 0.9942 |
| V3 b0 | labels d'origine | label_orig_multi | BENIGN | 0 | n.d. |
| V3 b0 | labels d'origine | label_orig_multi | Bot | 476 | 0.0000 ± 0.0000 / 0.0000 |
| V3 b0 | labels d'origine | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0001 / 0.9978 |
| V3 b0 | labels d'origine | label_orig_multi | DoS Hulk | 14,152 | 0.9911 ± 0.0001 / 0.9911 |
| V3 b0 | labels d'origine | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9976 ± 0.0003 / 0.9975 |
| V3 b0 | labels d'origine | label_orig_multi | DoS slowloris | 714 | 0.9902 ± 0.0007 / 0.9902 |
| V3 b0 | labels d'origine | label_orig_multi | FTP-Patator | 1,579 | 0.9962 ± 0.0000 / 0.9962 |
| V3 b0 | labels d'origine | label_orig_multi | Infiltration | 9 | 0.9222 ± 0.0537 / 0.8889 |
| V3 b0 | labels d'origine | label_orig_multi | PortScan | 20,046 | 0.9997 ± 0.0000 / 0.9997 |
| V3 b0 | labels d'origine | label_orig_multi | SSH-Patator | 1,192 | 0.9901 ± 0.0018 / 0.9899 |
| V3 b0 | labels d'origine | label_orig_multi | Web Attack - Brute Force | 260 | 1.0000 ± 0.0000 / 1.0000 |
| V3 b0 | labels d'origine | label_orig_multi | Web Attack - XSS | 66 | 0.9697 ± 0.0000 / 0.9697 |
| V3 b0 | labels d'origine | v2_family | other_change | 28 | 0.6821 ± 0.0113 / 0.6786 |
| V3 b0 | labels d'origine | v2_family | portscan_infiltration | 0 | n.d. |
| V3 b0 | labels d'origine | v2_family | server_response | 0 | n.d. |
| V3 b0 | labels d'origine | v2_family | unchanged | 52,172 | 0.9874 ± 0.0001 / 0.9874 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | BENIGN | 35,397 | 0.0034 ± 0.0003 / 0.0033 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | Bot | 474 | 0.0000 ± 0.0000 / 0.0000 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0001 / 0.9978 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | DoS Hulk | 14,152 | 0.9911 ± 0.0001 / 0.9911 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9976 ± 0.0003 / 0.9975 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | DoS slowloris | 709 | 0.9970 ± 0.0004 / 0.9972 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | FTP-Patator | 1,578 | 0.9962 ± 0.0000 / 0.9962 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | Infiltration | 9 | 0.9222 ± 0.0537 / 0.8889 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | PortScan | 20,046 | 0.9997 ± 0.0000 / 0.9997 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | SSH-Patator | 1,192 | 0.9901 ± 0.0018 / 0.9899 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | Web Attack - Brute Force | 260 | 1.0000 ± 0.0000 / 1.0000 |
| V3 b0 | v2 — Attempted comptés | label_orig_multi | Web Attack - XSS | 66 | 0.9697 ± 0.0000 / 0.9697 |
| V3 b0 | v2 — Attempted comptés | v2_family | other_change | 318 | 0.0566 ± 0.0000 / 0.0566 |
| V3 b0 | v2 — Attempted comptés | v2_family | portscan_infiltration | 29,787 | 0.0027 ± 0.0004 / 0.0025 |
| V3 b0 | v2 — Attempted comptés | v2_family | server_response | 5,312 | 0.0072 ± 0.0011 / 0.0075 |
| V3 b0 | v2 — Attempted comptés | v2_family | unchanged | 52,172 | 0.9874 ± 0.0001 / 0.9874 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | BENIGN | 33,918 | 0.0028 ± 0.0003 / 0.0027 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | Bot | 0 | n.d. |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0001 / 0.9978 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | DoS Hulk | 4,100 | 1.0000 ± 0.0000 / 1.0000 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | DoS Slowhttptest | 399 | 0.9952 ± 0.0008 / 0.9950 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | DoS slowloris | 558 | 1.0000 ± 0.0000 / 1.0000 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | FTP-Patator | 806 | 1.0000 ± 0.0000 / 1.0000 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | Infiltration | 9 | 0.9222 ± 0.0537 / 0.8889 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | PortScan | 20,046 | 0.9997 ± 0.0000 / 0.9997 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | SSH-Patator | 599 | 0.9808 ± 0.0035 / 0.9808 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | Web Attack - Brute Force | 13 | 1.0000 ± 0.0000 / 1.0000 |
| V3 b0 | v2 — Attempted exclus | label_orig_multi | Web Attack - XSS | 3 | 1.0000 ± 0.0000 / 1.0000 |
| V3 b0 | v2 — Attempted exclus | v2_family | other_change | 2 | 0.5000 ± 0.0000 / 0.5000 |
| V3 b0 | v2 — Attempted exclus | v2_family | portscan_infiltration | 29,787 | 0.0027 ± 0.0004 / 0.0025 |
| V3 b0 | v2 — Attempted exclus | v2_family | server_response | 4,130 | 0.0038 ± 0.0009 / 0.0041 |
| V3 b0 | v2 — Attempted exclus | v2_family | unchanged | 39,033 | 0.9988 ± 0.0001 / 0.9988 |
| V3 v2a | labels d'origine | label_orig_multi | BENIGN | 0 | n.d. |
| V3 v2a | labels d'origine | label_orig_multi | Bot | 476 | 0.9958 ± 0.0000 / 0.9958 |
| V3 v2a | labels d'origine | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0000 / 0.9978 |
| V3 v2a | labels d'origine | label_orig_multi | DoS Hulk | 14,152 | 0.9954 ± 0.0011 / 0.9960 |
| V3 v2a | labels d'origine | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9991 ± 0.0003 / 0.9992 |
| V3 v2a | labels d'origine | label_orig_multi | DoS slowloris | 714 | 0.9887 ± 0.0008 / 0.9888 |
| V3 v2a | labels d'origine | label_orig_multi | FTP-Patator | 1,579 | 0.9962 ± 0.0000 / 0.9962 |
| V3 v2a | labels d'origine | label_orig_multi | Infiltration | 9 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | labels d'origine | label_orig_multi | PortScan | 20,046 | 0.9999 ± 0.0000 / 0.9999 |
| V3 v2a | labels d'origine | label_orig_multi | SSH-Patator | 1,192 | 0.9992 ± 0.0000 / 0.9992 |
| V3 v2a | labels d'origine | label_orig_multi | Web Attack - Brute Force | 260 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | labels d'origine | label_orig_multi | Web Attack - XSS | 66 | 0.9545 ± 0.0000 / 0.9545 |
| V3 v2a | labels d'origine | v2_family | other_change | 28 | 0.6464 ± 0.0113 / 0.6429 |
| V3 v2a | labels d'origine | v2_family | portscan_infiltration | 0 | n.d. |
| V3 v2a | labels d'origine | v2_family | server_response | 0 | n.d. |
| V3 v2a | labels d'origine | v2_family | unchanged | 52,172 | 0.9980 ± 0.0003 / 0.9981 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | BENIGN | 35,397 | 0.9950 ± 0.0000 / 0.9950 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | Bot | 474 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0000 / 0.9978 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | DoS Hulk | 14,152 | 0.9954 ± 0.0011 / 0.9960 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | DoS Slowhttptest | 1,205 | 0.9991 ± 0.0003 / 0.9992 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | DoS slowloris | 709 | 0.9955 ± 0.0006 / 0.9958 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | FTP-Patator | 1,578 | 0.9962 ± 0.0000 / 0.9962 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | Infiltration | 9 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | PortScan | 20,046 | 0.9999 ± 0.0000 / 0.9999 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | SSH-Patator | 1,192 | 0.9992 ± 0.0000 / 0.9992 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | Web Attack - Brute Force | 260 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted comptés | label_orig_multi | Web Attack - XSS | 66 | 0.9545 ± 0.0000 / 0.9545 |
| V3 v2a | v2 — Attempted comptés | v2_family | other_change | 318 | 0.4780 ± 0.0000 / 0.4780 |
| V3 v2a | v2 — Attempted comptés | v2_family | portscan_infiltration | 29,787 | 0.9996 ± 0.0000 / 0.9996 |
| V3 v2a | v2 — Attempted comptés | v2_family | server_response | 5,312 | 0.9996 ± 0.0003 / 0.9996 |
| V3 v2a | v2 — Attempted comptés | v2_family | unchanged | 52,172 | 0.9980 ± 0.0003 / 0.9981 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | BENIGN | 33,918 | 0.9995 ± 0.0000 / 0.9995 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | Bot | 0 | n.d. |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0000 / 0.9978 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | DoS Hulk | 4,100 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | DoS Slowhttptest | 399 | 0.9997 ± 0.0008 / 1.0000 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | DoS slowloris | 558 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | FTP-Patator | 806 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | Infiltration | 9 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | PortScan | 20,046 | 0.9999 ± 0.0000 / 0.9999 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | SSH-Patator | 599 | 0.9983 ± 0.0000 / 0.9983 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | Web Attack - Brute Force | 13 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted exclus | label_orig_multi | Web Attack - XSS | 3 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2a | v2 — Attempted exclus | v2_family | other_change | 2 | 0.5000 ± 0.0000 / 0.5000 |
| V3 v2a | v2 — Attempted exclus | v2_family | portscan_infiltration | 29,787 | 0.9996 ± 0.0000 / 0.9996 |
| V3 v2a | v2 — Attempted exclus | v2_family | server_response | 4,130 | 0.9995 ± 0.0004 / 0.9995 |
| V3 v2a | v2 — Attempted exclus | v2_family | unchanged | 39,033 | 0.9992 ± 0.0000 / 0.9992 |
| V3 v2b | labels d'origine | label_orig_multi | BENIGN | 0 | n.d. |
| V3 v2b | labels d'origine | label_orig_multi | Bot | 476 | 0.9958 ± 0.0000 / 0.9958 |
| V3 v2b | labels d'origine | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0000 / 0.9978 |
| V3 v2b | labels d'origine | label_orig_multi | DoS Hulk | 14,152 | 0.8262 ± 0.0074 / 0.8266 |
| V3 v2b | labels d'origine | label_orig_multi | DoS Slowhttptest | 1,205 | 0.3324 ± 0.0007 / 0.3324 |
| V3 v2b | labels d'origine | label_orig_multi | DoS slowloris | 714 | 0.8839 ± 0.0008 / 0.8838 |
| V3 v2b | labels d'origine | label_orig_multi | FTP-Patator | 1,579 | 0.6187 ± 0.1340 / 0.5266 |
| V3 v2b | labels d'origine | label_orig_multi | Infiltration | 9 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | labels d'origine | label_orig_multi | PortScan | 20,046 | 0.9998 ± 0.0000 / 0.9998 |
| V3 v2b | labels d'origine | label_orig_multi | SSH-Patator | 1,192 | 0.7212 ± 0.1227 / 0.7085 |
| V3 v2b | labels d'origine | label_orig_multi | Web Attack - Brute Force | 260 | 0.7981 ± 0.2579 / 0.9462 |
| V3 v2b | labels d'origine | label_orig_multi | Web Attack - XSS | 66 | 0.7500 ± 0.2741 / 0.9091 |
| V3 v2b | labels d'origine | v2_family | other_change | 28 | 0.4964 ± 0.0929 / 0.5357 |
| V3 v2b | labels d'origine | v2_family | portscan_infiltration | 0 | n.d. |
| V3 v2b | labels d'origine | v2_family | server_response | 0 | n.d. |
| V3 v2b | labels d'origine | v2_family | unchanged | 52,172 | 0.9162 ± 0.0061 / 0.9140 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | BENIGN | 35,397 | 0.9775 ± 0.0002 / 0.9776 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | Bot | 474 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0000 / 0.9978 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | DoS Hulk | 14,152 | 0.8262 ± 0.0074 / 0.8266 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | DoS Slowhttptest | 1,205 | 0.3324 ± 0.0007 / 0.3324 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | DoS slowloris | 709 | 0.8898 ± 0.0004 / 0.8900 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | FTP-Patator | 1,578 | 0.6191 ± 0.1341 / 0.5269 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | Infiltration | 9 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | PortScan | 20,046 | 0.9998 ± 0.0000 / 0.9998 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | SSH-Patator | 1,192 | 0.7212 ± 0.1227 / 0.7085 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | Web Attack - Brute Force | 260 | 0.7981 ± 0.2579 / 0.9462 |
| V3 v2b | v2 — Attempted comptés | label_orig_multi | Web Attack - XSS | 66 | 0.7500 ± 0.2741 / 0.9091 |
| V3 v2b | v2 — Attempted comptés | v2_family | other_change | 318 | 0.4676 ± 0.0083 / 0.4717 |
| V3 v2b | v2 — Attempted comptés | v2_family | portscan_infiltration | 29,787 | 0.9998 ± 0.0000 / 0.9998 |
| V3 v2b | v2 — Attempted comptés | v2_family | server_response | 5,312 | 0.8819 ± 0.0014 / 0.8822 |
| V3 v2b | v2 — Attempted comptés | v2_family | unchanged | 52,172 | 0.9162 ± 0.0061 / 0.9140 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | BENIGN | 33,918 | 0.9998 ± 0.0000 / 0.9998 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | Bot | 0 | n.d. |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | DDoS | 12,501 | 0.9978 ± 0.0000 / 0.9978 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | DoS Hulk | 4,100 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | DoS Slowhttptest | 399 | 0.9987 ± 0.0013 / 0.9987 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | DoS slowloris | 558 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | FTP-Patator | 806 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | Infiltration | 9 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | PortScan | 20,046 | 0.9998 ± 0.0000 / 0.9998 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | SSH-Patator | 599 | 0.9965 ± 0.0030 / 0.9983 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | Web Attack - Brute Force | 13 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted exclus | label_orig_multi | Web Attack - XSS | 3 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted exclus | v2_family | other_change | 2 | 0.5000 ± 0.0000 / 0.5000 |
| V3 v2b | v2 — Attempted exclus | v2_family | portscan_infiltration | 29,787 | 0.9998 ± 0.0000 / 0.9998 |
| V3 v2b | v2 — Attempted exclus | v2_family | server_response | 4,130 | 1.0000 ± 0.0000 / 1.0000 |
| V3 v2b | v2 — Attempted exclus | v2_family | unchanged | 39,033 | 0.9991 ± 0.0000 / 0.9991 |

## Limites

- Les hyperparamètres ont été choisis sur les plis V2. Le test V3 ne recouvre pas V2-train (0 flux V3-test issus de V2-train), tandis que 118 497 flux V3-train viennent de V2-test; la comparaison entre versions de split n’est donc pas indépendante.
- Les règles d’audit sont heuristiques issues d’un article et ne constituent pas une vérité terrain.
- v2a utilise toutes les lignes avec les labels corrigés; v2b retire les Attempted du train. La comparaison isole l’effet du retrait des Attempted à paramètres et rounds identiques.
- Les 199 rounds sont fixes, sans early stopping ni nouvelle recherche d’hyperparamètres; les seuils sont recalibrés sur les prédictions hors-pli V3 de chaque variante.
- Le split V3 reste différent du §5.1 du guide, qui décrit un split par segments de classe.
- Évaluation de laboratoire sur CIC-IDS2017; les résultats ne garantissent pas la généralisation à un trafic de production.

Métriques par graine/scénario : `D:\AI\projet-gnn-ids\reports\xgboost_v3_metrics.csv`.
Recall par graine/famille et classe : `D:\AI\projet-gnn-ids\reports\xgboost_v3_recall.csv`.
