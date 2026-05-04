---
title: Own-account interposition — how Vancelian executes trades
slug: own-account-interposition
category: concepts
audience: internal
status: draft
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 27_Politique d'exécution des ordres_Automata France.docx
related:
  - wiki/concepts/vancelian-glossary.md
  - wiki/faq/legal-compliance/where-and-how-is-vancelian-regulated.md
tags: [interposition, MiCA, execution, trading, regulatory]
---

# Own-account interposition — how Vancelian executes trades

## Summary

Automata France (Vancelian's legal entity) executes all client crypto-asset transactions through systematic own-account interposition. This means Automata is always the counterparty to every trade — clients never trade directly with each other or with external exchanges. This model is distinct from order execution for third parties (RTO), which Automata does not provide.

## Details

### What own-account interposition means

When a client initiates a trade (buy/sell crypto, exchange one asset for another), Automata France steps in as the counterparty. The client's only counterparty is Automata — never a peer client or external venue.

This differs from a traditional exchange where:
- Clients place orders in a central order book
- Orders are matched peer-to-peer or against liquidity pools
- The exchange is a venue operator, not a counterparty

With Automata's model:
- The client's transaction is NOT an "order" in the MiCA sense
- Automata discretionarily determines the price within its spreads and conditions
- Settlement occurs directly between client and Automata

### Two service types under this model

Automata provides two crypto services, both with own-account interposition:

1. **Crypto-to-crypto exchange** (e.g., BTC ↔ ETH)
2. **Crypto-to-fiat buy/sell** (e.g., buy BTC for EUR, sell ETH to EUR)

Both routes follow the same interposition principle: Automata is always the counterparty.

### Why Automata uses own-account interposition

- **Regulatory clarity under MiCA.** Operating as an interposition model (not RTO) simplifies compliance with Article 3.1.21 MiCA and related execution obligations.
- **Operational control.** Automata can manage price discovery, spreads, custody conditions, and settlement timing internally.
- **Best execution obligation still applies.** Even though Automata is the counterparty, it must execute trades at prices, costs, and speeds that represent best execution for the client.

### Client consent

Clients consent to the own-account interposition model through Vancelian's Terms & Conditions (TCs). The TCs disclose that:
- Automata is the counterparty
- Prices are discretionarily set by Automata
- Client funds are segregated: EUR held with Modulr (EMI regulated by DNB), crypto custodied by Vancelian in per-client segregated wallets secured via the Fireblocks MPC technology

### Best execution standard

Under Article 78 of MiCA (Regulation EU 2023/1114), Automata must ensure best execution on:
- **Price** — the rate at which the trade executes
- **Cost** — fees and spreads charged
- **Speed** — timeliness of settlement
- **Custody conditions** — how assets are held and protected

Automata monitors these factors and documents its execution approach in its execution policy (Annexe 27).

### Post-trade transparency

- **Immediate confirmation.** Client receives a trade confirmation immediately after execution.
- **Quarterly AMF reporting.** Automata reports aggregated execution data to the French financial authority (AMF) in its quarterly compliance report.

## Regulatory basis

- **Article 78, Regulation (EU) 2023/1114 (MiCA)** — best execution of crypto-asset orders
- **Article 3.1.21, MiCA** — definition of RTO (order execution for third parties); Automata does not provide this service
- **Annexe 27, Execution Policy** — Automata's detailed execution procedures and best execution criteria

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 27_Politique d'exécution des ordres_Automata France.docx] — Automata's execution policy; defines own-account interposition as the operational model and confirms best execution obligations under MiCA Article 78
