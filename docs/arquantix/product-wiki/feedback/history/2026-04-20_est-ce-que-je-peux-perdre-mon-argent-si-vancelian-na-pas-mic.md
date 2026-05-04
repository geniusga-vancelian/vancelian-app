---
status: treated
date: 2026-04-20
feedback_type: negative
source_question: "est ce que je peux perdre mon argent si Vancelian n'a pas mica? dois je arreter d'investir dans l'app?"
user_comment: "a compléter et a corriger"
wiki_pages_used:
  - faq/legal-compliance/what-happens-if-vancelian-does-not-obtain-mica.md
  - faq/legal-compliance/mica-overview-and-vancelian.md
  - faq/legal-compliance/vancelian-mica-roadmap.md
  - faq/legal-compliance/risk-warning-summary.md
  - faq/legal-compliance/where-and-how-is-vancelian-regulated.md
channel_id: C0ASFKQFY2V
feedback_user: U01UY0Q7ZE1
treated_date: 2026-04-20
treated_action: bot_system_prompt_reinforced_v3_plus_wiki_short_answer
---

# est ce que je peux perdre mon argent si Vancelian n'a pas mica? dois je arreter d'investir dans l'app?

## Client question
> est ce que je peux perdre mon argent si Vancelian n'a pas mica? dois je arreter d'investir dans l'app?

## Bot answer
> Non, vous ne devez pas arrêter d'investir. Vancelian prépare activement sa transition vers le statut CASP sous MiCA, avec un objectif d'obtention de l'autorisation avant le **1er juillet 2026** — la date limite fixée par l'AMF.
>
> **La situation actuelle**
>
> Vancelian opère actuellement en tant que PSAN (Prestataire de Services sur Actifs Numériques) auprès de l'AMF sous le numéro E2023-087. Ce statut lui permet de continuer à fournir des services en crypto jusqu'au 30 juin 2026, dans le cadre de la période transitoire MiCA. Le dossier de demande CASP a déjà été soumis à l'AMF et est en instruction.
>
> **En cas de non-obtention de l'autorisation**
>
> Si, exceptionnellement, l'autorisation CASP n'était pas obtenue avant le 1er juillet 2026, Vancelian devrait mettre en place un plan de fermeture ordonnée. Cela signifierait que les fonds seraient restitués aux clients ou transférés vers un prestataire CASP autorisé — les actifs ne seraient pas perdus. Une telle situation entraînerait bien sûr une interruption de service, mais ce scénario reste très peu probable au vu de l'avancement de la demande.
>
> **Vos investissements existants**
>
> Vos investissements actuels ne sont pas à risque du fait de la transition MiCA. Que Vancelian opère en tant que PSAN ou CASP, la structure contractuelle et les droits des investisseurs demeurent les mêmes.
>
> Pour tout détail supplémentaire sur le calendrier réglementaire ou vos questions spécifiques, contactez le support Vancelian à support@vancelian.com.

## Feedback
**Type:** negative
**User comment:** "a compléter et a corriger"

## Diagnosis

Question double-enjeu : (1) factuel sur le scénario non-obtention MiCA — *"est-ce que je peux perdre mon argent ?"*, (2) conseil d'investissement — *"dois-je arrêter d'investir ?"*. Trois défauts identifiés.

**1. Régression garde-fou conseil (sévère).**
Le bot ouvre par : *"Non, vous ne devez pas arrêter d'investir."* → réponse **oui/non à une décision d'investissement**, strictement interdite. Le garde-fou `<escalation_triggers>` Personalized advice posé le 18/04 puis renforcé le 19/04 couvrait explicitement les verbes "recommander / vendre / acheter / allocation / swap" mais **pas** les verbes plus abstraits "continuer / arrêter / investir / diversifier / retirer / maintenir". Le LLM a exploité ce gap — il a interprété *"dois-je arrêter d'investir ?"* comme une demande de rassurance et a donné un "Non" direct. C'est du conseil en investissement déguisé en réassurance.

Flag Jean explicit : *"Il ne faut jamais répondre par oui ou par non aux questions relatives au conseil en investissement"*. Gap à combler dans le prompt.

**2. Section "Vos investissements existants" aplatie (gros gap éditorial).**
Le bot écrit : *"Vos investissements actuels ne sont pas à risque du fait de la transition MiCA. Que Vancelian opère en tant que PSAN ou CASP, la structure contractuelle et les droits des investisseurs demeurent les mêmes."* → **factuellement imprécis et vague**. La wiki `what-happens-if-vancelian-does-not-obtain-mica.md` contient déjà (lignes 75-99) une structure en 3 catégories impeccable :
- §1 Segregated custody (EUR Modulr + crypto Fireblocks MPC) → restitution directe
- §2 Vault allocations → engagement contractuel avec contreparties
- §3 Exclusive Offers → contrepartie externe active

