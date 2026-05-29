# Bundle Recovery Runbook (ops)

Guide opérationnel **read-only first** pour diagnostiquer et débloquer un bundle crypto (invest / withdraw / allocation).

> **Règle d'or** : un swap Li.FI interne bundle n'est jamais un trade self-trading. Seuls les transferts PE `bundle ↔ Mon Trading` apparaissent côté self-trading.

---

## 1. Symptômes courants

| Symptôme utilisateur | Cause probable |
|---------------------|----------------|
| « Investissement bloqué / allocating » | Lock invest actif + legs Li.FI pending |
| « Retrait en cours indéfiniment » | Lock withdraw + sells non finalisés |
| USDC visibles dans le bundle mais non alloués | Fund OK, allocation partielle ou failed — **cash leg intacte** |
| Mon Trading montre un transfert bundle mais pas les swaps | **Comportement attendu** |
| Mon Trading montre un « Échange USDC → CBBTC » après invest bundle | **Anomalie** — fuite à investiguer |

---

## 2. Inspection read-only (première étape)

Depuis `services/arquantix/api` :

```bash
python3 -m scripts.inspect_bundle_state \
  --person-id <PERSON_UUID> \
  --portfolio-id <BUNDLE_PORTFOLIO_UUID> \
  [--batch-id <BATCH_UUID>]
```

**Sortie JSON** :
- `cash_leg.available_usdc` — fonds récupérables dans le bundle
- `spot_legs` — allocations confirmées
- `invest_lock` / `withdraw_lock` — blocking vs recoverable
- `lifi_swaps` — swaps Li.FI liés (`is_live: true` = ne pas expirer le lock)
- `transaction_intents` — parents bundle_invest / bundle_withdraw
- `recommendations` — actions suggérées (sans exécution auto)

**Aucune mutation DB.** Pas de release automatique.

---

## 3. Vérifier la cash leg USDC

La cash leg = atoms PE `position_type=cash` sur le `bundle_portfolio`.

```sql
-- Read-only
SELECT pa.quantity, pa.cost_basis, a.symbol
FROM pe_position_atoms pa
JOIN pe_instruments i ON i.id = pa.instrument_id
JOIN pe_assets a ON a.id = i.asset_id
WHERE pa.portfolio_id = '<BUNDLE_PORTFOLIO_UUID>'
  AND pa.position_type = 'cash'
  AND pa.status = 'open';
```

Si `quantity > 0` après échec d'allocation : **fonds récupérables** — rebalance ou nouvel invest possible une fois le lock libéré.

---

## 4. Diagnostiquer les locks

### Invest lock (`metadata.bundle_invest_lock`)

| Statut | Bloquant ? | Action |
|--------|------------|--------|
| `pending_signature`, `partial_pending`, `submitted` | Oui (si swap vivant) | Resume / signer legs |
| `failed`, `expired` (terminal) | Non | Cash leg intacte — rebalance |
| Absent | Non | Normal |

**TTL** : `BUNDLE_INVEST_LOCK_TTL_MINUTES` (défaut 120). Expire automatiquement si aucun swap SUBMITTED/AWAITING_SIGNATURE vivant.

API :
```bash
curl -H "Authorization: Bearer …" \
  "http://localhost:8000/api/app/bundle/invest/active-lock?portfolio_id=<UUID>"
```

Si `reconciled: true` et `status: none` → lock stale nettoyé.

### Withdraw lock (`metadata.bundle_withdraw_lock`)

| Statut / phase | Bloquant ? | Action |
|----------------|------------|--------|
| `unwinding`, `pending_signature` | Oui | Attendre sells / signer |
| `ready_to_release`, `partially_unwound`, `failed_partial` | **Non** (récupérable) | Finalize withdraw |
| `released`, `expired` | Non | Terminé |

**Ne jamais** créditer self-trading manuellement si `failed_partial` et sells non confirmés.

---

## 5. Identifier un swap Li.FI vivant

```sql
SELECT id, status, from_asset, to_asset, tx_hash, audit_log
FROM person_wallet_swaps
WHERE person_id = '<PERSON_UUID>'
  AND status IN ('AWAITING_SIGNATURE', 'SUBMITTED', 'QUOTE_RECEIVED', 'PENDING')
ORDER BY created_at DESC
LIMIT 20;
```

