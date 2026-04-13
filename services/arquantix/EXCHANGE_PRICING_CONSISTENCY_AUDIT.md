# Exchange Engine Pricing Consistency Audit

## 1. Executive Summary

**Niveau de cohérence global : ÉLEVÉ — le système est globalement cohérent.**

La source de vérité du prix (table `market_data_latest_quotes`, champ `last_price`) est **la même** pour :
- Le moteur BUY
- Le moteur SELL
- Les valorisations wallet (positions, détail)
- Les endpoints market data (REST, WebSocket)
- L'affichage Flutter (via les payloads enrichis)

La formule EUR est **unique et centralisée** : `price_eur = price_usdt / eurusdt_rate` via le module `fx.py`.

**Risques majeurs identifiés :**

| # | Risque | Sévérité | Impact |
|---|--------|----------|--------|
| R1 | Exchange engine utilise `strict=False` pour le taux EURUSDT → fallback possible sur taux fixe 1.08 | **MOYEN** | Prix d'exécution potentiellement décalé si quote EURUSDT absente |
| R2 | `MarketSummaryItem` Flutter ne lit pas `price_eur` au chargement initial de CryptoDetailScreen | **FAIBLE** | Affichage initial incohérent avec la devise préférée |
| R3 | Gains et prix moyen d'achat sont mono-devise (EUR) côté backend | **FAIBLE** | Affichage formaté avec le symbole USD alors que la valeur est en EUR |
| R4 | Pas de contrôle de fraîcheur de la quote crypto (seul EURUSDT a MAX_AGE en mode strict) | **FAIBLE** | Prix potentiellement stale sans alerte |

---

## 2. BUY Engine Pricing Flow

### Source du prix
- **Fonction** : `ExchangeService._resolve_price(db, asset, payload.price)`
- **Table** : `market_data_latest_quotes` JOIN `market_data_instruments` ON `provider_symbol`
- **Champ** : `quote.last_price` (prix USDT depuis Binance bookTicker)

### Devise
- **Sortie** : EUR
- **Conversion** : `price_eur = price_usdt / eurusdt_rate`
- **Taux FX** : `get_eurusdt_rate(db, strict=False)` → `market_data_latest_quotes` pour instrument `EURUSDT`

### Flow complet

```
BUY Request (fiat_amount=100 EUR, asset=BTC)
  │
  ├─ 1. _resolve_price(db, "BTC", None)
  │     └─ query MarketDataLatestQuote WHERE provider_symbol = "BTCUSDT"
  │     └─ price_usdt = quote.last_price  (ex: 72000)
  │     └─ eurusdt_rate = get_eurusdt_rate(db)  (ex: 1.15)
  │     └─ price_eur = 72000 / 1.15 = 62608.70 EUR
  │
  ├─ 2. Volume calculation
  │     └─ volume_raw = 100 / 62608.70 = 0.00159722 BTC
  │     └─ fee_crypto = volume_raw × fee_bps / 10000
  │     └─ client_crypto = volume_raw - fee_crypto
  │
  ├─ 3. EUR debit client: -100 EUR (custody_transactions)
  ├─ 4. EUR credit settlement: +100 EUR (ledger double-entry)
  ├─ 5. Crypto position credit: +client_crypto BTC
  ├─ 6. Settlement delta: +volume_raw BTC (brut, avant frais)
  └─ 7. Order: status=completed, price=62608.70, currency=EUR
```

### Stockage dans exchange_orders

