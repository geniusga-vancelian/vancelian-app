# Controlled Production Pilot — LI.FI Intent Orchestrator (Phase 2)

| Champ | Valeur |
| --- | --- |
| **Statut** | **Actif — alternative au staging absent** |
| **Date** | 2026-06-07 |
| **Prérequis code** | S1–S3b ✅ mergés (#27–#35) · allowlist backend codée |
| **Epic** | [Issue #25](https://github.com/geniusga-vancelian/vancelian-app/issues/25) |
| **Contexte** | [STAGING_ACTIVATION_EXECUTION_REPORT.md](STAGING_ACTIVATION_EXECUTION_REPORT.md) — checklist staging **KO environnemental** (pas de staging Arquantix dédié) |
| **Références** | [PHASE2_POC_LIFI_STANDALONE_SWAP.md](PHASE2_POC_LIFI_STANDALONE_SWAP.md) · [SETTLEMENT_LAYER_CONTRACT_v1.md](SETTLEMENT_LAYER_CONTRACT_v1.md) |

---

## Position

| Décision | Statut |
| --- | --- |
| Staging Arquantix dédié | ❌ Absent — pas de staging fictif |
| Checklist staging | ✅ Acceptée KO environnemental (smoke tests verts, code S3b OK) |
| **Controlled Production Pilot** | ✅ Chemin réaliste retenu |
| S5 dual-run global | ❌ **Pas Go** |
| S3 Controller | ❌ **Verrouillé** |
| Flags globaux sans allowlist | ❌ **Interdit** |
| Élargissement au-delà du compte pilote | ❌ Sans **S4 Product Locks** + Go explicite |

---

## Principe

Les **3 flags** peuvent être `true` en production ECS, mais l’effet orchestrateur est **limité par allowlist** :

```
effet orchestrateur(person) =
  flags_globaux_ON
  ET LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS non vide
  ET email(person) ∈ allowlist
```

**Fail-closed** : flags ON + allowlist vide → **personne** n’est éligible (tous en legacy).

Tous les autres utilisateurs restent sur le flux **legacy Phase 7** (`lifi_intent_sync`, `apply_swap_settlement`).

---

## Préconditions obligatoires (avant tout flag ON prod)

| # | Prérequis | Statut |
| --- | --- | --- |
| P1 | Allowlist backend codée (`services/lifi/orchestrator_allowlist.py`) | ✅ |
| P2 | Tests allowlist verts (`test_lifi_orchestrator_allowlist.py`) | ✅ (CI) |
| P3 | Ce document validé | ⏳ |
| P4 | **Go Pilot Prod explicite** (ticket + opérateur + date) | ❌ **Non donné** |
| P5 | `person_id` + wallet Privy du compte pilote confirmés en prod | ⏳ |

### Compte pilote unique

| Champ | Valeur attendue |
| --- | --- |
| Email | `gaelitier@gmail.com` |
| `person_id` | À confirmer en prod (SQL § Identification) |
| Wallet Privy | Embedded Base — à confirmer |

### Variable d’environnement

```bash
LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS=gaelitier@gmail.com
```

Emails multiples : séparés par virgule (minuscules normalisées côté code).

Résolution email → person : `clients.email`, `person_external_identities.external_email`, `persons.profile_json.contact.collected_email`.

---

## Flags production (effet limité allowlist)

| Variable | Valeur pilot | Effet si allowlist OK |
| --- | --- | --- |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `true` | Confirm → intent orchestrateur + outbox `intent.created` (S2a.2 ; quote = draft seul) |
| `LIFI_OUTBOX_WORKER_ENABLED` | `true` | Worker `intent.created` / `intent.settle` |
| `LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED` | `true` | Settlement S3b : 1 débit + 1 crédit |

**Interdit** sans allowlist configurée : activer les 3 flags (fail-closed = legacy pour tous).

---

## Contraintes montants et périmètre

| Règle | Valeur |
| --- | --- |
| Montant max par swap | **1–5 USDC** |
| Chaîne | **Base only** |
| Produit | LI.FI **standalone** uniquement |
| Exclusions | bundle interne · vault · Lombard · webhooks orchestrés |

---

## Étapes pilot (séquentielles)

### Étape 0 — Baseline prod flags OFF

- [ ] Confirmer les 3 flags `false` + allowlist absente ou vide sur ECS prod
- [ ] SQL baseline (PE, cost basis, outbox, `lifi-swap:*` legs)
- [ ] Optionnel : 1 swap legacy très petit sur compte pilote (contrôle régression)
- [ ] **Go Étape 0**

### Étape 1 — Allowlist + orchestrateur (confirm crée l'intent — S2a.2)

```bash
LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS=gaelitier@gmail.com
LIFI_INTENT_ORCHESTRATOR_ENABLED=true
LIFI_OUTBOX_WORKER_ENABLED=false
LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=false
```

**Prérequis code** : PR **S2a.2** mergée (`intent at confirm`, pas au quote).

- [ ] Redémarrer API prod
- [ ] Quote seule → **0** intent / **0** outbox (swap draft uniquement)
- [ ] `POST /confirm-execute` (clic Confirm) → **1** intent + **1** outbox `intent.created`
- [ ] Autre user → **legacy** (pas d’outbox orchestrateur, pas de `phase2_orchestrator`)
- [ ] Aucune écriture ledger
- [ ] **Go Étape 1**

> Artefacts pilot pré-S2a.2 (quotes UI) : intents/outbox existants ignorés — pas de suppression sans Go séparé.

### Étape 2 — Worker + settlement NOOP

```bash
LIFI_OUTBOX_WORKER_ENABLED=true
# ledger reste false
```

- [ ] `intent.created` → `VALIDATED` → `QUEUED`
- [ ] `intent.settle` → `SETTLED_NOOP` (marker présent, pas de jambes `lifi-swap:*`)
- [ ] **Go Étape 2**

### Étape 3 — Ledger S3b (1 USDC)

```bash
LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED=true
```

- [ ] 1 swap **1 USDC** Base standalone confirmé
- [ ] Exactement **1 débit + 1 crédit**
- [ ] 2ᵉ `intent.settle` → `NOOP_ALREADY_SETTLED`
- [ ] Pas PE · pas cost basis · pas `COMPLETED`
- [ ] **Go Étape 3**

### Étape 4 — Montée progressive (si Étape 3 OK)

- [ ] Jusqu’à **10 swaps** pilotes de **1–5 USDC** chacun
- [ ] SQL checks par swap (checklist staging § Requêtes SQL)
- [ ] **Go Pilot complet**

---

## STOP immédiat (rollback flags OFF)

| Signal | Action |
| --- | --- |
| Un **autre user** passe par orchestrateur (outbox / `phase2_orchestrator`) | STOP · rollback · incident |
| Double débit / crédit | STOP |
| Jambe orpheline | STOP |
| PE ou cost basis écrit via orchestrateur | STOP |
| `COMPLETED` produit | STOP |
| Bundle interne touché par settlement S3b | STOP |
| `apply_swap_settlement` + settlement layer (double writer) | STOP |

---

## Rollback

1. Mettre les **3 flags** à `false`
2. Conserver ou vider `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS` (recommandé : vider)
3. Redémarrer API prod
4. 1 swap **legacy** sur compte pilote — doit fonctionner
5. Outbox `pending` : sans effet tant que worker OFF

---

## Identification compte pilote (prod, lecture seule)

```sql
-- person_id depuis email
SELECT c.person_id, c.email, c.id AS client_id
FROM clients c
WHERE lower(c.email) = 'gaelitier@gmail.com';

SELECT pei.person_id, pei.external_email, pei.provider
FROM person_external_identities pei
WHERE lower(pei.external_email) = 'gaelitier@gmail.com';

-- Wallet Privy embedded Base
SELECT id, address, chain_type, wallet_type, provider, status
FROM person_crypto_wallets
WHERE person_id = :person_id
  AND lower(provider) = 'privy'
  AND lower(wallet_type) != 'external';
```

---

## Smoke tests (avant Go Pilot Prod)

```bash
cd services/arquantix/api
PYTHONPATH=. pytest tests/test_lifi_orchestrator_allowlist.py -q
PYTHONPATH=. pytest tests/test_settlement_lifi_s3b.py tests/test_transaction_outbox_settlement_s3a.py \
  tests/test_settlement_contract_s2_5.py tests/test_transaction_outbox_worker_s2b.py \
  tests/test_lifi_orchestrator_quote_s2a.py -q
```

---

## Tableau swaps pilote

| # | Montant USDC | Quote | Intent | Outbox | CONFIRMED | Settle | 1D+1C | LEDGER_SETTLED | 2ᵉ NOOP | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 1 | | | | | | | | | |
| 2–10 | 1–5 | | | | | | | | | |

---

## Sign-off

| Rôle | Nom | Date | Étape |
| --- | --- | --- | --- |
| Dev / Cursor | | | Allowlist + tests + doc |
| Ops prod | | | Étapes 0–4 |
| CTO | | | Go Pilot Prod · pas Go S5 global |

---

## Prochaines actions (ordre verrouillé)

1. **Review** allowlist + doc + tests — **pas d’activation prod**
2. **Go Pilot Prod explicite** → exécuter Étapes 0–4
3. **S4 Product Locks** — requis avant tout élargissement allowlist
4. **S3 Controller** — verrouillé (pas Go S3)
5. **S5 dual-run global** — pas Go
