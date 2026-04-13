# Wallet Historical Value Data Audit

---

## 1. Trades data

### Table : `exchange_orders`

| Champ | Type SQL | Nullable | Contenu | Exploitable pour reconstruction |
|-------|----------|----------|---------|---------------------------------|
| `id` | UUID | Non | Identifiant unique de l'ordre | Oui — clé de jointure |
| `client_id` | UUID (FK pe_clients) | Non | Client propriétaire | Oui — filtre par client |
| `side` | String(10) | Non | `"buy"` ou `"sell"` | Oui — direction du flux |
| `asset` | String(20) | Non | Actif crypto (BTC, ETH, SOL, XRP, ADA) | Oui — identification de l'actif |
| `amount_crypto` | Numeric(30,18) | Non | Crypto nette reçue (buy) ou vendue (sell) | Oui — variation de position |
| `amount_fiat` | Numeric(30,10) | Non | Buy: EUR dépensés. Sell: EUR brut | Oui — valeur notionnelle EUR |
| `price` | Numeric(30,10) | Non | Prix unitaire en EUR (1 crypto = X EUR) | **Oui — prix d'exécution** |
| `currency` | String(10) | Non | Devise du prix (toujours `"EUR"`) | Oui — confirmation devise |
| `from_asset` | String(20) | Oui | Actif de départ (EUR ou crypto) | Oui — flux |
| `to_asset` | String(20) | Oui | Actif d'arrivée (crypto ou EUR) | Oui — flux |
| `amount_from` | Numeric(30,10) | Oui | Montant de départ | Oui — montant source |
| `amount_to` | Numeric(30,18) | Oui | Montant net d'arrivée | Oui — montant destination |
| `fee_amount` | Numeric(30,18) | Oui | Frais (crypto pour buy, EUR pour sell) | Oui — impact sur position |
| `fee_asset` | String(20) | Oui | Devise des frais | Oui |
| `status` | String(20) | Non | `completed`, `failed`, `processing` | Oui — filtre `completed` uniquement |
| `external_reference` | String(255) | Non | Référence idempotence | Non nécessaire |
| `failure_reason` | Text | Oui | Raison d'échec | Non nécessaire |
| `metadata_` | JSONB | Non (défaut `{}`) | Voir détail ci-dessous | Partiellement — `volume_raw`, `fee_bps` |
| `created_at` | DateTime(TZ) | Non | Timestamp de création de l'ordre | **Oui — meilleur proxy d'exécution** |
| `updated_at` | DateTime(TZ) | Non | Timestamp de dernière mise à jour | Oui — confirmation de complétion |

### Champs manquants dans exchange_orders

| Champ absent | Impact |
|--------------|--------|
| `executed_at` | Pas de timestamp d'exécution dédié. `created_at` est le meilleur proxy (les ordres sont exécutés de manière synchrone). |
| `fx_rate_used` (EURUSDT) | Le taux FX au moment du trade n'est pas stocké. Le prix est converti USDT→EUR via `_resolve_price()` puis seul le résultat EUR est enregistré. |
| `price_usdt` | Le prix brut USDT n'est pas stocké, seulement le prix EUR résultant. |
| `execution_price_currency` | Absent explicitement, mais `currency` = EUR systématiquement. |
| `provider` | Pas de champ provider sur l'ordre (le prix vient de `market_data_latest_quotes`). |
| `instrument_symbol` | Pas stocké directement ; déductible via `ASSET_PROVIDER_SYMBOL_MAP[asset]`. |

### Contenu de metadata_

**Buy** :
```json
{
  "client_account_id": "uuid",
  "settlement_account_id": "uuid",
  "volume_raw": "0.12345678",
  "fee_bps": 50
}
```

**Sell** :
```json
{
  "client_account_id": "uuid",
  "settlement_account_id": "uuid",
  "gross_eur": "4250.00",
  "fee_bps": 50
}
```

### Réponses aux questions

| Question | Réponse |
|----------|---------|
| Timestamp exact d'exécution ? | **Pas de champ dédié.** `created_at` est le proxy le plus fiable (exécution synchrone). |
| Prix exécuté ? | **Oui** — champ `price` en EUR. |
| Valeur notionnelle ? | **Oui** — `amount_fiat` (EUR), `amount_from`, `amount_to`. |
| Reconstruction en EUR ? | **Oui** — toutes les valeurs sont en EUR nativement. |
| Reconstruction en USD ? | **Non directement.** Le taux EURUSDT n'est pas stocké au trade. Nécessite historique FX ou approximation. |
| Swaps crypto/crypto ? | **Non supportés.** Seuls les flux EUR↔crypto existent (`from_asset`/`to_asset` = toujours EUR + crypto). |

---

## 2. Positions data

### Table : `crypto_positions`

