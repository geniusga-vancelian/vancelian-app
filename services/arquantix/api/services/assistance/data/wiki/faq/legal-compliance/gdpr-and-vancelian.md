---
title: "How does Vancelian comply with GDPR?"
slug: gdpr-and-vancelian
category: legal-compliance
audience: client
status: verified
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Fiche_Jason_Reglementation_EU.rtf
  - raw/Fiche MD Reglementation/Fiche_Jason_Regulation Vancelian MICA (Europe).rtf
related:
  - privacy-policy.md
  - vancelian-compliance-team.md
  - mica-overview-and-vancelian.md
  - lcb-ft-aml-compliance.md
tags: ["gdpr", "rgpd", "privacy", "data protection", "dpo", "cnil", "compliance"]
questions:
  - How does Vancelian comply with GDPR?
  - is my personal data safe with vancelian
  - gdpr data protection vancelian
  - Can I request deletion of my data?
  - who is vancelian's DPO
  - How do I exercise my data rights?
  - cnil vancelian privacy
  - does vancelian sell my data
---

# How does Vancelian comply with GDPR?

> **Regulatory escalation:** the chatbot must escalate any specific personal-data, exercise-of-rights, or DPO request to a Vancelian human advisor or directly to Vancelian's DPO.

## Short answer
The **GDPR** (General Data Protection Regulation) applies directly to Vancelian. Client data (identity, supporting documents, transactions) is stored securely with **encryption** and **restricted access**, never resold or used outside the contractual framework. Every client can exercise their rights of **access, rectification, and erasure**. Vancelian has appointed a **Data Protection Officer (DPO)** who oversees GDPR compliance and engages directly with the **CNIL** (French data protection authority) when needed.

## Details

### What GDPR covers at Vancelian
- **Personal data**: identity documents, proof of address, KYC data, transaction history, communication metadata.
- **Lawful basis**: contract execution, legal obligation (KYC, AML/CFT), legitimate interest, and consent where required.
- **Data minimisation**: only data necessary for the service or required by regulation is collected and retained.

### Security and access
- **Encryption** at rest and in transit.
- **Restricted access** controlled by role-based permissions and multi-factor authentication.
- **Logging and traceability** for sensitive data access (aligned with DORA — see [[dora-cybersecurity-explained|DORA explained]]).
- **Pseudonymisation** where applicable (note: blockchain pseudonymisation is **not** anonymisation — DPIA required for on-chain processing).

### Client rights under GDPR
Every client can exercise the following rights:
- **Right of access** — request a copy of personal data held.
- **Right of rectification** — request correction of inaccurate data.
- **Right of erasure** — request deletion of data, subject to legal retention obligations (e.g. KYC data must be kept under AML/CFT rules).
- **Right of objection / restriction** in specific cases.
- **Right to data portability** where applicable.

### Vancelian's DPO and the CNIL
- A **Data Protection Officer (DPO)** has been appointed and oversees GDPR compliance.
- The DPO is the dialogue point with the **CNIL** (Commission nationale de l'informatique et des libertés — France's data protection authority) when needed.
- A formal complaint with the CNIL is always available to clients as a final recourse.

### Cross-border transfers and third parties
- Personal data may be processed by approved third-party providers (e.g. KYC providers, custody technology partners such as Fireblocks, hosting providers).
- Transfers outside the EU are subject to GDPR safeguards (Standard Contractual Clauses, adequacy decisions).
- Vendor due diligence is performed and contractually documented (DORA-aligned for ICT providers).

### How to exercise your GDPR rights
- Submit your request to Vancelian customer support, or directly to the DPO via the contact details published in the [[privacy-policy|Vancelian privacy policy]].
- Vancelian responds within the legal deadline (one month, extendable in complex cases).

## Caveats
- **AML/CFT data must be retained** for legally mandated periods even if the client requests erasure — these obligations override the right to erasure.
- **Blockchain transactions are immutable**: data anchored on-chain cannot be deleted retroactively. This is a structural limit of distributed ledger technology that GDPR explicitly recognises.
- For any specific GDPR request or complaint, contact customer support — the chatbot must escalate.

## Sources
- raw/Fiche MD Reglementation/Fiche_Jason_Reglementation_EU.rtf — Team Q&A on GDPR, DPO, CNIL, client rights (translated from French).
- raw/Fiche MD Reglementation/Fiche_Jason_Regulation Vancelian MICA (Europe).rtf — Regulatory brochure on GDPR / blockchain interaction, DPIA, pseudonymisation vs anonymisation, third-country transfers (translated from French).
