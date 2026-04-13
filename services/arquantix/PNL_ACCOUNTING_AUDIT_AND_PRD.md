# PnL Accounting Audit & PRD

## 1. Executive Summary

### État actuel

Le système Vancelian dispose d’un moteur d’échange EUR ↔ crypto (BUY/SELL) fonctionnel, avec :
- Persistance des ordres dans `exchange_orders`
- Positions crypto dans `crypto_positions` (balance uniquement, pas de cost basis stocké)
- Calcul du P&L réalisé et non réalisé **reconstruit à la volée** à partir de l’historique des ordres
- Méthode implicite : **weighted average cost** (coût moyen pondéré)

### Niveau de robustesse

- **Points forts** : cohérence interne du cost basis (weighted average), reconstruction correcte dans `wallet_history` et `wallet_statistics`
- **Points faibles** :
  1. Aucun cost basis persisté dans `crypto_positions` — tout est dérivé des ordres
  2. Réalisé P&L utilise `amount_fiat` (gross) pour les SELL au lieu de `amount_to` (net) — surévaluation du realized par les frais
  3. Pas de lien explicite entre NAV, cash EUR et P&L au niveau portefeuille
  4. Pas de traçabilité des flux externes (dépôts/retraits) pour l’invariant C

### Principaux gaps

1. **Swap crypto ↔ crypto** : modèle non prévu, aucune valeur de référence figée
2. **Invariants comptables** : non vérifiés ni documentés
3. **Champs manquants** : `cost_basis_consumed`, `realized_pnl_generated` par ordre, `reference_currency` figée
4. **Cash flow net** : pas de table agrégée dépôts - retraits pour l’invariant C

---

## 2. Current System Audit

### A. Exchange Engine

#### BUY

- **Fichier** : `api/services/exchange/service.py` — méthode `buy()`
- **Flow** : validation → résolution prix (ask) → calcul crypto (volume_raw, fee_crypto, client_crypto) → débit EUR client → crédit EUR settlement → création `exchange_order` → crédit `crypto_position` → incrément `crypto_settlement_delta`
- **Données persistées** dans `exchange_orders` :
  - `side`, `asset`, `amount_crypto` (net client), `amount_fiat` (fiat payé)
  - `price` (EUR), `currency`, `from_asset`, `to_asset`, `amount_from`, `amount_to`
  - `fee_amount`, `fee_asset`, `status`, `external_reference`, `metadata_`

#### SELL

- **Flow** : validation → résolution prix (bid) → calcul EUR (gross, fee, net) → débit position crypto → crédit EUR client (net) → création ordre → delta négatif
- **Données** : `amount_fiat` = **gross_eur** (brut), `amount_to` = **net_eur** (reçu client)

#### preview_buy / preview_sell

- Même logique de prix que l’exécution (ask/bid, spread, FX)
- Aucun effet de bord

#### Persistence exchange_orders

| Champ | BUY | SELL |
|-------|-----|------|
| amount_crypto | net (post-fee) | quantité vendue |
| amount_fiat | fiat payé | **gross_eur** |
| amount_to | crypto net | **net_eur** |
| price | EUR/unité | EUR/unité |
| fee_amount | crypto | EUR |

### B. Wallet Statistics

- **Fichier** : `api/services/wallet_statistics/service.py`
- **Source** : `ExchangeOrder` (completed) + `CryptoPosition` + `MarketDataLatestQuote`
- **Calculs** :
  - `total_bought`, `total_sold`, `total_buy_cost`, `total_sell_revenue` (sommes sur ordres)
  - `avg_buy_price` = total_buy_cost / total_bought
  - `cost_basis` = position_size × avg_buy_price
  - `unrealized_pnl` = current_value - cost_basis
  - `realized_pnl` = total_sell_revenue - (total_sold × cost_per_unit) avec cost_per_unit = total_buy_cost / total_bought

**Problème** : `total_sell_revenue` = sum(amount_fiat) = **gross** ; le client reçoit **net**. Le realized est donc surévalué de la somme des frais SELL.

### C. Wallet History / Performance Charts

- **Fichier** : `api/services/wallet_history/service.py`
- **Modes** :
  - `value` : NAV = Σ position_i × price_i (reconstruction positions à partir des ordres)
  - `performance_value` : realized + unrealized PnL (time-series)

- **performance_value** : utilise un cost basis **weighted average** reconstruit pas à pas :
  - BUY : `cost_basis[asset] += amount × price` ; `positions[asset] += amount`
  - SELL : `avg_cost = cost_basis / positions` ; `realized_pnl += amount × (price - avg_cost)` ; `cost_basis -= amount × avg_cost` ; `positions -= amount`