| Champ | Type | Description |
|-------|------|-------------|
| `id` | UUID | Clé primaire |
| `client_id` | UUID (FK pe_clients) | Client |
| `asset` | String(20) | Ex. BTC, ETH |
| `balance` | Numeric(30,18) | Solde total actuel |
| `available_balance` | Numeric(30,18) | Solde disponible actuel |
| `created_at` | DateTime(TZ) | Création de la ligne |
| `updated_at` | DateTime(TZ) | Dernière modification |

### Analyse

- **Contrainte unique** : `(client_id, asset)` → une seule ligne par couple client/actif.
- **État courant uniquement** : `credit()` et `debit()` modifient la ligne en place. Aucune table d'historique ni trigger.
- **Pas de snapshots** : La table `position_snapshots` du Portfolio Engine concerne `position_atoms`, pas `crypto_positions`.
- **Audit partiel** : `AuditService.log_success()` enregistre `crypto_position_after` dans les métadonnées de l'ordre, mais ce n'est pas une table d'historique structurée.

### Conclusion

**L'historique des positions devra être entièrement reconstruit à partir des `exchange_orders`.**

Formule de reconstruction :

```
position(client, asset, t) = Σ amount_crypto WHERE side='buy' AND status='completed' AND created_at ≤ t
                            - Σ amount_crypto WHERE side='sell' AND status='completed' AND created_at ≤ t
```

---

## 3. Market data availability

### Tables OHLC disponibles

| Table | Timeframe | Source | Clé primaire |
|-------|-----------|--------|--------------|
| `market_data_bars_5m` | 5 minutes | Binance | `(instrument_id, open_time)` |
| `market_data_bars_1h` | 1 heure | Binance | `(instrument_id, open_time)` |
| `market_data_bars_4h` | 4 heures | Binance | `(instrument_id, open_time)` |
| `market_data_bars_1d` | 1 jour | Binance | `(instrument_id, open_time)` |
| `market_data_bars_1w` | 1 semaine | Binance | `(instrument_id, open_time)` |
| `market_data_bars_d1` | 1 jour | Yahoo | `(instrument_id, date)` |

### Colonnes communes (Binance)

```
instrument_id  — FK vers market_data_instruments
open_time      — DateTime(TZ)
open           — Numeric(20,8)
high           — Numeric(20,8)
low            — Numeric(20,8)
close          — Numeric(20,8)
volume         — Numeric(20,8)
source         — String (défaut "binance")
updated_at     — DateTime(TZ)
```

### Profondeur d'historique

| Timeframe | Fallback par défaut | Profondeur estimée |
|-----------|--------------------|--------------------|
| 5m | 7 jours | ~2 000 barres |
| 1h | 30 jours | ~720 barres |
| 4h | 120 jours | ~720 barres |
| 1d | 730 jours (~2 ans) | ~730 barres |
| 1w | 3 650 jours (~10 ans) | ~520 barres |

> La profondeur dépend du backfill effectué. Le script `run_candles_backfill.py` permet d'étendre avec `--fallback-days`.

### Devise des données

Toutes les données OHLC Binance sont en **USDT**. La devise est implicite via le symbole de l'instrument (ex. BTCUSDT = prix du BTC en USDT).

### Ingestion

- **REST Binance** : `GET /api/v3/klines` pour chaque timeframe (scripts `ingestion_binance_candles_*.py`)
- **Backfill incrémental** : `candles_backfill_service.run_backfill()` + cron toutes les 60s
- **WebSocket** : uniquement pour les quotes live (pas les candles)

---

## 4. FX data

### Table `market_data_latest_quotes`

- **Snapshot uniquement** : une seule ligne par instrument, mise à jour en continu.
- **Pas d'historique** : `upsert_latest_quote()` écrase la valeur précédente.
- Le taux EURUSDT courant y est stocké mais **sans historique**.

### Candles EURUSDT

| Table | Disponible ? | Impact |
|-------|-------------|--------|
| `market_data_bars_5m` | **Oui** (si EURUSDT ingéré) | Conversion EUR pour les 7 derniers jours |
| `market_data_bars_1h` | **Oui** | Conversion EUR pour le dernier mois |
| `market_data_bars_4h` | **Oui** | Conversion EUR pour les 4 derniers mois |
| `market_data_bars_1d` | **Oui** | Conversion EUR pour les 2 dernières années |
| `market_data_bars_1w` | **Oui** | Conversion EUR pour les 10 dernières années |

> **Condition** : l'instrument EURUSDT doit être actif et ingéré par le pipeline Binance. Il est créé par `ensure_binance_instruments.py` avec `asset_class="forex"`.

### Impact sur la reconstruction historique

