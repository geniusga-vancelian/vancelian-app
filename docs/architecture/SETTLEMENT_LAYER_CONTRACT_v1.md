# Settlement Layer Contract v1

> **Contrat normatif d’implémentation** — pas un ADR.  
> **But** : définir *comment* la Settlement Layer a le droit d’écrire la réalité économique, une fois qu’ADR 004 a établi *qui* a ce droit.

| Champ | Valeur |
| --- | --- |
| **Statut** | **Actif — v1 figé avant Go S2b** |
| **Date** | 2026-06-07 |
| **Version** | 1.0 |
| **Constitution** | [ADR 004 — Ledger Authority](adr/004-ledger-authority.md) |
| **Gouvernance** | [TRANSACTION_ENGINE_GOVERNANCE.md](TRANSACTION_ENGINE_GOVERNANCE.md) |
| **Nature** | Contrat d’implémentation — survit aux produits (spot, vault, bundle, Lombard, MiFID, tokenisé) |

---

## Relation avec les deux constitutions

| Document | Question | Rôle |
| --- | --- | --- |
| **ADR 004** | *Qui* peut modifier la réalité économique ? | Constitution — Settlement Layer uniquement |
| **Governance** | *Qu’est-ce qu’on refuse ?* | Barrière PR — rejets automatiques |
| **Ce contrat (v1)** | *Comment* la Settlement Layer écrit ? | Interface, garanties, tables, états, pré/post-conditions |

En cas de conflit : **ADR 004 prime** → ce contrat **opérationnalise** l’écriture économique → Governance **vérifie** les PR contre les deux.

---

## Principe fondateur — Pure Economic Projection

> **Settlement Layer = projection économique pure.**

La Settlement Layer **ne** :

- quote pas ;
- ne calcule pas un prix marché ;
- ne poll pas un provider ;
- ne décide pas (l’intent décide) ;
- ne réconcilie pas (le controller réconcilie) ;
- ne répare pas (pas d’auto-fix silencieux).

Elle prend un **intent déjà validé** par le pipeline (worker + règles produit) et **projette** la réalité économique dans les systèmes internes.

```
Provider Truth / Blockchain Truth
        ↓
Intent (décision + contexte)
        ↓
Settlement Layer (projection économique)
        ↓
Ledger · PE · Cost Basis · Trace Events
        ↓
Controller (validation — hors settlement)
```

**Ownership strict** :

| Rôle | Écrit | Valide |
| --- | --- | --- |
| Intent | Décide (orchestrateur) | — |
| Worker | Exécute provider / enqueue | — |
| **Settlement** | **Réalité économique** | **Jamais** |
| **Controller** | **Jamais** | **COMPLETED** |

---

## Interface universelle (v1)

Aucune référence produit ou provider dans la signature. LI.FI, Morpho, Lombard, MiFID, tokenisé : **même entrée**.

```python
def settle_transaction_intent_idempotently(
    db: Session,
    *,
    intent_id: UUID,
) -> SettlementResult:
    ...
```

### `SettlementResult` — états de sortie (fermés)

**Quatre états uniquement.** Pas de variante par produit.

| État | Signification | Action appelant (worker) |
| --- | --- | --- |
| `SUCCESS` | Projection économique complète et persistée | Continuer pipeline (ex. enqueue reconcile) |
| `RETRYABLE_FAILURE` | Échec transitoire (lock, DB, dépendance) | Retry outbox selon ADR 002 |
| `TERMINAL_FAILURE` | Intent non settleable (pré-condition, données invalides) | Transition intent → `failed` ; pas de retry settlement |
| `NOOP_ALREADY_SETTLED` | Settlement déjà appliqué pour cet `intent_id` — **aucune écriture DB autorisée** (lecture seule + retour) | Idempotent — continuer sans ré-écrire |

**Interdit** : inventer `PARTIAL_SUCCESS`, `SETTLED_WITH_WARNINGS`, `FORCE_SETTLED`, etc.

---

## Garantie 1 — Exactly-once économique

> Pour un `intent_id` donné : **0 settlement** ou **1 settlement**. **Jamais 2.**

Pas « best effort ». Pas « idempotent normalement ».

