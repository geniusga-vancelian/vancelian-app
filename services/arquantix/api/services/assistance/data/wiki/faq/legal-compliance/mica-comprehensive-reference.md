---
title: "MiCA: comprehensive regulatory reference (CASP, capital, governance, conservation)"
slug: mica-comprehensive-reference
category: legal-compliance
audience: internal
status: verified
last_reviewed: 2026-04-14
sources:
  - raw/Fiche MD Reglementation/Fiche_Jason_Regulation Vancelian MICA (Europe).rtf
  - raw/L'AMF rappelle que la période transitoire pour les PSAN pour continuer de fournir des services sur crypto-actifs en France sans autorisation sous MiCA prend fin le 1er juillet 2026.md
related:
  - mica-overview-and-vancelian.md
  - vancelian-mica-roadmap.md
  - dora-cybersecurity-explained.md
  - lcb-ft-aml-compliance.md
  - aktio-vnc-mica-compliance.md
  - vancelian-compliance-team.md
  - vancelian-legal-advisors.md
tags: ["mica", "casp", "regulation", "europe", "reference", "internal", "psan", "dora", "tfr"]
questions:
  - What does MiCA cover in detail?
  - mica casp capital requirements
  - mica governance and conservation rules
  - What services require a CASP license?
  - mica stablecoin art emt rules
  - full mica regulatory reference
  - mica timeline and application dates
  - How does MiCA interact with DORA and TFR?
---

# MiCA: comprehensive regulatory reference

> **Audience:** internal reference for advisors, compliance, and chatbot context. **Source date: 27 August 2025** — verify the most recent version of MiCA delegated acts, RTS/ITS, and ESMA/EBA guidelines before relying on specific clauses. **The chatbot must escalate any specific regulatory question to a Vancelian human advisor — this page is informational, not legal advice.**

## Short answer
MiCA (Regulation (EU) 2023/1114) harmonises across the EU the issuance, public offering, and admission to trading of crypto-assets (including ART and EMT stablecoins) and frames Crypto-Asset Service Providers (CASPs). This page is the comprehensive internal reference covering scope, timeline, CASP services and capital requirements, governance, conservation rules, sustainability disclosures, market abuse, and the interaction with DORA / TFR / GDPR / MiFID II.

## 1. Material scope and exclusions

### MiCA covers
1. The **public offering and admission to trading** of crypto-assets.
2. The **authorisation and obligations of CASPs** (Crypto-Asset Service Providers).

### Major exclusions
- Crypto-assets that qualify as **financial instruments under MiFID II** (these stay under traditional financial law).
- Banking deposits, funds, insurance, pension schemes.
- **Genuinely unique, non-fungible NFTs** (caution: fractionalised series may fall back into MiCA scope).
- **Mining and cloud mining as standalone activities** — no MiCA licence required (other national regimes on energy / consumer protection still apply).

## 2. Token typology (ART / EMT / Other)

| Category | Definition | Regime |
|---|---|---|
| **ART (Asset-Referenced Token)** | References a basket of assets or one or several assets | MiCA ART rules: dedicated authorisation, reserves (composition, segregation, audits), reinforced governance. Significant ART = additional requirements |
| **EMT (E-Money Token)** | 1:1 reference to an official currency | MiCA EMT rules + EMD2: issuance reserved to credit institutions or e-money institutions, whitepaper, redemption mechanism |
| **Other crypto-assets** | Utility tokens, payment tokens (non-EMT), etc. | "Generic" MiCA regime |

## 3. CASP services covered

Under MiCA, the following are CASP-regulated services:
- **Custody and administration** of crypto-assets on behalf of clients.
- **Operation of a trading platform**.
- **Exchange** crypto ↔ fiat and crypto ↔ crypto.
- **Execution of orders** for clients; **reception and transmission of orders** (RTO).
- **Placement** of crypto-assets.
- **Advisory** and **portfolio management** on crypto-assets.
- **Crypto-asset transfer service** (in the TFR / MiCA sense).

## 4. Application timeline & French transition

