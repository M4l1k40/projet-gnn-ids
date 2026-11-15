# Guide des données

## 1. En 30 secondes

Le dépôt contient le pipeline et les rapports du jeu CIC-IDS2017 ; les Parquet et
les scalers sont des artefacts locaux, non versionnés. Instantané consulté le
2026-11-15, révision Git `55421ee` (avant les commits de documentation).

Le jeu nettoyé comprend 2 827 677 flux. Les splits finaux en conservent
2 550 253 : 1 515 755 pour train, 151 714 pour val et 882 784 pour test. Les
277 424 flux du gap sont exclus. `clean.parquet` occupe 335 172 882 octets ;
train, val et test occupent respectivement 161 253 873, 17 894 604 et
98 832 353 octets. Les effectifs viennent des métadonnées Parquet et de
[la fiche des données](../reports/data_card.md) ; les tailles viennent des
métadonnées des fichiers.

## 2. Obtenir les fichiers

Lien de téléchargement : [à compléter].

Les CSV sources se trouvent sous
[data/raw/GeneratedLabelledFlows/TrafficLabelling/](../data/raw/GeneratedLabelledFlows/TrafficLabelling/)
(huit fichiers locaux, non versionnés). Les artefacts sont placés ici :

| Fichier | Versionnement |
|---|---|
| [data/interim/clean_raw.parquet](../data/interim/clean_raw.parquet) | Non versionné |
| [data/interim/clean.parquet](../data/interim/clean.parquet) | Non versionné |
| [data/interim/clean_sample.parquet](../data/interim/clean_sample.parquet) | Non versionné |
| [data/processed/train.parquet](../data/processed/train.parquet) | Non versionné |
| [data/processed/val.parquet](../data/processed/val.parquet) | Non versionné |
| [data/processed/test.parquet](../data/processed/test.parquet) | Non versionné |
| [data/processed/meta.parquet](../data/processed/meta.parquet) | Non versionné |
| [data/processed/label_audit.parquet](../data/processed/label_audit.parquet) | Non versionné |
| [data/processed/redundancy_flags.parquet](../data/processed/redundancy_flags.parquet) | Non versionné |
| [data/processed/folds.parquet](../data/processed/folds.parquet) | Non versionné |
| [data/processed/p2_folds.parquet](../data/processed/p2_folds.parquet) | Non versionné |
| [models/features.json](../models/features.json) | Versionné |
| [models/scaler.joblib](../models/scaler.joblib) | Non versionné |
| [configs/classes.yaml](../configs/classes.yaml) | Versionné |

Les scalers P2 non versionnés sont sous [models/p2/](../models/p2/) :
[models/p2/day_Tuesday.joblib](../models/p2/day_Tuesday.joblib),
[models/p2/day_Wednesday.joblib](../models/p2/day_Wednesday.joblib),
[models/p2/day_Thursday.joblib](../models/p2/day_Thursday.joblib),
[models/p2/day_Friday.joblib](../models/p2/day_Friday.joblib),
[models/p2/family_bruteforce.joblib](../models/p2/family_bruteforce.joblib),
[models/p2/family_dos.joblib](../models/p2/family_dos.joblib),
[models/p2/family_web.joblib](../models/p2/family_web.joblib),
[models/p2/family_recon.joblib](../models/p2/family_recon.joblib) et
[models/p2/family_bot.joblib](../models/p2/family_bot.joblib).

### Obtenir les donn?es pr?tes ? l'emploi

Les donn?es ne sont pas versionn?es (`.gitignore`) et ne sont
partag?es nulle part : chacun les r?g?n?re ? partir du zip brut
CIC-IDS2017 (`GeneratedLabelledFlows.zip`). Les graines sont fixes (42),
donc les chiffres de contr?le doivent ?tre identiques chez tout le monde.

1. D?compresser le zip pour obtenir les 8 CSV dans
   `data/raw/GeneratedLabelledFlows/TrafficLabelling/`.
2. Depuis la racine du d?p?t (PowerShell), lancer dans cet ordre :

```powershell
python -m pip install -r requirements.txt
python -m src.data.build --force
python -m src.data.folds
python -m src.data.p2
python -m src.data.relabel
python -m src.data.redundancy
python -m src.data.verify_final
python -m pytest -q
```

