---
title: "Scrypt (primary liquidity provider)"
slug: scrypt
category: entities
audience: internal
status: draft
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 27_Politique d'exécution des ordres_Automata France.docx
related:
  - wiki/entities/bitmart.md
  - wiki/faq/legal-compliance/how-does-vancelian-execute-trades.md
  - wiki/concepts/own-account-interposition.md
tags: [liquidity-provider, Scrypt, Switzerland, VQF, FINMA, execution]
questions:
  - "Who is Scrypt?"
  - "Is Scrypt regulated?"
  - "What is Scrypt's role at Vancelian?"
  - "What happens if Scrypt is unavailable?"
---

## Summary

Scrypt is Vancelian's primary liquidity provider, handling 65% of Automata France's market transactions. It is a Swiss-regulated platform, member of VQF (Verein zur Qualitätssicherung von Finanzdienstleistungen, a recognized self-regulatory organization) and licensed as a wealth manager by FINMA (Swiss Financial Market Supervisory Authority). Scrypt also maintains its own Best Execution policy, which is shared transparently with Automata France.

## Details

### Role
- Primary execution venue for Automata France's own-account interposition trades
- Processes 65% of Vancelian's market transactions

### Regulatory Status
- **VQF Member**: Verein zur Qualitätssicherung von Finanzdienstleistungen (Association for Quality Assurance of Financial Services) — a recognized self-regulatory organization in Switzerland, focusing on AML and client protection
- **FINMA License**: Licensed as a wealth manager by FINMA (Swiss Financial Market Supervisory Authority)

### Selection & Execution
- **Selection criteria**: infrastructure reliability, regulatory compliance, execution quality
- **Best Execution**: Scrypt maintains and publishes its own Best Execution policy, which is aligned with and shared with Automata France
- **Price execution**: competitively selected among available liquidity providers

### Fallback & Redundancy
- In case of Scrypt's unavailability or cessation of services, orders are automatically redistributed to remaining liquidity providers (primarily BitMart)
- Redistribution is based on capacity and execution quality metrics
- Ensures continuous service availability

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 27_Politique d'exécution des ordres_Automata France.docx] — Execution policy detailing liquidity provider selection, transaction share allocation, regulatory requirements, and fallback procedures.