Le bot avait la matière dans les pages chargées mais a aplati. Cause probable : PASS 2 a privilégié la synthèse courte au détriment de la structure. Le `short_answer` de la fiche ne contenait pas explicitement les 3 catégories → quand le LLM se base sur la première section, il perd la structure.

**3. Partie "situation actuelle" + "en cas de non-obtention" correcte.**
Jean flag *"Correcte"*. Le rappel du statut PSAN E2023-087, de la deadline 1er juillet 2026, du dossier CASP en instruction, et du plan de fermeture ordonnée avec restitution / transfert CASP est bien traité. Rien à toucher.

**Principe clé qu'il faut faire passer (selon Jean) :**
Ni la non-obtention MiCA ni une faillite Vancelian n'entraînent en elles-mêmes une perte de capital — (a) la part ségréguée (EUR IBAN + crypto wallet dédié) est restituée immédiatement par **principe de ségrégation** ; (b) la part engagée (Coffres, Offres Exclusives) est récupérée selon les échéances contractuelles avec les contreparties, Vancelian cessant d'être intermédiaire mais les fonds n'étant pas perdus.

## Action taken

Correctif **3 niveaux** appliqué en session 2026-04-20 :

**A. `vancelian-bot/bot.js` — 3 patches garde-fou conseil + exemple canonique :**

1. `<escalation_triggers>` **Personalized advice** étendu — ajout explicite des verbes d'action (*continuer, arrêter, investir, diversifier, retirer, maintenir, vendre, acheter*) comme triggers. Règle nouvelle : *"**NEVER answer yes/no to an investment-decision question.** The verb of action is the trigger — as soon as the client asks 'dois-je [verb] ?' on an investment action, the answer MUST be a direct refusal, never a yes or a no"*. Structure de réponse obligatoire clarifiée : [refus direct] + [rappel factuel des faits sans prendre position] + [redirect support].

2. `<forbidden_patterns>` — nouvelle entrée dédiée : *"Yes/no on an investment-decision action"*. Liste explicite des ouvertures interdites : *"Non, vous ne devez pas arrêter d'investir"*, *"Oui, vous pouvez continuer"*, *"No, don't stop investing"*, *"Vous n'avez pas à vous inquiéter"*, *"Il n'y a pas de raison de retirer vos fonds"*. Qualifié explicitement de **conseil déguisé en réassurance**.

3. `<examples>` — nouvel exemple canonique sur la question exacte du ticket : *"Est-ce que je peux perdre mon argent si Vancelian n'a pas MiCA ? Dois-je arrêter d'investir dans l'app ?"*. La réponse modèle :
   - Ouvre par le refus net sur *"dois-je arrêter d'investir"*
   - Rappelle les faits factuels : situation actuelle (PSAN E2023-087, dossier CASP en instruction, deadline 1er juillet 2026) + scénario non-obtention (plan de fermeture ordonnée AMF)
   - Restitue la structure en 3 catégories (ségrégation EUR Modulr + crypto Fireblocks, Coffres engagés, Offres Exclusives)
   - Formule le principe clé : faillite Vancelian ou non-obtention MiCA ≠ perte de capital — ségrégation pour la part directe, échéances contractuelles pour la part engagée
   - Clôt par redirect support

**B. Wiki — `what-happens-if-vancelian-does-not-obtain-mica.md` short_answer enrichi :**

`## Short answer` complété pour que les 3 catégories soient **explicites dès le short_answer** (ségrégation directement restituable + Vault allocations engagées contractuellement + Offres Exclusives avec contrepartie externe). Ajout du principe clé en fin de short_answer : *"neither non-obtainment of MiCA nor a Vancelian wind-down causes a loss of capital by itself"*. Raison : quand PASS 2 se base sur le short_answer (section la plus souvent utilisée), la structure doit déjà être là pour éviter l'aplatissement.

**C. Auto-capitalisation — note :**
Pas de nouvelle règle auto-memory cette fois-ci — la règle existante `feedback_advice_decline_no_product_list.md` (19/04) est étendue **dans le bot** (prompt renforcé) mais le principe reste le même : décliner le conseil. La nouveauté (verbes d'action abstraits) est maintenant gravée dans le `<escalation_triggers>` et les `<forbidden_patterns>` du bot, pas besoin de doubler en auto-memory.

Syntaxe bot.js vérifiée : `node -c bot.js` → OK.

**Action résiduelle côté Jean :** (1) restart bot (boot-cache reload), (2) rejouer la même question en Slack pour valider que le bot ouvre maintenant par un refus net sur *"dois-je arrêter d'investir"* et restitue les 3 catégories de fonds avec le principe "pas de perte de capital par ségrégation + engagement contractuel".
