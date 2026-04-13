# Quote System Audit Report

## 1. Executive Summary

**Etat actuel** : Le système Vancelian utilise exclusivement des prix en **USDT** (Binance) pour tous les flux crypto — exchange BUY, exchange SELL, valorisation des positions, affichage Flutter — mais les étiquette et les traite comme s'ils étaient en **EUR**. Aucune conversion FX n'existe nulle part dans le code.

**Principal probleme identifie** : Les prix USDT sont implicitement assimiles a des prix EUR (ratio 1:1). Cela signifie que tous les montants etiquetes "EUR" dans le systeme (gross_eur, net_eur, estimated_value_eur, price_eur) sont en realite des montants USDT. L'ecart EUR/USDT reel est d'environ 7-10% selon le taux de change, ce qui impacte directement les montants debites/credites et la valorisation affichee.

**Niveau de risque** : **ELEVE**. En production, un client qui achete 1000 EUR de BTC recevrait ~8% de crypto en trop (car le prix USDT est plus eleve que le prix EUR). A l'inverse, un client qui vend recevrait ~8% d'EUR en moins que ce qui lui est du.

---

## 2. Quote Data Inventory

### 2.1 Paires existantes en base

Toutes les paires sont des paires Binance USDT :

| provider_symbol | Nom | Source | Usage |
|-----------------|-----|--------|-------|
| BTCUSDT | Bitcoin | Binance WS + REST | Exchange, valuation, market-summary |
| ETHUSDT | Ethereum | Binance WS + REST | Exchange, valuation, market-summary |
| SOLUSDT | Solana | Binance WS + REST | Exchange, valuation, market-summary |
| XRPUSDT | XRP | Binance WS + REST | Exchange, valuation, market-summary |
| ADAUSDT | Cardano | Binance WS + REST | Exchange, valuation, market-summary |
| BNBUSDT | BNB | Binance WS + REST | Market-summary seulement |
| DOGEUSDT | Dogecoin | Binance WS + REST | Market-summary seulement |
| USDCUSDT | USD Coin | Binance WS + REST | Market-summary seulement |
| AVAXUSDT | Avalanche | Binance WS + REST | Market-summary seulement |
| LINKUSDT | Chainlink | Binance WS + REST | Market-summary seulement |
| DOTUSDT | Polkadot | Binance WS + REST | Market-summary seulement |

**Paires FX existantes : AUCUNE.** Pas de EURUSD, EURUSDT, USDTEUR, USDTUSD, ou toute autre paire de conversion.

### 2.2 Instruments non-crypto

| symbol | asset_class | provider | provider_symbol |
|--------|-------------|----------|-----------------|
| BTC | crypto | alphavantage | BTC |
| ETH | crypto | alphavantage | ETH |
| SOL | crypto | alphavantage | SOL |
| URTH | etf | alphavantage | URTH |
| QQQ | etf | alphavantage | QQQ |
| DIA | etf | alphavantage | DIA |
| GLD | etf | alphavantage | GLD |

Ces instruments CORE_V1 utilisent Alpha Vantage / Yahoo (historique D1 seulement), pas pour l'exchange.

### 2.3 Tables de stockage

| Table | Contenu | PK |
|-------|---------|-----|
| `market_data_instruments` | Referentiel instruments | `id` (auto) |
| `market_data_latest_quotes` | Derniere quote temps reel (1 ligne/instrument) | `instrument_id` |
| `market_data_bars_d1` | Barres journalieres Yahoo | `(instrument_id, date)` |
| `market_data_bars_5m/1h/4h/1d/1w` | Barres Binance multi-timeframe | `(instrument_id, open_time)` |

---

## 3. Exchange Price Resolution Audit

### 3.1 Methode `_resolve_price()` (service.py)

```python
provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(asset)  # ex: "BTC" -> "BTCUSDT"

quote = (
    db.query(MarketDataLatestQuote)
    .join(MarketDataInstrument, ...)
    .filter(MarketDataInstrument.provider_symbol == provider_symbol)
    .first()
)
return Decimal(str(quote.last_price))  # prix USDT retourne tel quel
```

**Aucune conversion. Aucune verification de devise. Le prix USDT est retourne comme prix "EUR".**

### 3.2 BUY

| Etape | Code | Devise reelle | Devise supposee |
|-------|------|---------------|-----------------|
| Input | `fiat_amount` (ex: 1000) | EUR | EUR |
| Prix | `_resolve_price()` → BTCUSDT | **USDT** | EUR |
| Calcul | `volume_raw = fiat_amount / price` | EUR / USDT | EUR / EUR |
| Resultat | "client recoit X BTC" | Faux (trop de BTC) | Correct si EUR |

