# Script de Chargement des Données Marchés D1

## Vue d'ensemble

Ce script permet de charger et maintenir les données historiques quotidiennes (D1) pour tous les instruments actifs depuis Yahoo Finance.

## Utilisation

### Vérifier la couverture des données

```bash
python3 api/scripts/load_market_data.py --check-only
```

Affiche un rapport de couverture pour tous les instruments actifs, indiquant :
- Le nombre de barres disponibles
- La plage de dates couverte
- Le statut (✓ COMPLETE, ⚠️ OUTDATED, ❌ NO DATA)

### Charger/mettre à jour les données

```bash
# Mettre à jour les données récentes (derniers 120 jours) pour tous les instruments
python3 api/scripts/load_market_data.py --update-recent

# Charger toutes les données pour un instrument spécifique
python3 api/scripts/load_market_data.py --instrument-id <ID>

# Charger toutes les données pour tous les instruments (peut être long)
python3 api/scripts/load_market_data.py --all

# Forcer un rechargement complet (ignore les données existantes)
python3 api/scripts/load_market_data.py --all --force-full
```

## Architecture

### Client Yahoo Finance

Le client `YahooFinanceClient` (`api/services/market_data/yahoo_client.py`) :
- Utilise la bibliothèque `yfinance` pour récupérer les données
- Gère automatiquement le format des symboles (BTC-USD pour crypto, ^GSPC pour indices, etc.)
- Supporte différents types d'actifs (crypto, ETF, equity, forex, index, commodities)

### Script de chargement

Le script `load_market_data.py` :
- Vérifie la couverture des données existantes
- Charge les données manquantes depuis Yahoo Finance
- Met à jour les données existantes si nécessaire
- Gère les erreurs et affiche un rapport détaillé

## Données existantes

D'après l'analyse actuelle :
- **102,707 barres** en base de données
- **17/18 instruments** ont des données complètes et à jour
- Seul **URTH (ETF)** n'a pas de données

### Source des données

Les données proviennent principalement de **Yahoo Finance** (source: "yahoo"), avec quelques données historiques d'Alpha Vantage (source: "alphavantage") qui sont progressivement remplacées.

## Notes importantes

1. **Rate limiting** : Yahoo Finance n'impose pas de limite stricte, mais il est recommandé de ne pas faire trop de requêtes simultanées.

2. **Symboles** : Le client gère automatiquement le format des symboles :
   - Crypto : `BTC-USD`, `ETH-USD`, etc.
   - ETFs : `QQQ`, `URTH`, etc.
   - Indices : `^GSPC` (S&P 500), `^DJI` (Dow Jones), etc.

3. **Mise à jour quotidienne** : Pour maintenir les données à jour, exécuter `--update-recent` quotidiennement (via cron par exemple).

## Exemples

### Exemple 1 : Vérifier la situation actuelle

```bash
python3 api/scripts/load_market_data.py --check-only
```

### Exemple 2 : Mettre à jour les données récentes

```bash
python3 api/scripts/load_market_data.py --update-recent
```

### Exemple 3 : Charger les données pour URTH (ETF manquant)

```bash
# Trouver l'ID de URTH
python3 -c "from api.database import SessionLocal, MarketDataInstrument; db = SessionLocal(); urth = db.query(MarketDataInstrument).filter(MarketDataInstrument.symbol == 'URTH').first(); print(f'URTH ID: {urth.id}'); db.close()"

# Charger les données
python3 api/scripts/load_market_data.py --instrument-id <ID>
```

