# Transaction Engine Governance

> **Document de gouvernance** — complète les ADR 001–004.  
> **But** : préserver l’architecture pendant 12–24 mois de développement, quand l’équipe change, qu’une urgence produit pousse au raccourci, ou qu’un prestataire « optimise » sans connaître l’historique.

| Champ | Valeur |
| --- | --- |
| **Statut** | **Actif — règles non négociables** |
| **Date** | 2026-06-07 |
| **Constitution** | [ADR 004 — Ledger Authority](adr/004-ledger-authority.md) |
| **ADR liés** | [001](adr/001-intent-as-orchestrator.md) · [002](adr/002-postgresql-outbox-canonical-queue.md) · [003](adr/003-final-reconciliation-controller.md) |
| **Index** | [adr/README.md](adr/README.md) |
| **Contrat settlement** | [SETTLEMENT_LAYER_CONTRACT_v1.md](SETTLEMENT_LAYER_CONTRACT_v1.md) — *comment* écrire (exactly-once, atomicité, tables) |

---

## Pourquoi ce document existe

Les ADR décrivent **ce qu’on construit**. Ce document décrit **ce qu’on refuse**.

Sans gouvernance explicite, les moteurs transactionnels se dégradent progressivement :

1. Un webhook écrit une balance « pour débloquer le client ».
2. Un cron répare un PE « en attendant le controller ».
3. Une API termine une transaction en `COMPLETED` « parce que le provider a confirmé ».
4. Six mois plus tard, personne ne sait plus quelle source de vérité fait foi.

**Ce document est la barrière PR.** Toute violation = rejet, sauf processus d’override documenté (Règle 5).

---

## Pipeline source de vérité

```
Provider / Blockchain
        ↓
Intent → Outbox → Worker
        ↓
Settlement Layer          ← seul writer économique
        ↓
Ledger → PE → Controller → COMPLETED
```

Hiérarchie opérationnelle : **ADR 004 > ADR 001 > ADR 002 > ADR 003**.

---

## Les 5 règles non négociables

### Règle 1 — Settlement Authority

**Aucune écriture économique en dehors du Settlement Layer.**

| Interdit | Pourquoi |
| --- | --- |
| Webhook → `person_wallet_balances` | Contourne intent + idempotence settlement |
| API → `pe_position_atoms` | Double source de vérité PE |
| Cron → `fund_*` / `apply_swap_settlement` hors settlement | Réparation silencieuse |
| Worker → écriture ledger directe | Worker exécute ; Settlement écrit |

**Tables sensibles** (toute modification doit prouver le passage par Settlement Layer) :

- `person_wallet_balances`
- `person_wallet_deposits`
- `pe_position_atoms`
- scopes PE : `trading_available`, `vault_position`, `bundle_cash`, Lombard, etc.

**Verdict PR** : rejet automatique si écriture économique hors `services/settlement/` ou `settle_transaction_intent_idempotently`.

→ Détail : [ADR 004](adr/004-ledger-authority.md)

---

### Règle 2 — Intent First

**Toute opération économique doit posséder un intent.**

Pas de swap, vault, bundle, Lombard ou transfert **sans** `transaction_intents` (ou successeur canonique).

| Interdit | Exemple |
| --- | --- |
| Settlement orphelin | `apply_swap_settlement(swap_id)` sans `intent_id` |
| Webhook crédit sans intent | Dépôt Privy → balance directe |
| Script ECS one-shot | PE Lombard créé sans intent traçable |

**Verdict PR** : rejet si un chemin produit un mouvement économique sans intent créé **avant** l’exécution (règle 0 ADR 004).

→ Détail : [ADR 001](adr/001-intent-as-orchestrator.md)

---

### Règle 3 — No Silent Repair

**Une réconciliation ne modifie jamais la réalité.**

Elle :

- **détecte** l’écart (on-chain, provider, ledger, PE),
- **documente** (transition, alerte, blocage),
- **bloque** (intent reste non `COMPLETED`, dead-letter, escalade),

mais **ne corrige pas automatiquement** ledger, PE ou balances.

| Interdit | Pourquoi |
| --- | --- |
| « Auto-fix » balance dans le controller | Masque la cause racine |
| Cron qui recrédite après échec settlement | Deux écritures possibles |
| Réconciliation qui force `COMPLETED` | Gate constitutionnelle violée |

**Verdict PR** : rejet si code de réconciliation appelle settlement, `increment_balance`, ou transition vers `COMPLETED` sans validation explicite du gate.

→ Détail : [ADR 003](adr/003-final-reconciliation-controller.md)

---

