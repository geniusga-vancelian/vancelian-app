# ADR 008 — Virtual Wallet Trade Primitive

| Champ | Valeur |
| --- | --- |
| **Statut** | **Accepté** |
| **Date** | 2026-06-11 |
| **Décideurs** | Équipe Arquantix / Vancelian |
| **Lié à** | ADR 006 (Accounting Event Schema) · ADR 007 (Swap Core + Settlement Router) |
| **Implémentation** | `services/trade_core/` · `services/portfolio_engine/wallets/resolver.py` · `services/settlement/wallet_ledger.py` |

---

## 1. Problème

Le swap portail fonctionne de façon fiable ; le rééquilibrage bundle échoue malgré un rail LI.FI partagé, car la **comptabilité** et l’**orchestration** sont implémentées en parallèle (portfolio_id + instrument_id + position_type) au lieu d’une primitive unique paramétrée par section.

---

## 2. Décision

### 2.1 Virtual Wallet = `pe_wallet_containers.id`

Un **wallet virtuel** est un compartiment comptable PE (`WalletContainer`), pas un wallet on-chain.

| `wallet_type` | Usage |
| --- | --- |
| `spot_wallet` | Positions actif (AV, BTC, ETH…) |
| `cash_wallet` | Cash leg bundle (USDC, EURC…) |

**Règle** : même symbole, portfolios différents → **wallet_id différent**.

### 2.2 Custody vs virtual

- **Custody** : un wallet Privy embedded par personne (inchangé).
- **Virtual** : débit `wallet_from_id` + crédit `wallet_to_id` après `CONFIRMED`.

### 2.3 Contrat `execute_trade`

```python
TradeRequest(
    wallet_from_id: UUID,
    wallet_to_id: UUID,
    instrument_from_id: UUID,
    instrument_to_id: UUID,
    quantity_from: Decimal,
    correlation_id: UUID,
    metadata: dict,
)
```

Tout trade LI.FI :
1. Quote via Swap Core (ADR 007)
2. Audit swap enrichi : `wallet_from_id`, `wallet_to_id`, `correlation_id`
3. Settlement via `SettlementRouter` + `wallet_ledger.settle_trade`

### 2.4 Lien ADR 006

`portfolio_scope` et `portfolio_id` sont **dérivés** de `wallet_from_id` / `wallet_to_id` — pas de `section_id` string parallèle.

### 2.5 Transferts internes (hors LI.FI)

Dépôt bundle (direct USDC → bundle cash) = `execute_transfer(wallet_from_id, wallet_to_id, qty)` — même ledger virtuel, rail `internal_transfer`.

---

## 3. Invariants

| ID | Règle |
| --- | --- |
| I1 | N legs = N `execute_trade` — jamais mega-swap |
| I2 | Swap Core ne touche pas `pe_position_atoms` directement |
| I3 | Tout mouvement économique = paire débit/crédit wallet virtuel |
| I4 | `ExchangeService.swap` (ledger interne) reste distinct de `execute_trade` (LI.FI) |

---

## 4. Migration (référence plan)

| Phase | Livrable |
| --- | --- |
| 1 | `VirtualWalletResolver` + bootstrap + backfill `PositionAtom.wallet_id` |
| 2 | `trade_core.execute_trade` + submit unifié |
| 3 | `wallet_ledger.settle_trade` |
| 4 | Rebalance = planner + chaîne trades ; web `executeTrade` |

---

*ADR 008 — verrouillage wallets virtuels · pilote Kings.*
