---
status: treated
date: 2026-04-20
feedback_type: negative
source_question: "est ce que je peux perdre mon argent si Vancelian n'a pas mica? dois je arreter d'investir dans l'app?"
user_comment: "Vancelian devrait mettre en place un plan de fermeture ordonnée supervisé par l'AMF

on ne sait pas si c'est l'AMF qui va supervisé ca"
wiki_pages_used:
  - faq/legal-compliance/what-happens-if-vancelian-does-not-obtain-mica.md
  - faq/legal-compliance/mica-overview-and-vancelian.md
  - faq/legal-compliance/vancelian-mica-roadmap.md
  - faq/legal-compliance/risk-warning-summary.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-20
treated_action: overattribution_amf_corrected
---

# est ce que je peux perdre mon argent si Vancelian n'a pas mica? dois je arreter d'investir dans l'app?

## Client question
> est ce que je peux perdre mon argent si Vancelian n'a pas mica? dois je arreter d'investir dans l'app?

## Bot answer
> Sur la question « dois-je arrêter d'investir » — je ne peux pas vous conseiller sur une décision d'investissement, ni vous dire de continuer, ni de vous arrêter, ni de retirer vos fonds. Cette décision dépend de votre situation personnelle et relève d'un conseiller qualifié.
> 
> Je peux en revanche vous rappeler les faits factuels concernant le cadre réglementaire et le traitement de vos fonds en cas de non-obtention MiCA.
> 
> **La situation actuelle**
> 
> Vancelian opère en tant que PSAN auprès de l'AMF sous le numéro E2023-087, ce qui l'autorise à fournir des services crypto jusqu'au 30 juin 2026 dans la période transitoire MiCA. Le dossier de demande CASP a été soumis à l'AMF et est en instruction, avec l'objectif d'obtenir l'autorisation avant le 1er juillet 2026 — date limite fixée par le régulateur.
> 
> **Si l'autorisation CASP n'était pas obtenue**
> 
> Vancelian devrait mettre en place un plan de fermeture ordonnée supervisé par l'AMF. Le traitement de vos fonds dépendrait alors de leur localisation, selon trois catégories distinctes :
> 
> 1. **Fonds ségrégués directement restituables**
>    - Vos EUR sur le compte dédié sont conservés en ségrégation chez Modulr Finance B.V. (EMI régulée) → restitution directe via virement IBAN vers votre compte bancaire.
>    - Vos crypto-actifs dans votre wallet dédié (non alloués à un Coffre ou à une Offre Exclusive), sécurisés en technologie Fireblocks → transfert vers un wallet de votre choix.
>    - Le principe de ségrégation rend cette restitution possible : les fonds clients sont juridiquement distincts des fonds propres de Vancelian.
> 
> 2. **Fonds engagés dans un Coffre** (Flexible, Future)
>    Vos fonds ne sont plus en unités cash ou crypto — ils représentent une part d'allocation dans des programmes sous-jacents (mining, lending, offres exclusives) engagés auprès de contreparties tierces. En cas de fermeture, la relation d'intermédiation s'interrompt mais l'engagement contractuel envers les contreparties demeure ; le capital serait récupéré selon les échéances prévues avec chacune d'elles.
> 
> 3. **Fonds engagés dans une Offre Exclusive** (Cloud Mining, Dubai Villa, Bali Villas, etc.)
>    Ces offres sont structurées avec une contrepartie externe. La contrepartie reste active et responsable d'exécuter le programme. En cas de fermeture de Vancelian, Vancelian ne serait plus intermédiaire mais les fonds resteraient engagés auprès de la contrepartie selon la feuille de route contractuelle.
> 
> **Principe clé**
> 
> La fermeture de Vancelian n'entraîne pas en elle-même une perte de capital. Une partie des fonds (EUR ségrégés + crypto en wallet dédié) est restituable immédiatement ; l'autre partie (Coffres et Offres Exclusives) est récupérable selon les échéances contractuelles prévues. Les vrais risques de perte de capital sont ceux propres à chaque programme sous-jacent (défaut d'une contrepartie, aléa opérationnel), pas le statut réglementaire de la plateforme.
> 
> Pour toute question spécifique à votre position, contactez le support Vancelian à support@vancelian.com ou via la section support de l'application.

## Feedback
**Type:** negative
**User comment:** "Vancelian devrait mettre en place un plan de fermeture ordonnée supervisé par l'AMF

on ne sait pas si c'est l'AMF qui va supervisé ca"

## Diagnosis

**Deuxième passe sur le même ticket après correctifs initiaux 2026-04-20.**

La réponse globale est maintenant conforme (refus net sur *"dois-je arrêter d'investir"* + rappel factuel PSAN/CASP + structure en 3 catégories + principe ségrégation / engagement contractuel). Un seul défaut résiduel, mais **récurrent** — flag Jean : *"on l'avait déjà relevé celui-là mais ça revient"*.

**Défaut identifié :** sur-attribution de rôle supervisoire à l'AMF.

Le bot écrit : *"Vancelian devrait mettre en place un plan de fermeture ordonnée **supervisé par l'AMF**"*.

Cause racine : dans le correctif initial de cette session 2026-04-20, j'ai (assistant) réécrit le `## Short answer` de la fiche wiki `what-happens-if-vancelian-does-not-obtain-mica.md` en introduisant la formule *"supervised by the AMF"*. Le bot a cité cette formule du wiki en toute bonne foi — le problème est donc en amont, dans ma propre écriture.

**Distinction factuelle qu'il fallait respecter :**
- L'AMF **exige** un plan de fermeture ordonnée des PSAN qui ne poursuivent pas CASP (deadline 30 mars 2026 pour initier le plan) → *"required by"* est exact
- L'AMF **supervise l'exécution** d'un tel plan → cela n'est **pas** documenté publiquement ; c'est une extrapolation
- La fiche originale utilisait *"supervised by the competent authority"* (vague par nature, volontairement) ligne 95 ; j'ai upgradé à *"AMF"* ce qui est une attribution trop forte

Pattern plus large : toute phrase de la forme *"[autorité nommée] [verbe actif fort] [processus hypothétique]"* est suspecte et doit être sourcée littéralement ou reformulée. Les verbes concernés : supervise, oversee, execute, manage, pilot, orchestrate, run. Les formulations sûres : *"required by"*, *"in the framework of"*, *"in accordance with"*.

La règle générale existait déjà dans `<factual_discipline>` du bot (*"NEVER name a specific authority, process, or third party as responsible for a hypothetical scenario unless the wiki page explicitly names them"*) — mais elle ne tenait pas car la source (wiki) elle-même avait été contaminée par cette sur-attribution.

## Action taken

Correctif **3 niveaux** appliqué en session 2026-04-20 (seconde passe) :

**A. Wiki — `what-happens-if-vancelian-does-not-obtain-mica.md` short_answer corrigé :**

Avant : *"Vancelian would have to implement an **orderly wind-down plan** supervised by the AMF"*
Après : *"Vancelian would have to implement an **orderly wind-down plan** as required by the AMF framework — which would be communicated transparently to clients. The exact supervisory modalities of such a plan are not publicly documented in advance."*

La hedging formula *"The exact supervisory modalities are not publicly documented in advance"* est ajoutée pour rendre explicite la limite de ce que l'on peut affirmer.

**B. Bot — exemple canonique MiCA corrigé** (dans `<examples>` du ANSWER_SYSTEM) :

Avant : *"Vancelian devrait mettre en place un plan de fermeture ordonnée supervisé par l'AMF"*
Après : *"Vancelian devrait mettre en place un plan de fermeture ordonnée, dans le cadre prévu par l'AMF. Les modalités précises de supervision d'un tel plan ne sont pas publiquement documentées en amont."*

**C. Bot — `<factual_discipline>` renforcé avec anti-exemple concret :**

Nouvelle règle ajoutée explicitant le cas : *"The AMF **requires** an orderly wind-down plan from PSANs; it does not necessarily **supervise its execution**. The correct phrasing is 'as required by the AMF framework' or 'in accordance with the AMF's requirements', not 'supervised by the AMF'."* Même règle étendue à ACPR, Banque de France, ESMA, VARA, SCA, DNB (Modulr), etc.

**D. Auto-memory — pattern récurrent gravé :**

Nouvelle mémoire `feedback_no_supervisory_overattribution.md` créée avec la distinction *required by / supervised by / executed by* et la règle d'audit pour tout verbe actif attaché à une autorité nommée. Ajoutée à `MEMORY.md`.

Syntaxe bot.js : `node -c bot.js` → OK.

**Observation transversale :** c'est la 4e fois en 3 jours qu'une correction bot dévoile un gap résiduel. Le pattern converge : le LLM (et moi) gravitons vers des formulations qui **ajoutent une structure rassurante** (oui/non, autorité nommée, garantie explicite) au-delà de ce que la source autorise. La règle méta est : *toute phrase qui ajoute de la certitude doit être sourcée littéralement*.

**Action résiduelle côté Jean :** (1) restart bot (boot-cache reload), (2) rejouer la même question → vérifier que le bot écrit *"dans le cadre prévu par l'AMF"* (ou *"as required by the AMF"*) et non *"supervisé par l'AMF"*.
