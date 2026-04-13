# Simulated Market Execution Audit Report

## 1. Executive Summary

### Etat actuel

Le systeme d'execution Arquantix (Exchange Engine) resout les prix via `_resolve_price()` qui a deux modes :
- **Mode override** : un prix en EUR est passe manuellement (page admin Exchange Test l'impose aujourd'hui).
- **Mode market** : le dernier tick est lu depuis `market_data_latest_quotes`, converti USDT→EUR via le taux EURUSDT.

Les deux modes (BUY et SELL) utilisent **exactement la meme source de prix** : `quote.last_price`. Il n'y a aucune distinction bid/ask aujourd'hui.

### Faisabilite

**Haute**. Le systeme possede deja en base les champs `bid_price` et `ask_price` dans `market_data_latest_quotes`, alimentes en temps reel par le worker WebSocket Binance (`bookTicker` stream). Le `last_price` actuel est deja un mid-price `(bid+ask)/2`. L'integration d'un mode "market simulated execution" ne necessite que des modifications mineures et localisees.

### Niveau de risque

**Faible**. Le prix d'execution est la source de verite pour tous les calculs aval (frais, PRU, P&L, settlement, wallet history). Tant que le prix d'execution final est enregistre correctement dans `exchange_orders.price`, tous les calculs aval restent coherents independamment de la source du prix.

---

## 2. Current Exchange Pricing Flow

### _resolve_price()

**Fichier** : `api/services/exchange/service.py` (lignes 696-728)

```
_resolve_price(db, asset, override_price) -> Decimal (EUR)

1. Si override_price fourni → retour direct (suppose en EUR)
2. Sinon :
   a. Lookup provider_symbol via ASSET_PROVIDER_SYMBOL_MAP (ex: BTC → BTCUSDT)
   b. Query MarketDataLatestQuote JOIN MarketDataInstrument WHERE provider_symbol = 'BTCUSDT'
   c. Extraction de quote.last_price (en USDT)
   d. get_eurusdt_rate(db, strict=True) → leve si quote absente ou > 300s
   e. price_eur = usdt_to_eur(price_usdt, eurusdt_rate)
   f. Retour price_eur
```

### BUY

**Fichier** : `api/services/exchange/service.py` (lignes 114-331)

```
price = _resolve_price(db, asset, payload.price)
volume_raw = fiat_amount / price
fee_crypto = volume_raw * fee_bps / 10000
client_crypto = volume_raw - fee_crypto
```

- Le prix est utilise pour convertir EUR → quantite crypto.
- Les frais sont en crypto, calcules sur le volume brut.

### SELL

**Fichier** : `api/services/exchange/service.py` (lignes 334-434)

```
price = _resolve_price(db, asset, payload.price)
gross_eur = amount_crypto * price
fee_eur = gross_eur * fee_bps / 10000
net_eur = gross_eur - fee_eur
```

- Le prix est utilise pour convertir quantite crypto → EUR.
- Les frais sont en EUR, calcules sur le montant brut.

### Source actuelle du prix

- BUY et SELL utilisent **la meme methode `_resolve_price()`** avec les memes parametres.
- Sans override : `MarketDataLatestQuote.last_price` (USDT) converti en EUR.
- Le champ `last_price` est un **mid-price** `(bid+ask)/2` quand alimente par le WebSocket.

---

## 3. Live Market Data Availability

### Stream Binance

**Fichier** : `api/services/market_data/binance_ws_ingestion.py`

Le worker WebSocket utilise le stream **`bookTicker`** (Individual Symbol Book Ticker) qui fournit :

| Champ Binance | Champ stocke | Description |
|---------------|--------------|-------------|
| `b` | `bid_price` | Meilleur bid |
| `a` | `ask_price` | Meilleur ask |
| `E` / `e` | `quote_time` | Timestamp Binance (ms) |
| calcule | `last_price` | `(bid + ask) / 2` (mid-price) |

### Persistance

**Fichier** : `api/services/market_data/quotes_repo.py` (fonction `upsert_latest_quote`, lignes 114-174)

