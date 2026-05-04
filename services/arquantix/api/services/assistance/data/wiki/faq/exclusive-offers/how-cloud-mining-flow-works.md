---
title: "How does the Cloud Mining program work technically?"
slug: how-cloud-mining-flow-works
category: exclusive-offers
audience: client
status: verified
last_reviewed: 2026-04-17
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
related:
  - wiki/faq/exclusive-offers/how-does-the-exclusive-offer-cloud-mining-by-hearst-infrastr.md
  - wiki/faq/exclusive-offers/what-is-the-exclusive-offer-cloud-mining-by-hearst-infrastru.md
  - wiki/faq/exclusive-offers/cloud-mining-risks-overview.md
tags: [cloud-mining, EURC, Vancelian-LTD, UAE, ADGM, computing-power]
questions:
  - "How does Cloud Mining work technically at Vancelian?"
  - "What is the role of Vancelian LTD in Cloud Mining?"
  - "What happens to my money when I subscribe to Cloud Mining?"
  - "Is Cloud Mining operated by the same entity as the rest of Vancelian?"
  - "How are Cloud Mining interest payments made?"
  - "Why is Cloud Mining denominated in EURC?"
  - "What is the legal structure behind Cloud Mining?"
---

# How does the Cloud Mining program work technically?

> **Important:** Cloud Mining is a **computing power purchase contract** — not a loan. Vancelian (Automata France SAS) acts as intermediary between you and the mining programme operated by **Vancelian LTD** (UAE-ADGM). The rewards you receive are mining rewards, not interest from a lending arrangement.

## Short answer
When you subscribe to a Cloud Mining program, you purchase computing power from **Vancelian LTD** (UAE-ADGM regulated) using **EURC** (a euro stablecoin). **Automata France** (European entity) handles only currency exchange, custody of rewards, and app display — it does not operate mining hardware. Your deposit is locked in EURC at subscription, interest is paid daily in EURC, and at maturity your capital is repaid in EURC by Vancelian LTD.

## Details

### The two entities behind Cloud Mining — and why the distinction matters
Cloud Mining involves two distinct regulated entities playing two distinct roles. **Vancelian LTD** (UAE-ADGM regulated) **owns and operates** the Bitcoin mining infrastructure and sells the computing-power contracts — it is the economic counterparty of your subscription. **Automata France SAS** (French PSAN-regulated) acts as the European intermediary and provides exactly three services on behalf of Cloud Mining subscribers: currency exchange between EUR/crypto and EURC, custody of the daily mining rewards, and aggregated position display inside the client app. It is essential to understand that Automata France **does not operate any mining hardware, pool or infrastructure** — that role sits entirely with Vancelian LTD. This legal separation is what allows the product to be distributed to European clients under AMF PSAN supervision while the industrial mining activity is operated from ADGM.

### What actually happens when you subscribe
The subscription flow unfolds in a clean sequence. You initiate the subscription on the Vancelian app and deposit in EUR or in a supported crypto-asset (USDC, EURC, BTC, etc.). Automata France converts that deposit to **EURC**, and the deposit value in EURC is **locked at the moment of subscription** — this is your capital-protection anchor and the reference figure used at maturity. The EURC is then transferred on-chain to Vancelian LTD from Vancelian's custody wallets, secured by the **Fireblocks MPC** infrastructure (the institutional-grade key-management technology Vancelian uses for crypto custody). Once Vancelian LTD receives the EURC, it allocates the computing-power contract to your account, and the contract officially starts on **Day+1** after subscription.

Once the EURC is on the Vancelian LTD side, the operational reality requires flexibility: Vancelian LTD can request Automata France to convert some of those EURC holdings to EUR or to other crypto-assets to operate the mining business — buying hardware, paying energy providers, managing working capital. From your side, that operational layer is invisible: your contract remains EURC-denominated throughout.

### How daily rewards are generated and paid
Bitcoin mining rewards are generated continuously as the mining hardware solves blocks. Each day, the share attributable to your contract is **converted to EURC** to keep the contract denominated in a stable unit, and credited to your omnibus wallet on the Vancelian platform. Interest accumulates and is visible in real time on your client dashboard. When you want to take those rewards off the platform, you have three paths: a **free 1:1 conversion to EUR** credited to your EUR account (typically a Modulr IBAN), a **conversion to USDC** subject to exchange fees and credited to your registered crypto wallet, or — for B2B clients — a withdrawal to a pre-registered company IBAN or crypto wallet. There is no lock-up on the interest earned; withdrawals are processed on demand.

### What your dashboard shows
Your Cloud Mining dashboard is designed to give a full-picture view in one place: the **locked deposit value in EURC** (your capital-protection reference), the **interest received to date** in EURC, the **remaining engagement period**, the **offer conditions and terms**, **mining difficulty and indicative annualised yield**, and a **withdrawal history**. The yield figure is explicitly indicative — it reflects current network conditions and is not a forecast.

### What happens at maturity
At the end of the contract term, Vancelian LTD repays the principal in EURC, equal to your original locked deposit value. The EURC is transferred on-chain from Vancelian LTD back to Automata France custody, Automata France credits your account, and the funds become available for withdrawal — free to EUR, or with fees to crypto. Concretely: if you locked €10,000 worth of EURC at subscription, you receive EURC equivalent to €10,000 at maturity, independently of where BTC has moved in the interim.

## Requirements / Documents

- Valid Vancelian account with completed KYC verification
- Sufficient funds in EUR or accepted crypto-assets to cover subscription (typically €1,000 minimum; check current terms)
- Acceptance of Cloud Mining Terms & Conditions and risk warnings
- For B2B clients: company registration documents and authorized signatories (already on file if you have a Vancelian Business account)

## Process

1. **Navigate to Cloud Mining offer** on the Vancelian app
2. **Review terms:** lock-up period, interest rate, mining difficulty assumptions
3. **Deposit funds** in EUR or accepted crypto
4. **Accept terms & conditions** and risk warnings
5. **Confirm subscription** — transaction processes immediately
6. **Confirmation:** email + app confirmation with deposit EURC value locked
7. **Day+1:** contract officially activates, mining rewards begin accruing
8. **Daily:** interest is computed and credited to your wallet
9. **Maturity:** principal is returned in EURC, available for withdrawal

Indicative timeline: subscription → immediate processing → Day+1 activation → daily interest accrual for contract duration → maturity repayment.

## Caveats

- **Mining rewards depend on:** Bitcoin network difficulty, pool uptime, hash rate allocation, and global Bitcoin price — all highly volatile
- **Returns are variable and not guaranteed.** The indicative yield assumes current network conditions; actual returns may be higher or lower
- **The EURC reference value protects capital stability** but does not guarantee profit — if mining rewards are lower than expected, you may receive only your capital back
- **Early exit:** Check the specific offer terms for early withdrawal provisions; some contracts may allow early exit at a discount or with penalties
- **Regulatory risk:** Mining regulations may change; Vancelian LTD is UAE-ADGM regulated but operates globally, subject to local jurisdiction rules
- **Counterparty risk:** Returns depend on Vancelian LTD's operational performance and ability to repay; review Vancelian LTD's governance and track record
- Always consult the risk warning page before subscribing
- For detailed technical questions about mining operations or pool participation, contact Vancelian support

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — Describes Cloud Mining legal structure (Vancelian LTD vs. Automata France), subscription flow, EURC conversion and on-chain transfers, daily interest accrual, repayment terms, and custody procedures via Fireblocks