- Cohérent avec la méthode weighted average.

### D. Positions

- **Table** : `crypto_positions`
- **Colonnes** : `client_id`, `asset`, `balance`, `available_balance`, timestamps
- **Pas de** : `cost_basis`, `avg_entry_price`, `total_cost`

Le cost basis est **toujours dérivé** des `exchange_orders` ; aucune réduction explicite du cost basis lors des sells — tout est recalculé.

### E. Cash / EUR Custody

- **Source** : `custody_accounts` + `custody_account_balances`
- **Client EUR** : `find_client_account(client_id, "EUR")` → `available_balance`
- **Settlement EUR** : compte séparé pour le flux BUY/SELL
- **Dépôts/retraits** : via `custody_transactions` (DEPOSIT, WITHDRAWAL)
- **Lien P&L** : le cash EUR n’est pas agrégé avec le P&L dans une formule explicite NAV = cash + crypto_value

---

## 3. Current Cost Basis Model

### Méthode identifiée

**Weighted Average Cost (WAC)** — coût moyen pondéré.

- À chaque BUY : `cost_basis_total += amount × price` ; `quantity += amount`
- À chaque SELL : `avg_cost = cost_basis_total / quantity` ; `realized += amount_sold × (sell_price - avg_cost)` ; `cost_basis_total -= amount_sold × avg_cost` ; `quantity -= amount_sold`

### Implémentation actuelle

- **wallet_statistics** : utilise `total_buy_cost / total_bought` comme coût unitaire moyen, puis :
  - cost_basis position = `position_size × avg_buy_price`
  - realized = `total_sell_revenue - total_sold × cost_per_unit`
- **wallet_history** : reconstruit pas à pas avec la même logique (équivalent WAC).

### Limites

1. **Pas de persistance** : le cost basis n’est jamais stocké ; toute erreur dans les ordres ou toute divergence de logique entre services peut créer des incohérences.
2. **Frais SELL** : le realized utilise le gross au lieu du net (client).
3. **Pas de FIFO/LIFO** : seule la WAC est supportée (choix acceptable, mais non documenté).

---

## 4. Realized / Unrealized P&L Audit

### Comment c’est calculé aujourd’hui

| Composant | Realized | Unrealized |
|-----------|----------|------------|
| wallet_statistics | total_sell_revenue - (total_sold × cost_per_unit) | current_value - cost_basis |
| wallet_history | idem, incrémental par trade | idem, incrémental |
| test_clients (wallet detail) | total_fiat_received - (total_sold × avg_price) | total_value - cost_basis |

- `total_sell_revenue` / `total_fiat_received` = sum(amount_fiat) pour les SELL = **gross_eur**
- Le client reçoit **net_eur** (amount_to). Donc le realized est **surévalué** d’environ 0,5 % (frais) par vente.

### Cohérence

- **realized + unrealized** : mathématiquement cohérent entre eux (même cost basis, même méthode).
- **Cohérence avec NAV** : non vérifiée explicitement. Le NAV affiché (mode `value`) = Σ position × price. La relation NAV = cash + crypto_value n’est pas calculée ni exposée de façon unifiée.

---

## 5. Portfolio-Level Invariants

### Invariant A : NAV = cash EUR + valeur de marché des positions crypto

**Statut** : **Non garanti formellement**.

- Le cash EUR existe (`custody_account_balances`).
- La valeur crypto = Σ (balance × prix) est calculée dans plusieurs endroits.
- Aucun service ne calcule ni ne vérifie `NAV = cash_eur + crypto_value` de façon centralisée.

### Invariant B : Total P&L = realized P&L + unrealized P&L

**Statut** : **Garanti** par construction dans `wallet_statistics` et `wallet_history` (même formule, même cost basis).

### Invariant C : NAV = net external cash flows + realized P&L + unrealized P&L

**Statut** : **Non garanti**.

- `net external cash flows` = dépôts - retraits n’est pas agrégé dans une table dédiée.
- Les `custody_transactions` contiennent les dépôts/retraits, mais il n’y a pas de vue agrégée « net cash flows » utilisée pour cet invariant.
- Les trades internes (BUY/SELL) ne doivent pas créer de richesse : ils transforment EUR ↔ crypto. Avec la WAC et des prix cohérents, cela devrait être respecté, mais ce n’est pas vérifié par des tests.

---

## 6. Swap Crypto ↔ Crypto Accounting Design

### Principe recommandé

Un swap BTC → ETH doit être traité comme :

1. **SELL BTC** dans la devise de référence (EUR) à un prix figé au moment de l’exécution
2. **BUY ETH** dans la devise de référence (EUR) au même moment

