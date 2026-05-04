---
status: treated
date: 2026-04-14
feedback_type: negative
source_question: "Que deveinnent mes fonds si Vancelian n'a pas mica"
user_comment: "La reponse n'est pas factuelle il y a de l'interpretation ici

**Vos investissements en cours (Cloud Mining, Dubai Villa, etc.).** Ces positions resteraient valides légalement — ce sont des contrats de prêt ou de financement, non directement régis par MiCA. Cependant, la gestion opérationnelle et l'accès à votre portefeuille seraient organisés via un tiers autorisé."
wiki_pages_used:
  - faq/legal-compliance/what-happens-if-vancelian-does-not-obtain-mica.md
  - faq/legal-compliance/mica-overview-and-vancelian.md
  - faq/legal-compliance/vancelian-mica-roadmap.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
  - faq/legal-compliance/how-does-vancelian-ensure-the-security-and-management-of-my-.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-14
treated_action: "Section 3 (Exclusive Offers) of what-happens-if-vancelian-does-not-obtain-mica.md rewritten to remove interpretive language. Deleted: partner constitution details (JV composition, SIREN, Solaria vehicle mention), 'economic relationship would continue' phrasing, 'alternative arrangements for platform and communication would be sought'. Kept strictly factual: counterparty is active and responsible for the programme, Vancelian is intermediary, wind-down falls under competent authority supervision, specific modalities cannot be anticipated, escalate to support for individual positions. Authority reference softened from 'AMF' to 'competent authority' (AMF may not necessarily be the supervising body for all counterparties). Pending Step 2: add anti-interpretation guardrail in ANSWER_SYSTEM."
---

# Que deveinnent mes fonds si Vancelian n'a pas mica

## Client question
> Que deveinnent mes fonds si Vancelian n'a pas mica

## Bot answer
> Si Vancelian n'obtient pas son autorisation CASP avant le **1er juillet 2026**, voici ce qui se passerait :
> 
> **Pas de perte de fonds immédiate.** La non-obtention de MiCA n'entraîne pas la confiscation ou la perte automatique de vos fonds. En revanche, Vancelian serait contrainte de cesser ses activités de services sur crypto-actifs à partir de cette date, car c'est un deadline ferme imposé par l'AMF français — il n'y a pas d'extension possible.
> 
> **Plan de dénouement ordonné.** Dans ce scénario, Vancelian mettrait en place un plan de sortie transparent communicué à tous les clients. Vos fonds seraient soit :
> - Restitués directement sur votre compte bancaire (pour les euros en compte), ou
> - Transférés vers un autre prestataire autorisé CASP (pour les crypto-actifs et les investissements en cours).
> 
> **Vos investissements en cours (Cloud Mining, Dubai Villa, etc.).** Ces positions resteraient valides légalement — ce sont des contrats de prêt ou de financement, non directement régis par MiCA. Cependant, la gestion opérationnelle et l'accès à votre portefeuille seraient organisés via un tiers autorisé.
> 
> **Vancelian travaille activement à l'obtention de sa licence CASP.** Son dossier a été soumis à l'AMF et est en cours d'instruction, avec un objectif de juin 2026. Cette situation demeure l'objectif principal de la conformité réglementaire.
> 
> Pour toute question spécifique sur l'impact d'un tel scénario sur votre propre situation, contactez support@vancelian.com — l'équipe peut répondre à vos préoccupations directement.

## Feedback
**Type:** negative
**User comment:** "La reponse n'est pas factuelle il y a de l'interpretation ici

**Vos investissements en cours (Cloud Mining, Dubai Villa, etc.).** Ces positions resteraient valides légalement — ce sont des contrats de prêt ou de financement, non directement régis par MiCA. Cependant, la gestion opérationnelle et l'accès à votre portefeuille seraient organisés via un tiers autorisé."

## Diagnosis
Two interpretive claims not grounded in the source:
1. *"Ces positions resteraient valides légalement — ce sont des contrats de prêt ou de financement, non directement régis par MiCA."* → legal qualification (validity, MiCA scoping) not present in the wiki page. Paraphrase-inflation by the LLM.
2. *"la gestion opérationnelle et l'accès à votre portefeuille seraient organisés via un tiers autorisé."* → the wiki said only "alternative arrangements would be sought"; the bot hardened it into "tiers autorisé", which is not a documented Vancelian commitment.

Root cause — double:
- **Wiki**: Section 3 used open, abstract phrasings ("intermediation role", "alternative arrangements would be sought") that invite interpretive paraphrase.
- **Bot prompt**: no explicit guardrail against adding legal qualifications or speculative modalities on hypothetical scenarios.

## Action taken
- Section 3 rewritten (see frontmatter action).
- Step 2 pending: ANSWER_SYSTEM guardrail on interpretive claims for hypothetical scenarios.