| Propriété | Exigence |
| --- | --- |
| Idempotence | Deux appels consécutifs → `NOOP_ALREADY_SETTLED` ou `SUCCESS` identique, **zéro double écriture** |
| Clé canonique | `intent.idempotency_key` + marqueur settlement interne (ex. `settlement_applied_at` / hash receipt) |
| Détection double | Vérification **avant** toute écriture ledger/PE |
| Violation | Bug critique — rollback + incident, pas de « compensating UPDATE » hors contrat |

---

## Garantie 2 — Unité atomique

> **Settlement réussi = Ledger + PE + Cost Basis + Trace Events — ou rien.**

Une transaction DB unique (ou équivalent serializable) englobe **toutes** les écritures autorisées du settlement.

| Composant | Obligation |
| --- | --- |
| **Ledger** | `person_wallet_balances`, `person_wallet_deposits` (mouvements custody) |
| **PE** | `pe_position_atoms` (scopes / positions portfolio engine) |
| **Cost Basis** | `cost_basis_executions` |
| **Trace** | `transaction_trace_events` (observabilité append-only liée à l’intent) |
| **Intent status** | `transaction_intents.status` (et champs settlement metadata) — **status only**, pas de réécriture métier |

**Interdit** :

```
ledger OK + PE KO → "on répare après"
```

Si une couche échoue → **ROLLBACK complet** → `RETRYABLE_FAILURE` ou `TERMINAL_FAILURE`.

---

## Garantie 3 — Liste blanche des écritures

Toute PR touchant une table économique **doit** montrer un appel à `settle_transaction_intent_idempotently` (ou module `services/settlement/` conforme à ce contrat).

### AUTHORIZED WRITES (Settlement Layer v1)

| Table | Scope |
| --- | --- |
| `person_wallet_deposits` | Crédits / mouvements custody |
| `person_wallet_balances` | Soldes disponibles / réservés |
| `pe_position_atoms` | Positions PE (incl. scopes `trading_available`, `vault_position`, `bundle_cash`, Lombard, etc.) |
| `bundle_ledger_entries` | Journal bundle append-only |
| `cost_basis_executions` | Exécutions cost basis |
| `transaction_trace_events` | Trace append-only |
| `transaction_intents` | **`status` + metadata settlement uniquement** (ex. `settlement_receipt_json`, pas de réécriture `assets_json` décisionnel) |

### FORBIDDEN WRITES (hors Settlement Layer)

Toute autre table — en particulier :

- écriture directe depuis API, webhook, cron, worker (hors handler settlement délégué) ;
- `transaction_outbox` (transport — ADR 002) ;
- tables provider / blockchain raw (détecteurs, pas writers économiques).

**Reviewer diff (30 secondes)** : si `UPDATE`/`INSERT` sur une table AUTHORIZED → chemin `services/settlement/` visible dans la PR.

Extension de la liste blanche → **amendement contrat v1.x** + Architecture Review (Governance Règle 5).

---

## 7. Pré-conditions / Post-conditions

### PRE-CONDITIONS (avant `settle_transaction_intent_idempotently`)

Le settlement **refuse** (`TERMINAL_FAILURE`) si l’une de ces conditions n’est pas remplie :

| # | Pré-condition |
| --- | --- |
| P1 | `intent` existe (`intent_id` valide) |
| P2 | `intent` dans un **état autorisé** pour settlement (défini par produit via metadata / `current_phase` — ex. provider truth capturée, pas `created` seul) |
| P3 | **Linked entity** existe (`linked_table` + `linked_id` résolvables) |
| P4 | `idempotency_key` présent et valide sur l’intent |
| P5 | Settlement **non déjà effectué** pour cet `intent_id` (sinon → `NOOP_ALREADY_SETTLED`) |
| P6 | Données de projection présentes dans l’intent / linked entity (montants, assets, preuves provider — **pas** de fetch provider dans settlement) |

> **Question répondue sans lire le code** : « À partir de quel état puis-je appeler settlement ? » → P2 + P6, documentés par produit dans metadata intent, **validés** par le worker avant enqueue `intent.settle`.

### POST-CONDITIONS (après `SUCCESS`)

| # | Post-condition |
| --- | --- |
| Q1 | Écritures économiques **persistées** (ledger + PE + cost basis) |
| Q2 | `transaction_trace_events` **persistés** (lien `intent_id`) |
| Q3 | `transaction_intents.status` mis à jour (ex. `confirmed` / état post-settlement produit — **pas** `COMPLETED`) |
| Q4 | **Checksum économique** calculé et stocké (ex. `settlement_receipt_hash` dans `metadata_json` ou colonne dédiée) — **déterministe** : deux projections identiques produisent le même hash (facilite audits et replays ; précision v1.1) |
| Q5 | **Aucune action compensatoire** requise — pas de file d’attente « repair PE » |