Avec une **valeur de référence figée** (ex. EUR) pour les deux jambes, afin d’éviter toute divergence FX ou de prix entre les deux côtés.

### Traitement comptable

| Étape | Action |
|-------|--------|
| 1 | Figer le prix BTC/EUR (bid) et ETH/EUR (ask) à l’instant T |
| 2 | Calculer : `eur_from_sell = amount_btc × price_btc_eur` (gross) ; `fee_eur` ; `net_eur = eur_from_sell - fee_eur` |
| 3 | Calculer : `amount_eth = net_eur / price_eth_eur` (ou avec fee crypto) ; `cost_basis_btc_consumed` ; `realized_pnl_btc = net_eur - cost_basis_btc_consumed` |
| 4 | Créer cost basis ETH : `cost_basis_eth = net_eur` (ou `amount_eth × price_eth_eur`) |
| 5 | Persister deux ordres liés ou un ordre composite avec les deux jambes |

### Valeur de référence

- **reference_currency** : EUR (ou devise de référence du client)
- **reference_notional_gross** : valeur brute de la jambe vendue en EUR
- **reference_notional_net** : valeur nette (après frais) utilisée pour la jambe achetée
- **fx_snapshot_used** : taux FX utilisé si conversion intermédiaire

### Jambe vendue (BTC)

- `cost_basis_consumed` : part du cost basis BTC consommée
- `realized_pnl_generated` : realized sur BTC
- `execution_price_from_in_ref_ccy` : prix BTC en EUR

### Jambe achetée (ETH)

- `execution_price_to_in_ref_ccy` : prix ETH en EUR
- Cost basis ETH = `reference_notional_net` (ou montant crypto × prix)

---

## 7. Required Data Model Enhancements

### Champs à ajouter ou persister

| Champ | Table / Contexte | Priorité | Description |
|-------|------------------|----------|-------------|
| `cost_basis_consumed` | exchange_orders (ou metadata) | **Indispensable** | Cost basis consommé pour les SELL (et swap jambe vendue) |
| `realized_pnl_generated` | exchange_orders | **Indispensable** | Realized P&L généré par cet ordre |
| `reference_currency` | exchange_orders | **Indispensable** | Devise de référence (EUR) |
| `amount_to` | exchange_orders | Existant | Pour SELL = net_eur ; à utiliser pour realized au lieu de amount_fiat |
| `reference_notional_gross` | swap / ordre composite | Utile | Valeur brute en ref currency |
| `reference_notional_net` | swap | Utile | Valeur nette pour jambe achetée |
| `execution_price_from_in_ref_ccy` | swap | Utile | Prix jambe vendue |
| `execution_price_to_in_ref_ccy` | swap | Utile | Prix jambe achetée |
| `fx_snapshot_used` | optionnel | Optionnel | Pour audit FX |
| `cost_basis` | crypto_positions | Utile | Cache du cost basis (évite recalcul) |
| `avg_entry_price` | crypto_positions | Utile | PRU (dérivable de cost_basis/balance) |

### Redondants

- `amount_from` / `amount_to` : déjà présents ; `amount_fiat` pour SELL est redondant avec la logique gross/net si on stocke les deux.

---

## 8. Recommended Accounting PRD

### A. Méthode retenue : Weighted Average Cost

- **Justification** : simplicité, cohérence avec l’existant, pas de lot tracking.
- **Formule** :
  - BUY : `CB_new = CB_old + qty × price` ; `Q_new = Q_old + qty`
  - SELL : `avg = CB / Q` ; `realized += qty × (price - avg)` ; `CB_new = CB_old - qty × avg` ; `Q_new = Q_old - qty`

### B. Realized P&L

- **Vente totale** : `realized = net_received - cost_basis_total` (net = montant reçu client après frais)
- **Vente partielle** : `realized = amount_sold × (sell_price - avg_cost)` ; cost basis restant = `(1 - amount_sold/Q) × CB`
- **Swap** : realized sur jambe vendue = `net_in_ref_ccy - cost_basis_consumed`

**Règle** : utiliser **net** (amount_to pour SELL) et non gross (amount_fiat) pour le realized côté client.

### C. Unrealized P&L

- `unrealized = current_value - cost_basis` avec `current_value = position × market_price` et `cost_basis` dérivé de la WAC.

### D. Invariants globaux

1. **NAV** = cash_eur + Σ (position_i × price_i)
2. **Total P&L** = realized + unrealized
3. **NAV** = net_external_cash_flows + realized + unrealized (avec net flows = dépôts - retraits)

### E. Persistance pour auditabilité