`build` produit `clean_raw`, `clean`, `train`, `val`, `test`, `meta`,
`classes.yaml`, le scaler et le rapport de fuite. Les quatre commandes
suivantes produisent `folds.parquet`, `p2_folds.parquet` avec
`models/p2/*.joblib`, `label_audit.parquet` et `redundancy_flags.parquet`.
Dur?e de `build --force` : non mesur?e.

Chiffres de contr?le : 2 827 677 lignes dans `clean.parquet` ;
train 1 515 755, val 151 714, test 882 784 ; 277 424 flux en gap ;
200 648 vecteurs test identiques au train dans la m?me classe.

Les empreintes SHA-256 des Parquet ne sont pas compar?es : deux
r?g?n?rations peuvent diff?rer octet par octet sans diff?rer en contenu.
Les invariants de `verify_final` et de pytest font foi.


## 3. Carte des fichiers

Les comptes de lignes sont lus dans les métadonnées Parquet ; les tailles sont
les tailles exactes des fichiers en octets. Un tiret signifie que la notion de
lignes ne s'applique pas ou que le compte n'a pas été mesuré.

| Fichier | Lignes | Taille (octets) | Rôle | Versionné |
|---|---:|---:|---|---|
| [data/raw/GeneratedLabelledFlows/TrafficLabelling/](../data/raw/GeneratedLabelledFlows/TrafficLabelling/) | — | — | CSV bruts, huit fichiers | Non |
| [data/interim/clean_raw.parquet](../data/interim/clean_raw.parquet) | 2 827 677 | 339 080 436 | Sortie du nettoyage des CSV | Non |
| [data/interim/clean.parquet](../data/interim/clean.parquet) | 2 827 677 | 335 172 882 | Horodatages interprétés, entrée des splits et audits | Non |
| [data/interim/clean_sample.parquet](../data/interim/clean_sample.parquet) | 5 000 | 830 961 | Échantillon de développement | Non |
| [data/processed/train.parquet](../data/processed/train.parquet) | 1 515 755 | 161 253 873 | Entraînement | Non |
| [data/processed/val.parquet](../data/processed/val.parquet) | 151 714 | 17 894 604 | Validation | Non |
| [data/processed/test.parquet](../data/processed/test.parquet) | 882 784 | 98 832 353 | Test final | Non |
| [data/processed/meta.parquet](../data/processed/meta.parquet) | 2 550 253 | 40 051 907 | `orig_flow_id`, `source_file`, `seen_in_train` | Non |
| [data/processed/label_audit.parquet](../data/processed/label_audit.parquet) | 2 827 677 | 21 126 719 | Labels alternatifs d'audit, sans modifier les cibles | Non |
| [data/processed/redundancy_flags.parquet](../data/processed/redundancy_flags.parquet) | 2 550 253 | 19 936 512 | Indicateurs de redondance sur les splits conservés | Non |
| [data/processed/folds.parquet](../data/processed/folds.parquet) | 1 515 755 | 11 337 008 | Pli et indicateurs de purge CV, alignés sur train | Non |
| [data/processed/p2_folds.parquet](../data/processed/p2_folds.parquet) | 25 449 093 | 189 453 879 | Rôles des plis P2/E5, sans duplication des features | Non |
| [models/features.json](../models/features.json) | 69 noms | 1 551 | Liste ordonnée utilisée par le scaler | Oui |
| [models/scaler.joblib](../models/scaler.joblib) | — | 2 223 | Scaler final, ajusté sur train | Non |
| [models/p2/](../models/p2/) | neuf fichiers | 2 223 chacun | Un scaler pour chaque pli P2/E5 | Non |
| [configs/classes.yaml](../configs/classes.yaml) | — | — | Classes multiclasse, binary-only et rares | Oui |

Les rapports de référence sont versionnés : [cleaning_report.md](../reports/cleaning_report.md),
[timestamps_check.md](../reports/timestamps_check.md),
[normalization_report.md](../reports/normalization_report.md),
[data_card.md](../reports/data_card.md),
[leakage_report.md](../reports/leakage_report.md),
[label_audit.md](../reports/label_audit.md),
[redundancy_report.md](../reports/redundancy_report.md),
[cv_folds.md](../reports/cv_folds.md) et [p2_report.md](../reports/p2_report.md).

