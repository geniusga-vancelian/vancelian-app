# Checklist Migration - Utilisation des Données Historiques dans les Backtests

## ✅ État Actuel

1. **Tables en base** : ✓ Les tables `market_data_bars_d1` et `market_data_instruments` existent déjà
   - **102,707 barres** historiques D1 disponibles
   - **18 instruments actifs** avec données

2. **Code implémenté** :
   - ✓ `repository.py` : Fonctions `load_instruments()` et `load_open_bars()` implémentées
   - ✓ `yahoo_client.py` : Client Yahoo Finance créé
   - ⚠️ `engine.py` : Fonctions du moteur de backtest sont encore des stubs (à implémenter)

3. **Dépendances** :
   - ✓ `pandas==2.2.0` ajouté à `requirements.txt`
   - ✓ `yfinance==0.2.40` ajouté à `requirements.txt`

## 🔄 Actions Nécessaires

### 1. Redémarrer le serveur API (REQUIS)

**Pourquoi ?** Pour charger les nouvelles dépendances (pandas, yfinance) qui ont été ajoutées à `requirements.txt`.

```bash
# Arrêter l'API actuelle
pkill -f "uvicorn main:app"

# Si vous utilisez Docker, redémarrer le conteneur
docker compose restart arquantix-api

# Ou si en local, réinstaller les dépendances puis redémarrer
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Installer les dépendances si nécessaire

Si les dépendances ne sont pas installées dans l'environnement Python de l'API :

```bash
cd api
pip install pandas==2.2.0 yfinance==0.2.40
```

### 3. Vérifier que tout fonctionne

```bash
# Tester l'import du repository
cd api
python3 -c "from services.backtest.repository import load_open_bars, load_instruments; print('✓ OK')"

# Vérifier que les données sont accessibles
python3 -c "
from database import SessionLocal, MarketDataBarD1
from datetime import date, timedelta
db = SessionLocal()
bars_count = db.query(MarketDataBarD1).count()
print(f'✓ {bars_count:,} barres disponibles en base')
db.close()
"
```

## ❌ Migrations NON nécessaires

**Pas besoin de créer de migrations Alembic** car :
- Les tables `market_data_bars_d1` et `market_data_instruments` existent déjà
- Le schéma est correct (défini dans `database.py`)
- Les données sont déjà présentes en base

## ⚠️ Note Importante

Le backtest engine (`engine.py`) contient encore des **stubs** (implémentations vides). Les fonctions `load_open_bars()` et `load_instruments()` du repository sont implémentées, mais elles ne sont pas encore utilisées car :

1. L'endpoint `/api/backtests/run` crée simplement un `BacktestRun` avec status "PENDING"
2. Il y a un TODO pour implémenter l'exécution asynchrone du backtest
3. Le moteur de backtest (`engine.py`) doit être implémenté pour utiliser ces données

**Pour que les backtests utilisent réellement les données historiques**, il faudra :
- Implémenter les fonctions du moteur de backtest (`engine.py`)
- Créer un worker/task queue pour exécuter les backtests de manière asynchrone
- Connecter le moteur de backtest au repository pour charger les données

## 🎯 Résumé

- ✅ **Migrations** : Non nécessaires (tables existent déjà)
- ✅ **Redémarrage API** : Oui, pour charger pandas et yfinance
- ✅ **Installation dépendances** : Oui, si pas déjà fait
- ⚠️ **Implémentation engine** : Encore à faire (stubs actuels)