- Par ordre : `cost_basis_consumed`, `realized_pnl_generated`, `reference_currency`
- Pour SELL : préférer `amount_to` (net) pour le realized
- Optionnel : `cost_basis`, `avg_entry_price` dans `crypto_positions` pour cache et vérification

### F. Règles de calcul

- Prix : ask pour BUY, bid pour SELL
- Frais : déduits du montant reçu (crypto pour BUY, fiat pour SELL)
- FX : EUR comme devise de référence ; snapshot au moment de l’exécution pour le swap

---

## 9. Cas critiques — raisonnement

### Cas 1 — BUY simple

- Achat 1000 € de BTC
- Position vaut ensuite 980 €
- **unrealized** = 980 - 1000 = -20 € ✓
- **realized** = 0 € ✓

Le système actuel gère ce cas correctement.

### Cas 2 — SELL total

- Vente totale à 980 € (net reçu client, ex. 975 € après frais)
- **realized** = net_reçu - cost_basis = 975 - 1000 = -25 € (si on utilise le net)
- Avec le code actuel (gross) : realized = 980 - 1000 = -20 € — **sous-évaluation des frais**
- **unrealized** = 0 € ✓

### Cas 3 — SELL partiel

- Achat initial 1 BTC @ 50k
- Vente partielle 0,5 BTC @ 45k
- cost_basis_consumed = 0,5 × 50k = 25k
- realized = 0,5 × (45k - 50k) = -2,5k ✓
- Reliquat : 0,5 BTC, cost_basis = 25k ✓

Le système WAC gère ce cas correctement (wallet_history, wallet_statistics).

### Cas 4 — Plusieurs BUY successifs

- Buy 1 @ 40k, Buy 1 @ 60k → total_cost = 100k, total_qty = 2, PRU = 50k ✓
- Vente partielle 1 @ 55k → realized = 1 × (55k - 50k) = 5k ✓

Cohérent avec la WAC.

### Cas 5 — Futur swap crypto ↔ crypto

- BTC → ETH : vendre X BTC, acheter Y ETH
- Valeur de référence EUR figée au moment T
- **Realized BTC** = notional_eur_net - cost_basis_btc_consumed
- **Cost basis ETH** = notional_eur_net (ou amount_eth × price_eth_eur)
- Aucune création de richesse : la valeur EUR sortie (BTC) = valeur EUR entrée (ETH), à l’instant T

---

## 10. Required Test Matrix

### Scénarios à tester absolument

| # | Scénario | Vérifications |
|---|----------|---------------|
| 1 | BUY simple 1000 € BTC | position = crypto_net ; cost_basis = fiat_spent ; unrealized = value - cost_basis ; realized = 0 |
| 2 | BUY puis valeur baisse (980 €) | unrealized = -20 € ; realized = 0 |
| 3 | SELL total à 980 € | realized = net_received - cost_basis ; unrealized = 0 ; position = 0 |
| 4 | SELL partiel (50 %) | realized = 0.5 × (price - avg_cost) ; cost_basis restant = 0.5 × CB_initial |
| 5 | Plusieurs BUY (40k, 60k) puis SELL partiel | PRU = 50k ; realized cohérent |
| 6 | Invariant A | NAV = cash_eur + crypto_value |
| 7 | Invariant B | total_pnl = realized + unrealized |
| 8 | Invariant C | NAV = net_cash_flows + realized + unrealized (avec dépôts/retraits) |
| 9 | Realized avec frais | Utiliser net (amount_to) pas gross |
| 10 | Swap BTC→ETH (futur) | realized BTC ; cost_basis ETH = notional_net ; pas de création de richesse |

---

## 11. Final Recommendation

### À verrouiller avant d’implémenter le swap

1. **Corriger le realized P&L** : utiliser `amount_to` (net) pour les SELL dans `get_client_asset_sell_totals` ou adapter la formule pour que le realized reflète le net reçu par le client.
2. **Persister cost_basis_consumed et realized_pnl_generated** par ordre (au moins pour les SELL) pour auditabilité et cohérence future.
3. **Documenter et tester les invariants** A, B, C.
4. **Introduire une vue ou table** pour `net_external_cash_flows` (dépôts - retraits) si l’invariant C doit être vérifié.
5. **Définir le schéma d’ordre composite** pour le swap (deux ordres liés ou un ordre avec deux jambes) avec les champs de référence figée.

### Ordre des actions

1. Audit et PRD (ce document) ✓
2. Correction realized (net vs gross) + tests
3. Ajout champs `cost_basis_consumed`, `realized_pnl_generated` sur les SELL
4. Tests des invariants A, B, C
5. Design détaillé du swap (schéma, API, persistance)
6. Implémentation du swap

---

*Document généré par audit du codebase. Aucune modification de code n’a été effectuée.*
