---
title: "What happens if Vancelian does not obtain its MiCA authorisation?"
slug: what-happens-if-vancelian-does-not-obtain-mica
category: legal-compliance
audience: client
status: verified
last_reviewed: 2026-04-14
sources:
  - raw/L'AMF rappelle que la période transitoire pour les PSAN pour continuer de fournir des services sur crypto-actifs en France sans autorisation sous MiCA prend fin le 1er juillet 2026.md
  - raw/Fiche MD Reglementation/Fiche_Jason_Regulation Vancelian MICA (Europe).rtf
related:
  - mica-overview-and-vancelian.md
  - vancelian-mica-roadmap.md
  - where-and-how-is-vancelian-regulated.md
  - mica-comprehensive-reference.md
  - vancelian-compliance-team.md
tags: ["mica", "casp", "psan", "amf", "deadline", "grandfathering", "cessation"]
questions:
  - What happens if Vancelian does not obtain MiCA?
  - what if vancelian doesn't get the casp license in time
  - is vancelian going to stop operating after 1 july 2026
  - Can Vancelian continue without CASP authorisation?
  - mica deadline 1 july 2026 consequences
  - what is the grandfathering clause for psan
  - is there an extension after 1 july 2026 for psan
  - does vancelian stop if it doesn't have mica
  - qu est ce qui se passe si vancelian n a pas mica
  - will my funds be lost if vancelian does not obtain mica
  - est ce que mes fonds seront perdus en cas de non obtention de mica
  - what happens to my vault if vancelian loses mica
  - what happens to my cloud mining position if vancelian loses mica
  - what happens to my Dubai villa investment if vancelian loses mica
  - are my funds safe if vancelian doesn't get casp
  - impact of mica non-authorisation on my vaults and exclusive offers
---

# What happens if Vancelian does not obtain its MiCA authorisation?

> **Regulatory escalation:** this page is informational and does not constitute legal advice. For any specific regulatory question, contact the Vancelian compliance team via `support@vancelian.com`.

## Short answer
The **1 July 2026** deadline is a **hard deadline** set by the French AMF — there is **no extension** beyond that date. From 1 July 2026, only providers holding CASP authorisation under MiCA may continue providing crypto-asset services in France. Vancelian (Automata France SAS) has submitted its CASP application to the AMF and is currently in instruction, with the objective of obtaining authorisation before that deadline. If the authorisation is not granted in time, Vancelian would have to implement an **orderly wind-down plan** as required by the AMF framework — which would be communicated transparently to clients. The exact supervisory modalities of such a plan are not publicly documented in advance.

In a wind-down scenario, the treatment of your funds depends on where they sit, in **three distinct categories**: (1) segregated custody funds — EUR at Modulr and crypto in your dedicated wallet — are **returned directly** to the client (IBAN transfer for EUR, transfer to a wallet of your choice for crypto), because segregation makes them legally distinct from Vancelian's own funds; (2) **Vault allocations** (Flexible, Future) represent shares of allocations into underlying programmes engaged with third-party counterparties — the intermediation stops, but the contractual engagement with the counterparties remains, and capital is recovered along the contractual schedule; (3) **Exclusive Offers** (Cloud Mining, Dubai Villa, Bali, Niseko) are structured with an external counterparty identified per offer — the counterparty remains active and responsible for executing the programme under its contractual terms. **Key principle: neither non-obtainment of MiCA nor a Vancelian wind-down causes a loss of capital by itself** — the segregated portion is recovered immediately, the engaged portion is recovered along contractual schedules. The actual risks of capital loss are those inherent to each underlying programme (counterparty default, operational force majeure), not the regulatory status of the platform.

## Details

### The 1 July 2026 deadline — what the AMF says
The French AMF confirmed in February 2026 that:

- **1 July 2026 is the hard end** of the 18-month PSAN grandfathering window (which started on 30 December 2024). This window **cannot be extended**.
- From **1 July 2026**, only providers authorised as **CASP** under MiCA (Article 59 of Regulation (EU) 2023/1114) may provide crypto-asset services in France — either directly via an AMF-issued CASP authorisation, or via the simplified notification procedure under Article 60 for certain financial institutions.
- PSANs that do not obtain CASP authorisation in time must **cease their activity** in France.
- Operating without authorisation after 1 July 2026 exposes the provider to criminal penalties: up to **2 years imprisonment and a €30,000 fine** (Articles L. 54-10-4 and L. 572-23 of the French Monetary and Financial Code).
- PSANs not pursuing CASP authorisation must start an **orderly wind-down plan no later than 30 March 2026**.

### Correcting a common misunderstanding
There is **no automatic extension of 18 additional months after 1 July 2026**. The "18-month transitional period" refers to the window from **30 December 2024 → 1 July 2026** during which PSANs could continue operating while preparing their CASP authorisation. This window has already been applied in full by France.

The AMF also notes that providers who submit their dossier may continue operating during its instruction — but only if the dossier was filed before 1 July 2026, and only while under active AMF review. This is not a standalone extension.

