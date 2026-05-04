---
status: treated
date: 2026-04-21
feedback_type: negative_retest
source_question: "Le support m'a demandé des documents mais ça devient abusif, je peux ignorer ou contourner ?"
user_comment: "Ici il faut rappeller la legisltation Européen et UAE (pas francaise)"
wiki_pages_used:
  - faq/account/email-from-vancelian-compliance-team.md
  - faq/legal-compliance/lcb-ft-aml-compliance.md
  - faq/account/why-was-my-identity-verification-refused.md
  - faq/company/how-to-contact-customer-support.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-21
treated_action: retest_no_new_rule_confirmed_generic_wording_over_double_jurisdiction_restart_required
---

# Retest "documents support abusifs" — 2026-04-21

## Contexte
Retest de la même question que T3 traité la veille (2026-04-20). Ce retest intervient **avant restart du bot** — les 5 nouveaux `<forbidden_patterns>` gravés hier ne sont donc pas encore chargés en boot-cache.

## Bot answer (retest)
> Ignorer ou contourner les demandes du support n'est pas possible. Les documents demandés — justificatifs d'identité complémentaires, preuve de source de fonds, ou clarifications sur vos transactions — répondent à des obligations réglementaires auxquelles Vancelian est tenu **en vertu de la législation française et européenne (AML/CFT, KYC)**.
>
> Ces demandes émanent du service de conformité et s'inscrivent dans un cadre légal strict. **Le non-respect d'une demande de documentation peut entraîner le gel ou la suspension de votre compte sans préavis, conformément aux conditions d'utilisation.**
>
> Si vous considérez qu'une demande est déraisonnable, excessive, ou si vous ne comprenez pas pourquoi elle vous est adressée, contactez support@vancelian.com [...]

## Diagnosis

### Progrès vs T3 (2026-04-20)
- ✓ Pas de nom d'individu (Benjamin Messika absent)
- ✓ Pas d'anglicismes (*Compliance and Internal Control Officer* absent)
- ✓ Pas de clôture moralisante (*"La transparence fonctionne mieux que le contournement"* absent)
- ✓ Longueur correcte (3 paragraphes)

### Défauts résiduels (non encore corrigés car bot non redémarré)
1. **Décoration régulatoire localisée** : *"la législation française et européenne (AML/CFT, KYC)"*. Le client peut être UAE — la localisation française est fausse. Règle `feedback_institutional_framing.md` #2.
2. **Anticipation sous-question non posée** : paragraphe 2 intégral sur *"le gel ou la suspension de votre compte sans préavis"*. Exactement la sous-question *"et si je ne réponds pas ?"* que la règle `#3` interdit d'anticiper.

### Correction Jean
*"Ici il faut rappeller la legisltation Européenne et UAE (pas francaise)"* — Jean rejette d'abord la localisation **française**. Quand présenté avec deux options (A : double juridiction explicite EU+UAE / B : générique sans juridiction nommée), **Jean choisit B**.

### Clarification importante de la règle
Le commentaire littéral de Jean suggère d'ajouter EU+UAE. Mais la règle gravée la veille dit : *"si la même réponse tient pour un client UAE (VARA) et un client EEA (AMF/MiCA), ne pas nommer de régulateur du tout"*. Comme la mécanique (documents KYC = obligation structurelle universelle) tient pour les deux juridictions, **le générique sans juridiction l'emporte** — même si le commentaire utilisateur suggère de nommer les deux.

**Heuristique à graver** : quand l'utilisateur corrige une localisation fausse (*"pas française, plutôt européenne et UAE"*), la correction canonique est **retirer la localisation** plutôt qu'**ajouter les deux**. La règle-mère est la sobriété, pas l'exhaustivité juridictionnelle.

## Réponse cible (inchangée vs canonical example 2026-04-20)
> Ignorer ou contourner les demandes du support n'est pas possible. Les documents demandés — justificatifs d'identité complémentaires, preuve de source de fonds, ou clarifications sur vos transactions — répondent à des obligations réglementaires auxquelles Vancelian est tenu.
>
> Ces demandes sont traitées par le service de conformité. Pour toute question sur un document précis ou sur le contexte d'une demande, contactez support@vancelian.com.

## Action taken

### A. Pas de modification wiki
Les 6 fichiers ont été nettoyés hier. La règle générique tient.

### B. Pas de modification bot.js
Les 5 `<forbidden_patterns>` gravés hier couvrent déjà les 2 défauts résiduels. L'`<example>` canonique gravé hier donne exactement la réponse cible. **Seul un restart bot est nécessaire** pour que le boot-cache charge les nouvelles règles.

### C. Auto-memory enrichie
`feedback_institutional_framing.md` complétée avec l'heuristique "retirer la localisation plutôt qu'ajouter les deux" pour les corrections utilisateur de type *"pas français, plutôt européen et UAE"*.

### D. Ticket archivé
Ce fichier en `history/` avec diagnostic retest + confirmation que les règles gravées étaient correctes.

## Priorité opérationnelle
🔴 **Restart bot requis** pour que les règles gravées le 2026-04-20 soient actives côté Slack. Jusqu'au restart, le bot continuera à produire la réponse retest (améliorée vs T3 mais pas totalement conforme).