Vue des flux de données : `CSV bruts -> clean_raw -> clean -> train/val/test -> normalisation -> fuite/meta`.
L'audit des labels et les plis P2 partent de `clean`; la CV part de train.
Ces diagnostics sont des branches séparées : `build.py` n'enchaîne pas l'audit
des labels, la CV ni P2 après le diagnostic de fuite.

## 4. Schéma des colonnes

Le schéma est défini dans [schema.py](../src/data/schema.py). Les features sont
les colonnes listées dans [features.json](../models/features.json), pas une
liste parallèle codée dans le guide.

| Groupe | Colonnes et types |
|---|---|
| Identifiants (6) | `flow_id`: string ; `src_ip`, `dst_ip`: string ; `src_port`, `dst_port`: int32 ; `ts_end`: float64 (epoch en secondes) |
| Cibles (2) | `label_bin`: int8 ; `label_multi`: string |
| Méta (2) | `split`: catégorie (`train`, `val`, `test`) ; `day`: string |
| Features (69) | Les noms ordonnés de `features.json`, tous float32 après normalisation |

Dans le Parquet, `split` est stocké comme dictionnaire de chaînes, les IP et
labels comme chaînes, et `ts_end` comme double précision. `meta.parquet` porte
les métadonnées additionnelles de provenance et le drapeau de fuite ; elles ne
sont pas des features.

## 5. Démarrage en 5 minutes

L'exemple lit les splits l'un après l'autre, limite la lecture aux features et
aux deux cibles, puis prépare les vues binaire et multiclasse. Les classes
multiclasse viennent de la configuration générée.

```python
from src.data.access import feature_names, load_split, multiclass_classes

features = feature_names()
classes = set(multiclass_classes())

def matrices(split):
    frame = load_split(split, columns=[*features, "label_bin", "label_multi"])
    x_binary = frame.loc[:, features]
    y_binary = frame["label_bin"]
    keep = frame["label_multi"].isin(classes)
    x_multi = frame.loc[keep, features]
    y_multi = frame.loc[keep, "label_multi"]
    print(f"{split}: binaire X={x_binary.shape}, y={y_binary.shape}; multiclasse X={x_multi.shape}, y={y_multi.shape}")
    return x_binary, y_binary, x_multi, y_multi

for name in ("train", "val", "test"):
    matrices(name)
```

Pour un modèle, conserver les valeurs retournées dans `X` et `y` pour le split
voulu. `label_bin` sert à la cible binaire ; le masque multiclasse conserve
seulement les labels renvoyés par `multiclass_classes()`.

## 6. Quel jeu pour quel usage

| Je veux… | J'utilise… |
|---|---|
| Entraîner un modèle | `load_split("train")` et `feature_names()` |
| Régler les hyperparamètres par CV purgée | `get_cv_fold(k)` pour obtenir les positions train/validation dans l'ordre de `train.parquet` |
| Mesurer le résultat final | `load_split("test")`, une fois le modèle et ses seuils fixés sur train/validation |
| Évaluer sur le test strict | `strict_test_mask()` appliqué à test, pour garder `seen_in_train == False` |
| Comparer aux règles d'audit | `load_audit_labels(split)` ; les labels retournés ne remplacent pas `label_multi` |
| Faire une expérience E5 | `load_p2_fold("day_Tuesday")` ou le nom de famille, par exemple `family_dos` |
| Préparer une démo Zeek | `feature_names()` et `models/scaler.joblib` décrivent le contrat de features et le scaler ; l'adaptateur Zeek n'est pas fourni ici |

`load_meta()` lit les métadonnées. `strict_test_mask()` renvoie un masque booléen
aligné sur l'ordre des lignes de test ; il aligne par `flow_id`, sans supposer
que l'ordre de `meta.parquet` est le même. Voir [access.py](../src/data/access.py).

## 7. Règles anti-fuite

À faire :

- Utiliser exactement `feature_names()` et conserver leur ordre.
- Ajuster le scaler uniquement sur train ; pour P2/E5, utiliser le scaler du pli.
- Employer la CV purgée pour le réglage disponible dans le dépôt et réserver le
  test à la mesure finale.
- Utiliser le test strict comme analyse distincte : le drapeau signifie qu'aucun
  vecteur arrondi à six décimales de la même classe n'est trouvé dans train.