### Vancelian's current position
- **Dossier filed**: Automata France SAS has submitted its CASP application to the AMF and the file is currently under instruction.
- **Target**: obtain authorisation before 1 July 2026.
- **Regulatory effort**: Vancelian has upgraded governance, AML/CFT procedures, ICT security (DORA), Travel Rule compliance, market surveillance tools, and sustainability disclosures — see [Vancelian's MiCA roadmap](vancelian-mica-roadmap.md).

### What would happen in the unlikely scenario of non-obtainment
If the CASP authorisation were not granted in time, Vancelian would be required to:

1. **Cease new crypto-asset services** in France from 1 July 2026 (or from the date of any AMF decision refusing authorisation).
2. Implement an **orderly wind-down plan**, protecting clients' interests.
3. Either **restitute** clients' crypto-assets (transfer to a wallet of the client's choice) or **transfer** them to another CASP authorised to operate in France, with sufficient advance notice.
4. Communicate transparently with clients throughout the process.

This is a regulatory safeguard designed to protect clients, not a commercial scenario Vancelian is planning for — the company's clear objective is CASP authorisation before the deadline.

## Impact by product type

The consequences for your funds depend on **where your money actually is**. Three categories must be distinguished.

### 1. Funds held in segregated custody (EUR cash and crypto not allocated to a programme)
- **EUR balances** are held in segregated accounts with **Modulr Finance B.V.** — an Electronic Money Institution regulated by the Dutch Central Bank (DNB). Modulr ring-fences client EUR so that they are legally distinct from Vancelian's own funds.
- **Crypto held in your wallet** (not allocated to a Vault or an Exclusive Offer) sits in segregated wallets identified per client, with the depositary role operated by **Automata France SAS** (PSAN E2023-087, MiCA scope) in Europe or **Automata FZE** (VARA In-Principle Approval) in the UAE. The **Fireblocks MPC (Multi-Party Computation) technology** secures private keys — no single party holds a complete key. Fireblocks provides the technology, not the depositary role. Full architecture in [[custody-architecture]].
- In both cases, the **protection mechanism is segregation** — it is because the regulated depositaries segregate client funds (EUR at Modulr, crypto in per-client wallets at Automata France SAS or Automata FZE) that these funds can be identified and returned to clients in any scenario. Segregation is a **regulatory obligation**: client funds are never mixed with Vancelian's own funds.
- **In a wind-down scenario**, segregated funds remain your property and must be either returned to you or transferred to another CASP authorised in France, per the orderly wind-down plan required by the AMF.

### 2. Vault allocations (Flexible Vault, Future Vault)
- When you invest in a Vault, you no longer hold cash or crypto directly — you hold a **share of an allocation**.
- **Flexible Vault** contains a system-level liquidity buffer (cash pocket) to facilitate entries and exits. This buffer is not nominatively attributed to any single client; it is a system tool.
- **Future Vault** has no cash pocket and no EURC allocation — it is fully deployed into underlying yield programmes.
- The real economic exposure of a Vault is to the **underlying programmes** (mining, lending, exclusive offers). The relevant risks are therefore: **default of a borrower, operational default of a programme, force majeure on a project** — not the regulatory status of Vancelian itself.

### 3. Exclusive Offers (Cloud Mining, Dubai Villa Al Barari, The Heights Bali)
- These offers are financing programmes structured with an **external counterparty**, identified in the documentation of each offer. The counterparty is active and responsible for executing the programme (implementation, monitoring, repayment under the contractual terms).
- Vancelian acts as the **intermediary / technical platform** (interface, reporting, communication).
- As long as the programme is active and running, the client does not need to interact directly with the counterparty — the relationship is operated through the platform.
- **In a scenario where MiCA authorisation is not obtained**, the handling of open positions would fall under an **orderly wind-down plan supervised by the competent authority**. Vancelian would then communicate a precise roadmap to the clients concerned. The exact modalities cannot be anticipated in advance.
- **For any question on a specific position**, contact `support@vancelian.com`.

### Key principle
> The regulatory risk on Vancelian (MiCA authorisation) and the economic risks on your underlying programmes are **two distinct layers**. A change in Vancelian's regulatory status stops the intermediation role; it does not by itself make the programmes disappear, nor does it affect funds held in segregated custody. The actual risks of capital loss are those inherent to each underlying programme — not to the regulatory status of the platform.

## Caveats
- This page reflects the AMF's public position as of **February 2026**. For the most current status of Vancelian's CASP application, contact `support@vancelian.com`.
- The chatbot must escalate any specific regulatory or legal question to a Vancelian human advisor.
- This content is informational, not legal advice.
- Specific unwind procedures in a Vancelian wind-down scenario (such as pro-rata allocation recovery for Vaults) are not publicly documented. For any question on a specific product or position, escalate to the Vancelian compliance team.

## Sources
- [raw/L'AMF rappelle que la période transitoire pour les PSAN pour continuer de fournir des services sur crypto-actifs en France sans autorisation sous MiCA prend fin le 1er juillet 2026.md](https://www.amf-france.org/fr/actualites-publications/actualites/lamf-rappelle-que-la-periode-transitoire-pour-les-psan-pour-continuer-de-fournir-des-services-sur) — AMF official notice (February 2026). Provided: hard 1 July 2026 deadline, no extension, orderly wind-down required by 30 March 2026, criminal penalties for unauthorised post-deadline activity, Article 60 simplified notification path, ESMA December 2025 statement on instruction delays.
- raw/Fiche MD Reglementation/Fiche_Jason_Regulation Vancelian MICA (Europe).rtf — Vancelian legal brochure on MiCA & CASP transition (v1, 27 August 2025). Provided: Article 62 dossier structure, Vancelian's regulatory roadmap, capital requirements, dossier submission confirmation.