| Champ | Valeur |
|-------|--------|
| `price` | EUR (prix d'exécution converti) |
| `amount_fiat` | Montant EUR débité |
| `amount_crypto` | Crypto nette reçue par le client |
| `fee_amount` | Frais en crypto |
| `fee_asset` | Asset crypto (ex: BTC) |
| `currency` | EUR |

---

## 3. SELL Engine Pricing Flow

### Source du prix
- **Identique au BUY** : `_resolve_price()` → même table, même champ, même conversion

### Devise
- **Sortie** : EUR
- **Conversion** : identique (`price_usdt / eurusdt_rate`)

### Flow complet

```
SELL Request (amount_crypto=0.001 BTC, asset=BTC)
  │
  ├─ 1. _resolve_price(db, "BTC", None)
  │     └─ Même logique que BUY → price_eur = 62608.70 EUR
  │
  ├─ 2. EUR calculation
  │     └─ gross_eur = 0.001 × 62608.70 = 62.61 EUR
  │     └─ fee_eur = gross_eur × fee_bps / 10000
  │     └─ net_eur = gross_eur - fee_eur
  │
  ├─ 3. Crypto position debit: -0.001 BTC
  ├─ 4. EUR credit client: +net_eur (custody_transactions)
  ├─ 5. EUR debit settlement: -net_eur (ledger double-entry)
  ├─ 6. Settlement delta: -0.001 BTC
  └─ 7. Order: status=completed, price=62608.70, currency=EUR
```

### Symétrie BUY ↔ SELL

| Aspect | BUY | SELL | Symétrique ? |
|--------|-----|------|:---:|
| Prix source | `_resolve_price` | `_resolve_price` | ✅ |
| Devise prix | EUR | EUR | ✅ |
| Direction EUR | Client → Settlement | Settlement → Client | ✅ |
| Direction crypto | Credit position | Debit position | ✅ |
| Delta settlement | +volume_raw | -amount_crypto | ✅ |
| Frais devise | Crypto | EUR | ⚠️ asymétrique par design |

---

## 4. Pricing Resolution Logic

### Fonction centrale

```python
# api/services/exchange/service.py
ExchangeService._resolve_price(db, asset, override_price) -> Decimal
```

### Formule exacte

```
SI override_price fourni:
    RETOURNER override_price  (supposé EUR)

SINON:
    provider_symbol = ASSET_PROVIDER_SYMBOL_MAP[asset]  (ex: BTC → BTCUSDT)
    quote = MarketDataLatestQuote JOIN MarketDataInstrument
            WHERE provider_symbol = provider_symbol
    price_usdt = quote.last_price
    eurusdt_rate = get_eurusdt_rate(db, strict=False)
    price_eur = price_usdt / eurusdt_rate
    RETOURNER price_eur
```

### Module FX (`api/services/market_data/fx.py`)

| Constante | Valeur |
|-----------|--------|
| `EURUSDT_PROVIDER_SYMBOL` | `"EURUSDT"` |
| `DEFAULT_EURUSDT_RATE` | `Decimal("1.08")` |
| `MAX_FX_QUOTE_AGE_SECONDS` | `300` |

```python
def usdt_to_eur(usdt_price, eurusdt_rate):
    return usdt_price / eurusdt_rate

def get_eurusdt_rate(db, strict=False):
    quote = MarketDataLatestQuote WHERE provider_symbol = "EURUSDT"
    if quote is None:
        if strict: raise FxQuoteUnavailableError
        else: return DEFAULT_EURUSDT_RATE  # 1.08
    return quote.last_price
```

---

## 5. Market Data Consistency

### Correspondance avec les quotes Binance

| Flux de données | Table source | Champ USDT | Formule EUR | Même source que BUY/SELL ? |
|-----------------|-------------|------------|-------------|:---:|
| REST `/api/market-data/quotes/latest` | `market_data_latest_quotes` | `last_price` | `price / eurusdt_rate` | ✅ |
| REST `/api/market-data/market-summary` | `market_data_latest_quotes` (+fallback Binance REST) | `last_price` | `price / eurusdt_rate` | ✅ |
| REST `/api/market-data/all-crypto` | via `get_market_summaries` | `last_price` | `price / eurusdt_rate` | ✅ |
| WebSocket `/ws/market-data` | `market_data_latest_quotes` | `last_price` | `price / eurusdt_rate` | ✅ |
| Crypto positions `/api/app/crypto-positions` | `market_data_latest_quotes` | `last_price` | `usdt_to_eur(p_usdt, rate)` | ✅ |
| Wallet detail `/api/app/crypto-positions/{asset}` | `market_data_latest_quotes` | `last_price` | `usdt_to_eur(price_usd, rate)` | ✅ |

**Conclusion** : tous les flux utilisent la **même table** (`market_data_latest_quotes`), le **même champ** (`last_price`), et la **même formule FX** (`price_usdt / eurusdt_rate`).

### Différences mineures

1. `market_summary` a un fallback Binance REST si la quote est absente — `_resolve_price` dans l'exchange n'a pas ce fallback (il raise `PriceUnavailableError`)
2. La performance 1j utilise `market_data_bars_1d` (barre close), pas `market_data_latest_quotes`

---

## 6. Wallet Valuation Consistency

### `get_crypto_positions()`

```python
p_usdt = Decimal(str(quote.last_price))                    # Même champ
p_eur = usdt_to_eur(p_usdt, eurusdt_rate)                  # Même formule
price_eur = f"{p_eur:.2f}"
estimated_value_eur = f"{(balance * p_eur):.2f}"

price_usd = f"{p_usdt:.2f}"                                # USDT traité comme USD
estimated_value_usd = f"{(balance * p_usdt):.2f}"
```

### `get_crypto_wallet_detail()`

```python
current_price_usd = Decimal(str(quote.last_price))          # Même champ
current_price_eur = usdt_to_eur(current_price_usd, eurusdt_rate)  # Même formule
```

### Correspondance avec BUY/SELL

| Élément | Valuation | BUY/SELL | Match ? |
|---------|-----------|----------|:---:|
| Table source | `market_data_latest_quotes` | `market_data_latest_quotes` | ✅ |
| Champ prix | `last_price` | `last_price` | ✅ |
| Taux FX | `get_eurusdt_rate(db, strict=False)` | `get_eurusdt_rate(db, strict=False)` | ✅ |
| Formule EUR | `price_usdt / eurusdt_rate` | `price_usdt / eurusdt_rate` | ✅ |

**Le prix affiché dans les valorisations utilise exactement la même source et la même formule que le prix d'exécution BUY/SELL.**

### Limites

- `estimated_value_eur` et `price_eur` sont calculés au moment du call API, pas au moment de l'exécution → latence possible entre affichage et exécution
- Les gains (`average_purchase_price`, `cost_basis`, `unrealized_gains`) sont calculés uniquement en EUR — pas de variante USD

---

## 7. Flutter Display Consistency

### Mapping des champs par écran

| Écran Flutter | Champ backend EUR | Champ backend USD | `selectValue` ? | Symbole dynamique ? |
|---------------|-------------------|-------------------|:---:|:---:|
| **HomeScreen** (Dashboard crypto) | `total_value_eur` | `total_value_usd` | ✅ | ✅ |
| **AllCryptoPositionsScreen** | `estimated_value_eur` | `estimated_value_usd` | ✅ | ✅ |
| **CryptoWalletDetailScreen** (totaux) | `total_value_eur` | `total_value_usd` | ✅ | ✅ |
| **CryptoWalletDetailScreen** (gains) | `unrealized_gains` (EUR only) | ❌ | ❌ | ✅ ⚠️ |
| **CryptoWalletDetailScreen** (PRU) | `average_purchase_price` (EUR only) | ❌ | ❌ | ✅ ⚠️ |
| **AllCryptoScreen** (Markets) | `price_eur` | `price` (USDT) | ✅ | ✅ |
| **AllCryptoScreen** (WS update) | `priceEur` | `price` | ✅ | ✅ |
| **CryptoDetailScreen** (initial) | ❌ | `price` (MarketSummaryItem) | ❌ ⚠️ | ❌ |
| **CryptoDetailScreen** (WS) | `priceEur` | `price` | ✅ | ❌ |
| **ChartAssetModule** (labels) | ❌ | Valeurs issues de l'API | ❌ | ✅ ⚠️ |

### Incohérences Flutter identifiées

**F1. CryptoDetailScreen — chargement initial**
- `MarketSummaryItem` Flutter ne parse que `price` (USDT), pas `price_eur`
- Le prix affiché au chargement est donc toujours en USD même si la préférence est EUR
- Corrigé dès la première mise à jour WebSocket (qui utilise `selectValue`)

**F2. CryptoWalletDetailScreen — gains et PRU**
- `average_purchase_price`, `unrealized_gains`, `realized_gains`, `total_gains` sont mono-devise (EUR) côté backend
- L'écran les formate avec `_activeFormatter` (qui peut être USD)
- Résultat : valeur en EUR affichée avec symbole `$` si préférence USD

**F3. ChartAssetModule — valeurs de graphique**
- Les valeurs close/open viennent de l'API candles en USD (USDT)
- Les labels utilisent `_currencySymbol` (dynamique EUR/USD)
- Résultat : valeur USD avec symbole `€` si préférence EUR

**F4. CryptoDetailScreen — `formatPrice` (market_display_utils)**
- Ne rajoute pas de symbole de devise (intentionnel — le symbole est ajouté par le layout)
- Le prix est affiché sans indicateur de devise dans certains contextes

---

## 8. Settlement & Custody Consistency

### Deltas settlement

| Opération | Delta | Unité | Basé sur prix d'exécution ? |
|-----------|-------|-------|:---:|
| BUY | `+volume_raw` | Crypto | ✅ (volume_raw = fiat/price) |
| SELL | `-amount_crypto` | Crypto | ✅ (montant direct) |

### Job de settlement

- Utilise `delta.delta_amount` tel quel — **pas de re-pricing**
- Vérifie la liquidité via `actual_balance` (settlement wallet) ou `get_aggregate_balance` (positions)
- Marque le delta comme `settled` — ne modifie pas `actual_balance` ni `expected_balance`

### Custody balances

- `actual_balance` : seedé manuellement via admin API (pas encore Fireblocks)
- `expected_balance` : pour `clients_pool`, dérivé de la somme des `crypto_positions` à l'affichage admin
- Pas de valorisation en fiat dans le flux custody — tout est en crypto

**Conclusion** : la couche settlement/custody est cohérente car elle opère exclusivement en unités crypto, sans conversion de prix.

---

## 9. Reference Currency Impact

### Validation

| Composant | Utilise `reference_currency` ? | Comment ? |
|-----------|:---:|------------|
| `ExchangeService.buy()` | ❌ | Prix toujours résolu en EUR via `_resolve_price` |
| `ExchangeService.sell()` | ❌ | Idem |
| `_resolve_price()` | ❌ | Retourne toujours EUR |
| Settlement job | ❌ | Opère en crypto uniquement |
| Custody layer | ❌ | Opère en crypto uniquement |
| `get_crypto_positions()` | ❌ | Retourne les deux devises, pas de filtre |
| `get_crypto_wallet_detail()` | ❌ | Idem |
| Market data endpoints | ❌ | Retournent `price` + `price_eur` systématiquement |
| Flutter `CurrencyPreference` | ✅ | Uniquement pour `selectValue` à l'affichage |
| Flutter `ProfileScreen` | ✅ | PATCH de la préférence |

**Conclusion** : `reference_currency` est **purement un paramètre d'affichage**. Les moteurs d'exécution (BUY/SELL), le settlement, et la custody ne le consultent jamais. Ils opèrent toujours en EUR (fiat) et en crypto (settlement).

---

## 10. Risk Assessment

### Risques d'incohérence identifiés

| # | Risque | Sévérité | Probabilité | Détail |
|---|--------|----------|-------------|--------|
| **R1** | Exécution BUY/SELL avec taux FX fallback | **MOYEN** | Faible (si WS EURUSDT tourne) | `get_eurusdt_rate(strict=False)` → si EURUSDT absent, utilise `DEFAULT=1.08` au lieu du taux live (~1.15). Décalage potentiel ~6% sur le prix d'exécution. |
| **R2** | Latence entre prix affiché et prix exécuté | **FAIBLE** | Normale | Le prix affiché est celui du dernier call API/WS. Le prix exécuté est celui de la DB au moment du `_resolve_price`. Décalage millisecondes à secondes normal. |
| **R3** | CryptoDetailScreen affiche USD au chargement initial | **FAIBLE** | Certaine si pref=EUR | `MarketSummaryItem` ne lit que `price` (USDT). Corrigé dès le premier WS update. |
| **R4** | Gains/PRU affichés avec mauvais symbole | **FAIBLE** | Certaine si pref=USD | Backend ne fournit qu'une valeur EUR pour ces champs. Flutter formate avec `_activeFormatter` → symbole `$` sur valeur EUR. |
| **R5** | Graphique chandelier : valeurs USD avec symbole EUR | **FAIBLE** | Certaine si pref=EUR | Candles API retourne des valeurs USDT. Labels affichent `_currencySymbol`. |
| **R6** | Override de prix non validé | **FAIBLE** | Faible (admin only) | `price_override` est supposé EUR sans validation. Si un admin envoie un prix en USD, l'exécution sera incorrecte. |
| **R7** | Pas de contrôle de fraîcheur de la quote crypto | **FAIBLE** | Rare | Seul le taux EURUSDT a un contrôle d'âge (en mode strict). La quote crypto pourrait être stale sans alerte. |

### Risques NON présents

| Risque vérifié | Statut |
|----------------|--------|
| Prix affiché ≠ prix exécuté (source différente) | ❌ **Non présent** — même table, même champ |
| Conversion EUR appliquée deux fois | ❌ **Non présent** — une seule conversion dans `_resolve_price` |
| Conversion EUR absente | ❌ **Non présent** — `_resolve_price` convertit systématiquement |
| BUY utilisant USDT alors que UI affiche EUR | ❌ **Non présent** — BUY utilise EUR converti |
| SELL utilisant EUR alors que UI affiche USD | ❌ **Non présent** — SELL utilise EUR, l'affichage USD est un mapping Flutter |
| `reference_currency` affectant l'exécution | ❌ **Non présent** — purement display |

---

## 11. Final Verdict

### **PRICING SYSTEM: SAFE**

Le système de pricing Vancelian est **cohérent et sûr** pour l'exécution des transactions.

**Points forts :**
- Source de vérité unique (`market_data_latest_quotes.last_price`)
- Formule FX centralisée et unique (`price_usdt / eurusdt_rate`)
- BUY et SELL utilisent exactement la même résolution de prix
- Les valorisations wallet utilisent la même source que l'exécution
- `reference_currency` est correctement isolé comme paramètre d'affichage
- Settlement opère en crypto sans re-pricing

**Améliorations recommandées (hors scope, non urgentes) :**
1. Passer `strict=True` dans `_resolve_price` pour le taux EURUSDT afin d'éviter le fallback 1.08 en exécution
2. Ajouter `price_eur` au modèle `MarketSummaryItem` Flutter pour le chargement initial de CryptoDetailScreen
3. Fournir les gains/PRU en double devise (EUR + USD) côté backend pour un affichage correct en mode USD
4. Ajouter les valeurs EUR dans les données de chandelier pour que les graphiques affichent la bonne devise