- Upsert dans `market_data_latest_quotes` (une ligne par instrument).
- Champs ecrits : `last_price`, `bid_price`, `ask_price`, `volume`, `quote_time`, `updated_at`.

### Batch et frequence

- Batch size : 20 ticks (configurable).
- Intervalle max entre commits : 2 secondes (configurable).
- En pratique : les quotes sont fraiches a ~2 secondes pres.

### Accessibilite backend

Le backend peut acceder au dernier tick a tout instant via :

```python
db.query(MarketDataLatestQuote)
  .join(MarketDataInstrument, ...)
  .filter(MarketDataInstrument.provider_symbol == "BTCUSDT")
  .first()
```

Les champs `bid_price` et `ask_price` sont accessibles mais **non utilises aujourd'hui** par l'Exchange Engine.

### Fallback REST

**Fichier** : `api/services/market_data/market_summary_repo.py`

Si le WebSocket est arrete, un fallback REST (`/api/v3/ticker/24hr`) met a jour les quotes avec un seuil de fraicheur configurable (60s par defaut).

---

## 4. Data Model Findings

### Table market_data_latest_quotes

**Fichier** : `api/database.py` (lignes 270-286)

| Colonne | Type | Nullable | Utilise par Exchange |
|---------|------|----------|----------------------|
| `instrument_id` | Integer (PK, FK) | Non | Oui (join) |
| `provider` | String(50) | Non | Non |
| `provider_symbol` | String(50) | Oui | Oui (filtre) |
| **`last_price`** | Numeric(20,8) | Non | **Oui** (prix d'execution) |
| **`bid_price`** | Numeric(20,8) | **Oui** | **Non** |
| **`ask_price`** | Numeric(20,8) | **Oui** | **Non** |
| `volume` | Numeric(20,8) | Oui | Non |
| `quote_time` | DateTime(TZ) | Oui | Non |
| `updated_at` | DateTime(TZ) | Non | Non |

### Constat cle

Les champs `bid_price` et `ask_price` existent deja et sont alimentes par le WebSocket Binance. Aucune migration de schema n'est necessaire pour implementer le mode "market simulated execution".

### Limitation actuelle

`last_price` est un mid-price `(bid+ask)/2` quand alimente par le WebSocket (`bookTicker`), mais un last traded price quand alimente par le REST (`24hr ticker`). En production avec le worker WS actif, c'est systematiquement un mid-price.

---

## 5. Admin Exchange Test Findings

### Fonctionnement actuel

**Fichier** : `web/src/app/admin/exchange-test/page.tsx`

| Element | Detail |
|---------|--------|
| Formulaire | Client + Asset + Montant + Prix unitaire (override) |
| Prix | **Champ obligatoire dans l'UI** (bouton desactive si vide) |
| Preview | Calcul local avec le prix saisi (pas de prix live) |
| Execution | `POST /api/exchange/buy` ou `sell` avec `price` dans le body |
| Contexte | `GET /api/admin/exchange/context` ne renvoie **aucun prix** |

### Friction actuelle

1. L'utilisateur **doit manuellement saisir un prix** pour chaque execution.
2. Il n'y a **aucun affichage du prix live** dans la page.
3. Le preview est purement theorique, base sur la saisie manuelle.
4. Pour tester, il faut aller chercher le prix actuel ailleurs (API, CoinGecko, etc.).

### Integration future

L'API backend accepte deja `price: null` et resout automatiquement le prix live. Il suffit de :
1. Rendre le champ prix optionnel dans l'UI.
2. Afficher le prix live (bid/ask/mid) comme information.
3. Ajouter un mode "Market Simulated Execution" qui n'envoie pas de `price`.

---

## 6. Recommended Target Design

### Architecture proposee

```
                        _resolve_price(db, asset, override_price)
                                    |
                     +--------------+--------------+
                     |                             |
              override_price != None        override_price == None
                     |                             |
               return override              _resolve_market_price()
                                                   |
                                    +--------------+--------------+
                                    |                             |
                             bid/ask reels               bid/ask absents
                              en base ?                        |
                                    |                    mid = last_price
                              bid = bid_price            bid = mid * (1 - spread/2)
                              ask = ask_price            ask = mid * (1 + spread/2)
                                    |                             |
                                    +--------------+--------------+
                                                   |
                                    BUY → price = ask (USDT)
                                    SELL → price = bid (USDT)
                                                   |
                                          usdt_to_eur(price, eurusdt_rate)
```

### Point d'integration recommande : `_resolve_price()`

Modifier **uniquement** `_resolve_price()` dans `api/services/exchange/service.py` pour :

1. Accepter un parametre supplementaire `side: Literal["buy", "sell"]`.
2. Quand `override_price` est absent :
   - Lire `bid_price` et `ask_price` en plus de `last_price`.
   - Si `bid_price` et `ask_price` sont disponibles et non-null :
     - BUY → `price_usdt = ask_price`
     - SELL → `price_usdt = bid_price`
   - Sinon (fallback, ne devrait pas arriver avec le WS actif) :
     - `mid = last_price`
     - `spread = get_spread_config(asset)`
     - BUY → `price_usdt = mid * (1 + spread/2)`
     - SELL → `price_usdt = mid * (1 - spread/2)`
   - Conversion USDT → EUR.

### Justification du point d'integration

- **`_resolve_price()` est le seul point de resolution** : modifier cette methode impacte automatiquement BUY et SELL.
- **Pas de nouveau service necessaire** : la logique reste simple et localisee.
- **Compatibilite totale** : `override_price` continue de fonctionner sans changement.
- **Tous les calculs aval** (frais, settlement, wallet, P&L) fonctionnent automatiquement car ils utilisent le prix retourne par `_resolve_price()`.

### Signature cible

```python
@staticmethod
def _resolve_price(
    db: Session,
    asset: str,
    override_price: Optional[Decimal],
    side: Literal["buy", "sell"] = "buy",
) -> Decimal:
```

---

## 7. Spread Configuration Recommendation

### Option recommandee : table `exchange_fee_configs` existante

La table `exchange_fee_configs` stocke deja les `fee_bps` par asset. On peut y ajouter un champ `spread_bps` :

| Champ existant | Nouveau champ |
|----------------|---------------|
| `asset` (PK) | |
| `fee_bps` | `spread_bps` (Integer, default 50 = 0.50%) |
| `active` | |

### Avantages

- **Par asset** : le spread peut etre different pour BTC (50 bps) vs DOGE (100 bps).
- **Configurable sans deploy** : modifiable via la page admin.
- **Coherent** : les frais et le spread sont dans la meme table.
- **Simple** : une seule migration, un seul point de lecture.

### Valeurs par defaut recommandees

| Asset | Spread recommande (bps) | Spread (%) |
|-------|--------------------------|------------|
| BTC | 50 | 0.50% |
| ETH | 50 | 0.50% |
| SOL | 75 | 0.75% |
| XRP | 75 | 0.75% |
| BNB | 75 | 0.75% |
| ADA | 100 | 1.00% |
| DOGE | 100 | 1.00% |
| AVAX | 100 | 1.00% |
| LINK | 100 | 1.00% |
| DOT | 100 | 1.00% |
| USDC | 10 | 0.10% |
| EUR | 10 | 0.10% |

### Alternatives considerees (non retenues)

| Option | Raison du rejet |
|--------|-----------------|
| Constante dans le code | Pas configurable sans deploy |
| Variable d'environnement | Pas par asset, pas modifiable en runtime |
| Nouvelle table `exchange_spread_configs` | Duplication inutile avec `exchange_fee_configs` |
| `app_runtime_settings` | Pas structure par asset |

---

## 8. Downstream Impact Analysis

### Principe fondamental

Le prix d'execution est enregistre dans `exchange_orders.price` au moment du trade. **Tous les calculs aval utilisent ce prix enregistre, pas un re-fetch market data.** Changer la source du prix (mid → bid/ask) ne casse donc aucun calcul aval.

### Analyse detaillee

| Composant | Source du prix | Impact | Risque |
|-----------|----------------|--------|--------|
| **Frais (fees)** | `exchange_orders.price` | Les frais seront calcules sur le prix bid ou ask au lieu du mid. Difference negligeable (~0.25% du spread). | **Nul** |
| **PRU (avg buy price)** | `exchange_orders.price` via wallet_statistics | Le PRU sera base sur le prix ask (BUY). Plus realiste qu'un mid. | **Nul** (amelioration) |
| **Wallet history** | `exchange_orders.price` aux timestamps de trade | Valeur du portefeuille aux points de trade legerement differente. | **Nul** |
| **P&L realise** | `total_sell_revenue - (total_sold * cost_per_unit)` | Calcule correctement car bases sur les prix enregistres. | **Nul** |
| **P&L non realise** | `position * current_market_price - cost_basis` | `current_market_price` vient de `MarketDataLatestQuote.last_price` (mid). `cost_basis` = PRU * qty. Coherent. | **Nul** |
| **Settlement delta** | BUY: `volume_raw = fiat_amount / price`. SELL: `amount_crypto` (inchange). | BUY: volume legerement different car prix ask > mid. Mais le delta est en crypto, pas en EUR. | **Nul** |
| **Ledger entries** | Montants des legs (trade.gross/net) | Derives du prix d'execution. Coherent. | **Nul** |
| **Conversion EUR** | `usdt_to_eur(price_usdt, eurusdt_rate)` | Inchange : le bid/ask est en USDT, la conversion est la meme. | **Nul** |

### Coherence avec la devise EUR

Le flux reste identique :
1. `bid_price` ou `ask_price` en USDT (depuis `market_data_latest_quotes`)
2. Conversion en EUR via `usdt_to_eur(price_usdt, eurusdt_rate)`
3. Prix final en EUR stocke dans `exchange_orders.price`

La conversion FX n'est pas affectee.

---

## 9. Risks

| # | Risque | Probabilite | Impact | Mitigation |
|---|--------|-------------|--------|------------|
| 1 | **Quote absente** : `bid_price` ou `ask_price` NULL en base | Faible (WS actif) | Bloquant | Fallback sur `last_price` + spread simule |
| 2 | **Quote perimee** : WS arrete, quote > 300s | Faible | Bloquant | Deja gere par `get_eurusdt_rate(strict=True)`. Ajouter meme check sur la quote principale. |
| 3 | **Spread trop large** : config incorrecte | Faible | Prix d'execution anormal | Validation : `spread_bps` entre 1 et 500 (0.01% a 5%) |
| 4 | **Tests existants** : les tests unitaires exchange utilisent `price_override` | Faible | Aucun | Les tests avec override ne sont pas affectes |
| 5 | **Migration DB** : ajout de `spread_bps` a `exchange_fee_configs` | Faible | Migration necessaire | Migration simple, valeur par defaut 50 |
| 6 | **Coherence BUY/SELL** : un BUY a l'ask suivi d'un SELL immediat au bid produit une perte = spread | Attendu | P&L negatif sur un aller-retour instantane | Comportement normal et realiste. Documenter. |
| 7 | **Impact PRU historique** : les anciens trades ont un PRU au mid, les nouveaux au ask | Attendu | Legere discontinuite dans l'historique | Pas de reprocessing necessaire. Les deux sont corrects dans leur contexte. |

---

## 10. Final Recommendation

### Implementation recommandee

1. **Ajouter `spread_bps` a `exchange_fee_configs`** (migration Alembic)
   - Default : 50 (0.50%)
   - Nullable : Non
   - Validation : 1-500

2. **Modifier `_resolve_price()`** pour accepter `side` et utiliser bid/ask
   - Lire `quote.bid_price` et `quote.ask_price` en plus de `last_price`
   - BUY → ask, SELL → bid
   - Fallback si bid/ask absent : spread simule sur `last_price`

3. **Modifier `buy()` et `sell()`** pour passer `side` a `_resolve_price()`
   - `buy()` : `_resolve_price(db, asset, payload.price, side="buy")`
   - `sell()` : `_resolve_price(db, asset, payload.price, side="sell")`

4. **Modifier la page admin Exchange Test**
   - Rendre le champ prix optionnel
   - Afficher le prix live (bid/mid/ask) en temps reel
   - Ajouter un toggle "Mode" : `Manual Override` / `Market Simulated`
   - En mode Market Simulated : ne pas envoyer `price` dans le payload

5. **Ajouter le spread au contexte admin**
   - `GET /api/admin/exchange/context` renvoie aussi `spread_bps` et les prix live

### Estimation d'effort

| Tache | Effort |
|-------|--------|
| Migration DB (`spread_bps`) | 15 min |
| Modification `_resolve_price()` | 30 min |
| Modification `buy()`/`sell()` (passage de `side`) | 10 min |
| Admin Exchange Test UI | 1h |
| Tests unitaires | 30 min |
| **Total** | **~2h30** |

### Ce qui ne change PAS

- `price_override` reste fonctionnel pour le debug/test manuel
- Tous les calculs aval (frais, PRU, P&L, settlement, wallet history) fonctionnent sans modification
- Les schemas API restent compatibles (price reste optionnel)
- La conversion EUR reste identique
- Le worker WebSocket n'est pas modifie

---

## Annexe A : Reponses aux 10 questions

| # | Question | Reponse |
|---|----------|---------|
| 1 | Source de prix BUY | `MarketDataLatestQuote.last_price` (USDT, mid-price) converti en EUR via EURUSDT. Override possible. |
| 2 | Source de prix SELL | Identique a BUY (meme `_resolve_price()`). |
| 3 | Le moteur lit-il la derniere quote live ? | **Oui**, si `price_override` n'est pas fourni. Lecture directe de `market_data_latest_quotes`. |
| 4 | Bid et ask en base ? | **Oui**, les champs `bid_price` et `ask_price` existent et sont alimentes par le WS Binance (`bookTicker`). |
| 5 | Peut-on construire un bid/ask simule ? | **Pas necessaire** : bid et ask reels sont deja en base. Fallback simule possible si null. |
| 6 | Meilleur point d'integration | `_resolve_price()` dans `api/services/exchange/service.py`. |
| 7 | Spread global ou par asset ? | **Par asset** : chaque crypto a une liquidite differente. |
| 8 | Ou stocker le spread ? | `exchange_fee_configs.spread_bps` (meme table que les frais). |
| 9 | Admin sans prix manuel ? | **Oui** : l'API accepte deja `price: null`, il suffit de rendre le champ optionnel dans l'UI. |
| 10 | Risques aval ? | **Aucun** : tous les calculs utilisent le prix enregistre dans `exchange_orders.price`, pas un re-fetch. |

---

## Annexe B : References de code

| Element | Fichier | Lignes |
|---------|---------|--------|
| `_resolve_price()` | `api/services/exchange/service.py` | 696-728 |
| `ExchangeService.buy()` | `api/services/exchange/service.py` | 114-331 |
| `ExchangeService.sell()` | `api/services/exchange/service.py` | 334-434 |
| `ExchangeBuyRequest` | `api/services/exchange/schemas.py` | 12-19 |
| `ExchangeSellRequest` | `api/services/exchange/schemas.py` | 43-49 |
| `ASSET_PROVIDER_SYMBOL_MAP` | `api/services/exchange/assets.py` | 20-26 |
| `MarketDataLatestQuote` | `api/database.py` | 270-286 |
| `upsert_latest_quote()` | `api/services/market_data/quotes_repo.py` | 114-174 |
| `_parse_book_ticker()` | `api/services/market_data/binance_ws_ingestion.py` | 61-83 |
| `get_eurusdt_rate()` | `api/services/market_data/fx.py` | 23-59 |
| `usdt_to_eur()` | `api/services/market_data/fx.py` | 62-66 |
| `ExchangeFeeConfigRepository` | `api/services/exchange/repository.py` | 85-95 |
| Wallet statistics | `api/services/wallet_statistics/service.py` | 196-236 |
| Wallet history | `api/services/wallet_history/service.py` | 202-249 |
| Position valuation | `api/services/portfolio_engine/valuations/service.py` | 296-322 |
| Price bridge | `api/services/portfolio_engine/instruments/price_bridge.py` | 40-88 |
| Admin exchange test page | `web/src/app/admin/exchange-test/page.tsx` | - |
| Exchange context endpoint | `api/services/exchange/admin_router.py` | 46-84 |
