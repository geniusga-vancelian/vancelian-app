---
title: "Custody architecture — who holds what at Vancelian, by product"
slug: custody-architecture
category: concepts
audience: client
status: draft
last_reviewed: 2026-04-29
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
  - raw/faq/faq-9224836184081-how-does-vancelian-ensure-the-security-and-management-of-my-.md
related:
  - wiki/faq/legal-compliance/how-does-vancelian-ensure-the-security-and-management-of-my-.md
  - wiki/faq/savings/what-is-the-flexible-vault.md
  - wiki/faq/savings/how-vault-liquidity-and-returns-work.md
  - wiki/entities/automata-group.md
  - wiki/entities/solaria-group.md
  - wiki/entities/the-heights-bali-sas.md
tags: [custody, depositary, modulr, automata, fireblocks, psan, mica, vara, segregation, ownership, exclusive-offers, intermediary, by-product]
questions:
  - Who legally holds my funds at Vancelian?
  - Who is the custodian of my crypto?
  - Is Vancelian itself the depositary of my crypto?
  - What is the difference between owner and depositary?
  - Where are the funds in my Coffre held?
  - Where is the EURC pocket of my Vault held?
  - Where are my crypto wallet funds held?
  - Where is the EUR balance of my IBAN account held?
  - Who holds the funds when I subscribe to Cloud Mining or an Exclusive Offer?
  - Who holds the funds allocated by my Vault to an Exclusive Offer?
  - Are the funds I engage in an Exclusive Offer still held by Vancelian?
  - Is Modulr a Vancelian entity?
---

# Custody architecture — who holds what at Vancelian, by product

The custody answer at Vancelian is **product-specific**. Each Vancelian product has its own custody profile : the entity that holds the funds, the regulatory framework, and Vancelian's own role differ from product to product. This page gives the canonical answer for each product, so that any custody question can be answered by composing the relevant product blocks.

## Owner versus depositary — the foundational distinction

Two roles must not be confused. You are the **owner** of your funds and crypto-assets : you alone hold the property right, and your assets are identified per client at all times. The **depositary** is the entity that holds the assets in segregation on your behalf, secured and identifiable. The depositary never becomes the owner. Segregation is the legal mechanism that keeps your assets identifiable and outside the depositary's own balance sheet. The depositary entity changes depending on the product — see below.

## Custody by Vancelian product

### IBAN account — your EUR balances

Your euros are held in segregated payment accounts at **Modulr Finance B.V.**, an electronic money institution authorised by De Nederlandsche Bank (DNB) under reference R182870. This applies to your IBAN balance, your incoming and outgoing SEPA transfers, and the EUR pocket of any Vault. Vancelian itself does not hold euros — the depositary role is delegated to Modulr under its electronic-money licence.

### Crypto wallets — your direct crypto holdings (spot trading and listed assets)

Your direct crypto holdings — BTC, ETH, USDC, EURC, AKTIO, and other listed assets that you buy, sell, transfer or hold via the Vancelian app — sit in segregated wallets identified per client. The depositary role is operated by **Automata France SAS** under PSAN registration E2023-087 with the AMF (MiCA scope) for clients served from Europe, or by **Automata FZE** under VARA In-Principle Approval for clients served from the United Arab Emirates. The wallets are secured by Fireblocks MPC, which ensures that private keys cannot be compromised through key fragmentation.

### Exclusive Offers — funds engaged with a partner counterparty

When you subscribe to an Exclusive Offer (Cloud Mining by Hearst, Dubai Villa Al Barari, The Heights Bali, and any future Exclusive Offer), the funds you engage **leave Vancelian's custody scope for the duration of the engagement**. They are transferred to the contractual counterparty named for the program, who uses them productively to generate the yield :

- **Cloud Mining by Hearst** — counterparty is **Vancelian LTD** (ADGM), the joint-venture entity contracted with Hearst Solution FZCO. The funds are used to purchase computing power from Hearst.
- **Exclusive Offer Dubai Villa Al Barari** — counterparty is **Solaria Group** (RCS Antibes 908 978 893), the borrower under the BTC-loan refinancing engagement.
- **Exclusive Offer The Heights Bali (Munduk)** — counterparty is **The Heights Bali SAS**, the dedicated SPV under the BTC-loan refinancing engagement.

