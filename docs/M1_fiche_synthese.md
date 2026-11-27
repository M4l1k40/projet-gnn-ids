# Fiche de synthèse M1 : E-GraphSAGE (Lo et al., IEEE/IFIP NOMS 2022)

*Source : arXiv:2103.16329v8. Tout ce qui suit sur l'article est tiré de sa lecture ; le code officiel des auteurs n'a pas été consulté.*

## 1. Problème et idée
Les NIDS classiques classent chaque flux isolément, ce qui rate les attaques distribuées (botnets, scans distribués, amplification DNS). Un flux est ici une **arête** (extrémités = nœuds, champs du flux = features d'arête). GraphSAGE ne classe que des **nœuds** à partir de features de **nœuds** ; E-GraphSAGE l'étend à la **classification d'arêtes**.

## 2. Algorithme (Algorithme 1, éq. 4 à 6)
| Étape | Contenu |
|---|---|
| Initialisation | `h⁰ᵥ = xᵥ = (1,…,1)`, de dimension égale au nombre de features d'arête (les nœuds n'ont pas de features) |
| Agrégation (couche k) | `hᵏ_N(v) = AGGₖ({eᵏ⁻¹_uv : u ∈ N(v), uv ∈ E})`, AGG = **moyenne** des features des **arêtes** voisines (éq. 6) |
| Mise à jour | `hᵏᵥ = σ(Wᵏ · CONCAT(hᵏ⁻¹ᵥ, hᵏ_N(v)))` |
| Embedding d'arête | `z_uv = CONCAT(z_u, z_v)` (éq. 5), soit **256 dimensions**, puis softmax |
| Hyperparamètres | K = 2, 128 unités, ReLU, dropout 0,2 entre les couches, entropie croisée, Adam (lr 0,001), voisinage **complet** (pas d'échantillonnage) |

**Graphe de l'article** : nœud = couple (IP, port) ; les IP sources sont remappées aléatoirement vers 172.16.0.1–172.31.0.1 pour qu'un petit nombre d'IP attaquantes ne serve pas de label implicite.

**Évaluation de l'article** : 4 jeux IoT (BoT-IoT, NF-BoT-IoT, ToN-IoT sous-échantillonné à 10 %, NF-ToN-IoT), **split aléatoire 70/30, une seule exécution, aucun intervalle de confiance**. F1 binaire de 0,97 à 1,00 ; F1 pondéré multiclasse de 0,63 (NF-ToN-IoT) à 1,00.

## 3. Points ambigus ou à vérifier dans l'article
1. **Exposant k−1 sur les features d'arête (éq. 4).** L'algorithme ne met jamais à jour `e_uv` d'une couche à l'autre. Lu littéralement, l'agrégation de la 2ᵉ couche redonne la même information qu'à la 1ʳᵉ et n'apporte pas de 2ᵉ saut, alors que l'article parle d'un voisinage à deux sauts. Non tranché sans le code des auteurs.
2. **Numéros de ligne incohérents.** Le texte situe `z_v = hᴷᵥ` à la « ligne 8 » et l'embedding d'arête à la « ligne 10 », alors que l'algorithme imprimé a `z_v` en ligne 6 et `z_uv` en ligne 8.
3. **Sens du voisinage** : `N(v)` n'est pas défini (flux entrants, sortants ou les deux).
4. **Split aléatoire 70/30** : des flux quasi identiques d'une même attaque se retrouvent des deux côtés, ce qui gonfle les scores. Notre protocole (split chronologique) donnera donc des scores plus bas, sans que ce soit une régression.
5. L'article cite **GNNExplainer comme travail futur** : il ne fournit aucune méthode d'explicabilité sur laquelle s'appuyer.

## 4. Nos écarts par rapport à l'article
| | Article | Ce projet |
|---|---|---|
| Nœud | (IP, port) | IP (noyau) ; (IP, port) en ablation E6 |
| Remappage des IP | Aléatoire vers 172.16.x.x | Permutation des identifiants de nœud (sans effet possible : features de nœud constantes, agrégation par moyenne) |
| Message | Lecture ambiguë (point 1) | `node_edge` (défaut) : `ReLU(W [hᵤ ; e_uv])` ; `edge_only` (lecture littérale) en ablation. Propagation dans les deux sens |
| Voisinage | Complet, graphe entier | Snapshots **causaux** (flux avec `ts_end` ≤ t), fenêtre 60 s, pas 15 s (fuite bornée à 15 s ; mesurée à 0,5 s) |
| Split | Aléatoire 70/30 | Chronologique par segment d'attaque (V2), gap 3 min |
| Perte / entraînement | Entropie croisée, 1 exécution | Entropie croisée pondérée, early stopping, 5 graines, snapshots mélangés |
| Métriques | Accuracy, F1, DR, FAR | + PR-AUC, ROC-AUC, **test strict**, résultats par attaque |

## 5. Ce que le projet en retient
L'idée d'un embedding d'arête `CONCAT(z_u, z_v)` appliquée à des flux, comme baseline de graphe face au Random Forest, avec un protocole sans fuite que l'article n'a pas. Résultats actuels, pour mémoire (5 graines, pas 15 s) : ROC-AUC du test strict 0,986 (écart-type 0,0015), PR-AUC 0,691 (0,016). Ces chiffres ne disent pas encore si le graphe apporte quelque chose : la comparaison avec le Random Forest de M4 sur le même test reste à faire.
