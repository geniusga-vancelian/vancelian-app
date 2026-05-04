---
title: "Recovery of your funds in case of a Vancelian default"
slug: custody-recovery-in-default
category: concepts
audience: client
status: draft
last_reviewed: 2026-04-29
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
  - raw/faq/faq-9224836184081-how-does-vancelian-ensure-the-security-and-management-of-my-.md
related:
  - wiki/concepts/custody-architecture.md
tags: [bankruptcy, default, faillite, défaillance, segregation, recovery, modulr, automata, mica, vara]
questions:
  - What happens to my funds if Vancelian goes bankrupt?
  - Que se passe-t-il en cas de défaillance de Vancelian ?
  - Que deviennent mes fonds si Vancelian fait faillite ?
  - Que se passe-t-il en cas de cessation d'activité de Vancelian ?
  - How do I recover my crypto if Vancelian fails?
  - Comment récupérer mes fonds si Vancelian s'arrête ?
  - Are my funds protected in case of insolvency?
---

# Recovery of your funds in case of a Vancelian default

> This page addresses only the specific scenario of a Vancelian default, bankruptcy, or cessation of activity. For ordinary questions on who holds your funds in normal operation, refer to [[custody-architecture]].

## Short answer

Segregation is the legal mechanism that keeps your assets identifiable per client and outside Vancelian's own balance sheet. In a default scenario, your funds are not part of the Vancelian estate and cannot be seized to pay Vancelian's debts. The recovery path differs by pocket : EUR is restituted by Modulr Finance B.V. via IBAN transfer ; crypto-assets and the EURC pocket are transferable from the Automata-operated wallets to a wallet of your choice ; the allocation engaged in an Exclusive Offer or Cloud Mining program follows the contractual maturity and recovery terms of the relevant counterparty.

## Why segregation protects you

Segregation is required by the regulatory frameworks that govern each depositary. Modulr Finance B.V. holds your euros in segregated payment accounts under the supervision of De Nederlandsche Bank (DNB) and within the safeguarding rules of the Financial Supervision Act. Automata France SAS holds your crypto-assets in segregated wallets identified per client under the PSAN E2023-087 registration and within the MiCA framework. Automata FZE applies the same segregation rule under the VARA In-Principle Approval. In all three cases, your assets are legally outside the depositary's own balance sheet and outside Vancelian's own balance sheet — they are your property, identified as such, at all times.

## Recovery path by pocket

| Pocket | Depositary in normal operation | Recovery path in default |
|---|---|---|
| EUR balances | Modulr Finance B.V. | Restitution via IBAN transfer to your bank account, applying the safeguarding rules of the Dutch Central Bank |
| Crypto-assets and EURC pocket of a Vault | Automata France SAS (Europe) / Automata FZE (UAE) | Transfer of the segregated wallet content to a wallet of your choice |
| Allocation engaged in an Exclusive Offer or Cloud Mining | Contractual counterparty of the program (Vancelian LTD JV for Cloud Mining, Solaria Group for Dubai, The Heights Bali SAS for Bali) | Recovery follows the contractual maturity and recovery terms of the program, as documented in the Conditions Particulières |

## What is not changed by a Vancelian default

Your **ownership** of your assets is never transferred to Vancelian, Modulr, Automata or any program counterparty during normal operation, and a Vancelian default does not change that fact. The depositary entities are required to keep your assets identifiable per client at all times — segregation is not just an accounting label, it is a legal mechanism enforced by the regulator that supervises each depositary. A Vancelian default is therefore handled at the level of the Vancelian operational umbrella ; the regulated depositaries continue to hold your assets and to apply the recovery path described above.

## What may take time in a default scenario

The recovery itself is mechanically guaranteed by segregation, but practical execution may take time depending on the nature of the default. The EUR restitution by Modulr typically follows the safeguarding procedures defined by DNB. The crypto restitution by Automata follows the procedures defined by the AMF (PSAN/MiCA) or VARA. The recovery of the allocation engaged in an Exclusive Offer or Cloud Mining program follows the contractual maturity of the program — meaning it may not be immediate even in a default scenario, since the underlying engagement (real-estate financing, mining capacity contract) has its own timeline. For any specific question on the recovery timeline, refer to the Conditions Particulières of the program and contact [support@vancelian.com](mailto:support@vancelian.com).

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — segregation architecture and recovery path per asset class
- [raw/faq/faq-9224836184081-how-does-vancelian-ensure-the-security-and-management-of-my-.md] — Modulr safeguarding statement under the Financial Supervision Act
