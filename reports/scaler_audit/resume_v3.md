# Audit du scaler V3 et simulations en mémoire

- Train brut V3 : `data/interim/clean.parquet` filtré par les flow_id du train V3, 1 649 128 lignes, 69 features. Aucun scaler ni Parquet modifié.
- Audit courant : mean_/scale_ du scaler V3; std central = std(ddof=0) du z entre p1 et p99; hors-norme = valeur brute > 1 000 x p99.
- B : les négatifs des en-têtes, min_seg_size_forward, durées/IAT et rates sont imputés par la médiane des valeurs non négatives; signed_log1p puis standardisation train.
- C : RobustScaler train (médiane/IQR; échelle 1 si IQR nul), clip [-10,10]. Spearman sur 200 000 flux, échantillon sans remise, graine 42.

## Audit courant
- std central < 0,3 : 23 features; 5 avec négatifs invalides, 9 avec queue > 1 000 x p99, 9 structurelles/rares.
- Les causes par feature et les 69 lignes d’audit sont dans `feature_audit_v3.csv`. Pour les indicateurs binaires avec p99=0, le seuil 1 000 x p99 est dégénéré.

## Simulations
- B : 65/69 dans [0,3; 1,5], 4 sous 0,3, 0 au-dessus; 69/69 ont moins de 1 % des flux avec |z|>10 (max 0.0672 %).
- C : 11/69 dans [0,3; 1,5], 8 sous 0,3, 50 au-dessus; 69/69 ont moins de 1 % avec |z|>10 (clip : part nulle au-dessus de 10).
- En-têtes, durées/IAT et rates (n=22) : B satisfait le spread pour 22/22; Spearman exactement 1 pour 13/22 (min 0.998575).
- C satisfait le spread pour 2/22; Spearman exactement 1 pour 1/22 (min 0.992540); les deux méthodes ont <1 % de flux hors |z|=10 sur ces features.
- Aucune ne satisfait strictement les trois critères pour toutes les features concernées. B est la plus proche; l’imputation change les rangs, alors que C crée des ex-aequo par clipping et une dispersion centrale souvent >1,5.
- Proposition sans application : retenir B comme candidat pour les mesures continues; traiter les indicateurs rares séparément. Si Spearman=1 est absolu, ne retenir aucune des deux en l’état.
- Détails B/C par feature : `simulation_B_C_v3.csv`.

## Fwd Header Length négatif - recomptage de clean.parquet
- Total 35 : Monday 23, Tuesday 11, Wednesday 1, Friday 0; les 23 sont Monday, toutes BENIGN. L’attribution précédente à Friday était erronée.
- Ventilation par jour/classe : `anomalies_fwd_header_v3.csv`.

Aucune transformation appliquée; simulations uniquement en mémoire. Sorties dans `reports/scaler_audit/`.
