# projet-gnn-ids

Projet d'étude de la détection d'intrusions réseau sur CIC-IDS2017, avec
préparation des flux, analyses de labels et benchmarks XGBoost/Random Forest.
Le travail est en cours : les résultats sont provisoires et les décisions de
méthode restent à valider à quatre (R3).

## Installation sous WSL2

Depuis le terminal WSL2, placez-vous dans le dépôt, créez un environnement virtuel et installez les dépendances :

```bash
python3 --version  # Python 3.10 ou supérieur
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Pour PyTorch, choisissez au besoin la commande d'installation adaptée à votre matériel et à votre version de CUDA dans la documentation officielle de PyTorch avant d'installer les autres dépendances.

## Données factices

Sous PowerShell, créez l'environnement, installez les dépendances puis générez `data/interim/fake_flows.parquet` :

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.data.fake
```

## Démarrage rapide

Depuis la racine du dépôt, après installation des dépendances :

```powershell
python -m pytest -q
python -m src.data.fake
```

Le second appel produit `data/interim/fake_flows.parquet`; il n'utilise pas
CIC-IDS2017. Les dépendances incluent notamment pandas, NumPy, PyArrow,
scikit-learn, XGBoost, SHAP, SciPy, Matplotlib et joblib
(`requirements.txt`).

## Pipeline données

Guide complet : [docs/DONNEES.md](docs/DONNEES.md).

