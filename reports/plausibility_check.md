# Diagnostic de plausibilité des features — CIC-IDS2017

- Source : `data/interim/clean.parquet`; 2,827,677 lignes; features brutes, non normalisées. Les ventilations complètes par classe et jour figurent dans le CSV associé.
- `Flow Duration` est mesuré en microsecondes dans CICFlowMeter; 120 s = 120 000 000 µs. Les parts globales ont pour dénominateur toutes les lignes de `clean.parquet`.

## Contrôles de cohérence

| Contrôle | Flux | Part | Classes les plus touchées (effectif; part de classe) | Combinaisons classe/jour dominantes | Recommandation |
|---|---:|---:|---|---|---|
| Flow Duration ≤ 0 | 115 | 0.0041% | BENIGN: 115 (0.0051% de la classe) | BENIGN/Friday: 47; BENIGN/Wednesday: 21; BENIGN/Tuesday: 17 | Inspecter ces valeurs non physiques; corriger à la source ou exclure après audit. |
| Flow Duration > 120 s | 0 | 0.0000% | aucun | aucun | Documenter la configuration CICFlowMeter et vérifier le découpage/timeout avant toute exclusion. |
| 0 paquets, octets > 0 | 0 | 0.0000% | aucun | aucun | Incohérence physique: corriger à la source ou exclure après audit. |
| Max Packet Length > 1 500 | 466,146 | 16.4851% | BENIGN: 221,963 (9.7733% de la classe); DoS Hulk: 154,852 (67.2910% de la classe); DDoS: 81,346 (63.5392% de la classe) | DoS Hulk/Wednesday: 154,852; DDoS/Friday: 81,346; BENIGN/Friday: 49,299 | Documenter jumbo frames/encapsulation; ne pas retirer automatiquement. |
| Max Packet Length > 65 535 | 0 | 0.0000% | aucun | aucun | Valeur non plausible pour une longueur IP; vérifier conversion/calcul, puis corriger ou retirer. |
| Min Packet Length > Max Packet Length | 0 | 0.0000% | aucun | aucun | Incohérence de calcul: corriger ou retirer après vérification. |
| SYN ≥ 1 et moins de 3 paquets | 57,936 | 2.0489% | BENIGN: 55,317 (2.4357% de la classe); FTP-Patator: 1,491 (18.7902% de la classe); DoS Slowhttptest: 604 (10.9838% de la classe) | BENIGN/Monday: 20,314; BENIGN/Tuesday: 11,041; BENIGN/Wednesday: 10,527 | Documenter comme flux incomplet/scan possible; conserver si cohérent avec le scénario. |

Les 115 lignes avec `Flow Duration ≤ 0` sont toutes négatives; **aucune n’a une durée exactement égale à zéro**. Aucun flux ne dépasse 120 s.
Le CSV contient, pour chaque contrôle, les totaux, les comptes par classe, par jour et par paire `(classe, jour)`; les parts sont calculées dans le sous-groupe correspondant.

## Valeurs négatives par feature

| Feature | Occurrences négatives | Part de toutes les lignes | Valeurs min..max | Valeur -1 | Classes/jours dominants | Interprétation et recommandation |
|---|---:|---:|---:|---:|---|---|
| `Init_Win_bytes_backward` | 1,439,475 | 50.9066% | [-1,-1] | 1,439,475 | BENIGN/Monday: 298,839; BENIGN/Thursday: 266,319; BENIGN/Wednesday: 260,854 | -1 est une sentinelle CICFlowMeter possible (champ non disponible/non applicable); confirmer et documenter, sans suppression globale. |
| `Init_Win_bytes_forward` | 1,001,172 | 35.4062% | [-1,-1] | 1,001,172 | BENIGN/Monday: 224,482; BENIGN/Wednesday: 203,252; BENIGN/Tuesday: 200,128 | -1 est une sentinelle CICFlowMeter possible (champ non disponible/non applicable); confirmer et documenter, sans suppression globale. |
| `Flow IAT Min` | 2,890 | 0.1022% | [-14,-1] | 2,753 | BENIGN/Thursday: 615; BENIGN/Wednesday: 581; BENIGN/Monday: 512 | -1 peut être un marqueur d’absence selon la feature, mais les autres valeurs négatives ne sont pas des mesures plausibles; vérifier la source et documenter. |
| `Flow Duration` | 115 | 0.0041% | [-13,-1] | 109 | BENIGN/Friday: 47; BENIGN/Wednesday: 21; BENIGN/Tuesday: 17 | -1 peut être un marqueur d’absence selon la feature, mais les autres valeurs négatives ne sont pas des mesures plausibles; vérifier la source et documenter. |
| `Flow Packets/s` | 115 | 0.0041% | [-2000000,-153846.156] | 0 | BENIGN/Friday: 47; BENIGN/Wednesday: 21; BENIGN/Tuesday: 17 | Valeurs négatives dérivées de durées négatives; corriger la durée/source et recalculer ces taux. |
| `Flow IAT Mean` | 115 | 0.0041% | [-13,-1] | 109 | BENIGN/Friday: 47; BENIGN/Wednesday: 21; BENIGN/Tuesday: 17 | -1 peut être un marqueur d’absence selon la feature, mais les autres valeurs négatives ne sont pas des mesures plausibles; vérifier la source et documenter. |
| `Flow IAT Max` | 115 | 0.0041% | [-13,-1] | 109 | BENIGN/Friday: 47; BENIGN/Wednesday: 21; BENIGN/Tuesday: 17 | -1 peut être un marqueur d’absence selon la feature, mais les autres valeurs négatives ne sont pas des mesures plausibles; vérifier la source et documenter. |
| `Flow Bytes/s` | 85 | 0.0030% | [-261000000,-461538.469] | 0 | BENIGN/Friday: 46; BENIGN/Wednesday: 16; BENIGN/Thursday: 14 | Valeurs négatives dérivées de durées négatives; corriger la durée/source et recalculer ces taux. |
| `min_seg_size_forward` | 35 | 0.0012% | [-536870656,-1] | 1 | BENIGN/Monday: 23; BENIGN/Tuesday: 11; BENIGN/Wednesday: 1 | Valeurs fortement négatives incompatibles avec une longueur/taille; suspecter conversion/signe ou corruption, corriger ou retirer après audit. |
| `Fwd Header Length` | 35 | 0.0012% | [-3.22122342e+10,-11] | 0 | BENIGN/Monday: 23; BENIGN/Tuesday: 11; BENIGN/Wednesday: 1 | Valeurs fortement négatives incompatibles avec une longueur/taille; suspecter conversion/signe ou corruption, corriger ou retirer après audit. |
| `Bwd Header Length` | 22 | 0.0008% | [-1.07374131e+09,-83885008] | 0 | BENIGN/Monday: 17; BENIGN/Tuesday: 5 | Valeurs fortement négatives incompatibles avec une longueur/taille; suspecter conversion/signe ou corruption, corriger ou retirer après audit. |
| `Fwd IAT Min` | 17 | 0.0006% | [-12,-1] | 15 | DoS Hulk/Wednesday: 8; DDoS/Friday: 6; DoS GoldenEye/Wednesday: 3 | -1 peut être un marqueur d’absence selon la feature, mais les autres valeurs négatives ne sont pas des mesures plausibles; vérifier la source et documenter. |