During the engagement period, **Vancelian acts as the intermediary, not as the depositary**. The contractual default risk sits with the partner — recovery of the engaged capital depends on the partner's ability to honour the contract, as documented in the Conditions Particulières of each program. At contractual maturity (or at each periodic interest payment, depending on the program), the funds (or interest) are returned by the partner and re-enter Vancelian's custody scope, where they are held again by Automata France SAS or Automata FZE.

### Coffre (Flexible Vault, Future Vault) — a composite allocation product

A Coffre is not held by a single depositary. It is a **composite allocation product** that generates a yield, and its custody answer depends entirely on **how the allocation is composed**. The allocation is split into three pockets, each in a different custody situation :

- The **EUR pocket** (cash side of the Coffre) is held at **Modulr Finance B.V.** in segregated payment accounts — same as the IBAN account.
- The **EURC pocket** (stablecoin liquidity for deposits and withdrawals) is held at **Automata France SAS** or **Automata FZE** in segregated wallets — same as the crypto wallets.
- The **allocation to Exclusive Offers** (the share of the Coffre directed to one or several underlying programs : Cloud Mining, Solaria, Bali) is held by the **partner counterparty of each program** — same as a direct subscription to an Exclusive Offer. This portion follows the engagement flow described above (funds at the partner during the engagement, contractual return at maturity or via the periodic interest cycle).

The funds and their associated risk depend on the current allocation. The allocation is **not static** — it can evolve over time as Vancelian adjusts the Coffre structure to deliver the indicative rate. The current allocation in force for your Coffre is always displayed in the Vancelian app ; for any question on the allocation applicable at a given date, refer to your Coffre page in the app.

## How to read this page when answering a custody question

Custody questions can mention one product, several products, or generic "all my funds". The answer is built by composing the relevant product blocks above :

- A question about the IBAN account or EUR balances → use the **IBAN block** only.
- A question about the crypto wallet, spot trading, or holdings of BTC / ETH / USDC / AKTIO outside a Vault → use the **Crypto wallets block** only.
- A question about an Exclusive Offer (Cloud Mining, Dubai, Bali) → use the **Exclusive Offers block** only ; name the relevant counterparty.
- A question about a Coffre → use the **Coffre block** only ; the answer naturally references the EUR pocket (Modulr), the EURC pocket (Automata), and the allocation pocket (partner counterparty), without forcing a separate IBAN or wallet narrative.
- A question that mentions several products (e.g. "Coffres et crypto") → compose the relevant blocks side by side, in the order given by the client.
- A generic "who holds my funds" question without a product specified → list the product blocks in the canonical order : IBAN, Crypto wallets, Exclusive Offers, Coffre.

The owner-vs-depositary distinction applies to every block — the client is always the legal owner ; the depositary entity changes per block.

## What "Vancelian" means in this context

When the Vancelian app or this wiki refers to "Vancelian" in custody discussions, it refers to the operational umbrella through which the regulated entities deliver the service. Vancelian is the brand ; Modulr, Automata France SAS and Automata FZE are the named regulated depositaries for the in-app custody scope. For Exclusive Offers, **Vancelian acts strictly as an intermediary** — the operator of the underlying activity is the named partner of each program (Hearst for Cloud Mining via the Vancelian LTD ADGM JV, Solaria for Dubai, The Heights Bali SAS for Bali). Vancelian LTD (ADGM) is a joint-venture entity acting as the contractual counterparty of the Cloud Mining program ; it is not a generic custodian.

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — flow architecture between client wallets, Vancelian segregation, and contractual counterparties for each transactional product
- [raw/faq/faq-9224836184081-how-does-vancelian-ensure-the-security-and-management-of-my-.md] — Modulr safeguarding statement and Automata France SAS payment-services role
