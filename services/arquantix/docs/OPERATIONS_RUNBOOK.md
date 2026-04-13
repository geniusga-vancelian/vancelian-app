# Operations Runbook — Market Data & Backtest

## Guide pratique pour reprendre le projet

Ce document fournit les commandes et procédures pour démarrer, vérifier et utiliser les modules Market Data et Backtest.

---

## Prérequis

### Variables d'environnement

**Backend** (`api/.env.local`) :
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/arquantix_quant
ALPHAVANTAGE_API_KEY=your_api_key_here
MARKET_DATA_PROVIDER=alphavantage
JWT_SECRET_KEY=super-secret-dev-key
ENV=local
DEBUG=true
```

**Frontend** (`web/.env.local`) :
```bash
JWT_SECRET_KEY=super-secret-dev-key
AUTH_SECRET=super-secret-dev-key
```

---

## Démarrer les serveurs

### Backend (FastAPI)

**Commande** :
```bash
cd api
python3 -m uvicorn main:app --reload --port 8000
```

**Vérification** :
```bash
curl http://localhost:8000/health
# Devrait retourner: {"status":"ok","service":"arquantix-api"}
```

**Logs** : Vérifier que `DATABASE_URL` est chargé correctement (nom DB affiché).

---

### Frontend (Next.js)

**Commande** :
```bash
cd web
npm run dev
```

**Vérification** :
- Ouvrir `http://localhost:3000/admin/backtests`
- Devrait afficher la page (avec auth requise)

---

## Vérifier la base de données

### Nom de la base

**Backend** : Vérifier logs au démarrage :
```
[database.py] Database name: arquantix_quant
```

**Ou via script** :
```bash
cd api
python3 -c "from database import DATABASE_URL; from urllib.parse import urlparse; print(urlparse(DATABASE_URL).path[1:])"
```

---

### Tables existantes

**Via psql** :
```bash
psql $DATABASE_URL -c "\dt public.*"
```

**Tables attendues** :
- `market_data_instruments`
- `market_data_bars_d1`
- `backtest_runs`
- `backtest_portfolio_series`
- `backtest_instrument_series`
- `backtest_metrics`

---

### Appliquer migrations Alembic

**Si tables manquantes** :
```bash
cd api
alembic upgrade head
```

**Vérifier révision** :
```bash
cd api
python3 scripts/alembic_state_inspect.py
```

---

## Lancer les diagnostics

### Via UI

1. Ouvrir `http://localhost:3000/admin/diagnostics`
2. Click "Run Quick Diagnostic"
3. Vérifier rapport JSON (6 checks : PASS/FAIL)

---

### Via API (curl)

**Quick diagnostic** :
```bash
curl -X POST http://localhost:3000/api/diagnostics/market-backtest/run \
  -H "Content-Type: application/json" \
  -d '{"mode":"quick"}' \
  --cookie "authjs.session-token=your_session_cookie"
```