Filtrer côté ops : `audit_log` contient `event: bundle_leg_context` + `bundle_execution: true` + `batch_id`.

Statuts terminaux : `CONFIRMED`, `FAILED`, `EXPIRED` → ne bloquent pas l'expiration TTL du lock (sauf SUBMITTED en vol).

---

## 6. Relancer finalize / resume (client ou API)

| Action | Endpoint | Quand |
|--------|----------|-------|
| Reprendre invest | `POST /api/app/bundle/invest/resume` | Lock actif + legs pending |
| Finaliser invest batch | `POST /api/app/bundle/batch/finalize` | Legs confirmés, clear lock |
| Finaliser retrait | `POST /api/app/bundle/withdraw/finalize` | Sells terminés, cash leg suffisant |
| Rebalance (cash → actifs) | `POST /api/app/bundle/{id}/rebalance` | Cash leg > 0, pas de lock invest bloquant |

Portal BFF : `/api/portal/bundles/*` (proxies identiques).

---

## 7. Vérifier que Mon Trading n'affiche pas les swaps bundle

### Test automatisé (CI / local)

```bash
cd services/arquantix/api
python3 -m pytest tests/test_bundle_self_trading_isolation.py -q
python3 -m pytest tests/test_bundle_transaction_scope.py -q
```

### Vérification manuelle API

```bash
curl -H "Authorization: Bearer …" \
  "http://localhost:8000/api/app/crypto-positions/USDC/transactions"
```

**Attendu** :
- Présence possible de `transaction_kind: bundle_pe_transfer` (transfert vers/depuis bundle)
- **Absence** de swaps `source_system: lifi_swap` dont le titre correspond à une allocation bundle (ex. USDC → CBBTC interne)

### Historique bundle (doit montrer les swaps internes)

```bash
curl -H "Authorization: Bearer …" \
  "http://localhost:8000/api/app/bundle/<PORTFOLIO_UUID>/transactions"
```

**Attendu** : `transaction_kind: bundle_internal_swap`, `source_system: bundle_lifi`, plus transferts PE.

---

## 8. Matrice décision rapide

```
inspect_bundle_state
    │
    ├─ cash_leg > 0 ET invest_lock.blocking = false
    │       → Rebalance ou nouvel invest
    │
    ├─ invest_lock.blocking = true ET live_lifi_swap
    │       → Resume + signature client
    │
    ├─ invest_lock.blocking = true ET age > TTL ET pas de swap live
    │       → GET active-lock (reconcile/expire) puis rebalance
    │
    ├─ withdraw_lock.recoverable = true
    │       → POST withdraw/finalize
    │
    └─ withdraw_lock.blocking + live sell
            → Attendre confirmation on-chain
```

---

## 9. Commandes tests / santé

```bash
# Suite anti-fuite + locks
python3 -m pytest tests/test_bundle_self_trading_isolation.py -q

# Intents bundle
python3 -m pytest tests/test_phase7d_bundle_transaction_intents.py -q

# Withdraw fund-first
python3 -m pytest tests/test_bundle_withdraw.py -q

# Intents stale (read-only par défaut)
python3 -m scripts.transaction_intent_health --dry-run --person-id <UUID>
```

---

## 10. Escalade / interdit sans validation

- **Interdit** : modifier `pe_portfolios.metadata` locks à la main en prod sans audit
- **Interdit** : `release` comptable manuel SQL (fund/release PE) sans ticket
- **Interdit** : supprimer des swaps Li.FI ou intents en prod
- **Demander validation** avant tout script de mutation (`complete_bundle_lifi_legs_mock`, etc.)

---

## Références

- Audit initial : [BUNDLE_DEPOSIT_WITHDRAW_AUDIT.md](./BUNDLE_DEPOSIT_WITHDRAW_AUDIT.md)
- Validation post-fix : [BUNDLE_POST_FIX_VALIDATION.md](./BUNDLE_POST_FIX_VALIDATION.md)
- Script inspection : `services/arquantix/api/scripts/inspect_bundle_state.py`