- **EUR** : Pour chaque timestamp `t`, on peut chercher la chandelle EURUSDT la plus proche et utiliser `close` pour convertir.
- **USD** : Les prix OHLC sont nativement en USDT ≈ USD, aucune conversion nécessaire.
- **Limitation** : Si l'instrument EURUSDT n'a pas été ingéré suffisamment tôt, les taux FX historiques anciens seront manquants.

---

## 5. Timestamp consistency

### Exchange orders

```sql
created_at  — DateTime(timezone=True), server_default=func.now()
updated_at  — DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
```

- **UTC** : PostgreSQL stocke en UTC en interne pour les colonnes `timestamptz`.
- **Précision** : microseconde (PostgreSQL `timestamp with time zone`).

### Market data bars (Binance)

```sql
open_time   — DateTime(timezone=True)
```

- Les timestamps Binance sont en millisecondes UTC, convertis en `datetime` Python.
- Stockés comme `timestamptz` → UTC.

### Market data bars D1 (Yahoo)

```sql
date        — Date (pas DateTime)
```

- Type `Date` sans timezone ni heure → granularité journalière uniquement.

### Conclusion

| Source | Timezone | Précision | Compatible |
|--------|----------|-----------|------------|
| `exchange_orders.created_at` | UTC | μs | Oui |
| `market_data_bars_*.open_time` | UTC | μs (ms source) | Oui |
| `market_data_bars_d1.date` | N/A (Date) | jour | Oui (pour les chandelles daily) |

**Les timestamps sont cohérents en UTC.** La jointure temporelle entre trades et chandelles est possible.

---

## 6. Asset coverage

### Actifs négociables (Exchange Engine)

| Actif | Précision | provider_symbol | Instrument market data |
|-------|-----------|-----------------|----------------------|
| BTC | 8 décimales | BTCUSDT | ✅ Présent |
| ETH | 18 décimales | ETHUSDT | ✅ Présent |
| SOL | 9 décimales | SOLUSDT | ✅ Présent |
| XRP | 6 décimales | XRPUSDT | ✅ Présent |
| ADA | 6 décimales | ADAUSDT | ✅ Présent |

### Instruments market data supplémentaires (non négociables, affichage uniquement)

| provider_symbol | Nom | asset_class |
|-----------------|-----|-------------|
| BNBUSDT | BNB | crypto |
| DOGEUSDT | Dogecoin | crypto |
| USDCUSDT | USD Coin | crypto |
| AVAXUSDT | Avalanche | crypto |
| LINKUSDT | Chainlink | crypto |
| DOTUSDT | Polkadot | crypto |
| EURUSDT | EUR/USDT | forex |

### Couverture

**100% des actifs négociables ont un instrument market data correspondant avec des chandelles OHLC Binance disponibles.**

EURUSDT est présent pour la conversion FX.

---

## 7. Reconstruction feasibility

### Formule cible

```
wallet_value(t) = Σ position_asset_i(t) × price_asset_i(t)
```

Où :
- `position_asset_i(t)` = position reconstituée depuis les trades
- `price_asset_i(t)` = prix OHLC interpolé au timestamp `t`

### Évaluation

| Composant | Disponible | Source | Qualité |
|-----------|-----------|--------|---------|
| Position historique par actif | ✅ | Reconstruction depuis `exchange_orders` | Exacte |
| Prix d'exécution aux timestamps de trade | ✅ | `exchange_orders.price` (EUR) | Exacte |
| Prix marché inter-trade | ✅ | Chandelles OHLC (5m, 1h, 4h, 1d, 1w) | Bonne (interpolation) |
| Conversion USDT → EUR | ✅ | Chandelles EURUSDT OHLC | Bonne si ingéré |
| Conversion USDT → USD | ✅ | Nativement USDT ≈ USD | Exacte |
| Timestamp exact d'exécution | ⚠️ | `created_at` (proxy) | Suffisant (exécution synchrone) |
| Taux FX au moment du trade | ❌ | Non stocké dans l'ordre | Reconstruit via chandelles EURUSDT |

### Verdict : **PARTIAL — faisable avec approximations mineures**

La reconstruction est faisable et fiable, sous réserve de :
1. Le backfill des chandelles EURUSDT doit couvrir la période souhaitée
2. Le taux FX aux timestamps de trade est interpolé (pas exact)
3. `created_at` est utilisé comme proxy pour l'heure d'exécution

---

## 8. Gaps identified

### Gap 1 : Pas de `executed_at` sur exchange_orders (Impact: LOW)

- `created_at` est le seul timestamp utilisable comme moment d'exécution.
- Les ordres sont exécutés de façon synchrone dans une seule transaction, donc `created_at` ≈ `executed_at` à quelques millisecondes près.
- **Impact** : négligeable pour un chart wallet.

### Gap 2 : Taux FX non stocké au moment du trade (Impact: MEDIUM)

