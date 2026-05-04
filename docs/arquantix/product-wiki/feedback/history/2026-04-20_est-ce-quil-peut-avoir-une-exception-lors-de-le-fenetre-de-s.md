---
status: treated
date: 2026-04-20
feedback_type: needs_improvement
source_question: "est ce qu'il peut avoir une exception lors de le fenetre de sortie pour etre en premier?"
user_comment: "reclassified by Jean — bot opened with 'I don't have information' when the mechanic in the wiki IS the answer (FIFO strict, no exception). Flight to support by excess prudence."
wiki_pages_used:
  - faq/exclusive-offers/how-do-project-exit-windows-work.md
  - faq/legal-compliance/vancelian-platform-terms-and-conditions.md
  - faq/company/how-to-contact-customer-support.md
channel_id: C0ASFKQFY2V
feedback_user: U02D2P6UY2X
treated_date: 2026-04-20
treated_action: bot_rule_added
---

# est ce qu'il peut avoir une exception lors de le fenetre de sortie pour etre en premier?

## Client question
> est ce qu'il peut avoir une exception lors de le fenetre de sortie pour etre en premier?

## Bot answer
> Je n'ai pas d'information dans la documentation disponible sur des mécanismes d'exception ou de priorité qui permettraient de dépasser l'ordre premier arrivé, premier servi lors d'une fenêtre de sortie.
>
> Le fonctionnement standard est : les demandes de sortie sont traitées dans l'ordre de soumission pendant la fenêtre de 2 semaines. Une fois la fenêtre fermée, votre demande devient définitive.
>
> Pour savoir s'il existe des situations exceptionnelles — circonstances particulières, demandes urgentes, ou autres mécanismes de priorité — contactez directement le support Vancelian à support@vancelian.com ou via la section support de l'application. L'équipe pourra examiner votre situation spécifique et vous conseiller.

## Feedback
**Type:** needs_improvement (reclassé par Jean)
**User comment originel:** "none"
**Correction Jean:** *"le bot a dit d'abord 'je n'ai pas la documentation' et rappelle le principe. Là il aurait dû donner le fonctionnement ET dire non il n'y a pas d'exception en aucun cas ET diriger aussi vers le support ensuite pour toute information complémentaire."*

## Diagnosis

Anti-pattern : **fuite vers le support par excès de prudence**.

Le bot avait l'information factuelle dans le wiki — la fenêtre de sortie fonctionne en FIFO strict pendant 2 semaines, et la page `how-do-project-exit-windows-work.md` ne documente aucun mécanisme d'exception. C'est une réponse directement dérivable de la mécanique documentée. Mais le bot a ouvert par *"Je n'ai pas d'information dans la documentation disponible"*, ce qui n'est factuellement pas vrai : la documentation dit que c'est FIFO, donc elle dit implicitement qu'il n'y a pas d'exception par construction.

Distinction critique à faire :
- **"Absence d'information ≠ absence de fait"** (règle déjà gravée) : quand le wiki ne dit rien, ne pas affirmer que ça n'existe pas.
- **"Mécanique documentée = réponse dérivable"** (règle à ajouter) : quand le wiki documente une mécanique exclusive (FIFO strict, ordre de soumission, pas de prioritisation), la réponse à "y a-t-il une exception" est dérivable directement : **non, par construction**. Ne pas ouvrir par "je n'ai pas d'info" dans ce cas — c'est une fuite par excès de prudence.

La structure attendue pour ce type de question :
1. **Fonctionnement factuel** (ce que dit le wiki sur la mécanique)
2. **Réponse directe dérivable** (non, pas d'exception en aucun cas — par construction FIFO)
3. **Redirect vers support pour info complémentaire** (pour toute situation spécifique)

Pattern voisin mais différent de celui flaggé plus tôt sur le ticket MiCA (sur-attribution AMF) : ici le bot s'auto-minimise au lieu de s'auto-majorer, mais la racine est la même — confusion entre ce que la source dit et ce qui est dérivable de ce que la source dit.

C'est le 5ème ticket du cascade 2026-04-19/04-20 et le 2ème pattern récurrent identifié en 24h (après la sur-attribution supervision AMF).

## Action taken

1. **Nouvelle règle `<factual_discipline>` dans bot.js** — distinction "absence d'info" vs "fait dérivable de la mécanique". Quand le wiki documente la mécanique exclusive (FIFO, ordre strict, pas de file prioritaire), répondre directement *"non, pas d'exception par construction"* au lieu d'ouvrir par *"je n'ai pas d'info"*.
2. **Nouveau `<example>` canonique** — la question exception fenêtre de sortie avec la structure correcte : fonctionnement → non direct → redirect.
3. **Forbidden pattern ajouté** — *"Je n'ai pas d'information"* interdit quand la mécanique documentée répond par construction.
4. **Auto-memory** — feedback mémorisé pour les futures sessions.