**Exemple concret** :
- Client depose 1000 EUR
- Prix BTC : 85000 USDT (= ~78700 EUR au taux reel)
- Le systeme calcule : 1000 / 85000 = 0.01176 BTC
- Le prix correct en EUR serait : 1000 / 78700 = 0.01270 BTC
- Ecart : le client recoit **7.4% de BTC en moins** qu'il ne devrait

### 3.3 SELL

| Etape | Code | Devise reelle | Devise supposee |
|-------|------|---------------|-----------------|
| Input | `amount_crypto` (ex: 0.01) | Crypto | Crypto |
| Prix | `_resolve_price()` → BTCUSDT | **USDT** | EUR |
| Calcul | `gross_eur = amount_crypto * price` | Crypto * USDT | Crypto * EUR |
| Resultat | "client recoit X EUR" | Faux (trop d'EUR credites) | Correct si EUR |

**Exemple concret** :
- Client vend 0.01 BTC
- Prix : 85000 USDT
- Le systeme calcule : 0.01 * 85000 = 850 "EUR"
- Prix reel en EUR : 0.01 * 78700 = 787 EUR
- Le client recoit **8% d'EUR en trop**

### 3.4 Ambiguites identifiees

| Lieu | Variable | Etiquetee | Reellement |
|------|----------|-----------|------------|
| `ExchangeSellResponse.price_eur` | Prix par unite | EUR | **USDT** |
| `ExchangeSellResponse.gross_eur` | Montant brut | EUR | **USDT** |
| `ExchangeSellResponse.fee_eur` | Frais | EUR | **USDT** |
| `ExchangeSellResponse.net_eur` | Montant net | EUR | **USDT** |
| `ExchangeBuyResponse.amount_fiat` | Montant fiat | EUR | EUR (input) |
| `ExchangeBuyResponse.price` | Prix par unite | EUR | **USDT** |
| Custody transaction | `amount` | EUR | EUR (fonds reels) |
| Settlement balance | `delta` | EUR | EUR (fonds reels) |

**Le prix est en USDT mais les fonds debites/credites sont en EUR reel.** C'est la l'incoherence fondamentale.

---

## 4. Valuation Audit

### 4.1 All Crypto Positions (`GET /api/app/crypto-positions`)

```python
# test_clients/service.py
p = Decimal(str(quote.last_price))  # prix USDT
price_eur = f"{p:.2f}"              # etiquete "EUR"
val = (balance * p).quantize(...)   # valorisation en USDT, etiquetee EUR
```

- **Source** : `market_data_latest_quotes` → Binance USDT
- **Conversion FX** : aucune
- **Resultat** : `estimated_value_eur` est en fait `estimated_value_usdt`

### 4.2 Crypto Wallet Detail (`GET /api/app/crypto-positions/{asset}`)

```python
current_price = Decimal(str(quote.last_price))  # USDT
total_value = (balance * current_price).quantize(...)  # USDT, etiquete EUR
```

- Le PRU (prix de revient unitaire) est aussi calcule a partir des ordres historiques qui utilisent le meme prix USDT
- Les gains non-realises sont donc coherents en interne (USDT vs USDT) mais faux en EUR

### 4.3 Dashboard Flutter

| Ecran | API | Source prix | Devise affichee | Devise reelle |
|-------|-----|-------------|-----------------|---------------|
| AllCryptoPositionsScreen | `/api/app/crypto-positions` | Backend → USDT | EUR (€) | **USDT** |
| CryptoWalletDetailScreen | `/api/app/crypto-positions/{asset}` | Backend → USDT | EUR (€) | **USDT** |
| AllCryptoScreen | `/api/market-data/all-crypto` | market-summary → USDT | EUR (€) | **USDT** |
| CryptoDetailScreen | market-summary + WS | Binance → USDT | EUR (€) | **USDT** |

### 4.4 Logique de formatage Flutter

```dart
// all_crypto_api.dart
static String formatPrice(double value) {
  if (value >= 1000) return '${...} €';  // suffixe € sur un prix USDT
  if (value >= 1) return '${...} €';
  ...
}
```

**Flutter ne fait aucun calcul de valorisation** — tout vient du backend. Mais il ajoute le symbole `€` sur des prix USDT.

### 4.5 Admin Exchange Test (Next.js)

- Preview BUY/SELL : calcul local `amount * priceOverride`
- `priceOverride` est saisi manuellement par l'admin (pas de fetch automatique)
- Les resultats d'execution affichent `price_eur`, `gross_eur`, `net_eur` — qui sont en USDT

---

## 5. FX Availability

### 5.1 Paires FX dans le systeme

| Paire | Presente ? | Ou ? |
|-------|------------|------|
| EURUSD | Non | Documentee dans architecture (Yahoo `EURUSD=X`) mais non seedee |
| EURUSDT | Non | Binance la supporte mais non configuree |
| USDTEUR | Non | N'existe pas sur Binance |
| USDTUSD | Non | Non configuree |

### 5.2 Support technique forex

- La colonne `asset_class` supporte `"forex"` dans `market_data_instruments`
- Yahoo Finance peut fournir `EURUSD=X` via `yfinance`
- Binance peut fournir `EURUSDT` via l'API publique
- La table `market_data_latest_quotes` peut stocker n'importe quel instrument
- **Le support est la techniquement, mais aucune paire FX n'est configuree ni ingeree**

### 5.3 Faisabilite d'une conversion EUR propre

**Oui, c'est faisable** avec l'infrastructure existante :

1. Creer un instrument `EURUSDT` (ou `EURUSD`) dans `market_data_instruments`
2. L'ajouter au WebSocket Binance ou au refresh periodique
3. Utiliser `last_price` de EURUSDT comme taux de conversion
4. Appliquer : `crypto_eur_price = crypto_usdt_price / eurusdt_rate`

---

## 6. Consistency Gaps

### 6.1 Divergences identifiees

| Composant A | Composant B | Ecart |
|-------------|-------------|-------|
| Prix exchange (USDT) | Fonds debites/credites (EUR reel) | ~8% selon EUR/USD |
| Valorisation affichee (USDT) | Solde EUR reel du client | Incoherent |
| Preview Flutter (USDT+€) | Montant reel sur le compte EUR | ~8% |
| PRU calcule (USDT) | Prix actuel (USDT) | Coherent en interne |
| Gains affiches (USDT) | Gains reels en EUR | ~8% |

### 6.2 Ou un prix USDT est affiche comme EUR

| Lieu | Champ | Impact |
|------|-------|--------|
| Flutter AllCryptoPositionsScreen | `estimatedValueEur` | Valorisation portfolio fausse |
| Flutter CryptoWalletDetailScreen | `currentPriceEur`, `totalValueEur` | Detail wallet faux |
| Flutter AllCryptoScreen | `price` + suffixe `€` | Prix affiche faux |
| Exchange BUY response | `price` | Prix d'execution faux |
| Exchange SELL response | `price_eur`, `gross_eur`, `net_eur` | Montants calcules faux |
| Admin exchange-test | Preview et resultat | Preview faux |

### 6.3 Staleness (fraicheur des quotes)

| Consommateur | Verifie la fraicheur ? | Risque |
|--------------|------------------------|--------|
| Exchange BUY/SELL | **NON** | Trade sur un prix perime |
| Valuation positions | **NON** | Affichage d'un prix obsolete |
| market-summary | OUI (60s fallback) | Faible risque |
| WS market-data | OUI (30s refresh) | Faible risque |

---

## 7. Recommended Target Model

### 7.1 Modele cible : `crypto_eur_price`

```
crypto_eur_price = crypto_usdt_price / eurusdt_rate
```

Ou :
- `crypto_usdt_price` = `market_data_latest_quotes.last_price` pour BTCUSDT, ETHUSDT, etc.
- `eurusdt_rate` = `market_data_latest_quotes.last_price` pour l'instrument EURUSDT

### 7.2 Source de verite

| Donnee | Source | Table | Colonne |
|--------|--------|-------|---------|
| Prix crypto/USDT | Binance WS (bookTicker) | `market_data_latest_quotes` | `last_price` |
| Taux EUR/USDT | Binance WS (bookTicker) ou REST | `market_data_latest_quotes` | `last_price` |

### 7.3 Formule complete

```
Pour BUY (EUR -> Crypto) :
  eurusdt = get_latest_quote("EURUSDT").last_price
  btcusdt = get_latest_quote("BTCUSDT").last_price
  btc_eur_price = btcusdt / eurusdt
  crypto_amount = eur_amount / btc_eur_price

Pour SELL (Crypto -> EUR) :
  eurusdt = get_latest_quote("EURUSDT").last_price
  btcusdt = get_latest_quote("BTCUSDT").last_price
  btc_eur_price = btcusdt / eurusdt
  gross_eur = crypto_amount * btc_eur_price

Pour VALUATION :
  estimated_value_eur = balance * (crypto_usdt_price / eurusdt_rate)
```

### 7.4 Fallback

1. **Quote EURUSDT absente** : utiliser un taux fixe configurable (ex: `DEFAULT_EURUSDT_RATE = 1.08`)
2. **Quote EURUSDT perimee** (> 5 min) : utiliser la derniere connue + ajouter un warning dans la reponse
3. **Quote crypto absente** : rejeter l'operation (comme actuellement)
4. **Quote crypto perimee** : rejeter si > 60s pour l'exchange, afficher avec warning pour la valuation

### 7.5 Gestion des stale quotes

```
Avant chaque trade :
  1. Lire EURUSDT quote
  2. Verifier : (now - quote.updated_at) < MAX_QUOTE_AGE_SECONDS (ex: 60)
  3. Si perime : rejeter avec "stale_fx_quote"
  4. Lire crypto quote
  5. Verifier fraicheur idem
  6. Si OK : calculer crypto_eur_price = crypto_usdt / eurusdt
```

---

## 8. Minimal Correction Plan

### Phase 1 : Ajouter la paire EURUSDT (impact zero)

1. Creer l'instrument `EURUSDT` dans `market_data_instruments` (provider=binance, provider_symbol=EURUSDT, asset_class=forex)
2. L'ajouter au script `ensure_binance_instruments.py`
3. L'ajouter au WebSocket Binance pour ingestion temps reel
4. Verifier que la quote est bien ingeree dans `market_data_latest_quotes`

### Phase 2 : Modifier `_resolve_price()` (impact central)

1. Modifier `_resolve_price()` dans `exchange/service.py` pour :
   - Lire la quote crypto (BTCUSDT)
   - Lire la quote EURUSDT
   - Retourner `crypto_usdt / eurusdt` comme prix EUR
   - Ajouter un controle de fraicheur
2. Impact automatique : BUY et SELL utilisent le bon prix EUR

### Phase 3 : Modifier la valorisation (impact Flutter)

1. Modifier `get_crypto_positions()` et `get_crypto_wallet_detail()` dans `test_clients/service.py`
2. Appliquer la meme formule : `price_eur = last_price_usdt / eurusdt`
3. Impact automatique : Flutter affiche les bons montants EUR

### Phase 4 : Ajouter le taux FX aux endpoints market-data

1. Modifier `market-summary` / `all-crypto` pour inclure le prix EUR converti
2. Impact : Flutter AllCryptoScreen affiche le bon prix

### Estimation

| Phase | Complexite | Fichiers | Impact |
|-------|------------|----------|--------|
| 1 | Faible | 2-3 scripts | Aucun (preparation) |
| 2 | Moyenne | 1 fichier (service.py) | Exchange BUY + SELL corriges |
| 3 | Moyenne | 1 fichier (test_clients/service.py) | Wallet Flutter corrige |
| 4 | Faible | 1-2 fichiers | Market display corrige |

---

## 9. What Must NOT Be Done

### Raccourcis dangereux a eviter absolument

1. **NE PAS assimiler USDT a EUR** (ratio 1:1). L'ecart reel est de 7-10% et varie quotidiennement. C'est le probleme actuel.

2. **NE PAS utiliser un taux fixe en dur** comme solution permanente. Un taux fixe (ex: 1.08) divergerait rapidement du marche reel.

3. **NE PAS creer une table separee pour les prix EUR**. Utiliser `market_data_latest_quotes` existante avec un nouvel instrument EURUSDT. Ne pas dupliquer l'infrastructure.

4. **NE PAS convertir cote Flutter/frontend**. La conversion doit se faire dans le backend, source de verite unique. Le front ne doit jamais connaitre le taux de change.

5. **NE PAS appliquer la conversion de maniere selective** (ex: uniquement dans SELL mais pas dans BUY, ou uniquement dans la valuation mais pas dans l'exchange). Tous les points de consommation doivent utiliser le meme mecanisme.

6. **NE PAS ignorer la fraicheur des quotes FX**. Un taux de change vieux de plusieurs heures peut etre significativement faux. Ajouter un controle de staleness.

7. **NE PAS modifier les montants EUR historiques**. Les ordres passes ont ete executes avec des prix USDT. Ne pas tenter de "corriger" retroactivement — documenter l'ecart et appliquer la correction pour les futurs ordres uniquement.

8. **NE PAS utiliser une API FX tierce** alors que Binance fournit deja EURUSDT. Rester dans l'ecosysteme existant pour minimiser la complexite.

9. **NE PAS modifier les modeles de donnees existants** pour cette correction. Aucune migration n'est necessaire — l'infrastructure actuelle supporte deja un instrument EURUSDT.

10. **NE PAS supprimer le `price_override`**. Il reste essentiel pour les tests et les quotes verrouillees. Mais documenter que l'override doit etre en EUR, pas en USDT.
