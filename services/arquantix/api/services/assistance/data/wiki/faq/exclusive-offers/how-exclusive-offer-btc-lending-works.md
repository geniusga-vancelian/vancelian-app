---
title: "How does the BTC lending mechanism work in Exclusive Offers?"
slug: how-exclusive-offer-btc-lending-works
category: exclusive-offers
audience: client
status: verified
last_reviewed: 2026-04-16
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
  - raw/Brochures commerciales/Brochure offre exclusive Dubai Villa Solaria.pdf
  - raw/faq/faq-35231215442449-financial-structure-of-the-project.md
related:
  - wiki/faq/exclusive-offers/how-does-the-7-luxury-villas-in-bali-exclusive-offer-work.md
  - wiki/faq/exclusive-offers/how-does-the-dubai-villa-al-barari-exclusive-offer-work.md
  - wiki/faq/exclusive-offers/how-are-returns-generated-dubai-villa.md
  - wiki/faq/exclusive-offers/how-do-project-exit-windows-work.md
  - wiki/faq/savings/how-vault-liquidity-and-returns-work.md
tags: [exclusive-offers, BTC, lending, RWA, EURC, capital-protection, refinancing, interest, returns, counterparty]
questions:
  - "How do Exclusive Offers work technically?"
  - "What happens to my money when I invest in an Exclusive Offer?"
  - "Is my capital protected in Exclusive Offers?"
  - "How does the BTC lending work in Vancelian's exclusive offers?"
  - "Why are Exclusive Offers denominated in Bitcoin?"
  - "How are my Exclusive Offer interest payments made?"
  - "What happens at the end of an Exclusive Offer?"
  - "How are the returns generated on an exclusive offer?"
  - "Why do I receive interest from day one?"
  - "Where does the yield come from on exclusive offers?"
  - "How can the counterparty pay daily interest before the project is finished?"
---

# How does the BTC lending mechanism work in Exclusive Offers?

## Short answer

Exclusive Offers are **BTC lending programmes** where you lend directly to a project counterparty through the Vancelian platform. Your deposit is **value-locked in EURC** at subscription to neutralise BTC volatility on the principal. The return comes from the projected revenue of the underlying real estate operation — sale or rental income funds the interest paid to you, in BTC, converted for stability. At maturity you receive BTC equivalent to your original EURC value. Full financial structure and projections are in the official brochure per offer — always consult it.

## Details

### How the refinancing mechanism works

The mechanism is the same across all real estate Exclusive Offers (Bali, Dubai, and future projects). A project counterparty needs to refinance a real estate project whose underlying asset is a physical property. You participate by lending funds (via a BTC-denominated loan) directly to the counterparty through the Vancelian platform.

The return you receive comes from the projected revenue laid out in the financial elements available in the official documentation for each offer. For the counterparty to generate that revenue, the sale or rental management of the property must produce the income that is then allocated to the rate distributed by the offer.

### Why interest is paid from the day after your deposit

If interest is paid from the day following your deposit — before the project is completed, managed, or sold — it is simply because the project counterparty commits, under the terms of the exclusive offer, to paying interest and to reimbursing the capital that serves to finance the project.

In practice, a portion of the funds collected goes towards the realisation of the project (acquisition, renovation, operational costs), while another portion is used to service the interest payments. The risk therefore sits on the counterparty's treasury management and on the counterparty's ability — as the counterparty — to complete, manage, or sell the targeted property.

### Exit strategy for the underlying property

The property can be sold off-plan before the end of the works, sold after completion once the renovation or construction is finished, or rented out. The counterparty's strategy typically encompasses all of these avenues. However, regardless of the chosen exit route, the counterparty is contractually committed to respect the terms of the exclusive offer — including interest payments and capital reimbursement at maturity.

### Why the rate is attractive

The return reflects a direct lending model: you lend directly to the project counterparty, with no banking intermediation. Vancelian, as the regulated platform (DASP E2023-087), facilitates the transaction and takes a low intermediation fee — the rest goes to you. In exchange for this direct exposure — and the counterparty risk it implies on the counterparty — you benefit from a rate that is significantly higher than what traditional structured finance would deliver.

