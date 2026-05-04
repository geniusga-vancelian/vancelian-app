---
status: treated
date: 2026-04-20
feedback_type: auto_gap + positive_pair
source_question: "je ne souhaite pas communiquer mon numéro fiscal"
user_comment_autogap: "[Auto-detected gap] missing_detail: Clarify whether tax ID provision is mandatory for account activation, trading, or withdrawal, or if it can be deferred without service restrictions."
user_comment_positive: ""
wiki_pages_used:
  - faq/account/why-and-how-do-i-provide-my-tax-identification-number-in-the.md
  - faq/account/how-can-i-modify-my-personal-information.md
  - faq/legal-compliance/gdpr-and-vancelian.md
channel_id: C0ASFKQFY2V
feedback_user_autogap: system
feedback_user_positive: U02D2P6UY2X
treated_date: 2026-04-21
treated_action: wiki_fixed_tin_deadline_italian_exception_removed_bot_example_added
---

# je ne souhaite pas communiquer mon numéro fiscal

## Client question
> je ne souhaite pas communiquer mon numéro fiscal

## Paire de signaux
Deux tickets même timestamp (2026-04-20 09:04), même réponse bot :
- **Version positive** : 👍 utilisateur U02D2P6UY2X, aucun commentaire.
- **Version auto_gap** : système a détecté un gap factuel — *"Clarify whether tax ID provision is mandatory for account activation, trading, or withdrawal, or if it can be deferred without service restrictions."*

Feedback positif ≠ réponse correcte : l'auto-détection révèle que le bot ne répond pas clairement à la question sous-jacente (conséquence si refus), et cinq défauts s'y ajoutent au passage au crible des règles gravées.

## Bot answer (intégrale)
> Je comprends votre préoccupation concernant vos données personnelles.
>
> Selon la politique de Vancelian, le numéro fiscal est demandé dans le cadre de la mise en conformité avec la réglementation européenne **DAC8** [...]
>
> **Pour les nouveaux utilisateurs**, cette information est demandée lors de l'inscription [...]
>
> **Pour les utilisateurs existants**, vous serez invités à la fournir ultérieurement dans l'application — à l'exception des utilisateurs italiens chez qui cette donnée est déjà collectée.
>
> **Votre données personnelles et votre confidentialité**
>
> Vancelian se conforme au **GDPR** : vos données personnelles [...] Vous disposez également de droits sur vos données : accès, rectification, et suppression selon les conditions légales.
>
> **Si vous avez des questions spécifiques** sur pourquoi cette information est obligatoire pour votre situation personnelle, ou si vous souhaitez explorer des alternatives ou des dérogations possibles, je vous invite à contacter directement le support Vancelian à support@vancelian.com.

## Diagnosis

### Défaut 1 — Exception italienne erronée

Mention d'une distinction *"à l'exception des utilisateurs italiens chez qui cette donnée est déjà collectée"*. Clarification Jean 2026-04-21 : **pas d'exception italienne côté réponse client**. Si l'Italie l'a déjà collecté tant mieux, mais DAC8 étant une mesure européenne alignée avec MiCA, **le même régime s'applique à tous les clients EEA**. La distinction en réponse crée une asymétrie injustifiée et laisse penser à certains utilisateurs qu'ils peuvent être dans un cas de figure différent.

### Défaut 2 — "Alternatives ou dérogations possibles" (inventé)

*"si vous souhaitez explorer des alternatives ou des dérogations possibles, je vous invite à contacter..."*. Clarification Jean 2026-04-21 : **pas de dérogation possible**. DAC8 est une obligation légale sans exception individuelle. La formulation suggère l'existence d'une marge de négociation qui n'existe pas — pattern classique du bot qui cherche à "garder la porte ouverte" plutôt que poser la règle. Rattaché à la règle gravée `no supervisory over-attribution` (règle 2026-04-20 : affirmer un fait non documenté).

### Défaut 3 — Bloc GDPR anticipé hors sujet

*"Votre données personnelles et votre confidentialité — Vancelian se conforme au GDPR [...] droits sur vos données"*. Clarification Jean 2026-04-21 : *"GDPR => hors sujet"*. Le client dit *"je ne veux pas"* — il ne pose pas de question sur la confidentialité des données, il exprime un refus sur l'obligation. Le bot anticipe un angle "protection des données" pour rassurer, mais cette rassurance n'est pas demandée. Rattaché à la règle gravée `feedback_institutional_framing.md` #3 (pas d'anticipation des sous-questions non posées). Coquille au passage : *"votre données"* (→ *"vos données"*).