| Date | Event |
|---|---|
| **30 June 2024** | ART / EMT (stablecoin) provisions enter into force |
| **30 December 2024** | Rest of MiCA applies — including CASP obligations |
| **17 January 2025** | DORA enters into force |
| **1 July 2026** | **Hard end of national grandfathering** (the 18-month transitional window ran from 30 December 2024 to 1 July 2026). From this date, only CASP-authorised providers may operate in France. PSANs without authorisation must cease activity; criminal penalties apply (up to 2 years imprisonment + €30,000 fine). **No extension beyond 1 July 2026** (AMF notice, Feb 2026). |
| **30 March 2026** | Latest date to start an **orderly wind-down plan** for PSANs not pursuing CASP authorisation (AMF, Feb 2026) |

The French AMF doctrine adapts during the transition; the objective is the migration to **CASP authorisation + EU passport**.

## 5. Authorisations and EU passport

### CASP authorisation (Articles 59 et seq.)
- Must be a **legal entity established in the EU**.
- **Article 62 dossier**: programme of operations, governance, ICT systems, internal control, AML/CFT, business continuity & wind-down plan, key policies.
- **Process**: admissibility check → instruction by the National Competent Authority (AMF, CSSF, BaFin, …) → coordination with ESMA / EBA where needed.
- **Passport**: notification + freedom to provide services / freedom of establishment across the EU.

### ART / EMT issuers
- **ART**: dedicated authorisation + reserves (composition, segregation, audits), reinforced governance.
- **EMT**: reserved to credit institutions or EMIs (under EMD2) + whitepaper + redemption mechanism.

## 6. Cross-cutting CASP requirements

| Area | Requirement |
|---|---|
| **Minimum capital** | Tiered by service (see §10) — equity ≥ ¼ of previous-year fixed costs if higher than the minimum |
| **Governance & Fit & Proper** | Administrative body, experienced and trustworthy directors, integrity |
| **Organisation (Art. 68)** | Internal control, risk management, continuity & regularity, orderly wind-down plan, complete record-keeping |
| **ICT & cybersecurity** | Security, backups, traceability, testing — articulated with DORA: critical-function mapping, major incidents, critical TPP oversight, advanced penetration testing |
| **Outsourcing (Art. 73)** | Due diligence, contracts, controls, sub-outsourcing chain management, reversibility — no full delegation of critical functions |
| **Conduct** | Honest, fair, professional behaviour; clear, non-misleading information; marketing consistent with whitepaper / info sheet; sustainability indicators on website |
| **Conflicts of interest (Art. 72)** | Identification / prevention / management + disclosure; restrictions between activities (platform / internal market making, etc.) |
| **Complaints** | Transparent procedure, deadlines, traceability |
| **Client protection** | Suitability tests (advice / management) and appropriateness tests where relevant; risk disclosure; fees & best execution where relevant |
| **Market abuse (Title VI)** | Prohibitions on insider dealing, unlawful disclosure, market manipulation; surveillance (detection / STOR), Chinese walls, insider lists |
| **Travel Rule (TFR)** | Originator / beneficiary information accompanying every transfer; self-hosted wallet handling; blocking / analysing incomplete transfers |

## 7. Specific requirements — Custody & Exchange (Vancelian's core services)

### 7.1 Custody and administration
- **Segregation** on-chain / off-chain between client assets and own assets (dedicated addresses / keys, distinct registers).
- **Custodian liability**: duty of safekeeping; liability for loss / impairment **capped at the market value at the moment of loss**, except force majeure. Proof of controls, dual control, HSM / MPC, key policy and rotation.
- **Custody policy**: access procedures, quorum, logging, disaster recovery, independent audits.

### 7.2 Exchange (fiat ↔ crypto and crypto ↔ crypto)
- **Price and fee transparency**, conflict management — **proprietary trading prohibited on the operator's own platform**; **matched principal trading** allowed only under strict conditions.
- **Best execution proportionate** to the service: venue and liquidity selection, slippage, latency, aggregation and routing management where applicable.
- **Asset listing management**: admission / removal criteria, sanctions and embargo screening, ART / EMT analysis (whitepaper compliance) and MiFID qualification check (out of MiCA).