**Note** : Requiert session cookie (login via UI d'abord).

---

### Checks diagnostics

1. **Router Availability** : Vérifie que routers sont importables
2. **Instruments Exist** : Vérifie instruments existent, seed si nécessaire
3. **Bars Existence** : Vérifie bars D1 existent
4. **Quick Backfill** : Backfill 120 jours pour 1 crypto + 1 tradfi
5. **Backtest Run Minimal** : Exécute backtest minimal (BTC+SPY, equal_weight, weekly)
6. **API/Proxy Verification** : Vérifie endpoints répondent

**Tous checks doivent être PASS** pour système opérationnel.

---

## Backfill Market Data

### Seed instruments CORE_V1

**Via UI** :
1. `/admin/backtests` → Market Data panel
2. (Automatique si diagnostic détecte 0 instruments)

**Via API** :
```bash
curl -X POST http://localhost:3000/api/market-data/seed \
  -H "Content-Type: application/json" \
  -d '{"universe":"CORE_V1"}' \
  --cookie "authjs.session-token=your_session_cookie"
```

**Résultat** : 7 instruments créés/activés (BTC, ETH, SOL, URTH, QQQ, DIA, GLD).

---

### Valider Alpha Vantage

**Via UI** :
1. `/admin/backtests` → Market Data panel
2. Click "Validate Alpha Vantage (7 assets)"
3. Vérifier tableau : tous symboles doivent être OK

**Via API** :
```bash
curl -X POST http://localhost:3000/api/market-data/validate-provider \
  -H "Content-Type: application/json" \
  -d '{"symbols":["BTC","ETH","SOL","URTH","QQQ","DIA","GLD"],"years":10}' \
  --cookie "authjs.session-token=your_session_cookie"
```

**Résultat** : `{ total: 7, passed: 7, failed: 0, results: [...] }`

---

### Backfill instruments manquants

**Via UI** :
1. `/admin/backtests` → Market Data panel
2. Sélectionner jours (90/180/365/730)
3. Click "Backfill Missing (365d)"
4. Attendre completion (progress bar + liste instruments)

**Via API** :
```bash
curl -X POST http://localhost:3000/api/market-data/backfill-missing \
  -H "Content-Type: application/json" \
  -d '{"days":365,"symbols":["BTC","ETH","SOL","URTH","QQQ","DIA","GLD"],"force":false}' \
  --cookie "authjs.session-token=your_session_cookie"
```

**Résultat** : `{ total_bars_added: 2555, missing_after: 0, ... }`

**Durée** : ~2-5 minutes pour 7 instruments (rate limit 4 calls/min).

---

### Vérifier bars insérés

**Via psql** :
```bash
psql $DATABASE_URL -c "
SELECT i.symbol, COUNT(b.instrument_id) as bars_count, 
       MIN(b.date) as min_date, MAX(b.date) as max_date
FROM market_data_instruments i
LEFT JOIN market_data_bars_d1 b ON i.id = b.instrument_id
WHERE i.is_active = 'true'
GROUP BY i.id, i.symbol
ORDER BY i.symbol;
"
```

**Résultat attendu** : Chaque instrument actif doit avoir `bars_count > 0`.

---

## Lancer un backtest

### Via UI

1. `/admin/backtests` → Backtest Builder
2. Sélectionner instruments (multi-select)
3. Dates : `start_date`, `end_date`
4. Strategy : `equal_weight` ou `momentum` (avec `lookback_days` si momentum)
5. Rebalance : `daily`, `weekly`, `monthly`
6. Costs : `fees_bps`, `slippage_bps`
7. Weekend Trading : checkbox
8. Click "Run Backtest"
9. Attendre completion (loading)
10. Résultats affichés dans panel Results (Chart, Stats, Weights)

---

### Via API

**Exemple** :
```bash
curl -X POST http://localhost:3000/api/backtests/run \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2023-01-01",
    "end_date": "2023-12-31",
    "instrument_ids": [1, 2],
    "strategy": {
      "type": "equal_weight",
      "params": null
    },
    "rebalance": "weekly",
    "fees_bps": 0.0,
    "slippage_bps": 0.0,
    "allow_weekend_trading": true
  }' \
  --cookie "authjs.session-token=your_session_cookie"
```

**Résultat** : `{ run_id: 1, status: "SUCCESS", metrics: {...}, ... }`

---

### Récupérer résultats

**Detail** :
```bash
curl http://localhost:3000/api/backtests/1 \
  --cookie "authjs.session-token=your_session_cookie"
```

**Series** :
```bash
curl http://localhost:3000/api/backtests/1/series \
  --cookie "authjs.session-token=your_session_cookie"
```

---

## Voir historiques (sans backtest)

### Via UI

1. `/admin/backtests` → Backtest Builder
2. Sélectionner instruments
3. Dates : `start_date`, `end_date`
4. Click "Voir historiques"
5. Graphique base100 affiché (une ligne par instrument)

---

### Via API

```bash
curl "http://localhost:3000/api/market-data/performance?instrument_ids=1,2&start=2023-01-01&end=2023-12-31&base=100" \
  --cookie "authjs.session-token=your_session_cookie"
```

**Résultat** : `{ start, end, base, instruments: [{ instrument_id, symbol, series, stats }] }`

---

## Déboguer un échec

### Backfill échoue

**Symptômes** :
- `status="error"` dans réponse backfill
- `bars_added=0`

**Vérifications** :

1. **Alpha Vantage API key** :
   ```bash
   echo $ALPHAVANTAGE_API_KEY
   ```

2. **Rate limit** :
   - Vérifier logs backend : "Alpha Vantage rate limit"
   - Attendre 1 minute, relancer

3. **Symbole invalide** :
   - Valider avec `POST /api/market-data/validate-provider`
   - Vérifier `provider_symbol` dans DB

4. **Date range** :
   - Vérifier que date range contient des données
   - Alpha Vantage peut ne pas avoir données récentes pour certains symboles

**Solution** :
- Valider symboles d'abord
- Réduire `days` si nécessaire
- Vérifier logs backend pour erreur exacte

---

### Backtest échoue

**Symptômes** :
- `status="FAILED"` dans réponse
- `error_message` présent

**Vérifications** :

1. **Bars manquants** :
   ```bash
   psql $DATABASE_URL -c "
   SELECT i.symbol, COUNT(b.instrument_id) as bars_count
   FROM market_data_instruments i
   LEFT JOIN market_data_bars_d1 b ON i.id = b.instrument_id
   WHERE i.id IN (1, 2)
   GROUP BY i.id, i.symbol;
   "
   ```

2. **Date range** :
   - Vérifier que `effective_start_date` et `effective_end_date` sont définis
   - Vérifier intersection dates disponibles

3. **Logs backend** :
   - Vérifier logs FastAPI pour stack trace
   - Erreur pandas/numpy souvent liée à données manquantes

**Solution** :
- Backfill instruments manquants
- Ajuster date range si nécessaire
- Vérifier logs backend pour erreur exacte

---

### 401 Unauthorized

**Symptômes** :
- Tous appels API retournent `401 Unauthorized`

**Vérifications** :

1. **Session cookie** :
   - Ouvrir DevTools → Application → Cookies
   - Vérifier présence `authjs.session-token`

2. **JWT secret** :
   - Backend : `JWT_SECRET_KEY` dans `api/.env.local`
   - Frontend : `JWT_SECRET_KEY` ou `AUTH_SECRET` dans `web/.env.local`
   - Doivent être identiques

3. **Auth probe** :
   - `/admin/diagnostics` → "Auth Probe"
   - Vérifier `session_found=true`, `jwt_generated=true`

**Solution** :
- Se reconnecter via `/admin/login`
- Vérifier `JWT_SECRET_KEY` identique backend/frontend
- Vérifier logs backend pour erreur JWT decode

---

### Diagnostic échoue

**Symptômes** :
- Checks diagnostics retournent FAIL

**Vérifications** :

1. **Router availability** :
   - Vérifier que `api/services/market_data/routes.py` et `api/services/backtest/routes.py` sont importables
   - Vérifier que routers sont inclus dans `api/main.py`

2. **Instruments exist** :
   - Vérifier DB : `SELECT COUNT(*) FROM market_data_instruments WHERE is_active = 'true';`
   - Si 0 : seed CORE_V1

3. **Bars existence** :
   - Vérifier DB : `SELECT COUNT(*) FROM market_data_bars_d1;`
   - Si 0 : backfill missing

4. **Backtest run minimal** :
   - Vérifier logs backend pour erreur exacte
   - Souvent lié à bars manquants ou date range invalide

**Solution** :
- Suivre checks dans ordre (1→6)
- Résoudre chaque check avant de passer au suivant

---

## Commandes utiles

### Vérifier DB utilisée

```bash
cd api
python3 -c "
from database import DATABASE_URL
from urllib.parse import urlparse
print('DB:', urlparse(DATABASE_URL).path[1:])
"
```

---

### Compter instruments actifs

```bash
psql $DATABASE_URL -c "SELECT COUNT(*) FROM market_data_instruments WHERE is_active = 'true';"
```

---

### Compter bars par instrument

```bash
psql $DATABASE_URL -c "
SELECT i.symbol, COUNT(b.instrument_id) as bars_count
FROM market_data_instruments i
LEFT JOIN market_data_bars_d1 b ON i.id = b.instrument_id
WHERE i.is_active = 'true'
GROUP BY i.id, i.symbol;
"
```

---

### Lister backtest runs

```bash
psql $DATABASE_URL -c "
SELECT id, name, status, created_at, start_date, end_date
FROM backtest_runs
ORDER BY created_at DESC
LIMIT 10;
"
```

---

### Vérifier métriques portfolio

```bash
psql $DATABASE_URL -c "
SELECT key, value
FROM backtest_metrics
WHERE run_id = 1 AND scope = 'portfolio' AND instrument_id IS NULL;
"
```

---

## Ordre recommandé (première utilisation)

1. **Démarrer serveurs** :
   - Backend : `cd api && python3 -m uvicorn main:app --reload --port 8000`
   - Frontend : `cd web && npm run dev`

2. **Vérifier DB** :
   - Vérifier nom DB dans logs backend
   - Appliquer migrations si nécessaire : `cd api && alembic upgrade head`

3. **Lancer diagnostic** :
   - `/admin/diagnostics` → "Run Quick Diagnostic"
   - Vérifier tous checks PASS

4. **Backfill market data** :
   - `/admin/backtests` → "Validate Alpha Vantage (7 assets)"
   - Si OK : "Backfill Missing (365d)"
   - Attendre completion

5. **Lancer backtest test** :
   - `/admin/backtests` → Sélectionner BTC + SPY, dates 2023-01-01 à 2023-12-31
   - Strategy : `equal_weight`, Rebalance : `weekly`
   - Click "Run Backtest"
   - Vérifier résultats (Chart, Stats)

6. **Vérifier historiques** :
   - `/admin/backtests` → Sélectionner instruments, dates
   - Click "Voir historiques"
   - Vérifier graphique base100

---

## Pièges connus

1. **Rate limit Alpha Vantage** :
   - Free tier : 4 calls/minute
   - Backfill séquentiel lent
   - Solution : Attendre ou upgrade tier

2. **Date range invalide** :
   - Alpha Vantage peut ne pas avoir données récentes
   - Vérifier `effective_start_date` / `effective_end_date` dans réponse backtest

3. **Weekend tradability** :
   - ETFs non-tradables le weekend
   - Poids gelés automatiquement (pas d'erreur)

4. **JWT secret mismatch** :
   - Backend et frontend doivent avoir même `JWT_SECRET_KEY`
   - Vérifier `api/.env.local` et `web/.env.local`

5. **DB isolée** :
   - `arquantix_quant` n'a pas `admin_users`
   - `created_by_user_id` est nullable (pas de FK)

---

## Bonnes pratiques

1. **Toujours valider Alpha Vantage** avant backfill massif
2. **Vérifier bars existence** avant lancer backtest
3. **Utiliser diagnostic** pour vérifier système opérationnel
4. **Vérifier logs backend** en cas d'erreur
5. **Commit DB par instrument** dans backfill (pas de rollback global)

---

## Documents associés

- [Overview](./MARKET_DATA_AND_BACKTEST_OVERVIEW.md)
- [Market Data Architecture](./MARKET_DATA_ARCHITECTURE.md)
- [Backtest Engine Architecture](./BACKTEST_ENGINE_ARCHITECTURE.md)
- [Database Schema](./DATABASE_SCHEMA_MARKET_BACKTEST.md)
- [Alpha Vantage Provider](./PROVIDERS_ALPHA_VANTAGE.md)
- [Frontend UI](./FRONTEND_BACKTEST_AND_MARKET_UI.md)






