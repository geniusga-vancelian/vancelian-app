# PR3 — Enqueue-and-wait réel (file user V1, swap simple, allowlist)

> Construit sur **PR2** (worker autoritaire). Prérequis Privy levé par **PR0.2** (signature
> serveur fiable). Périmètre strict, flag OFF par défaut, rollback immédiat.

## Changement de doctrine

| | PR2 (déployé) | PR3 (cette PR) |
|---|---|---|
| 2e swap concurrent | **409** au `confirm-execute` (fail-fast) | **mis en file** : reste PENDING, démarre après terminalité du 1er |
| Acquisition du slot user | au **confirm** (API) | au **worker** (au moment d'exécuter) |
| Sérialisation | rejet | attente réelle (1 transaction active / user) |

## Comment ça marche

```
confirm (enqueue-and-wait) : crée intent.created, PAS de lock fail-fast → 200
worker tick :
  intent.created → QUEUED → enqueue intent.execute
  intent.execute :
    acquire global user lock (intent_id)
      - acquis (ou idempotent même intent) → exécute le swap serveur
      - ProductLockConflict (autre intent actif) → DIFFÉRÉ : event remis PENDING
        (sans incrémenter attempt_count) → retry au prochain tick
  swap terminal (CONFIRMED/FAILED/EXPIRED) → on_swap_confirmed/on_swap_failed → release lock
  → au tick suivant, le 2e intent acquiert le slot et s'exécute
```

Ordre **FIFO** garanti : `poll_pending_events` trie par `created_at ASC`.

## Périmètre (strict)

- ✅ Swap simple LI.FI, allowlist, file **1 user**.
- ✅ Worker attend le **terminal complet** avant le suivant (le lock n'est libéré qu'au terminal).
- ❌ Pas de rebalancing, pas de DCA, pas de multi-leg (PR4+).
- ❌ Ledger interne OFF au début (`LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=false` → `SETTLED_NOOP`).
- ❌ Pas d'ouverture à tous les users.

## Changements

| Fichier | Changement |
|---|---|
| `services/lifi/config.py` | Flag `LIFI_ENQUEUE_AND_WAIT_ENABLED` (défaut **OFF**) |
| `services/lifi/orchestrator_allowlist.py` | `lifi_enqueue_and_wait_enabled_for_person` = flag enqueue **ET** mode autoritaire (PR2) |
| `services/swap_core/confirm_poll.py` | En mode enqueue-and-wait : **pas** de `acquire_lifi_swap_global_lock_or_raise` au confirm |
| `services/transaction_outbox/execution_worker.py` | Le worker acquiert le slot global par intent ; **diffère** (PENDING) sur conflit |
| `tests/test_lifi_enqueue_and_wait_pr3.py` | helper + worker defer + worker run + confirm sans 409 |

## Flags & ordre d'activation prod (allowlist)

Tout est déjà ON en prod (orchestrator, outbox, execution worker, autoritaire, global lock,
allowlist=`gaelitier@gmail.com`). Il ne reste qu'à activer :

```
LIFI_ENQUEUE_AND_WAIT_ENABLED=true
```

> Garde-fous code : enqueue-and-wait exige le **mode autoritaire** (sinon le client pourrait
> exécuter en parallèle) **et** `GLOBAL_USER_TRANSACTION_LOCK_ENABLED=true` (sinon `acquire`
> est no-op → pas de sérialisation). Les deux sont ON en prod.

Rollback : `LIFI_ENQUEUE_AND_WAIT_ENABLED=false` (env, sans redeploy) → retour doctrine 409 (PR2).

## Grand test de validation (à dérouler une fois activé)

| # | Scénario | Attendu |
|---|---|---|
| 1 | 1 swap isolé | `CONFIRMED` via worker, intent `EXECUTED`, settlement, lock libéré |
| 2 | 2 swaps rapides | 1 actif ; le 2e **en file** (PENDING, `deferred`) puis démarre **après** terminalité du 1er ; pas de 409 |
| 3 | swap + autre intent financier | sérialisés via le slot global (jamais concurrents) |
| 4 | échec contrôlé | swap → `FAILED`, intent réconcilié, **lock libéré** (le suivant peut démarrer) |
| 5 | lock release | `transaction_product_locks` → `released` on terminal |
| 6 | pas de double signature / pas de fallback client | routes client → 409 `swap.server_authoritative` ; seul le worker exécute |

### Vérification

```sql
-- File user : intents en attente vs actif
SELECT i.id, i.current_phase, s.status AS swap_status, i.created_at
FROM transaction_intents i JOIN person_wallet_swaps s ON s.id = i.linked_id
WHERE i.person_id = :person_id ORDER BY i.created_at;

-- Slot global (1 actif max)
SELECT intent_id, status, acquired_at, released_at
FROM transaction_product_locks
WHERE person_id = :person_id AND scope = 'financial_transaction'
ORDER BY acquired_at DESC;
```

```
# CloudWatch — défer (2e en file) + exécution worker
fields @timestamp, @message
| filter @message like /transaction_outbox_intent_execute/
| sort @timestamp desc | limit 50
```

`deferred >= 1` pendant que le 1er swap est actif ; `processed` augmente quand le slot se libère.

## Limites connues (acceptées pour le pilote V1)

- Latence file = cadence du tick (~10 min) → un swap en file peut attendre 1-2 cycles.
- Si l'exécution serveur retombe en fallback sans terminal, le slot reste tenu jusqu'au TTL
  (3600 s) — non rencontré depuis PR0.2. À durcir en PR4 (re-enqueue/expiry actif).
- Mixte swap/bundle : bundle garde le fail-fast à son confirm ; swap attend. Jamais concurrents,
  mais doctrines distinctes tant que les bundles ne sont pas migrés en enqueue-and-wait.