## 8. Sustainability disclosures (environmental indicators)
- **CASP website**: publication of key impact indicators (energy consumption, emissions, % renewable, waste / equipment, etc.) per listed / serviced asset, in line with regulatory technical standards (RTS).
- **Issuer whitepapers**: information on consensus mechanism, consumption, impacts, methodologies.
- **Data chain**: sources, periodicity, independence, version archiving.

## 9. Interaction with other frameworks

| Framework | Interaction with MiCA |
|---|---|
| **MiFID II** | If a token = financial instrument, MiCA does **not** apply → MIFIR / Prospectus / MAR / UCITS / AIFMD as applicable |
| **EMD2 / PSD2** | EMT issuance reserved to banks / EMIs; related payment services subject to PSD2 / PSR |
| **TFR (EU 2023/1113)** | Travel Rule applied to crypto from 30 December 2024 — zero threshold, with specific rules > €1,000 for self-hosted wallets |
| **DORA (EU 2022/2554)** | Applies from 17 January 2025: ICT risk management, major incident notification, TLPT (threat-led penetration testing), oversight of critical ICT providers |
| **AML/CFT** | EBA guidelines on VASP / CASP risk, KYC, sanctions, asset freezing |
| **GDPR** | Lawful basis, minimisation, DPIA (blockchain: pseudonymisation ≠ anonymisation), data subject rights, third-country transfers, security |

## 10. Capital requirements per CASP service (France / Vancelian mapping)

### Vancelian PSAN ↔ MiCA CASP service mapping
- **Custody (PSAN)** → Custody and administration (CASP)
- **Buy/sell fiat (PSAN)** → Exchange crypto ↔ fiat (CASP)
- **Crypto ↔ crypto exchange (PSAN)** → idem (CASP)
- **Trading platform (PSAN)** → Operation of a trading platform (CASP)
- **(Optional PSAN)** RTO / Execution / Placement / Advice / Management → corresponding CASP services

### Minimum permanent capital by service

| Service | Minimum capital |
|---|---|
| **Trading platform operation** | **€150,000** |
| **Custody & administration** | **€125,000** |
| **Exchange (fiat ↔ crypto / crypto ↔ crypto)** | **€125,000** |
| **Execution / RTO / Placement / Advice / Management** | **€50,000** |

**Equity must also be ≥ ¼ of the previous year's fixed costs** if that figure exceeds the minimum capital.

## 11. CASP application — key Article 62 deliverables
- **Programme of operations** (+ 3-year business plan).
- **Org chart and governance** (committees, key functions, independence).
- **Policies**: compliance, AML/CFT, risk management, conflicts, complaints, business continuity / wind-down, outsourcing, ICT security (MFA / HSM / MPC / key management), listing / delisting, market surveillance (Title VI), data and records, sustainability.
- **Systems**: architecture, resilience, logging, access, backups, BCP/DRP, testing.
- **Contracts**: client ToS, critical providers (DORA clauses), banks / custodians, insurers (cyber, criminality).
- **Financial proofs**: capital, insurance, audited accounts, liquidity stress tests (if ART/EMT involved).

## 12. Market abuse and surveillance (Title VI)
- **Coverage**: crypto-assets admitted (or proposed for admission) to trading on a CASP platform.
- **Prohibitions**: insider dealing, unlawful disclosure of inside information, manipulation (wash trades, spoofing, pump & dump…).
- **CASP obligations**:
  - Detection mechanism (orders / transactions surveillance, thresholds, scenarios)
  - **STOR** (Suspicious Transaction and Order Reports) to authorities
  - Insider lists, Chinese walls, information access procedures
  - Public communication governance (tweets, blogs, influencer marketing)

## 13. Marketing and communication
- Content must be **identifiable, clear, fair**, and consistent with the whitepaper / information sheet; mention of whitepaper availability is mandatory.
- **Prohibited**: suggesting extended regulatory protection on products outside MiCA scope (misleading risk).
- Traceability of campaigns (sites, social networks, influencers, affiliates); GDPR compliance (consent, cookies, right to object); AML/CFT (risky promotions).

## 14. Mining / Cloud mining (EU position)
- **No MiCA authorisation required** for mining or selling computing power.
- Other applicable rules: consumer / contract law, energy / environment, taxation, ICT security, fair advertising.
- Caution required on communication (yields, comparisons, risks) and on the perimeter of CASP services if combined with mining (e.g. custody / exchange of mined assets).

