# PR2 — Worker serveur autoritaire pour le swap simple (allowlist, flag OFF)

> Prérequis levé : **PR 0.2** a réparé la signature déléguée Privy (HTTP 401
> `zero_correct_authorization_signatures` → clé d'idempotence désormais signée). La signature
> serveur réussit (vérifié swap `c5f0f17e`). On peut donc rendre le worker autoritaire.

## Objectif

Faire du **worker d'exécution serveur** l'**unique** exécuteur d'un swap LI.FI simple
pour les personnes allowlistées :

```
user confirme swap → intent créée (intent.created) → worker QUEUED
  → enqueue intent.execute → worker exécute (execute_prepared_swap_server_side)
  → swap CONFIRMED → enqueue intent.settle → settlement (ledger) → release lock
```

Le navigateur ne signe/soumet plus rien : les routes d'exécution client sont refusées (409).

## Périmètre (strict)

- ✅ Swap simple LI.FI (`product_type=lifi_swap`, `operation_type=swap`).
- ❌ Pas de multi-leg, pas de DCA, pas de rebalancing (PR3/PR4).
- ❌ Pas de refactor du chemin d'exécution : on **réutilise** le câblage existant
  (`execution_worker.handle_intent_execute_event` → `execute_prepared_swap_server_side`,
  enqueue `intent.execute`, settlement worker). PR2 = **gating** uniquement.

## Changements

| Fichier | Changement |
|---|---|
| `services/lifi/config.py` | Nouveau flag `LIFI_AUTHORITATIVE_EXECUTION_ENABLED` (défaut **OFF**) + `lifi_authoritative_execution_enabled()` |
| `services/lifi/orchestrator_allowlist.py` | `lifi_authoritative_execution_enabled_for_person()` = flag autoritaire **ET** worker d'exécution actif pour la personne (garde-fou : pas de blocage si aucun exécuteur) |
| `services/lifi/routes.py` | `_ensure_not_server_authoritative()` → **409 `swap.server_authoritative`** sur `/execute`, `/{id}/submit`, `/{id}/server-execute`, `/{id}/approval` |
| `tests/test_lifi_authoritative_execution_pr2.py` | Helper + gating des 4 routes |

**Inchangé** : `confirm-execute` (garde le lock global → doctrine **409** sur concurrent),
quote, refresh, settlement, lock, primitive serveur. Le worker appelle la primitive
**directement** (hors HTTP) → non affecté par le gating.

## Doctrine concurrence (PR2)

Deuxième swap quasi-simultané → **409 `TransactionInProgress`** au `confirm-execute` (lock global
acquis par le premier, libéré sur terminal). L'« enqueue-and-wait » (B reste QUEUED puis démarre
après A) est explicitement reporté à **PR3**.

## Flags & ordre d'activation prod (allowlist)

L'éligibilité autoritaire **exige** que l'exécuteur serveur tourne. Activer dans cet ordre :

1. Tick worker actif (cron/ECS) exécutant `process_transaction_outbox_intent_created` /
   `_intent_execute` / `_intent_settle`.
2. `LIFI_INTENT_ORCHESTRATOR_ENABLED=true`
3. `LIFI_OUTBOX_WORKER_ENABLED=true`
4. `LIFI_EXECUTION_WORKER_ENABLED=true`
5. `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS=gaelitier@gmail.com`
6. **En dernier** : `LIFI_AUTHORITATIVE_EXECUTION_ENABLED=true`

> Garde-fou code : si (4) est OFF pour la personne, le helper retourne `False` → le client
> n'est **jamais** bloqué (pas de swap orphelin sans exécuteur).

## Critères de réussite

| # | Attendu |
|---|---|
| 1 | 1 swap isolé → `CONFIRMED` + intent `EXECUTED` + settlement (`LEDGER_SETTLED`/`SETTLED_NOOP`) |
| 2 | 2 swaps rapides → 1 actif, le 2e **409** au confirm (doctrine PR2) |
| 3 | Aucune double signature (routes client refusées 409 `swap.server_authoritative`) |
| 4 | Aucun fallback client (pas de `client-trace`/`submit` côté serveur) |
| 5 | Ledger OK |
| 6 | Lock libéré on terminal (`on_swap_confirmed`/`on_swap_failed`) |

## Vérification manuelle (SQL, read-only)

```sql
-- Timeline intent + swap pour un swap de test
SELECT i.id AS intent_id, i.status AS intent_status, i.current_phase,
       s.id AS swap_id, s.status AS swap_status, s.tx_hash,
       i.created_at, i.updated_at
FROM transaction_intents i
JOIN person_wallet_swaps s ON s.id = i.linked_id
WHERE i.linked_table = 'person_wallet_swaps'
  AND s.id = :swap_id;

-- Transitions (doit contenir VALIDATED, QUEUED, EXECUTED, settle)
SELECT phase, actor, created_at
FROM transaction_intent_transitions
WHERE intent_id = :intent_id
ORDER BY created_at;

-- Lock global libéré on terminal
SELECT scope, status, intent_id, acquired_at, released_at
FROM transaction_product_locks
WHERE intent_id = :intent_id;
```

## Vérification CloudWatch (`/ecs/arquantix-api`)

```
# Tentative d'exécution client refusée (preuve : worker autoritaire)
fields @timestamp, @message
| filter @message like /server_authoritative/ or @message like /server-execute/ or @message like /\/submit/
| sort @timestamp desc | limit 50

# Worker execute le swap (pas le client)
fields @timestamp, @message
| filter @message like /outbox_intent_execute/ or @message like /intent.execute/
| sort @timestamp desc | limit 50
```

Attendu après activation : `POST /server-execute` et `/submit` initiés par le client → **409**
(`swap.server_authoritative`) ; l'exécution réelle vient du worker `intent.execute`.

## Rollback

`LIFI_AUTHORITATIVE_EXECUTION_ENABLED=false` (env, sans redeploy code) → retour immédiat au
chemin client legacy. Aucun changement de schéma, aucune migration.

## Limite connue (acceptée pour le pilote)

Si la signature serveur retombe en fallback (`signed_server_side=False`) alors que le client est
bloqué, le swap reste `AWAITING_SIGNATURE` jusqu'au TTL du lock (3600 s). Non rencontré depuis
PR 0.2 (signature serveur fiable). À durcir en PR3 (re-enqueue/retry sur fallback).
