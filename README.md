# projet-gnn-ids

Projet de détection d'intrusions réseau par graphes de neurones.

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

## Structure

```text
configs/              Configuration YAML du projet
data/raw/             Données sources (non versionnées)
data/interim/         Données intermédiaires (non versionnées)
data/processed/       Données préparées (non versionnées)
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

## Règles de travail

- Ne pas coder de chemin de données en dur : déclarer les chemins et paramètres dans `configs/*.yaml` et les charger depuis la configuration.
- Chaque membre travaille sur sa propre branche.
- Toute modification doit être proposée dans une pull request (PR) relue avant intégration.
