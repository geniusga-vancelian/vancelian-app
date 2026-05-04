---
title: Vault allocation mechanics — liquidity pocket, rebalancing, and interest payments
slug: vault-allocation-mechanics
category: policies
audience: internal
status: draft
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
related:
  - wiki/faq/savings/what-is-the-flexible-vault.md
  - wiki/faq/savings/how-does-the-future-vault-work.md
  - wiki/faq/savings/how-flexible-vault-returns-are-paid.md
tags: [vault, flexible, future, allocation, liquidity, rebalancing, interest, EURC]
---

# Vault allocation mechanics — liquidity pocket, rebalancing, and interest payments

## Summary

A Vancelian Vault is a diversified portfolio composed of: (1) a liquidity pocket in EUR/EURC (not remunerated per MiCA) + (2) allocations to yield-bearing investments such as BTC loans and mining programs. The liquidity pocket enables flexible entries/exits and reduces overall yield. Daily rebalancing adjusts allocations and converts interest income (paid in BTC) to EURC for stability. All allocation decisions are made by an internal management committee of finance and blockchain professionals.

## Details

### Vault structure

A Vault is not a single asset but a basket allocation across:

1. **Liquidity pocket (EUR/EURC):**
   - A holding of stablecoins and EUR equivalents
   - NOT remunerated (earns no interest)
   - Enables deposits, withdrawals, and internal liquidity for rebalancing
   - Acts as a "buffer" — higher liquidity pocket = lower overall yield but easier exits

2. **Yield-bearing allocations:**
   - BTC loan programs (e.g., collateralized lending)
   - Mining programs (e.g., hashpower investments)
   - Other regulated crypto yield strategies (subject to Vancelian's investment criteria)
   - These allocations earn interest, typically paid in BTC

### Liquidity pocket mechanics

- **Purpose:** Enables clients to enter and exit Vaults without liquidating yield-bearing allocations immediately.
- **Trade-off:** A larger liquidity pocket reduces the proportion of capital allocated to yield, thus lowering overall portfolio returns.
- **Sizing:** Vancelian's management committee decides the liquidity pocket size based on:
  - Redemption volume forecasts
  - Market conditions
  - Risk management goals

### Allocation decisions

- Made by an **internal management committee** comprising Vancelian's finance and blockchain professionals.
- The committee reviews:
  - Performance of existing allocations
  - New investment opportunities
  - Risk exposure across asset classes and counterparties
  - Client redemption patterns
- Decisions are documented and reviewed quarterly (or more frequently if market conditions change).

### Daily rebalancing process

Rebalancing occurs in two phases:

**Phase A: Allocation adjustment**
- The management committee reviews the current allocation mix.
- If yield-bearing assets have grown (e.g., interest accrual), or if redemption requests warrant a shift to higher liquidity, adjustments are made.
- Crypto holdings may be rebalanced between yield programs and the liquidity pocket.

**Phase B: Interest payment**
- Yield-bearing allocations (e.g., BTC loan programs) generate interest, typically paid in BTC.
- BTC interest is aggregated across all allocations.
- BTC is converted to EURC (stablecoin) via a designated trading pair at market rates.
- EURC is credited to the client's account or reinvested per their allocation settings.

### Interest payment and conversion

- **Frequency:** Interest accrues daily and is settled daily (Phase B).
- **Currency:** Interest is received in BTC from yield programs, then converted to EURC.
- **Rate:** Rates are **indicative** and subject to market conditions and Vancelian's internal policies. Confirm current rates with a Vancelian advisor.
- **Conversion cost:** The BTC → EURC conversion is at market rates; any conversion cost is borne by Vancelian, not the client.

### Entry and exit (withdrawal)

**Entries (deposits):**
- Client deposits EUR (or crypto).
- EUR is converted to EURC and added to the liquidity pocket.
- Client's share of the Vault increases.

**Exits (withdrawals):**
- Withdrawal requests are queued and matched against available liquidity in the liquidity pocket.
- If liquidity is sufficient, withdrawal is processed immediately (subject to Vault-specific timelines, e.g., lock-up for Future Vault).
- If liquidity is insufficient, the withdrawal request enters a dynamic waiting list.
- Vancelian continuously tries to match withdrawals against incoming deposits and interest rebalancing, subject to a maximum waiting period (see [[wiki/faq/savings]]).

### Caveats and operational notes

- **Liquidity pocket size varies.** If client redemptions spike, the liquidity pocket may shrink, temporarily reducing yield on new deposits until it is replenished.
- **Interest accrual depends on allocation performance.** If yield programs underperform, interest payments may be lower than historical averages.
- **Allocation concentrations.** The management committee may concentrate allocations in one asset (e.g., BTC loans) if risk-adjusted returns favor it. Clients accept this as part of the Vault model.
- **Withdrawal queuing.** During periods of high redemptions, clients may experience a short delay (typically 1–5 business days) before their withdrawal is processed. This is detailed in the Vault product FAQ.

## Regulatory context

- The liquidity pocket is NOT remunerated per MiCA (Article 78, Regulation EU 2023/1114), which prohibits remuneration of stablecoins held as settlement or liquidity buffers in certain configurations.
- Yield-bearing allocations comply with MiCA and Vancelian's investment policies.

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — Vault flow diagram; details liquidity pocket structure, daily rebalancing phases (A: allocation adjustment, B: interest payment), EURC conversion, and withdrawal queue mechanics