**Données réelles.** Télécharger CIC-IDS2017 depuis la
[page officielle UNB](https://www.unb.ca/cic/datasets/ids-2017.html), puis
placer les CSV sous `data/raw/<raw_subdir>`. La valeur de `raw_subdir` est
`GeneratedLabelledFlows/TrafficLabelling` dans `configs/data.yaml`.

Le pipeline V2 par défaut se lance depuis la racine. Il réutilise les étapes
complètes déjà présentes; `--force` force la régénération et peut remplacer
les Parquet V2.

```powershell
python -m src.data.build
```

Les étapes annexes V2 ne sont pas toutes orchestrées par `build` :

```powershell
python -m src.data.folds
python -m src.data.p2
python -m src.data.relabel
python -m src.data.redundancy
python -m src.data.verify_final
```

`labels_v2_all.parquet` se construit séparément, après que ses entrées existent :

```powershell
python -c "from src.data.labels_v2 import build_labels_v2_all; build_labels_v2_all()"
```

Pour construire le split V3, puis l'option V3 log-z :

```powershell
python -m src.data.split_v3
python -m src.data.normalize_logz
```

Schéma du pipeline :

```text
CSV CIC-IDS2017
      |
      v
clean_raw.parquet -- timestamps/ts_end --> clean.parquet
      |                                      |
      +------------ split V2/V3 -------------+
                           |
                           v
             train / val / test + normalisation
                           |
                folds.parquet / p2_folds.parquet
                           |
               labels d'origine / labels v2
                           |
       XGBoost / Random Forest / multiclasse / P2
```

Le pipeline `python -m src.data.build` produit notamment
`data/interim/clean_raw.parquet`, `data/interim/clean.parquet`,
`data/processed/{train,val,test,meta}.parquet`, `models/scaler.joblib`,
`models/features.json` et les rapports de nettoyage, horodatage,
normalisation et fuite. Les effectifs V2 de référence (clean 2 827 677;
train 1 515 755, val 151 714, test 882 784) sont ceux de
`reports/data_card.md` et `docs/DONNEES.md`.

Les Parquet, scalers et modèles sont des artefacts locaux, non fournis avec le
dépôt. Les règles `.gitignore` excluent `data/`, `*.parquet`, `*.joblib` et
`predictions/`; les dossiers de modèles XGBoost et RF, y compris
`models/xgboost_v3_logz/` et `models/rf_v3_logz/`, sont également ignorés.

Les configurations principales sont `configs/data.yaml`,
`configs/labels.yaml`, `configs/classes.yaml`, `configs/xgboost.yaml`,
`configs/rf.yaml`, `configs/multiclass.yaml` et `configs/leakage_v3.yaml`.
Les chemins sont relatifs à la racine du dépôt;
les données réelles ne doivent pas être ajoutées à Git.

Commandes du pipeline et sorties (les durées ne sont pas rapportées pour les
étapes de préparation) :

| Étape | Commande vérifiée | Sorties principales | Rapport |
|---|---|---|---|
| Nettoyage, horodatage, split et normalisation V2 | `python -m src.data.build` | `clean_raw.parquet`, `clean.parquet`, `data/processed/*.parquet`, `models/scaler.joblib` | `reports/cleaning_report.md`, `reports/timestamps_check.md`, `reports/normalization_report.md`, `reports/leakage_report.md` |
| Split V3, normalisation et plis purgés | `python -m src.data.split_v3` | `data/processed_v3/`, `models/scaler_v3.joblib`, `data/processed_v3/folds_report.md` | `reports/split_v3.md`, `reports/normalization_v3.md` |
| Variante log-z | `python -m src.data.normalize_logz` | `data/processed_v3_logz/`, `models/scaler_v3_logz.joblib` | `normalization_v3_logz.md` |
| Plis CV V2 | `python -m src.data.folds` | `data/processed/folds.parquet` | `reports/cv_folds.md` |
| Rôles P2/E5 | `python -m src.data.p2` | `data/processed/p2_folds.parquet`, `models/p2/` | `reports/p2_report.md` |
| Audit des labels d'origine | `python -m src.data.relabel` | `data/processed/label_audit.parquet` | `reports/label_audit.md` |
| Labels v2 complets | appel Python ci-dessus | `data/processed/labels_v2_all.parquet` (clé `flow_id`) | `reports/labels_v2.md` |

Les durées disponibles concernent les expériences modèle ci-dessous; les
rapports de préparation ne donnent pas de durée de génération des données.

Pour charger les données, utiliser `src/data/access.py`
(`load_split`, `feature_names`, `multiclass_classes`, `get_cv_fold`,
`load_p2_fold`) plutôt que coder les chemins en dur.

## Versions des données

| Variante | Dossier préparé | Normaliseur | Split et plis | Usage provisoire |
|---|---|---|---|---|
| V2 (défaut) | `data/processed/` | `models/scaler.joblib` | Split historique; `folds.parquet` et `p2_folds.parquet` dans le dossier préparé | Compatibilité et comparaison historique |
| V3 | `data/processed_v3/` | `models/scaler_v3.joblib` | Split V3 par segments; plis purgés `folds.parquet`; rôles P2 copiés dans `p2_folds.parquet` | Référence des expériences V3 |
| V3 log-z (option) | `data/processed_v3_logz/` | `models/scaler_v3_logz.joblib` | Mêmes lignes, identifiants, meta et plis que V3; seules les 69 features sont transformées | Comparaison expérimentale, sans remplacer V3 |

### Normalisation standard et log-z

La normalisation standard reste le défaut (`data/processed_v3/`,
`models/scaler_v3.joblib`). La variante expérimentale applique une imputation
par médiane valide du train, `signed_log1p`, puis standardisation; elle est
enregistrée dans `models/scaler_v3_logz.joblib` et ses splits dans
`data/processed_v3_logz/`. Le transformeur peut être chargé sans importer le
code du dépôt avec `joblib.load("models/scaler_v3_logz.joblib")`.

La simulation vise à limiter l'écrasement de trois features par des valeurs
négatives corrompues du train : `Fwd Header Length` (35), `min_seg_size_forward`
(35) et `Bwd Header Length` (22); elle réduit aussi l'influence des queues
lourdes, notamment `Total Fwd Packets` et `Total Backward Packets`. Les
imputations et statistiques sont documentées dans
`reports/normalization_v3_logz.md` (lignes 2–7, 22–26) et
`reports/scaler_audit/feature_audit_v3.csv` (lignes 6–15).
Quatre indicateurs restent hors de la plage de dispersion recherchée :
`Fwd URG Flags`, `CWE Flag Count`, `RST Flag Count` et `ECE Flag Count`;
leur valeur dominante dépasse 99,97 % des flux
(`reports/plausibility_check.md`, lignes 42–47). La transformation monotone
ne peut pas créer de variance informative pour ces indicateurs constants
dans l'intervalle central.

Comparaison test V3, graine 42, scores calculés sur les mêmes flux. Les
prédictions sont indexées par flow_id et restent comparables.

| Modèle | Normalisation | PR-AUC | ROC-AUC | TPR@FPR≤0,1 % | TPR@FPR≤1 % | Fit |
|---|---|---:|---:|---:|---:|---:|
| XGBoost b0 | Standard | 0.992944 | 0.998368 | 0.985651 | 0.988525 | Repris |
| XGBoost b0 | Log-z | 0.993644 | 0.998725 | 0.985326 | 0.987989 | 118.44 s |
| RF b0 | Standard | 0.988107 | 0.994015 | 0.958755 | 0.980307 | Repris |
| RF b0 | Log-z | 0.988829 | 0.994089 | 0.968506 | 0.983506 | 275.86 s |

Source des quatre lignes : `reports/normalization_v3_logz.md`, lignes 54–57.
Les seuils restent ceux des modèles b0 existants; le jeu V3 standard reste le
défaut (`reports/normalization_v3_logz.md`, lignes 50–51, 72–74).

Les partitions contiennent les labels d'origine `label_bin` et `label_multi`.
La table `data/processed/labels_v2_all.parquet` ajoute les labels v2 et se
joint par `flow_id`; elle ne remplace pas les labels d'origine. Les décisions
de seuil V3 sont calibrées sur les scores hors-pli, et non sur les plis
zéro-shot.

## Contrats de données et prédictions

Le schéma de [src/data/schema.py](src/data/schema.py) définit les colonnes
d'identité `flow_id`, `src_ip`, `dst_ip`, `src_port`, `dst_port`, `ts_end`;
les cibles `label_bin`, `label_multi`; et les métadonnées `split`, `day`.
Les features numériques suivent `models/features.json` (69 colonnes dans les
expériences décrites). `meta.parquet` V3 contient aussi `seen_in_train`.

Toutes les prédictions suivent `PREDICTION_COLUMNS` :
`flow_id`, `y_true`, `y_pred`, `score`, `recon_error`, `seed`. Les deux
dernières colonnes restent présentes même si `recon_error` vaut NaN. En
multiclasse, `y_true` et `y_pred` sont les noms de classe et `score` est la
probabilité de la classe prédite.

Inventaire local constaté (chaque prédiction binaire/multiclasse V3 ci-dessous
contient 631 557 lignes; les effectifs de P2 varient avec le pli) :

| Expérience | Motif de fichier | Nombre | Lignes par fichier |
|---|---|---:|---:|
| XGBoost V2 binaire | `predictions/xgboost/xgb_bin_seed{42..51}.parquet` | 10 | 882 784 |
| XGBoost V3 b0 | `predictions/xgboost_v3/xgb_bin_b0_seed{42..51}_v3.parquet` | 10 | 631 557 |
| XGBoost V3 v2a / v2b | `predictions/xgboost_v3/xgb_bin_{v2a,v2b}_seed{42..51}_v3.parquet` | 20 (10 par variante) | 631 557 |
| Random Forest V3 b0 | `predictions/rf_v3/rf_bin_b0_seed{42..51}_rf.parquet` | 10 | 631 557 |
| Multiclasse XGBoost / RF | `predictions/{xgboost_v3_multi,rf_v3_multi}/{xgb,rf}_seed{42..46}_multi.parquet` | 10 (5 par modèle) | 631 557 |
| P2 XGBoost | `predictions/xgboost_p2/xgb_bin_{partition}_seed42_p2.parquet` | 9 | 1 956–702 713 |
| V3 log-z XGBoost / RF | `predictions/xgboost_v3_logz/{xgb,rf}_bin_b0_seed42_logz_v3.parquet` | 2 | 631 557 |

Exemple de lecture testé en lecture seule (depuis la racine du dépôt) :

```python
import pandas as pd
from src.data.schema import PREDICTION_COLUMNS
p = pd.read_parquet("predictions/xgboost_v3/xgb_bin_b0_seed42_v3.parquet")
assert list(p.columns) == PREDICTION_COLUMNS
print(p.shape, p["seed"].unique().tolist())
```

## Modèles et expériences

Toutes les commandes de ce tableau sont des points d'entrée réellement
disponibles. L'appel Python indiqué pour RF correspond au run complet; le
module `src.models.rf` lancé directement ne fait que le benchmark du pli 0.

| Expérience | Commande ou appel | Durée rapportée | Rapport |
|---|---|---|---|
| Recherche XGBoost V2 binaire | `python -m src.models.xgb search --mode bin` | Pas de durée totale publiée | [reports/xgboost_report.md](reports/xgboost_report.md) |
| Entraînement final XGBoost V2 | `from src.models.xgb import search_hyperparameters, run_final_training; r = search_hyperparameters("bin"); run_final_training("bin", r)` | Durée non rapportée | [reports/xgboost_report.md](reports/xgboost_report.md) |
| XGBoost V3 b0/v2a/v2b | `python -m src.models.xgb_v3` | Non résumée dans le rapport | [reports/xgboost_v3.md](reports/xgboost_v3.md) |
| Random Forest V3 complet | `from src.models.rf import run_rf_v3; run_rf_v3()` | Fits finaux : 3 084,8 s; inférence totale : 53,8 s (rapport, ligne 112) | [reports/rf_v3.md](reports/rf_v3.md) |
| Multiclasse benchmark / entraînement / évaluation | `python -m src.models.multiclass benchmark xgboost`; `python -m src.models.multiclass train rf`; `python -m src.models.multiclass evaluate` | Non rapportée | [reports/multiclass_v3.md](reports/multiclass_v3.md) |
| XGBoost P2/E5 | `python -m src.models.xgb_p2` | 163,6–264,8 s par pli (lignes 133–141) | [reports/xgboost_p2.md](reports/xgboost_p2.md) |
| SHAP V3 | `python -m src.models.xgb_shap` | Non rapportée | [reports/xgboost_v3_shap.md](reports/xgboost_v3_shap.md) |
| Diagnostic fuite V2/V3 | `python -m src.data.leakage_v3` (benchmark); `from src.data.leakage_v3 import run_full_v3, run_full_v2; run_full_v3(); run_full_v2()` (calcul complet) | Non rapportée comme durée totale | [reports/leakage_report_v3.md](reports/leakage_report_v3.md), [reports/leakage_report_v2.md](reports/leakage_report_v2.md) |
| Plausibilité et audit scaler | Aucun point d'entrée de génération vérifié; rapports existants seulement | Non applicable | [reports/plausibility_check.md](reports/plausibility_check.md), [reports/scaler_audit/resume_v3.md](reports/scaler_audit/resume_v3.md) |
| Comparaison log-z seed 42 | `python -m src.data.normalize_logz`; la comparaison de modèles n'a pas de CLI dédié | XGBoost 118,44 s et RF 275,86 s (tableau, lignes 54–57) | [reports/normalization_v3_logz.md](reports/normalization_v3_logz.md) |

La comparaison RF/XGBoost pour l'expérience V3 binaire est dans
`reports/rf_v3.md`. Les scripts peuvent écrire de nouveaux modèles,
prédictions ou rapports; vérifier les chemins configurés avant de les lancer.

## Résultats provisoires

Scores issus des rapports cités; test V3, labels d'origine sauf indication
contraire :

| Expérience / vue | Résultat principal | Source |
|---|---|---|
| XGBoost b0 V3, test complet | PR-AUC 0,9936 ± 0,0004; ROC-AUC 0,9987 ± 0,0002; TPR à FPR ≤ 1 % : 0,9881 ± 0,0003 | [reports/xgboost_v3.md](reports/xgboost_v3.md), ligne 13 |
| RF V3, test complet | PR-AUC 0,9885 ± 0,0002; ROC-AUC 0,9940 ± 0,0001; TPR à FPR ≤ 1 % : 0,9818 ± 0,0013 | [reports/rf_v3.md](reports/rf_v3.md), ligne 32 |
| Multiclasse XGBoost, test strict | Macro-F1 avec/sans Bot : 0,6914 / 0,7606; MCC 0,9360 | [reports/multiclass_v3.md](reports/multiclass_v3.md), ligne 40 |
| Multiclasse RF, test strict | Macro-F1 avec/sans Bot : 0,6699 / 0,7369; MCC 0,8888 | [reports/multiclass_v3.md](reports/multiclass_v3.md), ligne 39 |
| XGBoost P2, vendredi, labels d'origine | PR-AUC 0,75307; ROC-AUC 0,80540; TPR à FPR ≤ 1 % : 0,2848 | [reports/xgboost_p2.md](reports/xgboost_p2.md), ligne 19 |

Ces résultats sont ceux d'un banc de test CIC-IDS2017, avec labels d'origine
et split par segments; ils ne démontrent pas une généralisation à une
production réelle. Une seule configuration RF a été retenue et son seuil a
été calibré à FPR 1 % sur les plis hors-pli.

## Limites et points ouverts

- Les splits V3 contiennent des plis zéro-shot après purge; les métriques CV
  ne sont pas représentatives de toutes les classes
  ([rapport XGBoost V3](reports/xgboost_v3.md)).
- La contradiction des labels Bot affecte l'interprétation multiclasse
  ([rapport multiclasse](reports/multiclass_v3.md)).
- Le diagnostic de fuite ne suffit pas à prouver une fuite; proximité peut
  refléter un outil d'attaque partagé
  ([rapport V3](reports/leakage_report_v3.md)).
- Plusieurs valeurs brutes ont des anomalies ou sentinelles; ne pas en
  déduire une correction sans valider le protocole
  ([plausibilité](reports/plausibility_check.md), [audit scaler](reports/scaler_audit/resume_v3.md)).
- La normalisation standard reste le défaut; les 2 867 lignes retirées au
  nettoyage étaient porteuses d'inf/-inf, et ne sont pas toutes confirmées
  comme flux à durée nulle. Dans les données nettoyées, les 115 durées
  non-positives sont négatives et aucune n'est exactement nulle; la valeur de
  durée des lignes supprimées n'est plus disponible
  ([nettoyage](reports/cleaning_report.md), [plausibilité](reports/plausibility_check.md), lignes 18 et 51–72).
- Quatre indicateurs rares restent quasi constants (>99,97 % sur une seule
  valeur); la transformation log-z ne crée pas d'information pour eux
  ([plausibilité](reports/plausibility_check.md), lignes 42–47).
- V3 log-z est expérimental et ne remplace pas le défaut V3
  ([rapport log-z](reports/normalization_v3_logz.md)).
- Les résultats multiclasse sont provisoires, avec une seule configuration RF
  et sans recherche d'hyperparamètres dédiée.

## Guide par rôle

### M1 — graphe

- Lire les Parquet avec les fonctions de `src/data/access.py`.
- Conserver `flow_id` comme clé de correspondance des flux.
- Exclure les colonnes ID et cibles des nœuds/features du modèle.
- Charger le scaler correspondant exactement à V2, V3 ou V3 log-z.
- Vérifier l'ordre des features dans `models/features.json`.

### M2 — prédictions et métriques

- Respecter les six colonnes de `PREDICTION_COLUMNS`.
- Joindre vérités et meta par `flow_id`, jamais par position seule.
- Garder les seeds identifiables dans les métriques agrégées.
- Séparer test complet et test strict (`seen_in_train == False`).
- Documenter la version des labels et le seuil utilisé.

### M3 — features et démonstration

- Lire l'ordre canonique dans `models/features.json`.
- Choisir le scaler qui correspond au dossier de données chargé.
- Pour log-z, charger `models/scaler_v3_logz.joblib` avec joblib.
- Respecter le prétraitement/imputation appris sur le train.
- Ne pas traiter log-z comme le défaut du projet.

## Structure

```text
configs/              Configuration YAML du projet
data/raw/             Données sources (non versionnées)
data/interim/         Données intermédiaires (non versionnées)
data/processed/       Données préparées (non versionnées)
data/processed_v3/    Split V3 (non versionné)
data/processed_v3_logz/ Variante V3 log-z (non versionnée)
models/               Scalers, modèles et liste des features
predictions/          Parquets de prédictions (non versionnés)
src/data/             Chargement et préparation des données
src/graph/            Construction et traitement des graphes
src/models/           Modèles
src/eval/             Évaluation
src/explain/          Explicabilité
src/zeek/             Intégration Zeek
src/utils/            Utilitaires partagés
app/                  Application
tests/                Tests
reports/              Rapports générés
```

Les suffixes de sortie distinguent `_v3`, `_multi`, `_p2`, `_rf` et `_logz`.
La reprise est implémentée pour plusieurs expériences longues; les rapports
et CSV finaux existants peuvent toutefois empêcher une nouvelle exécution.

## Références (à vérifier avant citation)

- Probst, Wright et Boulesteix (2019), *Hyperparameters and Tuning Strategies for Random Forest*.
- Bergstra et Bengio (2012), *Random Search for Hyper-Parameter Optimization*.
- Chen et Guestrin (2016), *XGBoost: A Scalable Tree Boosting System*.
- Engelen et al. (2021), *Troubleshooting an Intrusion Detection Dataset: The CICIDS2017 Case Study*.
- Pekár, Plný et Hynek, arXiv:2601.04089 (2026), selon le guide du projet.
- Liu, Engelen et al. (CNS 2022), titre exact à vérifier; attribution employée dans [src/data/relabel.py](src/data/relabel.py), ligne 110.
- Lanvin et al. (CRiSIS 2022), titre exact à vérifier; attribution employée dans [src/data/relabel.py](src/data/relabel.py), lignes 110–111.
- Arp et al. (2022), *Dos and Don'ts of Machine Learning in Computer Security*.
- CIC-IDS2017 : Iman Sharafaldin, Arash Habibi Lashkari et Ali A. Ghorbani,
  “Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic
  Characterization”, citation reproduite de la
  [page dataset UNB](https://www.unb.ca/cic/datasets/ids-2017.html).

## Règles de travail

- Ne pas coder de chemin de données en dur : déclarer les chemins et paramètres dans `configs/*.yaml` et les charger depuis la configuration.
- Chaque membre travaille sur sa propre branche.
- Toute modification doit être proposée dans une pull request (PR) relue avant intégration.
