---
title: "How do vault liquidity and returns work?"
slug: how-vault-liquidity-and-returns-work
category: savings
audience: client
status: verified
last_reviewed: 2026-04-25
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
related:
  - wiki/faq/savings/what-is-the-flexible-vault.md
  - wiki/faq/savings/how-does-the-future-vault-work.md
  - wiki/faq/savings/how-flexible-vault-returns-are-paid.md
  - wiki/faq/savings/are-there-any-risks-of-capital-loss.md
tags: [vault, liquidity, returns, EURC, rebalancing, buffer, interest, pocket, fixed-rate, smoothing]
questions:
  - "How do vault returns work at Vancelian?"
  - "Why is the Flexible Vault yield lower than the Future Vault?"
  - "What is the liquidity pocket in a vault?"
  - "How are my vault interest payments calculated?"
  - "Can I withdraw from my vault at any time?"
  - "Why might my withdrawal take time from a vault?"
  - "How does Vancelian generate returns on vaults?"
  - "Is the EURC liquidity pocket remunerated?"
---

# How do vault liquidity and returns work?

## Short answer

Vancelian vaults are **diversified pockets** composed of a non-remunerated EURC liquidity layer (used for deposits and withdrawals) and allocations to yield-generating products like Exclusive Offers (BTC loans) and mining programs. The allocation is **defined upfront at the moment of deposit** and may evolve over time within that framework. The liquidity layer ensures you can access your funds, but because it earns no return (as required by MiCA for stablecoins), it reduces the overall yield of the vault. The Future Vault's lock-up period means more of your funds can be allocated to yield-generating products, which is why it typically offers higher rates than the Flexible Vault. The rate distributed to clients is fixed; rates are indicative for new subscriptions and may change — always verify the live rate in the Vancelian app.

## Details

### How a vault is actually built
A Vancelian vault is a **two-layer pocket**. The first layer is a **non-remunerated EURC liquidity reserve**, which holds the deposits and manages the withdrawals — it is the "cash" layer of the pocket. The second layer is the **yield-generating allocation**: exposure to Exclusive Offers (BTC loans to real-world-asset companies), mining programmes, and other selected products. When you deposit into a vault, your funds are converted to EURC and held in segregated wallets with key security delivered through **Fireblocks MPC** technology, where the depositary role is operated by **Automata France SAS** (PSAN E2023-087, MiCA scope) in Europe or **Automata FZE** (VARA In-Principle Approval) in the United Arab Emirates — see [[custody-architecture]] for the full architecture. The allocation is **defined upfront at the moment of deposit** within the framework you accepted at subscription.

### Why the EURC pocket does not pay interest — this is a regulatory point, not a design choice
The most common question on vaults is why the liquidity pocket earns nothing. The answer is a **MiCA compliance requirement**: EURC is a euro stablecoin, and under MiCA, stablecoins must maintain transparent, verifiable backing and cannot be deployed in yield-bearing activities without explicit regulatory approval. Vancelian does not have the latitude to remunerate that pocket — it is a regulatory constraint on the stablecoin itself, not a Vancelian limitation.

### Flexible Vault versus Future Vault — why the yields are structurally different
The difference in indicative returns between the **Flexible Vault** and the **Future Vault** comes directly from the liquidity trade-off. In the Flexible Vault, your funds are accessible on demand: withdrawals are processed from the liquidity pocket via a **dynamic queue** that continuously attempts to match withdrawal requests with incoming deposits, and if the pocket is short of liquidity, your request waits in queue until funds become available. Because this model requires keeping more funds in the non-remunerated pocket, **less of the vault can be allocated to yield products** — and indicative returns are lower.

In the Future Vault, funds are **locked for a fixed term** with no withdrawal available before maturity. Liquidity risk is eliminated, which means a larger share of the vault can sit in yield-generating products. The structural result is a **higher indicative return** than the Flexible Vault. The yield gap is not a pricing decision — it is the direct consequence of the liquidity constraint.

### The daily rebalancing cycle
Every day, the vault runs a two-phase cycle. In **Phase A — allocation review**, Vancelian's management committee (finance professionals and blockchain specialists) reviews the current allocations and decides whether excess liquidity in the pocket can be moved into yield products, with the dual objective of maximising returns while preserving enough liquidity for withdrawals. In **Phase B — interest aggregation**, each yield product pays interest into the vault's omnibus account (BTC from loans, EURC from mining programmes), Vancelian aggregates those flows, and the BTC portion is converted to EURC to maintain a stable vault denomination. Interest is automatically reinvested into the vault unless you have chosen to receive it as a payout.

### Compounding, withdrawal preferences, and what we disclose
If interest is reinvested immediately, it **compounds automatically** inside the vault. You control that preference directly in the app: auto-reinvest or receive as payment. On allocation transparency: Vancelian does **not publicly disclose the exact percentage allocated to each product at any given time**, because those allocations are dynamic and adjust daily based on market conditions, liquidity needs and product performance. The indicative yield you see in the app reflects the **blended yield of all underlying products**, weighted by the current allocation.

### Why your distributed rate stays stable when the allocation rebalances
The rate Vancelian distributes to clients on Vaults is **fixed**: the rate visible in the app at the moment of subscription applies for the duration of your engagement. When the underlying allocation rebalances or one source of yield contracts, small variations on the gross yield are absorbed by **Vancelian's intermediation margin** — so your distributed rate remains the rate you subscribed at. This is the only product family with a fixed distributed rate together with real estate Exclusive Offers; Cloud Mining is the exception, with a contractually variable rate. Full mechanic in [[vancelian-rate-smoothing-and-margin]].

## Caveats

- **Returns are indicative** and depend on market conditions, underlying project performance, and the composition of Exclusive Offers in the vault at any given time
- The EURC liquidity pocket may limit withdrawal speed during periods of high client withdrawals or low incoming deposits
- Interest rates and allocations may change; always check the app for current rates
- Past performance is not a guarantee of future returns
- For specific return information or vault composition documentation, contact Vancelian support to help locate the FAQ, T&C, or the relevant section in the app

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — Describes vault structure, liquidity pocket mechanism, daily rebalancing cycle, interest aggregation, and EURC stablecoin treatment under MiCA
