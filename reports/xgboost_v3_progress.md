# Résultats intermédiaires XGBoost V3

## V3 b0 — résultats intermédiaires

- Seuil OOF FPR 1 % : 0.01539807 (FPR OOF observée 0.9975%); 199 rounds fixes.

| Vérité test | PR-AUC (moyenne ± écart-type / médiane) | FP min–max |
|---|---:|---:|
| labels d'origine | PR-AUC 0.9936 ± 0.0004 / 0.9938<br>TPR@FPR≤1% 0.9881 ± 0.0003 / 0.9880<br>FP 2400.3 ± 71.7 / 2389.0 (min–max 2313–2547)<br>FN 665.6 ± 3.0 / 666.5<br>TPR/FPR seuil 0.9872 ± 0.0001 / 0.9872 / 0.0041 ± 0.0001 / 0.0041<br>FP signalés 0.049 ± 0.005 / 0.049 | 2313–2547 |
| v2 — Attempted comptés | PR-AUC 0.8011 ± 0.0062 / 0.8020<br>TPR@FPR≤1% 0.5921 ± 0.0005 / 0.5921<br>FP 2282.8 ± 68.1 / 2262.5 (min–max 2198–2423)<br>FN 35937.1 ± 12.1 / 35941.0<br>TPR/FPR seuil 0.5897 ± 0.0001 / 0.5897 / 0.0042 ± 0.0001 / 0.0042<br>FP signalés 0.000 ± 0.000 / 0.000 | 2198–2423 |
| v2 — Attempted exclus | PR-AUC 0.7476 ± 0.0073 / 0.7485<br>TPR@FPR≤1% 0.5379 ± 0.0005 / 0.5379<br>FP 2282.8 ± 68.1 / 2262.5 (min–max 2198–2423)<br>FN 33869.1 ± 11.5 / 33872.5<br>TPR/FPR seuil 0.5357 ± 0.0002 / 0.5357 / 0.0042 ± 0.0001 / 0.0042<br>FP signalés 0.000 ± 0.000 / 0.000 | 2198–2423 |
## V3 v2a — résultats intermédiaires

- Seuil OOF FPR 1 % : 0.01306097 (FPR OOF observée 0.9998%); 199 rounds fixes.

| Vérité test | PR-AUC (moyenne ± écart-type / médiane) | FP min–max |
|---|---:|---:|
| labels d'origine | PR-AUC 0.7843 ± 0.0068 / 0.7857<br>TPR@FPR≤1% 0.5053 ± 0.0144 / 0.5010<br>FP 41420.5 ± 178.3 / 41411.0 (min–max 41164–41726)<br>FN 115.3 ± 15.8 / 107.0<br>TPR/FPR seuil 0.9978 ± 0.0003 / 0.9980 / 0.0715 ± 0.0003 / 0.0715<br>FP signalés 0.850 ± 0.004 / 0.850 | 41164–41726 |
| v2 — Attempted comptés | PR-AUC 0.9986 ± 0.0001 / 0.9986<br>TPR@FPR≤1% 0.9967 ± 0.0002 / 0.9966<br>FP 6203.0 ± 178.4 / 6195.0 (min–max 5947–6511)<br>FN 286.8 ± 16.1 / 279.0<br>TPR/FPR seuil 0.9967 ± 0.0002 / 0.9968 / 0.0114 ± 0.0003 / 0.0114<br>FP signalés 0.000 ± 0.000 / 0.000 | 5947–6511 |
| v2 — Attempted exclus | PR-AUC 0.9996 ± 0.0000 / 0.9996<br>TPR@FPR≤1% 0.9993 ± 0.0000 / 0.9993<br>FP 6203.0 ± 178.4 / 6195.0 (min–max 5947–6511)<br>FN 46.7 ± 2.1 / 47.0<br>TPR/FPR seuil 0.9994 ± 0.0000 / 0.9994 / 0.0114 ± 0.0003 / 0.0114<br>FP signalés 0.000 ± 0.000 / 0.000 | 5947–6511 |
## V3 v2b — résultats intermédiaires

- Seuil OOF FPR 1 % : 0.00458237 (FPR OOF observée 0.9999%); 199 rounds fixes.

| Vérité test | PR-AUC (moyenne ± écart-type / médiane) | FP min–max |
|---|---:|---:|
| labels d'origine | PR-AUC 0.7535 ± 0.0166 / 0.7552<br>TPR@FPR≤1% 0.4868 ± 0.0331 / 0.4929<br>FP 40751.4 ± 173.0 / 40692.0 (min–max 40565–41033)<br>FN 4384.1 ± 320.2 / 4501.5<br>TPR/FPR seuil 0.9160 ± 0.0061 / 0.9138 / 0.0703 ± 0.0003 / 0.0702<br>FP signalés 0.849 ± 0.003 / 0.850 | 40565–41033 |
| v2 — Attempted comptés | PR-AUC 0.9828 ± 0.0013 / 0.9832<br>TPR@FPR≤1% 0.9386 ± 0.0033 / 0.9374<br>FP 6150.8 ± 169.0 / 6099.5 (min–max 5966–6429)<br>FN 5172.5 ± 320.4 / 5289.0<br>TPR/FPR seuil 0.9409 ± 0.0037 / 0.9396 / 0.0113 ± 0.0003 / 0.0112<br>FP signalés 0.000 ± 0.000 / 0.000 | 5966–6429 |
| v2 — Attempted exclus | PR-AUC 0.9997 ± 0.0000 / 0.9997<br>TPR@FPR≤1% 0.9994 ± 0.0000 / 0.9994<br>FP 6150.8 ± 169.0 / 6099.5 (min–max 5966–6429)<br>FN 41.0 ± 2.7 / 40.0<br>TPR/FPR seuil 0.9994 ± 0.0000 / 0.9995 / 0.0113 ± 0.0003 / 0.0112<br>FP signalés 0.000 ± 0.000 / 0.000 | 5966–6429 |
