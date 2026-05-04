---
status: treated
date: 2026-04-14
feedback_type: negative
source_question: "c'etait pas clair"
user_comment: "il a pa pas pris en compte nos modification sur les dernier ticket.

Attention autant ModulR est une entité autant fireblocks est une solutions MPC le custody est chez Vancelian.

DAns les deux cas c'est par ceque vancelian a segregué les fond qu'ils pourra les retransférés aux clients"
wiki_pages_used:
  - faq/legal-compliance/what-happens-if-vancelian-does-not-obtain-mica.md
  - faq/legal-compliance/vancelian-mica-roadmap.md
  - faq/legal-compliance/what-is-mica-and-why-is-it-important-for-vancelian.md
  - faq/legal-compliance/how-does-vancelian-ensure-the-security-and-management-of-my-.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-14
treated_action: "Full-wiki Fireblocks sweep (14 pages corrected). Canonical framing established: Vancelian is the custodian; Fireblocks supplies MPC technology, not custody. Client protection derives from segregation — operated by Vancelian on crypto (per-client segregated wallets, MPC + TAP + multi-sig) and enforced at Modulr Finance B.V. (DNB-regulated EMI, not FCA) on EUR. Pages touched: what-happens-if-vancelian-does-not-obtain-mica, how-does-vancelian-ensure-the-security, settlement-delivery-model, crypto-transfer-policy, where-and-how-is-vancelian-regulated, who-are-vancelians-partners, how-crypto-deposits-and-withdrawals-work-technically, how-can-i-trade-cryptoassets, own-account-interposition, cloud-mining-risks-overview, how-cloud-mining-flow-works, how-exclusive-offer-btc-lending-works, how-vault-liquidity-and-returns-work, gdpr-and-vancelian. Bot restart required to apply (boot-cache)."
---

# c'etait pas clair

## Client question
> c'etait pas clair

## Bot answer
> Je comprends. Laissez-moi clarifier les points clés.
> 
> **Situation actuelle :** Vancelian a soumis sa demande de licence CASP à l'AMF et est actuellement en instruction, avec pour objectif de l'obtenir avant le 1er juillet 2026. C'est le scénario attendu.
> 
> **Si la licence n'est PAS obtenue à temps :**
> 
> Le 1er juillet 2026 est une date limite ferme fixée par l'AMF — pas de prolongation possible. À partir de cette date, seuls les prestataires autorisés CASP peuvent continuer à opérer en France. Si Vancelian n'avait pas la licence, elle ne pourrait plus proposer ses services.
> 
> **Mais vos fonds seraient-ils perdus ? Non.**
> 
> Vos euros sont détenus chez **Modulr Finance** (institution de monnaie électronique régulée aux Pays-Bas). Vos cryptoactifs sont custodisés chez **Fireblocks** (l'un des plus grands prestataires d'industrie). Ces deux entités sont complètement indépendantes de Vancelian.
> 
> En cas de problème opérationnel, Vancelian mettrait en place un plan de liquidation ordonné : vos fonds seraient restitués ou transférés à un autre prestataire autorisé. Les fonds ségrégés restent accessibles — ils ne disparaissent pas.
> 
> **En résumé :** La licence MiCA est un *permis d'opération*, pas une *garantie des fonds*. Même sans elle, vos fonds physiques restent protégés par les régulations locales de Modulr et Fireblocks.
> 
> Y a-t-il un point spécifique que vous souhaitez que j'éclaircisse davantage ?

## Feedback
**Type:** negative
**User comment:** "il a pa pas pris en compte nos modification sur les dernier ticket.

Attention autant ModulR est une entité autant fireblocks est une solutions MPC le custody est chez Vancelian.

DAns les deux cas c'est par ceque vancelian a segregué les fond qu'ils pourra les retransférés aux clients"

## Diagnosis
Two distinct problems layered:
1. **Factual error in the wiki** — several pages framed Fireblocks as an independent third-party custodian ("Vos cryptoactifs sont custodisés chez Fireblocks"). Incorrect. Fireblocks is an MPC technology supplier. The custodian is Vancelian itself. Client protection comes from **segregation** (per-client wallets operated by Vancelian on crypto, EUR ring-fenced at Modulr Finance B.V., regulated by DNB — not FCA).
2. **Bot hadn't absorbed prior corrections** — boot-cache: wiki edits don't take effect without a restart.

## Action taken
- **Full sweep of 14 wiki pages** to align on the canonical framing:
  > Vancelian is the custodian. Assets in per-client segregated wallets. Private keys secured via Fireblocks MPC technology — no single party holds a complete key. Fireblocks provides the technology, not the custody. Client fund protection derives from segregation (operated by Vancelian on crypto, enforced at Modulr DNB on EUR).
- Corrected Modulr regulator error that had propagated: FCA → DNB (Modulr Finance B.V. is the Dutch EMI, not the UK entity).
- Bot restart pending — required to apply.