`Init_Win_bytes_forward` et `Init_Win_bytes_backward` valent exactement -1 pour leurs occurrences négatives; -1 peut y signifier un champ TCP indisponible/non applicable, à confirmer et documenter. Les taux `Flow Bytes/s` et `Flow Packets/s` négatifs apparaissent sur des durées négatives. Les fortes valeurs négatives des longueurs d’en-tête et de `min_seg_size_forward` sont compatibles avec une anomalie de conversion/signe, pas avec une sentinelle standard. Pour les autres délais, ne pas supposer que toute valeur négative est une sentinelle.

## Variance quasi nulle (> 99 % sur une seule valeur)

| Feature | Valeur dominante | Effectif | Part | Recommandation |
|---|---:|---:|---:|---|
| `Fwd URG Flags` | 0 | 2,827,499 | 99.9937% | Envisager de retirer seulement après validation du rôle et de l’impact sur les classes rares. |
| `CWE Flag Count` | 0 | 2,827,499 | 99.9937% | Envisager de retirer seulement après validation du rôle et de l’impact sur les classes rares. |
| `RST Flag Count` | 0 | 2,826,991 | 99.9757% | Envisager de retirer seulement après validation du rôle et de l’impact sur les classes rares. |
| `ECE Flag Count` | 0 | 2,826,988 | 99.9756% | Envisager de retirer seulement après validation du rôle et de l’impact sur les classes rares. |

## Pertes de nettoyage et limites de traçabilité

- `cleaning_report.md` donne les suppressions inf/NaN par fichier, mais pas par classe : 2,867 lignes avec inf/-inf, 0 avec NaN seulement, 2,867 supprimées à l’étape 5.
- Le delta de classe ci-dessous compare « avant étape 4 » à « après étape 10 »; il combine les suppressions inf/NaN et les doublons, donc ne constitue pas un taux de perte inf/NaN isolé.

| Classe | Avant | Après | Delta total | Taux du delta / avant |
|---|---:|---:|---:|---:|
| BENIGN | 2,273,097 | 2,271,122 | 1,975 | 0.0869% |
| Bot | 1,966 | 1,956 | 10 | 0.5086% |
| DDoS | 128,027 | 128,025 | 2 | 0.0016% |
| DoS GoldenEye | 10,293 | 10,293 | 0 | 0.0000% |
| DoS Hulk | 231,073 | 230,123 | 950 | 0.4111% |
| DoS Slowhttptest | 5,499 | 5,499 | 0 | 0.0000% |
| DoS slowloris | 5,796 | 5,796 | 0 | 0.0000% |
| FTP-Patator | 7,938 | 7,935 | 3 | 0.0378% |
| Heartbleed | 11 | 11 | 0 | 0.0000% |
| Infiltration | 36 | 36 | 0 | 0.0000% |
| PortScan | 158,930 | 158,804 | 126 | 0.0793% |
| SSH-Patator | 5,897 | 5,897 | 0 | 0.0000% |
| Web Attack - Brute Force | 1,507 | 1,507 | 0 | 0.0000% |
| Web Attack - Sql Injection | 21 | 21 | 0 | 0.0000% |
| Web Attack - XSS | 652 | 652 | 0 | 0.0000% |

- `clean_raw.parquet` a 2,827,677 lignes : `src/data/clean.py` l’écrit après le filtrage inf/NaN (étape 5) et la déduplication (étape 6). Les lignes perdues n’y sont donc plus; la part de ces lignes avec `Flow Duration = 0` n’est pas récupérable à partir des Parquet nettoyés et n’est pas estimée.
- Recommandation générale : corriger à la source les incohérences impossibles; ne retirer qu’après vérification; documenter les sentinelles et anomalies de capture plausibles. Aucune donnée n’a été modifiée.

CSV détaillé : `reports/plausibility_check.csv`.