- Traiter `label_rule` comme une analyse de sensibilité, pas comme une correction
  des labels d'origine.

À ne pas faire :

- Ne pas réajuster le scaler sur val, test ou sur l'ensemble des splits.
- Ne pas utiliser test pour sélectionner un seuil ou un modèle.
- Ne pas ajouter `flow_id`, IP, ports, `ts_end`, labels ou méta aux features.
  `dst_port` (comme `src_port`) est une colonne d'identification, exclue des
  features.
- Ne pas réintroduire les flux du gap dans train/val/test : ils n'y figurent pas.
- Ne pas confondre `seen_in_train` toutes classes confondues avec le drapeau
  actuel, qui compare les vecteurs dans la même classe.

## 8. Chaque membre en 5 lignes

**M1**

1. Les champs réseau disponibles sont `flow_id`, `src_ip`, `dst_ip`, `src_port`,
   `dst_port`, `ts_end` et les features de `features.json`.
2. Pour un graphe à l'instant `t`, la contrainte causale à respecter est
   `ts_end <= t` ; ce filtrage n'est pas implémenté dans ce dépôt.
3. Les IP sont en clair dans les Parquet ; leur remappage appartient à la
   construction du graphe, pas au pipeline de données.
4. Les flux du gap sont absents des splits finaux ; ils ne sont pas disponibles
   par `load_split`.
5. Le répertoire [src/graph/](../src/graph/) ne contient pas de constructeur de
   graphe dans cette révision.

**M2**

1. Le format de prédiction déclaré est `PREDICTION_COLUMNS` dans
   [schema.py](../src/data/schema.py) : `flow_id`, `y_true`, `y_pred`, `score`,
   `recon_error`, `seed`.
2. La cible binaire est `label_bin` ; la vue multiclasse est filtrée par
   `multiclass_classes()`.
3. Les trois vues d'évaluation et le bootstrap par blocs temporels ne sont pas
   implémentés dans [src/eval/](../src/eval/).
4. `folds.parquet` contient l'affectation et les indicateurs de purge de la CV.
5. `get_cv_fold(k)` renvoie les positions train et validation, alignées sur
   l'ordre des lignes de `train.parquet`.

**M3**

1. `feature_names()` lit l'ordre canonique dans `models/features.json`.
2. `models/scaler.joblib` est ajusté uniquement sur train avec la méthode
   `standard`.
3. Une démo doit construire le vecteur dans le même ordre et ne pas inclure les
   IP, ports, `ts_end` ou labels.
4. Les expériences P2/E5 ont un scaler par pli sous `models/p2/`, distinct du
   scaler final.
5. Le répertoire [src/zeek/](../src/zeek/) ne contient pas d'adaptateur de
   prédiction Zeek dans cette révision.

**M4**

1. Le nettoyage lit les CSV de
   `data/raw/GeneratedLabelledFlows/TrafficLabelling/` et produit
   `data/interim/clean_raw.parquet`.
2. Les étapes de nettoyage, horodatage, split, normalisation et diagnostic de
   fuite sont orchestrées par [build.py](../src/data/build.py).
3. Les colonnes de `meta.parquet` conservent la provenance et le drapeau
   `seen_in_train` sans les ajouter aux features.
4. L'audit de labels, la redondance, la CV purgée et P2/E5 ont leurs rapports et
   modules dédiés ; l'audit ne réécrit pas les labels.
5. Les fonctions de lecture en lecture seule sont dans
   [access.py](../src/data/access.py).

## 9. Pièges connus

- Val ne contient aucun DDoS, DoS Hulk ni PortScan ; ces absences sont visibles
  dans [data_card.md](../reports/data_card.md).
- 19 699 des 20 046 flux PortScan de test (98,269 %) ont un vecteur identique
  dans train pour la même classe. Au total, 200 648 flux test (22,7290 %) sont
  concernés ; voir [leakage_report.md](../reports/leakage_report.md).
- L'audit trouve 364 551 différences textuelles (12,8922 %) entre labels
  d'origine et règles : BENIGN 108 063/2 271 122 (4,7581 %), Bot 1 956/1 956
  (100 %) et PortScan 158 804/158 804 (100 %). Ces écarts incluent casse et
  nomenclature ; ils ne sont pas à eux seuls une preuve d'erreur terrain.
  Détails dans [label_audit.md](../reports/label_audit.md).
