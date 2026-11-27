# Synthèse M4 — XGBoost CIC-IDS2017

## Protocole

- **Données et split.** V2 conserve le découpage historique. V3 ne change que la propriété des BENIGN : une fenêtre officielle d’attaque étendue de sa tolérance détermine les coupures; les flux d’attaque gardent leurs coupures par classe. V3 conserve 2 521 796 flux et en place 305 881 en gap; il utilise les mêmes 69 features. Sources : [split_v3.md](./split_v3.md), [xgboost_v3.md](./xgboost_v3.md).
- **Labels.** b0 apprend et évalue sur les labels d’origine. Les variantes v2a/v2b utilisent `label_v2_bin`; l’évaluation distingue les Attempted comptés comme attaques et les Attempted exclus. v2a entraîne sur toutes les lignes; v2b exclut les Attempted du train. `labels_v2_all.parquet` couvre les 2 827 677 flux audités; la construction V3 contient 25 264 flux absents de l’ancien fichier de labels. Les règles v2 proviennent de l’audit et ne sont pas une vérité terrain. Sources : [labels_v2.md](./labels_v2.md), [label_audit.md](./label_audit.md), [xgboost_v3.md](./xgboost_v3.md).
- **Modèle.** Recherche de 25 essais sur 3 plis; essai 24 retenu. Paramètres : `max_depth=11`, `min_child_weight=1.8671`, `subsample=0.5914`, `colsample_bytree=0.6938`, `lambda=0.03919`, `alpha=3.2945`; `gbtree`, `hist`, `eta=0.05`, 199 rounds fixes. Source : [best_bin.json](./xgboost/best_bin.json), [xgboost.yaml](../configs/xgboost.yaml).
- **Seuils et répétitions.** V2 : seuil OOF 0.478321. V3 : seuils OOF FPR≈1 % de 0.01539807 (b0), 0.01306097 (v2a), 0.00458237 (v2b). V3 et V2 principal : graines 42–51; P2/E5 : neuf plis, graine 42, seuil calibré sur les BENIGN de validation. Sources : [xgboost_report.md](./xgboost_report.md), [xgboost_v3.md](./xgboost_v3.md), [xgboost_p2.md](./xgboost_p2.md).

## Résultats à retenir

- **Référence V2, labels d’origine.** Sur 882 784 flux test : PR-AUC 0.9920±0.0004, TPR à FPR≤1 % de 0.9875±0.0001. Au seuil OOF, les FP moyens sont 1 377±1 284, médiane 550, avec une plage de 532 à 3 527. Source : [xgboost_report.md](./xgboost_report.md).
- **V3 b0, labels d’origine.** PR-AUC 0.9936±0.0004 et TPR à FPR≤1 % de 0.9881±0.0003; au seuil, 2 400±72 FP (min–max 2 313–2 547). Ce résultat n’est pas directement comparable à V2 : split différent. Source : [xgboost_v3.md](./xgboost_v3.md).
- **Sensibilité des labels en V3.** Avec les labels v2 et Attempted comptés, v2a atteint PR-AUC 0.9986±0.0001 et TPR à FPR≤1 % de 0.9967±0.0002; v2b atteint respectivement 0.9828±0.0013 et 0.9386±0.0033. En excluant les Attempted du test, les valeurs montent à 0.9996/0.9993 pour v2a et 0.9997/0.9994 pour v2b. À l’inverse, contre les labels d’origine, v2a/v2b produisent environ 41 421/40 751 FP au seuil. Ces écarts montrent la sensibilité à la cible et aux flux Attempted, pas une preuve indépendante de meilleure détection. Source : [xgboost_v3.md](./xgboost_v3.md).
- **P2 zéro-shot.** Les plis par jour/famille testent des classes absentes du train. Exemple : le rappel PortScan est 0.0058 en P2 Friday contre 0.9997 pour V3 b0 en distribution; pour Bot, P2 obtient 0.0046 contre 0 en V3 b0. Sur Thursday, la PR-AUC P2 passe de 0.01925 (labels d’origine, prévalence 0.4755 %) à 0.98216 (v2, prévalence 15.1645 %). La vérité de référence change fortement l’interprétation; plusieurs métriques des plis famille sur labels d’origine sont non définies faute de négatifs. Sources : [xgboost_p2.md](./xgboost_p2.md), [xgboost_v3.md](./xgboost_v3.md).
- **Interprétabilité.** Sur l’échantillon SHAP V3 b0 de 24 922 flux, les premières features globales par |SHAP| sont `Init_Win_bytes_forward`, `Bwd Packet Length Min` et `Init_Win_bytes_backward`; le contrôle TreeExplainer sur 200 lignes a un écart absolu max et moyen nul. Pour V2, les deux features de longueur minimale représentent 55.49 % du gain moyen. Les explications varient selon le modèle et la méthode. Sources : [xgboost_v3_shap.md](./xgboost_v3_shap.md), [xgboost_report.md](./xgboost_report.md).

