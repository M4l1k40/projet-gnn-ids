# Suggestion de durée de gap

- Mode de split : `count`.
- Gap actuel : 300 s (5 min).
- Marge appliquée pour la suggestion : 60 s (hypothèse de diagnostic, soit une minute supplémentaire).
- Suggestion globale conservatrice : 240 s (4.00 min).

| Jour | Durée max Flow Duration (s) | Résolution ts_end (s) | Gap actuel (s) | Marge (s) | Gap minimal suggéré (s) | Flux marqués gap |
|---|---:|---:|---:|---:|---:|---:|
| Friday | 119.999992 | 60 | 300 | 60 | 239.999992 | 47711 |
| Monday | 119.999985 | 1 | 300 | 60 | 180.999985 | 13642 |
| Thursday | 119.999992 | 60 | 300 | 60 | 239.999992 | 20946 |
| Tuesday | 119.999977 | 60 | 300 | 60 | 239.999977 | 8307 |
| Wednesday | 120.000000 | 60 | 300 | 60 | 240.000000 | 6091 |
