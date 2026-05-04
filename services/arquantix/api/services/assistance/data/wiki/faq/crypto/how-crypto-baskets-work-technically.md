---
title: "How do Crypto Baskets work technically?"
slug: how-crypto-baskets-work-technically
category: crypto
audience: client
status: verified
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 27_Politique d'exécution des ordres_Automata France.docx
related:
  - wiki/faq/crypto/what-is-a-crypto-basket.md
  - wiki/faq/crypto/what-crypto-baskets-are-available-and-what-is-their-allocati.md
  - wiki/faq/crypto/what-is-rebalancing.md
tags: [crypto-basket, multi-digital-assets, rebalancing, allocation, portfolio]
questions:
  - "How do Crypto Baskets work technically?"
  - "What happens when I deposit into a Crypto Basket?"
  - "How does rebalancing work in a Crypto Basket?"
  - "How are Crypto Basket exchanges executed?"
  - "Can I choose my own rebalancing frequency?"
  - "What is the capital preservation feature in Crypto Baskets?"
---

# How do Crypto Baskets work technically?

## Short answer

Crypto Baskets (called "Multi-Digital Assets" service) let you invest in a fixed allocation of multiple crypto-assets. When you deposit, your EUR or USDC is automatically exchanged into the target crypto allocation. Rebalancing happens at your chosen frequency to maintain the target allocation. All exchanges are executed through Vancelian's own-account interposition model. You can also activate a "Capital Preservation" feature that shifts part of your allocation to stablecoins during market downturns.

## Details

### What a Crypto Basket actually is
A Crypto Basket — named "**Multi-Digital Assets**" in the execution policy — is a **fixed-allocation portfolio** of several crypto-assets, proposed by Automata France either as a thematic bundle (a theme the team has selected) or as a crypto bundle (a predefined market exposure). The core characteristic is that each basket has a **predefined allocation percentage per asset**, which is what you subscribe to when you deposit.

### What happens when you deposit
When you select a basket and choose the amount you want to deposit (in EUR or USDC), the platform computes the exchanges required to match the target allocation. Those exchanges are executed through Vancelian's **own-account interposition model** — Vancelian acts as principal and routes the orders to its selected liquidity providers, rather than matching you to a public order book. Once execution completes, you receive a **recap** showing the final allocation and any applicable fees, and your portfolio becomes active.

### How withdrawals unfold
On a withdrawal, the mechanic runs in reverse: you indicate the amount you want to take out (in EUR or USDC), the platform computes the reverse exchanges, and the **execution order is sells first, buys second** — overweight assets are converted to stablecoins before any realignment buy is placed. Funds are then returned in your chosen denomination with a confirmation receipt.

### How rebalancing works — the mechanism that keeps the basket aligned
Rebalancing is what maintains the target allocation as prices move. The trigger is either **your chosen frequency** (daily, weekly, monthly) or an **allocation target change**. At each trigger, the platform computes the current percentage of each asset in your portfolio, detects the deviation against the target, and — if the deviation is outside tolerance — calculates the exchanges needed to restore the target allocation. As with withdrawals, the execution order is sells first (overweight assets), then buys (underweight assets). A recap is issued at the end of each rebalance showing which assets were adjusted and any fees incurred. If the portfolio is already within tolerance, no exchanges are executed.

### The Capital Preservation feature — how it reduces exposure
On top of the basket logic, Vancelian offers a **Capital Preservation** feature that lets you shift part of your exposure into stablecoins. You select one of **five risk profiles**, each determining the percentage of the portfolio allocated to stablecoins — lower-risk profiles carry more stablecoin weight and therefore less exposure to crypto volatility. The feature can be activated or deactivated at any time, and takes effect on the next rebalancing window. It **reduces but does not eliminate** market risk: the non-stablecoin portion of the portfolio remains exposed to the market.

### The execution layer — own-account interposition
All exchanges — crypto ↔ fiat or crypto ↔ crypto — follow Vancelian's standard execution policy. Automata France acts as **principal via own-account interposition**, executing trades on your behalf across a selected panel of **liquidity providers** (Scrypt, BitMart, and others), with orders routed to optimise price and execution quality under best-execution rules. Fees are indicative — verify current rates in the app or contact Vancelian support to help locate the fee schedule.

## Caveats

- Crypto Baskets involve exposure to crypto-asset price volatility. Past performance does not guarantee future returns.
- Rebalancing may trigger exchange fees. Verify the current fee structure in the app or contact Vancelian support to help locate the fee documentation.
- The Capital Preservation feature reduces but does not eliminate market risk.
- Deposit and withdrawal processing may incur fees (indicative — confirm with Vancelian).
- Rebalancing frequency and capital preservation adjustments take effect on the next scheduled rebalancing window.
- Market conditions may delay execution slightly beyond the normal rebalancing cycle.

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — Technical flow diagrams showing deposit, withdrawal, rebalancing, and capital preservation mechanics.
- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 27_Politique d'exécution des ordres_Automata France.docx] — Execution policy covering own-account interposition, liquidity provider selection, best execution, and capital preservation profile options.