- En E5, des attaques du test sont volontairement absentes du train du pli :
  c'est le cas évalué, non une fuite de données. Le détail est dans
  [p2_report.md](../reports/p2_report.md).
- V2 n'est pas chronologique globalement : ses frontières sont calculées par
  classe et par jour. Le corpus porte sur cinq jours ouvrés seulement.
- La résolution d'une minute concerne sept des huit fichiers ; 115 flux de
  durée nulle ou négative sont conservés. Les limites sont détaillées dans
  [data_card.md](../reports/data_card.md).

## 10. Décisions ouvertes à signer à quatre (R3)

Les paramètres sont ceux actuellement présents dans
[data.yaml](../configs/data.yaml) ; la liste ci-dessous est à signer, pas une
nouvelle recommandation :

- [ ] Variante V2 (`segment`).
- [ ] Gap de 3 minutes.
- [ ] Seuil multiclasse de 50 flux par split.
- [ ] Validation croisée purgée plutôt que validation uniquement.
- [ ] `dst_port` exclu des features.
- [ ] Flux du gap absents des splits finaux.
- [ ] Usage du test strict (`seen_in_train == False`) comme analyse distincte.
- [ ] Usage des labels audités comme analyse de sensibilité, sans remplacement
      des labels d'origine.

## 11. Régénérer

Depuis la racine du dépôt sous PowerShell :

```powershell
python -m src.data.build
```

Le pipeline suit l'ordre clean → timestamps → split final → classes →
normalisation → fuite. Il ignore une étape uniquement si toutes ses sorties
existent ; des sorties partielles provoquent une erreur. `--force` réécrit les
sorties des étapes, y compris les Parquet : ne l'utiliser qu'en sachant que les
artefacts locaux seront remplacés. La commande ci-dessus a été exécutée pour ce
guide ; les étapes étaient déjà produites et ont été ignorées. La durée et la
RAM d'une génération complète ne sont pas mesurées dans les rapports ni dans le
code consultés.

## 12. Dépannage : 6 erreurs fréquentes

| Symptôme | Cause probable et solution |
|---|---|
| `ModuleNotFoundError: No module named 'src'` | Le terminal n'est pas à la racine du dépôt. Revenir au dossier qui contient `src/` et `configs/`. |
| `FileNotFoundError` sur un Parquet | Les artefacts ne sont pas versionnés. R?g?n?rer les donn?es (section 2), puis vérifier leur emplacement. |
| Mémoire insuffisante au chargement | Ne pas charger des colonnes inutiles : passer `columns=feature_names()` et lire un split à la fois avec `load_split`. |
| Chemin Windows introuvable sous WSL, ou inversement | Utiliser le chemin du système courant ; sous WSL, le lecteur Windows apparaît sous `/mnt/` suivi de sa lettre. |
| `KeyError` sur une feature ou un label | Lire les features via `feature_names()` et les classes via `multiclass_classes()` plutôt que de recopier les noms. |
| Masque strict absent ou non aligné | Vérifier que `meta.parquet` contient `seen_in_train` et utiliser `strict_test_mask()`, qui aligne le drapeau par `flow_id`. |

**Provenance des chiffres du guide.** Les effectifs et tailles des fichiers du
tableau ont été lus dans les métadonnées Parquet et les métadonnées de fichiers.
Les colonnes et types viennent de [schema.py](../src/data/schema.py) et du
schéma Parquet ; les 69 features viennent de
[features.json](../models/features.json). Les paramètres de split, gap,
seuils, graines, normalisation, échantillonnage et CV viennent de
[data.yaml](../configs/data.yaml). Les effectifs, limites, résolution et jours
viennent de [data_card.md](../reports/data_card.md) et
[timestamps_check.md](../reports/timestamps_check.md) ; fuite et test strict
de [leakage_report.md](../reports/leakage_report.md) ; écarts d'audit de
[label_audit.md](../reports/label_audit.md) ; plis et classes absentes de
[cv_folds.md](../reports/cv_folds.md) et [p2_report.md](../reports/p2_report.md).
La date et la révision Git sont celles de la commande `Get-Date` et de
`git rev-parse --short HEAD` au moment de la lecture.