See [[../exclusive-offers/cloud-mining-mica-and-european-regulation|Cloud Mining and European regulation]] for the client-facing version.

## 15. Vancelian's 12–18 month roadmap
1. **Gap analysis PSAN → CASP** (services, capital, policies, IT, contracts).
2. **Policies & registers** upgrade (conflicts, complaints, market abuse, sustainability, listing, TFR, outsourcing, DORA).
3. **ICT / DORA**: critical-function mapping, BCP/DRP, SOC/EDR, immutable logging, advanced penetration testing (TLPT-like).
4. **Market surveillance**: detection tooling (rules, scenarios, alerts, STOR), Chinese walls.
5. **Sustainability**: data pipeline, methodologies, per-asset web publication.
6. **TFR**: integration of a Travel Rule solution (VASP directory, sunrise compliance, self-hosted handling).
7. **CASP application**: preparation of the Article 62 programme of operations, AMF pre-filing, calendar.
8. **Passport**: target country selection, freedom of establishment / freedom to provide services, local product and marketing alignment.

See [[vancelian-mica-roadmap|Vancelian MiCA roadmap]] for the client-facing version.

## 16. Documentary register (required / expected)
- **Manuals**: compliance, risks, ICT security, AML/CFT, DORA, sustainability, TFR, market abuse.
- **Procedures**: onboarding / KYC, transaction monitoring, asset freezing, sanctions screening, incident management, breach notification.
- **Policies**: key custody, privileged access, change management, encryption, data retention (GDPR), outsourcing, business continuity, wind-down.
- **Registers**: ICT incidents, complaints, conflicts, key access, insider lists, marketing communications, training & competencies.

## 17. Token qualification — simplified decision tree
1. **Is it a financial instrument (MiFID II)?** (economic / political rights, negotiability, security class) → **Out of MiCA**; full financial regime applies.
2. **Is it an EMT?** (1:1 reference to a currency) → EMD2 + MiCA EMT rules (bank / EMI).
3. **Is it an ART?** (basket / other reference) → MiCA ART rules (authorisation, reserves).
4. **Otherwise** → "Other crypto-assets" — generic MiCA regime.

## 18. Conclusion
MiCA gives custody and exchange of crypto-assets a unified, passportable EU framework. For Vancelian, the PSAN → CASP trajectory requires governance / IT / control upgrades (DORA), TFR compliance, market abuse surveillance, and ESG indicator publication. This page is the internal reference for the 100+ legal and operational fact sheets feeding the Vancelian chatbot and teams.

## Caveats
- **Source date: 27 August 2025.** Delegated acts, RTS / ITS, and ESMA / EBA guidelines continue to evolve — verify the most recent version for any specific clause.
- **Informational only — not legal advice.** The chatbot must escalate any specific regulatory question to a Vancelian human advisor.

## Sources
- raw/Fiche MD Reglementation/Fiche_Jason_Regulation Vancelian MICA (Europe).rtf — Comprehensive Vancelian internal legal brochure on MiCA & European digital asset regime, v1, 27 August 2025 (translated from French). Cited public sources include: EU MiCA Regulation (CELEX:32023R1114), TFR Regulation (CELEX:32023R1113), DORA Regulation (CELEX:32022R2554), ESMA MiCA hub, EBA MiCA & EMT/ART, EIOPA DORA guidance, AMF PSAN, AMF PSAN → CASP transition.
- [raw/L'AMF rappelle que la période transitoire pour les PSAN pour continuer de fournir des services sur crypto-actifs en France sans autorisation sous MiCA prend fin le 1er juillet 2026.md](https://www.amf-france.org/fr/actualites-publications/actualites/lamf-rappelle-que-la-periode-transitoire-pour-les-psan-pour-continuer-de-fournir-des-services-sur) — AMF official notice (February 2026). Confirms: hard end of PSAN transitional period is 1 July 2026 (no extension); orderly wind-down plan required by 30 March 2026 for non-applicants; criminal penalties (Art. L. 54-10-4 and L. 572-23 CMF) for unauthorised activity after 1 July 2026; ESMA December 2025 statement notes instruction delays up to 4 months once dossier complete.
