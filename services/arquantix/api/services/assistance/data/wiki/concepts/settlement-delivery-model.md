---
title: Settlement and delivery — the hybrid EUR-immediate / crypto-deferred model
slug: settlement-delivery-model
category: concepts
audience: internal
status: draft
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
related:
  - wiki/concepts/own-account-interposition.md
  - wiki/faq/crypto/how-can-i-trade-cryptoassets-on-the-vancelian-app.md
tags: [settlement, delivery, Modulr, Fireblocks, custody, trading]
---

# Settlement and delivery — the hybrid EUR-immediate / crypto-deferred model

## Summary

Vancelian uses a hybrid settlement model: EUR (fiat) is settled immediately via Modulr's segregated accounts, while crypto-assets are delivered at end-of-day to the client's Vancelian-custodied wallet (key security managed via the Fireblocks MPC technology). This design balances operational efficiency with client fund protection — fiat payment is guaranteed instantly, while crypto is consolidated and delivered in batches at day-end to optimize on-chain costs and liquidity management.

## Details

### The hybrid model

**EUR settlement (immediate):**
- When a client buys crypto or sells to EUR, the EUR leg is settled immediately.
- EUR is debited from the client's segregated settlement account (held with Modulr).
- The client's EUR account balance updates in real time.

**Crypto-asset delivery (deferred, end-of-day):**
- The crypto-asset side of the trade is not delivered immediately.
- Throughout the trading day, client trade requests accumulate.
- At end-of-day, Vancelian consolidates all pending orders.
- Net deltas per client per asset are calculated (e.g., Client A net +0.5 BTC, −0.1 ETH).
- Assets are delivered at end-of-day to the client's dedicated wallet, custodied by Vancelian (key operations run through the Fireblocks MPC infrastructure).

### Why this model

1. **EUR immutability.** EUR is held in segregated bank accounts (Modulr); settlement is irreversible once debited.
2. **Crypto consolidation.** By batching delivery, Vancelian reduces on-chain transaction costs and optimizes liquidity use.
3. **Client fund protection.** EUR in the settlement account remains client property (segregation enforced at Modulr). Crypto is placed in the client's dedicated wallet — custodied by Vancelian in segregation — within one day.

### Client EUR account (segregated)

- Held with Modulr Finance B.V., an Electronic Money Institution regulated by the Dutch Central Bank (DNB).
- Remains the property of the client — Automata France does NOT have claims on these funds.
- Updated in real time when EUR is deposited, withdrawn, or used in trades.

### Crypto-asset custody

- All client crypto-assets are **custodied by Vancelian** in segregated wallets, with key security handled via the **Fireblocks MPC technology** (Multi-Party Computation — no single party holds a complete private key). Fireblocks provides the technology infrastructure; the custody itself is operated by Vancelian.
- Delivered end-of-day to the client's designated wallet.
- A multi-signature transaction policy and the underlying MPC architecture mean no single Vancelian operator can unilaterally move client assets.

### Liquidity pocket and rebalancing

See [[wiki/policies/vault-allocation-mechanics.md]] for how Flexible and Future Vaults manage liquidity internally. In brief:

- Vaults hold a liquidity pocket (EUR/EURC) to enable entries and exits.
- Daily rebalancing adjusts allocations and interest payments.
- This does not affect the settlement/delivery process for regular trades outside Vaults.

### LP liquidity adjustment

- When Vancelian needs to source crypto liquidity for a client trade, it draws from its own treasury (company funds).
- Client funds are **never** used to adjust liquidity positions.
- This ensures the immediate EUR settlement and end-of-day crypto delivery schedule is maintained without delay.

### Example walkthrough

**Scenario:** Client buys €100 worth of BTC at 10:00 AM.

1. **10:00 AM (immediate):** €100 is debited from the client's segregated EUR account (Modulr). The client's balance shows −€100 instantly. The BTC trade is recorded but not yet delivered.

2. **End-of-day (e.g., 20:00):** Vancelian consolidates all BTC trades for this client during the day. If the client bought only BTC, net delta is +0.00317 BTC (illustrative). This amount is transferred from Vancelian's hot wallet to the client's dedicated Vancelian-custodied wallet (operation orchestrated through the Fireblocks MPC infrastructure).

3. **Next morning:** Client can see their BTC balance in their Vancelian wallet.

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — Vancelian's flow diagram; details EUR immediate settlement via Modulr, crypto end-of-day delivery via Fireblocks, and LP liquidity sourcing from company treasury