- Le champ `price` est en EUR mais le taux EURUSDT utilisé pour la conversion n'est pas enregistré.
- Pour afficher la valeur en USD à un timestamp de trade, il faut retrouver le taux EURUSDT dans les chandelles au même moment.
- **Impact** : approximation mineure pour USD. EUR est exact car stocké nativement.

### Gap 3 : Profondeur historique des chandelles EURUSDT (Impact: MEDIUM)

- Si l'instrument EURUSDT n'a pas été ingéré dès le premier trade, les taux FX historiques manquent.
- Les chandelles daily ont un fallback de 730 jours ; les chandelles 5m seulement 7 jours.
- **Impact** : pour les trades anciens (> profondeur de backfill), la conversion EUR peut être approximée au taux le plus proche disponible ou au taux courant.

### Gap 4 : Pas de chandelles 1 minute (Impact: LOW)

- La granularité la plus fine est 5 minutes.
- Pour un chart wallet (typiquement 1j, 1s, 1m, 1a), c'est largement suffisant.
- **Impact** : négligeable.

### Gap 5 : Pas d'historique dans `market_data_latest_quotes` (Impact: NONE)

- Les quotes live sont des snapshots.
- Les chandelles OHLC compensent entièrement ce manque pour la reconstruction historique.
- **Impact** : aucun.

### Gap 6 : Pas de swaps crypto/crypto (Impact: NONE)

- Le moteur ne supporte que EUR↔crypto.
- La reconstruction est donc simple : chaque trade est un achat ou vente d'un seul actif.
- **Impact** : aucun (simplification).

---

## 9. Recommendations

### Avant implémentation (obligatoire)

1. **Vérifier le backfill EURUSDT** : Exécuter `python scripts/run_candles_backfill.py --timeframe 1d --symbol EURUSDT --fallback-days 730` pour s'assurer d'avoir 2 ans de taux FX daily. Faire de même pour 1h et 4h.

2. **Vérifier le backfill des actifs tradés** : Pour chaque actif (BTCUSDT, ETHUSDT, etc.), s'assurer que les chandelles 1h et 1d couvrent la période depuis le premier trade du client.

### Améliorations recommandées (optionnel, post-v1)

3. **Stocker `eurusdt_rate` dans `exchange_orders.metadata_`** : Lors de l'exécution d'un trade sans price override, enregistrer le taux FX utilisé. Coût : 1 ligne de code dans `service.py`. Bénéfice : conversion USD exacte aux timestamps de trade.

4. **Ajouter `executed_at` à `exchange_orders`** : Migration simple (`ALTER TABLE ADD COLUMN executed_at TIMESTAMPTZ`), peuplé juste avant le commit. Bénéfice : clarté sémantique.

5. **Considérer une table de cache `wallet_value_history`** : Si la reconstruction à la demande est trop coûteuse (nombreux trades × nombreux timestamps), un cache matérialisé (recalculé périodiquement) accélérerait le chargement.

### Stratégie d'implémentation recommandée

```
Algorithme de reconstruction :

1. Charger tous les exchange_orders du client (status=completed), triés par created_at
2. Pour chaque point de temps t dans la série :
   a. Calculer position(asset, t) = cumul des trades jusqu'à t
   b. Pour chaque actif avec position > 0 :
      - Si t correspond exactement à un trade → utiliser exchange_orders.price (EUR)
      - Sinon → chercher la chandelle OHLC la plus proche et utiliser close
      - Si devise = USD → utiliser le prix USDT directement
      - Si devise = EUR → convertir le prix USDT via la chandelle EURUSDT au même t
   c. wallet_value(t) = Σ position(asset) × price(asset, t)
3. Retourner la série de points
```

### Choix du timeframe OHLC pour la reconstruction

| Période chart | Timeframe OHLC recommandé | Nb points estimé |
|---------------|--------------------------|------------------|
| 1 jour | 5m | ~288 points |
| 1 semaine | 1h | ~168 points |
| 1 mois | 4h | ~180 points |
| 1 an | 1d | ~365 points |
| 5 ans | 1w | ~260 points |

---

## Résumé exécutif

| Critère | Statut |
|---------|--------|
| Données de trades | ✅ Complètes pour reconstruction EUR |
| Données de positions | ⚠️ État courant uniquement → reconstruire depuis trades |
| Données OHLC | ✅ 5 timeframes Binance disponibles |
| Données FX historiques | ✅ Via chandelles EURUSDT (si backfill effectué) |
| Cohérence timestamps | ✅ Tout en UTC |
| Couverture actifs | ✅ 100% des actifs tradés |
| **Faisabilité reconstruction** | **PARTIAL → YES avec backfill EURUSDT** |

La reconstruction du chart `wallet_value(t)` est **techniquement faisable** avec les données existantes. Le seul prérequis bloquant est de s'assurer que le backfill des chandelles EURUSDT couvre la période nécessaire.