## Limites

- Les règles d’audit sont heuristiques et ne remplacent pas une vérité terrain indépendante; aucune vérification PCAP n’est disponible. Certaines règles utilisent des caractéristiques liées aux variables d’entrée, ce qui peut rendre l’évaluation sur les labels v2 circulaire.
- CIC-IDS2017 est une capture de laboratoire. Les splits V2 et V3 diffèrent; V3 n’est pas le split par segments de classe décrit au §5.1 du guide.
- L’essai 24 a été sélectionné sur les plis V2; les résultats P2 sont zéro-shot pour plusieurs classes, mais les hyperparamètres ne sont pas indépendants de ces familles. P2 ne comporte qu’une graine.
- Le seuil fixe reste sensible à la graine en V2. Des classes ont de petits supports (p. ex. Infiltration et XSS dans le test); leurs recalls sont incertains.
- Les features corrélées peuvent se partager l’importance; SHAP décrit le modèle, sans démontrer de causalité ni de généralisation en production.

## Décisions à prendre en R3 (à quatre)

1. Quelle vérité de labels retenir pour les conclusions : labels d’origine, règles v2, et quel traitement des Attempted? Quelles règles doivent être vérifiées indépendamment?
2. Quel split (V2 ou V3) est le résultat principal à présenter, et quelle stratégie permet d’évaluer proprement la généralisation temporelle et les classes zéro-shot?
3. Quel compromis opérationnel FP/rappel et quelle méthode de calibration du seuil sont acceptables? Le seuil OOF proche de 1 % ne garantit pas ce FPR sur un test décalé.
4. Quelle variante poursuivre (b0, v2a ou v2b), et quelles validations indépendantes (PCAP, autre capture, étude de stabilité) sont requises avant toute conclusion de déploiement?

## Artefacts

- Rapports : [résultats V2](./xgboost_report.md), [V3](./xgboost_v3.md), [P2/E5](./xgboost_p2.md), [split V3](./split_v3.md), [labels v2](./labels_v2.md), [audit des labels](./label_audit.md), [SHAP](./xgboost_v3_shap.md).
- Données et modèles : `data/processed_v3/`, `data/processed/labels_v2_all.parquet`, `models/xgboost_v3/`, `models/xgboost_p2/`, `predictions/xgboost_v3/`, `predictions/xgboost_p2/`.
- Exports SHAP : [importance globale CSV](./xgboost_v3_shap_global.csv), [par classe CSV](./xgboost_v3_shap_by_class.csv), [sens de l’effet CSV](./xgboost_v3_shap_direction.csv), [comparaison gain/SHAP CSV](./xgboost_v3_shap_gain_comparison.csv), et [figures](./figures/).
- Code et tests : [runner P2](../src/models/xgb_p2.py), [runner SHAP](../src/models/xgb_shap.py), [tests P2](../tests/test_xgb_p2.py), [tests SHAP](../tests/test_xgb_shap.py).