### Règle 4 — Controller Owns COMPLETED

**Seul le Reconciliation Controller peut produire `COMPLETED`.**

Ni :

- API,
- Worker,
- Webhook,
- Provider callback,

ne peuvent terminer une transaction (état terminal `COMPLETED`).

| Rôle autorisé | Action |
| --- | --- |
| Worker | Exécute provider, enqueue settlement, transitions intermédiaires |
| Settlement | Écrit ledger / PE |
| Controller | Vérifie cohérence → **seul** à émettre `COMPLETED` |
| Webhook / API | Détecteur d’événement → intent / outbox, **pas** terminal |

**Verdict PR** : rejet si `status = COMPLETED` (ou équivalent) est assigné hors module controller / transition canonique ADR 003.

→ Détail : [ADR 003](adr/003-final-reconciliation-controller.md)

---

### Règle 5 — ADR Override Process

**Si quelqu’un veut contourner ADR 004 (ou toute règle ci-dessus) : Architecture Review obligatoire.**

Pas de shortcut de développement, pas de « temporaire » sans ticket, pas de flag prod qui réactive l’écriture directe.

**Processus minimal** :

1. Issue ou ADR amendement avec **motivation**, **durée**, **plan de retrait**.
2. Review architecture (au moins 1 reviewer hors auteur).
3. Si accepté : nouveau ADR ou section « Exception » datée avec échéance.
4. Si refusé : implémentation conforme au pipeline canonique.

**Verdict PR** : rejet si contournement sans trace dans ADR / issue architecture.

---

## Checklist reviewer (copier-coller en PR)

```markdown
## Transaction Engine Governance

- [ ] Règle 1 — Écritures économiques uniquement via Settlement Layer
- [ ] Règle 2 — Chaque mouvement économique a un `intent_id` traçable
- [ ] Règle 3 — Réconciliation détecte / documente / bloque — pas d’auto-repair
- [ ] Règle 4 — `COMPLETED` uniquement via Reconciliation Controller
- [ ] Règle 5 — Pas de contournement ADR sans Architecture Review
```

---

## Anti-patterns fréquents (rejeter)

| Phrase en review | Réponse |
| --- | --- |
| « On écrit direct dans le ledger pour aller plus vite » | Violation Règle 1 — rejet |
| « Le webhook a confirmé, on peut COMPLETED » | Violation Règle 4 — rejet |
| « On corrige la balance en cron le temps que… » | Violation Règle 3 — rejet |
| « Pas besoin d’intent pour ce petit transfert » | Violation Règle 2 — rejet |
| « Exception temporaire, on revert après » | Violation Règle 5 — Architecture Review d’abord |

---

## Ordre de mise en œuvre (roadmap)

Ce document **ne remplace pas** la roadmap technique ; il la protège.

| Phase | Focus | Gouvernance active |
| --- | --- | --- |
| S1 | Outbox foundation | Règles 1–2 préparées (pas de runtime branché) |
| S2 | Intent orchestrator LI.FI | Règle 2 stricte ; pas de settlement « pour tester » |
| S3 | Reconciliation Controller | Règles 3–4 |
| S4 | Product locks + `balance_snapshot_hash` | Règle 2 (concurrence) |
| S5 | Staging dual-run | Toutes règles en environnement réel |
| S6 | Webhook Privy | Règle 1 + 2 (intent existant d’abord) |

→ Ticket epic : [PHASE2 POC](../PHASE2_POC_LIFI_STANDALONE_SWAP.md) · Issue [#25](https://github.com/geniusga-vancelian/vancelian-app/issues/25)

---

## Relation avec les ADR

| Document | Rôle |
| --- | --- |
| **TRANSACTION_ENGINE_GOVERNANCE.md** (ce fichier) | **Loi opérationnelle** — interdits, rejets PR, override |
| **ADR 004** | **Constitution** — qui écrit quoi |
| **SETTLEMENT_LAYER_CONTRACT_v1** | **Contrat normatif** — comment écrire (interface, exactly-once, tables, états) |
| **ADR 001** | Orchestration intent |
| **ADR 002** | Transport outbox |
| **ADR 003** | Gate final |

En cas de conflit textuel : **ADR 004 prime** → **Settlement Contract** précise l’implémentation → ce document **opérationnalise** les rejets PR.

---

## Historique

| Date | Événement |
| --- | --- |
| 2026-06-07 | ADR 001–004 acceptés (S1 review) |
| 2026-06-07 | Publication gouvernance — avant Go S2 |
| 2026-06-07 | Référence Settlement Layer Contract v1 — avant Go S2b |