### Défaut 4 — Gap auto-détecté non adressé

Le gap signale que le bot ne précise pas **quand** l'information devient bloquante (*"mandatory for account activation, trading, or withdrawal, or if it can be deferred without service restrictions"*). Le bot dit *"ultérieurement"* sans échéance ni conséquence claire. Clarification Jean 2026-04-21 : *"il y a un délai pour communiquer l'information [...] non bloquant à date mais des restrictions seront appliquées après donc il vaut mieux le communiquer et mettre à jour cette donnée."* Le bot doit rendre la temporalité explicite sans donner de date précise (règle Jean : date susceptible d'évoluer, renvoyer au support pour l'échéance exacte).

### Défaut 5 — Longueur (6 paragraphes)

6 paragraphes pour *"je ne souhaite pas"*. La règle-mère du registre institutionnel sobre (2026-04-20) appelle ici une réponse en 3 paragraphes courts maximum : obligation + délai / conséquence + redirect. Rattaché à `feedback_institutional_framing.md` pattern transversal.

## Réponse cible

3 paragraphes (~80 mots) :

> La communication du numéro fiscal est obligatoire au titre de la directive européenne DAC8, qui s'applique à tous les clients Vancelian résidents de l'Union européenne.
>
> Un délai a été accordé pour la fournir. Avant échéance, votre accès n'est pas restreint ; après échéance, certaines fonctionnalités seront limitées tant que le numéro fiscal n'aura pas été renseigné. Il est préférable de mettre à jour cette donnée dès maintenant pour éviter toute interruption.
>
> Pour toute question sur votre échéance ou sur les modalités, contactez support@vancelian.com.

**Règle sur la date précise** : le bot ne donne **pas** la date (31/12/2026). Les dates peuvent évoluer ; si le client veut l'échéance exacte, il contacte support. Cette règle s'applique aussi au `short_answer` de la fiche wiki pour éviter que le bot la reprenne en PASS-1.

## Action taken

### A. Wiki — `faq/account/why-and-how-do-i-provide-my-tax-identification-number-in-the.md`

- **`short_answer` réécrit** : obligation DAC8 + délai accordé + conséquences post-échéance + redirect support. Pas de date précise.
- **Exception italienne retirée** de la section *"When will this information be requested?"* : même régime pour tous les clients EEA.
- **Deadline utilisateur ajoutée** de manière sobre (*"within a deadline granted to all Vancelian clients residing in the European Union"*) sans datation précise dans le texte client-facing.
- **Key dates DAC8 officielles conservées** (1 Jan 2026 start / 31 Jan 2027 first reporting) — ces dates viennent du régulateur, pas de la deadline opérationnelle Vancelian.
- **`questions:` enrichies** avec 4 phrasings naturels du refus/doute client : *"I do not wish to provide my tax identification number"*, *"can I refuse to give my tax ID?"*, *"what happens if I do not provide my tax number?"*, *"when is the deadline to provide my tax ID?"*.
- `last_reviewed: 2026-04-21`.

### B. bot.js — nouvel `<example>` canonique

Inséré entre l'example *"combien d'impôts"* et l'example *"fenêtre de sortie exception"*. Question : *"je ne souhaite pas communiquer mon numéro fiscal"*. Réponse en 3 paragraphes courts sans date précise, redirect support pour l'échéance personnelle.

### C. Archives

Les deux tickets (positif et auto_gap) fusionnés dans ce fichier unique de history.

### D. Pas de nouvelle règle memory

Les règles gravées couvrent déjà tous les défauts détectés :
- Anticipation GDPR → `feedback_institutional_framing.md` #3
- Dérogations inventées → `feedback_no_supervisory_overattribution.md`
- Longueur → `feedback_institutional_framing.md` pattern transversal
- Distinction hors sujet (Italie) → couvert par le principe de sobriété

Pas de nouvelle règle à graver.

## Pattern à surveiller

- Toute réponse bot qui introduit une **distinction par nationalité dans l'EEA** sur une mesure européenne commune (DAC8, MiCA) → candidat reclassification.
- Toute réponse qui utilise *"alternatives"* / *"dérogations possibles"* sur une obligation légale sans base documentée → candidat reclassification.
- Toute réponse qui ajoute un **bloc GDPR** sans que le client ait posé de question sur ses données → candidat reclassification.
- Toute réponse qui donne une **date précise** sur une deadline opérationnelle susceptible d'évoluer → reformuler sans date + redirect support.
