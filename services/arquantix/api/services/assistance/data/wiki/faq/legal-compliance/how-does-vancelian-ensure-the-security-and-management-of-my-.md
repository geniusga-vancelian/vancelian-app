---
title: "How does Vancelian ensure the security and management of my funds?"
slug: how-does-vancelian-ensure-the-security-and-management-of-my-
category: legal-compliance
audience: client
status: verified
last_reviewed: 2026-04-29
sources:
  - raw/faq/faq-9224836184081-how-does-vancelian-ensure-the-security-and-management-of-my-.md
related:
  - who-are-vancelians-partners.md
  - where-and-how-is-vancelian-regulated.md
  - wiki/concepts/custody-architecture.md
tags: ["bankruptcy", "guarantee", "modulr", "garantie", "funds safety", "sécurité fonds", "Modulr", "Fireblocks", "Automata", "PSAN", "MiCA", "VARA", "depositary", "regulation-and-partners", "by-product"]
questions:
  - How are my funds kept safe at Vancelian?
  - is my crypto secure on vancelian
  - what happens to my money if vancelian goes bankrupt
  - How does Vancelian protect client assets?
  - fireblocks custody vancelian
  - modulr segregated accounts
  - Are euro deposits protected?
  - Who is the depositary of my crypto?
  - Where are the funds in my Coffre held?
  - Where are my crypto wallet funds held?
  - Where is my IBAN balance held?
  - Where are funds engaged in Cloud Mining held?
  - Is Vancelian itself the custodian?
---

# How does Vancelian ensure the security and management of my funds?

## Short answer

The security of your funds rests on segregation by regulated depositaries — but the depositary entity differs from product to product. For your **IBAN account** (EUR balances), the depositary is **Modulr Finance B.V.**, a Dutch electronic money institution. For your **crypto wallets** (BTC, ETH, USDC, EURC, AKTIO and other listed assets you hold or trade in the app), the depositary is **Automata France SAS** (PSAN/MiCA) in Europe or **Automata FZE** (VARA) in the United Arab Emirates, in segregated wallets secured by Fireblocks MPC. For an **Exclusive Offer** (Cloud Mining, Dubai Villa, Bali), the funds you engage are held by the partner counterparty of each program for the duration of the engagement (Vancelian LTD ADGM JV with Hearst Solution FZCO for Cloud Mining ; Solaria Group for Dubai ; The Heights Bali SAS for Bali), and Vancelian acts as the intermediary. For a **Coffre**, the answer depends on the current allocation : the EUR pocket is at Modulr, the EURC pocket is at Automata, and the allocation to Exclusive Offers is at the relevant partner counterparty. You remain the legal owner of your assets at all times, in every product.

## Details

The security architecture answers the same question — *who holds my funds* — differently for each product. The relevant block to read depends on the product or products mentioned in your question.

### IBAN account — your EUR balances

Your euros are held in segregated payment accounts at **Modulr Finance B.V.**, a regulated electronic money institution authorised by De Nederlandsche Bank (DNB) under reference R182870. This applies to your IBAN balance and your incoming and outgoing SEPA transfers. Modulr is the depositary ; you are the legal owner. The relationship is documented in the [Modulr Terms and Conditions](https://vancelian.com/en/terms-conditions-modulr) :

> *Automata France SAS is an outsourced service provider of Modulr Finance B.V., a company registered in the Netherlands under business number 81852401, which is authorised and regulated by the Dutch Central Bank (DNB) as an Electronic Money Institution (company reference number: R182870) for the issuance of electronic money and payment services. Your account and the associated payment services are provided by Modulr Finance B.V. Your funds will be held in one or more segregated accounts and [protected in accordance with the Financial Supervision Act](https://www.modulrfinance.com/eu-safeguarding-information).*

### Crypto wallets — your direct crypto holdings (spot trading and listed assets)

Your direct crypto holdings — BTC, ETH, USDC, EURC, AKTIO, and other listed assets you hold or trade in the app — sit in segregated wallets identified per client. The depositary role is operated by **Automata France SAS** under the PSAN registration E2023-087 with the AMF (MiCA scope) for clients served from Europe, or by **Automata FZE** under the VARA In-Principle Approval for clients served from the United Arab Emirates. The wallets are secured by **Fireblocks MPC**, which ensures that private keys cannot be compromised through key fragmentation. Additional security layers include a transaction authorisation policy on sensitive operations, two-factor authentication on client-side actions, and blockchain analytics with anti-money-laundering screening on every incoming and outgoing flow.

### Exclusive Offers — funds engaged with a partner counterparty

When you subscribe to an Exclusive Offer (Cloud Mining by Hearst, Dubai Villa Al Barari, The Heights Bali, and any future Exclusive Offer), the funds you engage **leave Vancelian's custody scope for the duration of the engagement**. They are transferred to the contractual counterparty named for the program, who uses them productively to generate the yield :

| Exclusive Offer | Contractual counterparty (holds the engaged funds during the engagement) |
|---|---|
| Cloud Mining by Hearst | **Vancelian LTD** (ADGM), the joint-venture entity contracted with Hearst Solution FZCO. The funds are used to purchase computing power from Hearst |
| Dubai Villa Al Barari | **Solaria Group** (RCS Antibes 908 978 893), borrower under the BTC-loan refinancing engagement |
| The Heights Bali (Munduk) | **The Heights Bali SAS**, dedicated SPV under the BTC-loan refinancing engagement |

During the engagement period, Vancelian acts as the **intermediary**, not as the depositary. The contractual default risk sits with the partner — recovery of the engaged capital depends on the partner's ability to honour the contract, as documented in the Conditions Particulières of each program. At contractual maturity (or at each periodic interest payment, depending on the program), the funds re-enter Vancelian's custody scope and are held again by Automata France SAS or Automata FZE.

### Coffre — composite allocation product

A Coffre is a composite allocation product whose custody depends on **how the allocation is composed**. The Coffre is split into three pockets, each in a different custody situation :

- The **EUR pocket** is held at **Modulr Finance B.V.** in segregated payment accounts — same depositary as your IBAN balance.
- The **EURC pocket** is held by **Automata France SAS** (PSAN/MiCA) in Europe or **Automata FZE** (VARA) in the UAE — same depositary as your crypto wallets.
- The **allocation to Exclusive Offers** (the share of the Coffre directed to Cloud Mining, Solaria, or Bali) is held by the **partner counterparty of each program** for the duration of the engagement — same custody situation as a direct subscription to an Exclusive Offer.

The funds and their associated risk depend on the current allocation. The allocation is **not static** — it can evolve over time as Vancelian adjusts the Coffre structure to deliver the indicative rate. The current allocation in force for your Coffre is always displayed in the Vancelian app ; for any question on the allocation applicable at a given date, refer to your Coffre page in the app. The full architecture is documented in [[custody-architecture]].

## Sources
- [raw/faq/faq-9224836184081-how-does-vancelian-ensure-the-security-and-management-of-my-.md](https://support.vancelian.com/hc/en-gb/articles/9224836184081-How-does-Vancelian-ensure-the-security-and-management-of-my-funds) — Vancelian help center article (Zendesk section: About Vancelian / Regulation and Partners). Last updated upstream: 2025-12-11T09:58:59Z
