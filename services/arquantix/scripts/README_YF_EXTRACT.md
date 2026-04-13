# Yahoo Finance Data Extractor

Script Python autonome pour extraire des données historiques de Yahoo Finance avec dividendes et splits.

## Installation

```bash
# Installer les dépendances
cd api
pip install -r requirements.txt
```

Les dépendances requises sont :
- `yfinance` : Bibliothèque Python pour accéder aux données Yahoo Finance
- `pandas` : Manipulation de données
- `numpy` : Calculs numériques (dépendance de pandas)

## Usage

### Extraction basique

```bash
python scripts/yf_extract.py --ticker AAPL --start 2025-01-01 --end 2026-01-09
```

### Avec options personnalisées

```bash
python scripts/yf_extract.py \
  --ticker MSFT \
  --start 2024-01-01 \
  --end 2026-01-09 \
  --interval 1d \
  --out_dir ./exports
```

### Paramètres

- `--ticker` (requis) : Symbole du ticker (ex: `AAPL`, `MSFT`, `BTC-USD`)
- `--start` (requis) : Date de début au format `YYYY-MM-DD`
- `--end` (requis) : Date de fin au format `YYYY-MM-DD`
- `--interval` (optionnel) : Intervalle des données (`1d`, `1wk`, `1mo`). Par défaut: `1d`
- `--out_dir` (optionnel) : Répertoire de sortie. Par défaut: `./data`

## Fichiers générés

Pour chaque ticker, le script génère 3 fichiers CSV dans le répertoire de sortie :

### 1. `<ticker>_prices.csv`

Données de prix quotidiennes :
- `date` : Date (YYYY-MM-DD)
- `open` : Prix d'ouverture
- `high` : Prix maximum
- `low` : Prix minimum
- `close` : Prix de clôture
- `adj_close` : Prix de clôture ajusté (dividendes et splits inclus)
- `volume` : Volume échangé

### 2. `<ticker>_actions.csv`

Événements corporatifs :
- `date` : Date de l'événement
- `type` : Type d'événement (`dividend` ou `split`)
- `value` : Montant du dividende ou ratio de split

### 3. `<ticker>_merged.csv`

Données fusionnées avec calculs :
- Toutes les colonnes de `prices.csv`
- `dividend` : Montant du dividende (0 si aucun)
- `split_factor` : Facteur de split (1 si aucun)
- `daily_return_close` : Rendement quotidien basé sur `close`
- `daily_return_total` : Rendement quotidien total basé sur `adj_close` (inclut dividendes)

## Exemples

### Actions US (AAPL)

```bash
python scripts/yf_extract.py --ticker AAPL --start 2020-01-01 --end 2026-01-09
```

Génère :
- `data/AAPL_prices.csv`
- `data/AAPL_actions.csv` (dividendes + splits)
- `data/AAPL_merged.csv`

### Crypto (BTC-USD)

```bash
python scripts/yf_extract.py --ticker BTC-USD --start 2024-01-01 --end 2026-01-09
```

### ETF (SPY)

```bash
python scripts/yf_extract.py --ticker SPY --start 2020-01-01 --end 2026-01-09 --out_dir ./exports
```

## Test

Un script de test est fourni pour valider l'extraction :

```bash
python scripts/yf_smoke_test.py
```

Le test :
1. Extrait les données pour AAPL sur 30 jours
2. Vérifie que les 3 fichiers CSV sont créés
3. Vérifie que chaque fichier contient au moins 10 lignes
4. Vérifie que les colonnes requises sont présentes

## Gestion d'erreurs

Le script inclut :
- **Retry automatique** : 3 tentatives en cas d'erreur réseau
- **Validation des dates** : Vérifie que start < end
- **Validation des colonnes** : Vérifie que toutes les colonnes requises sont présentes
- **Détection de doublons** : Supprime automatiquement les dates en double
- **Messages d'erreur clairs** : Exit code != 0 en cas d'échec

## Notes techniques

- Le script utilise la bibliothèque `yfinance` qui accède aux API publiques de Yahoo Finance
- Les données sont récupérées avec `auto_adjust=False` pour obtenir à la fois `close` et `adj_close`
- Les dividendes et splits sont récupérés séparément et fusionnés avec les prix
- Le calcul de `daily_return_total` utilise `adj_close` qui inclut déjà les ajustements pour dividendes et splits

## Limitations

- Yahoo Finance peut limiter le nombre de requêtes (rate limiting)
- Certains tickers peuvent ne pas avoir de données historiques disponibles
- Les données peuvent avoir des délais (15-20 minutes pour les données intraday)