`COMPLETED` reste **exclusivement** au Reconciliation Controller (ADR 003, Governance Règle 4).

---

## Entrées / Sorties (résumé)

### Entrées

| Paramètre | Source |
| --- | --- |
| `intent_id` | Worker (event `intent.settle` — ADR 002) |
| Session DB | Appelant (une TX englobante) |
| Contexte implicite | Intent row + linked entity + metadata (vérité déjà capturée) |

**Pas d’entrée** : quote ID provider, webhook payload brut, prix marché live.

### Sorties (`SettlementResult`)

| Champ | Description |
| --- | --- |
| `outcome` | `SUCCESS` \| `RETRYABLE_FAILURE` \| `TERMINAL_FAILURE` \| `NOOP_ALREADY_SETTLED` |
| `intent_id` | Echo |
| `settlement_receipt_hash` | Présent si `SUCCESS` (checksum Q4) |
| `error_code` | Présent si échec (stable, loggable) |
| `error_message` | Détail humain / debug |

---

## Erreurs — retryables vs terminales

| Type | Exemples | `SettlementResult` |
| --- | --- | --- |
| **Retryable** | Lock DB timeout, serialization failure, dépendance temporairement indisponible | `RETRYABLE_FAILURE` |
| **Terminal** | Pré-condition P1–P6 violée, montant invalide, linked entity absente, violation atomicité | `TERMINAL_FAILURE` |
| **Déjà fait** | Settlement marker présent | `NOOP_ALREADY_SETTLED` |

Le settlement **ne retente pas** lui-même — le worker / outbox retente (ADR 002).

---

## Hors scope (appartient aux ADR existants)

Ce contrat **ne définit pas** :

| Sujet | Document |
| --- | --- |
| Machine à états intent | ADR 001 |
| Outbox, retry, dead-letter | ADR 002 |
| Gate `COMPLETED` | ADR 003 |
| Qui a le droit d’écrire | ADR 004 |
| Rejets PR | Governance |
| Product locks, concurrence | S4 / ADR 001 §5bis |
| Webhooks, providers | S6 / workers |
| Logique métier swap / vault / bundle | Modules produit → **alimentent l’intent**, pas le settlement |

**Une seule question** pour ce contrat :

> Lorsqu’un intent est prêt à être comptabilisé, quelles règles universelles gouvernent l’écriture de la réalité économique ?

---

## Migration legacy

Des chemins **legacy** (écritures directes hors `settle_transaction_intent_idempotently`) existent encore en production sous flags OFF.

| Règle | Exigence |
| --- | --- |
| Nouveau code | **Conforme contrat v1** — pas de nouveau writer parallèle |
| Legacy | Coexistence temporaire jusqu’à dual-run S5 ; retrait planifié |
| PR | Toute extension legacy = **rejet** (Governance Règle 1) |

---

## Checklist reviewer (settlement)

```markdown
## Settlement Layer Contract v1

- [ ] Écriture uniquement via `settle_transaction_intent_idempotently` ou `services/settlement/`
- [ ] Tables touchées ⊆ AUTHORIZED WRITES
- [ ] Exactly-once : garde idempotence avant écriture
- [ ] Atomicité : Ledger + PE + Cost Basis + Trace ou rollback
- [ ] Settlement ne valide pas (pas de COMPLETED)
- [ ] Pas de quote / poll / repair dans settlement
- [ ] États sortie ⊆ { SUCCESS, RETRYABLE_FAILURE, TERMINAL_FAILURE, NOOP_ALREADY_SETTLED }
```

---

## Séquence programme

```
Settlement Contract v1 (ce document)
        ↓
Review + Merge
        ↓
Go S2b (worker intent.created)
        ↓
…
        ↓
S3 (settlement branché — vrai test ADR 004)
```

**Pas de Go S2b** avant merge de ce contrat.

---

## Historique

| Date | Événement |
| --- | --- |
| 2026-06-07 | Rédaction v1 — après S2a/S2a.1, avant S2b |
| 2026-06-07 | S2a validé : orchestrateur sans writer économique (#29, #30) |
