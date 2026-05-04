---
title: "How do crypto deposits and withdrawals work technically?"
slug: how-crypto-deposits-and-withdrawals-work-technically
category: crypto
audience: client
status: verified
last_reviewed: 2026-04-12
sources:
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 31_Politique de transfert de cryptos-actifs_Automata France.docx
  - raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx
related:
  - wiki/faq/crypto/how-to-deposit-cryptoassets-on-the-vancelian-app.md
  - wiki/faq/crypto/how-to-make-a-crypto-asset-withdrawal.md
  - wiki/faq/crypto/travel-rules-crypto-asset-withdrawals-and-compliance-with-re.md
tags: [deposit, withdrawal, blockchain, Ethereum, Base, Fireblocks, KYT, AML, security]
questions:
  - "How do crypto deposits and withdrawals work technically on Vancelian?"
  - "What blockchains does Vancelian support for transfers?"
  - "How long does a crypto withdrawal take on Vancelian?"
  - "What security checks happen on my crypto transfer?"
  - "What happens if my crypto withdrawal fails?"
  - "Why is my crypto withdrawal pending?"
  - "What if I deposit from a blacklisted platform?"
  - "How many block confirmations does Vancelian require?"
---

# How do crypto deposits and withdrawals work technically?

## Short answer

Vancelian supports crypto transfers on Ethereum and Base blockchains. Deposits are received on a dedicated wallet custodied by Vancelian (key security via the Fireblocks MPC technology), verified through KYT (Chainalysis), Travel Rule (Notabene), and AML (ComplyAdvantage) checks, then moved to secure omnibus storage. Withdrawals require 3-factor authentication and undergo the same compliance checks. Maximum execution time is 1 day, and if a transfer fails due to high gas fees, your funds are fully refunded at no cost.

## Details

### Deposits

1. You request a deposit for a supported crypto-asset.
2. Platform checks if you have a dedicated wallet; if not, one is created for you (custodied by Vancelian, key security managed via the Fireblocks MPC infrastructure).
3. You receive a deposit address and initiate the transfer from your external platform.
4. Crypto is received on your dedicated wallet under Vancelian's Transaction Authorisation Policy (TAP).
5. **Blacklist check**: If deposit originates from a blacklisted platform → assets are frozen and reviewed by the Compliance team.
6. **Verification checks**:
   - KYT (Know Your Transaction) via Chainalysis
   - Travel Rule TFR via Notabene
   - AML (Anti-Money Laundering) via ComplyAdvantage
7. Deposit is confirmed and validated.
8. Assets are transferred to omnibus client account for secure storage.

### Withdrawals

1. You request a withdrawal, selecting the crypto-asset and target blockchain.
2. You receive a recap showing amount and applicable fees.
3. **3-factor authentication required**: email confirmation + time-based code (Google Authenticator or equivalent).
4. Information is verified and recorded.
5. **Compliance checks**:
   - AML check (ComplyAdvantage)
   - KYT (Chainalysis)
   - Travel Rule TFR (Notabene)
6. Funds are sent from Vancelian's withdrawal wallet to your external address under the Transaction Authorisation Policy (TAP), orchestrated through the Fireblocks infrastructure.
7. Withdrawal is confirmed.

### Technical specifications

**Blockchains supported**:
- Ethereum
- Base

**Execution**:
- Maximum execution delay: 1 day (subject to blockchain confirmation times)
- Ethereum: 70 block confirmations required for transaction irreversibility
- Hot wallet architecture: Vancelian-custodied dedicated withdrawal wallets + omnibus storage, orchestrated via the Fireblocks MPC infrastructure
- If hot wallet insufficient: internal rebalancing is triggered, status remains "Pending", max 1 day total

**Gas fees**:
- If gas fees exceed expected amount: transfer is automatically rejected
- Your funds are fully re-credited at no cost
- Gas fees are absorbed by Automata France

## Caveats

- Transfer times depend on blockchain network congestion. The 1-day maximum applies under normal conditions.
- Deposits from flagged or blacklisted platforms may be frozen for compliance review, potentially delaying access.
- Always double-check the destination address and selected blockchain before confirming a withdrawal.
- Compliance checks (KYT, AML, Travel Rule) may require additional verification or documentation in certain cases.
- Withdrawal confirmations are permanent — ensure your destination address is correct before submission.

## Sources

- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 31_Politique de transfert de cryptos-actifs_Automata France.docx] — Crypto asset transfer policy, covering deposit/withdrawal flows, compliance checks, and blockchain specifications.
- [raw/Fiche MD Reglementation/Notice Vancelian/Annexe 36_Schéma des flux.docx] — Technical flow diagrams detailing the full deposit and withdrawal process, wallet management, and settlement.
