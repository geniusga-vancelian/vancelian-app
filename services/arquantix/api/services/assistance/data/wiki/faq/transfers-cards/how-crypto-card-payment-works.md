---
title: "How does paying with crypto via my Vancelian card work?"
slug: how-crypto-card-payment-works
category: transfers-cards
audience: client
status: verified
last_reviewed: 2026-04-18
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
related:
  - wiki/faq/transfers-cards/how-can-i-pay-with-cryptoassets-using-my-vancelian-card.md
  - wiki/faq/transfers-cards/where-can-i-use-my-vancelian-card.md
  - wiki/faq/account/why-and-how-do-i-provide-my-tax-identification-number-in-the.md
  - wiki/faq/legal-compliance/where-and-how-is-vancelian-regulated.md
tags: [card, crypto-payment, reserve, EURC, temporary-loan, tax, flat-tax, capital-gains]
questions:
  - "How does paying with crypto via my Vancelian card work?"
  - "What happens technically when I pay with crypto at a shop?"
  - "How long do I have to make a crypto card payment?"
  - "Is the crypto reserve for card payments remunerated?"
  - "What if I don't use my crypto card payment within 15 minutes?"
  - "How is the crypto-to-EUR conversion done for card payments?"
  - "Do I have to pay flat tax when I pay in crypto with the Vancelian card?"
  - "Est-ce que je dois payer la flat tax quand je paye en crypto avec la carte Vancelian ?"
  - "Is paying with the Vancelian crypto card a taxable event?"
  - "What is the tax treatment of crypto card payments?"
  - "Does a Vancelian card payment trigger capital gains?"
---

# How does paying with crypto via my Vancelian card work?

## Short answer

When you pay with crypto via your Vancelian card, you are not directly converting crypto into EUR. The platform blocks the chosen crypto as a temporary reserve, lends you an equivalent amount of EURC (the euro stablecoin), and converts that EURC 1:1 without fees into EUR to settle the card payment. After the payment clears, the crypto reserve is exchanged into EURC to repay the EURC loan. From your wallet's perspective, the only movement on your crypto-asset is an exchange crypto → EURC; the EURC → EUR conversion is a stablecoin-to-fiat exchange at parity that does not generate a gain or a loss. This mechanic is specific to Vancelian.

## Details

### How the payment flow actually works

When you tap "pay with crypto" in the app, Vancelian does not sell your crypto for euros. The platform first calculates the maximum amount you can spend based on your profile and the balance of the crypto-asset you selected. Once you confirm, that maximum is **blocked on your crypto wallet as a temporary reserve** — your crypto is not sold at this stage, it is simply frozen.

In parallel, Vancelian **lends you an equivalent amount in EURC** (the euro stablecoin regulated under MiCA as an e-money token). That EURC loan is non-remunerated: you pay no interest and earn no interest. The EURC is then **converted 1:1 without fees into EUR** via the platform's exchange engine, and the resulting EUR is made available to the Modulr-issued card for the card transaction.

You then have **15 minutes** to complete a card payment at any merchant that accepts Visa/Mastercard. If you do not pay within the window, the entire operation is cancelled automatically: the reserve is unfrozen, the EURC loan is closed, and nothing leaves your crypto wallet.

### What happens after you pay — the repayment leg

Once the card transaction settles, Vancelian compares the actual EUR amount charged at the merchant to the reserve. The system then **exchanges the crypto reserve into EURC** (not into EUR) for the exact amount needed to repay the EURC loan. If the card charge equals the reserve, the full reserve is used and the reserve is closed. If the card charge is lower than the reserve, only the used portion of the crypto is exchanged into EURC, the remaining crypto is released back to your wallet, and the delta EUR is returned against the unused EURC.

The key point, often overlooked, is this: **the only movement on your crypto-asset is an exchange crypto → EURC**. The crypto → EUR conversion that appears to happen from a merchant's standpoint is in fact a two-leg operation inside Vancelian — a stablecoin loan (EURC → EUR at parity) and a subsequent crypto-for-stablecoin exchange to close the loan.

### Why this mechanic matters — the technical nature of the transaction

This is not just a back-office detail; it changes the nature of the operation recorded on your account. A direct crypto-to-fiat sale would be a single cession of your crypto-asset against euros. Here, the flow is structured differently:

- **Leg 1 (EURC → EUR):** a 1:1 stablecoin-to-fiat conversion. By design a stablecoin redemption at parity, this leg does not generate a gain or a loss.
- **Leg 2 (crypto → EURC):** a crypto-for-stablecoin exchange at market price. This is a crypto-to-crypto operation in the technical sense — one crypto-asset is exchanged against another crypto-asset (EURC being itself a crypto-asset under MiCA).

Taxation rules vary widely across jurisdictions. In some countries, crypto-to-crypto exchanges are treated as taxable events; in others, only the realisation of fiat (cession in legal tender) triggers a capital-gain calculation. The interpretation of a crypto-to-stablecoin exchange is itself a matter of local rule and sometimes of administrative practice.

For these reasons, **the technical nature of the operation should be presented as it is to your tax advisor or to your tax administration**: a crypto-to-EURC exchange followed by a non-remunerated EURC loan converted 1:1 into EUR to settle a card payment. Whether this qualifies as a taxable cession, as a crypto-to-crypto exchange deferred until a later fiat realisation, or under any specific regime (for instance the French "flat tax" on digital asset gains, article 150 VH bis of the CGI), depends on your country of residence and on the interpretation of your advisor.

### What Vancelian does and does not do

Vancelian provides the technical record of every leg of the operation — the reserve creation, the EURC loan, the EURC → EUR conversion, the merchant settlement, and the closing crypto → EURC exchange — so that you or your advisor can reconstitute the full sequence. Vancelian **does not provide tax advice**, **does not qualify the tax regime applicable to your operations**, and **does not represent that the mechanic produces a specific tax outcome** in any jurisdiction. The determination of your tax obligations is your personal responsibility.

## Caveats

- The 15-minute reserve window is strict. If no payment is made within that period, the entire operation is cancelled automatically and nothing moves out of your crypto wallet.
- The crypto-to-EURC exchange rate used at the repayment leg is determined by the platform's execution engine at the moment of reserve creation, not at payment time.
- The EURC loan is non-remunerated — it is an operational mechanism, not a credit product.
- Actual payment limits depend on your account level, card type, and applicable daily/monthly caps.
- Card payments must be made at standard Visa/Mastercard-accepting merchants.
- **Tax treatment is jurisdiction-specific.** Vancelian does not provide tax advice. Present the technical nature of the operation to a qualified tax advisor in your country of residence before drawing any conclusion on the applicable regime.

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — §544-606: "Service de paiement sur réserve de crypto-actifs" — full technical description of the reserve creation, the EURC loan, the crypto-to-EURC exchange at repayment, and the 15-minute window.
