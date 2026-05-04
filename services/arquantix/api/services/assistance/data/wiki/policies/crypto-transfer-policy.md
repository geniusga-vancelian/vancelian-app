---
title: Crypto transfer policy — blockchains, timelines, security, and rejection rules
slug: crypto-transfer-policy
category: policies
audience: internal
status: draft
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 31_Politique de transfert de cryptos-actifs_Automata France.docx
related:
  - wiki/faq/crypto/how-to-deposit-cryptoassets-on-the-vancelian-app.md
  - wiki/faq/crypto/how-to-make-a-crypto-asset-withdrawal.md
  - wiki/faq/crypto/travel-rules-crypto-asset-withdrawals-and-compliance-with-re.md
tags: [transfer, blockchain, Ethereum, Base, Fireblocks, KYT, AML, TFR, withdrawal, deposit]
---

# Crypto transfer policy — blockchains, timelines, security, and rejection rules

## Summary

Vancelian supports crypto deposits and withdrawals on Ethereum and Base blockchains. Transfers are executed by Fireblocks (a regulated custody provider) within a maximum of 1 day. All withdrawals undergo Know-Your-Transaction (KYT) checks via Chainalysis, Travel Rule compliance via Notabene, and AML screening via ComplyAdvantage. If on-chain confirmation fails due to gas fee volatility, the transaction is automatically rejected and the full amount is re-credited to the client's account — Automata absorbs the gas fee loss.

## Details

### Supported blockchains

- **Ethereum** (mainnet)
- **Base** (Optimism Layer 2)

These are the only blockchains currently supported for crypto deposits and withdrawals on Vancelian.

### Execution timeline

- **Maximum delay:** 1 business day from submission to on-chain confirmation.
- **Typical timeline:** Most transfers complete within 2–6 hours, depending on network congestion.
- **Indicative.** Times may vary based on blockchain load and gas prices.

### Confirmation and irreversibility

**Ethereum:**
- Requires 70 block confirmations for transaction irreversibility.
- At current Ethereum block times (~12 seconds per block), this is approximately 14 minutes.
- After 70 confirmations, the transaction is considered final and cannot be reversed.

**Base:**
- Confirmation timeline is faster than Ethereum due to shorter block times.
- The same security standard is applied (70 block confirmations or equivalent safety measure) through the Fireblocks MPC infrastructure.

### Custody and withdrawal architecture

Crypto-asset custody is operated by **Vancelian**. Private-key security is handled via the **Fireblocks MPC (Multi-Party Computation) technology**: key shares are distributed so that no single party ever holds a complete private key, and transaction authorisation goes through a Transaction Authorisation Policy (TAP) with multiple approvals.

**Hot wallet:**
- Vancelian maintains dedicated withdrawal wallets for each supported blockchain, orchestrated via the Fireblocks infrastructure.
- These hot wallets hold sufficient liquidity to process most withdrawal requests immediately.

**Omnibus storage:**
- Bulk client crypto-assets are held in Vancelian omnibus wallets (shared custody structure, segregated at the client level in Vancelian's ledger).
- These are not accessible to individual Vancelian staff members: the MPC architecture, combined with the multi-signature policy, means no single operator can move client assets unilaterally.

**Rebalancing:**
- If a hot wallet has insufficient funds for a requested withdrawal, an internal rebalancing is triggered from omnibus storage through the Fireblocks infrastructure.
- The withdrawal request remains pending (max 1 day) while rebalancing occurs.
- No additional cost is charged to the client.

### Pre-transfer compliance checks

All withdrawals undergo the following checks before on-chain execution:

**1. Know-Your-Transaction (KYT) via Chainalysis:**
- Scans the destination address for association with sanctioned entities, stolen funds, or high-risk counterparties.
- If the address is flagged, the withdrawal is held for Compliance review (typically 24–48 hours).

**2. Travel Rule compliance (TFR) via Notabene:**
- For withdrawals to exchanges or custodians in certain jurisdictions, Vancelian collects originator and beneficiary information per FATF Travel Rule.
- If required information is missing, the withdrawal is delayed until TFR fields are completed.

**3. Anti-Money Laundering (AML) screening via ComplyAdvantage:**
- Cross-references the destination address against AML watchlists and sanctions databases.
- If a match is found, the transaction is escalated to Compliance.

### Blacklisted platform deposits

- If a client deposits crypto from a blacklisted exchange or high-risk platform (identified via Chainalysis KYT), the deposit is flagged.
- Funds are frozen pending Compliance review.
- Compliance may request additional documentation (e.g., source of funds) or reject the deposit and return it to the sending address.

### Transaction rejection and re-crediting

**Scenario: Gas fee failure**

If on-chain confirmation fails due to unexpectedly high gas prices or network congestion:
1. The transaction is submitted on-chain (via the Fireblocks infrastructure) at an estimated gas price.
2. If actual gas cost exceeds the estimate and the transaction would fail, it is rejected before being committed on-chain.
3. The full crypto amount is **automatically re-credited** to the client's Vancelian account.
4. **Gas fees are absorbed by Automata France** — the client is not charged.

**Other rejection scenarios:**

- **Destination address invalid:** Client is notified; funds are not sent.
- **KYT flag (sanctions):** Transaction is held for Compliance review; client is notified.
- **Insufficient hot wallet liquidity + rebalancing timeout (>1 day):** Client is notified; alternative withdrawal schedule is offered.

### Withdrawal security requirement

- **3-Factor Authentication (3FA) is required for all withdrawals:**
  - Email confirmation (OTP or link)
  - TOTP authenticator (Google Authenticator, Authy, or similar)
  - This ensures that even if a client's password is compromised, withdrawal cannot proceed without the second factor.

### Deposit process

- **No 3FA required for deposits** (incoming transfers are unidirectional; client is receiving funds).
- KYT check occurs post-deposit; funds may be temporarily frozen if source is flagged.
- Compliance review timeline: typically 24–48 hours for flagged deposits.

### Reversals and dispute process

- **On-chain transactions are irreversible** once confirmed (70 blocks on Ethereum, equivalent on Base).
- If a client believes a withdrawal was made in error, they must contact Vancelian Compliance within 30 days.
- Vancelian can request assistance from the destination address owner or exchange, but cannot reverse an on-chain transaction.
- For lost or misdirected withdrawals, Compliance will investigate and attempt to recover funds; recovery success depends on the destination counterparty's cooperation.

## Operational notes

- **Chain congestion:** During periods of high blockchain traffic, all timelines may extend (but max 1 day remains the policy target).
- **Stablecoin conversions:** If a client requests a withdrawal to a different stablecoin than currently held (e.g., USDC → USDT), an internal conversion occurs before on-chain transfer.
- **Partial withdrawal holds:** If Vancelian suspects fraud or AML risk, it may hold a withdrawal pending Compliance sign-off (up to 10 business days per regulatory requirement).

## Regulatory basis

- **MiCA Article 78** — best execution; applies to on-chain timing and cost (gas) optimization.
- **FATF Travel Rule** — Travel Rule compliance via Notabene.
- **EU AML Regulation (5AMLD/6AMLD)** — KYT and AML screening via third-party providers.

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 31_Politique de transfert de cryptos-actifs_Automata France.docx] — Crypto transfer policy; details supported blockchains (Ethereum, Base), Automata France SAS custody architecture (PSAN E2023-087, secured via Fireblocks MPC technology), pre-transfer compliance (KYT, TFR, AML), rejection and re-crediting rules, and 3FA withdrawal security requirement (updated per AMF feedback, Nov 2025)