Rates are indicative and depend on your Privilege Club status. Always verify the live rate in the Vancelian app.

### Where to find the full financial details

The official commercial brochure for each offer contains the complete financial plan, including the projected cost breakdown, gross margin, timeline, and partner information. It is available directly in the offer detail within the Vancelian app and on the official Vancelian website. Always consult this documentation before investing.

---

### Technical flow: subscription, custody, and repayment

**Subscription and capital protection**
- You deposit EUR or crypto (stablecoins, BTC, etc.)
- Vancelian immediately converts your deposit to BTC
- Your **deposit value in EURC is locked and recorded at subscription** — this acts as your capital protection reference
- This EURC reference value is maintained regardless of BTC price movements during the engagement period

**Internal asset transfer and custody**
- BTC is transferred internally through the Fireblocks MPC infrastructure (the institutional-grade key-management technology used by Vancelian to secure its in-house custody)
- **No on-chain blockchain transaction occurs** — because the borrowing company has a business account on the Vancelian platform, the transfer happens within Automata France's infrastructure
- No network fees apply

**Borrower access**
- The RWA company can request to convert their BTC holdings to EUR or other crypto-assets at any time
- Conversion is handled by Automata France's exchange engine (same service used for client trading)
- The company uses the funds for the stated project (real estate development, infrastructure, etc.)

**Loan activation and wallet**
- The loan officially starts on Day 1 after subscription (Day+1)
- A dedicated wallet is created on the platform for the deposit
- You can view the wallet details on your client dashboard

**Interest payments and conversion**
- Interest is paid in BTC at the frequency specified in the offer terms (daily, monthly, annual, or at maturity)
- BTC interest is **automatically converted to crypto-assets** (including JME tokens and other partner assets) for stability
- Converted interest is credited directly to your wallet
- Interest can be withdrawn on demand without penalty

**Interest withdrawal options**
- Exchange interest to EUR: free conversion at 1:1 rate
- Exchange interest to USDC: subject to exchange fees
- EUR withdrawals: credited to your EUR account (typically a Modulr IBAN)
- Crypto withdrawals: sent to your registered crypto wallet

**Client dashboard visibility**
- Interest received so far (in BTC + equivalent crypto conversion price)
- Time remaining until project maturity
- Offer conditions and terms
- Intended use of funds by the borrower company
- Wallet address and transaction history

**Repayment at maturity**
- At the end of the loan term, the company repays in BTC
- You receive **BTC equivalent to your original EURC deposit value** — protecting you against BTC price volatility over the loan period
- For example: if you locked in €10,000 at BTC/EUR = 40,000 (0.25 BTC), you receive back 0.25 BTC at maturity, regardless of whether BTC is €50,000 or €30,000 at that time

## Caveats

- **Returns depend on underlying project performance.** The borrower must successfully execute the project and repay on schedule
- **The EURC reference value mechanism protects against BTC price volatility** but does not eliminate all risks — the borrower may default or the project may face delays
- **Interest rates are indicative** and reflect current market conditions; always review specific offer terms before committing
- **Risks are real:** Exclusive Offers are typically high-yield because they carry higher risk than standard savings products. Always review the risk warning page before investing
- Early exit windows may be available for some offers, but they may involve penalties or discounts
- Contact Vancelian support or your advisor if you have questions about a specific offer's terms or risks

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — Describes BTC lending flow, EURC reference value mechanism, interest payment and conversion process, repayment terms, and internal custody procedures (Vancelian in-house, via Fireblocks MPC infrastructure)
- [raw/Brochures commerciales/Brochure offre exclusive Dubai Villa Solaria.pdf] — Commercial brochure (Dubai Villa): financing plan, timeline, revenue model
- [raw/faq/faq-35231215442449-financial-structure-of-the-project.md] — Financial structure (Bali): diversified revenue streams, yield justification
- CEO framing (Jean Guillou, 2026-04-16): refinancing mechanic explanation is generic to all real estate Exclusive Offers; interest from day 1 = counterparty contractual commitment + treasury allocation; risk = treasury management + counterparty ability to sell/manage; always reference official brochure
