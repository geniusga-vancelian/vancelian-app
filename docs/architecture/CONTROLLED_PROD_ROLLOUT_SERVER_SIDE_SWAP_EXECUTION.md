# Controlled Rollout — Server-Side Swap Execution Worker (Privy Delegated)

| Champ | Valeur |
| --- | --- |
| **Statut** | ⏳ Prêt à piloter — flags OFF par défaut |
| **Date** | 2026-06-12 |
| **Objectif** | Le worker défile un intent `lifi_swap` et **signe + soumet le swap côté serveur** (Privy Session Signers), sans navigateur |
| **Prérequis code** | Délégation Privy (`delegated_signer.py`), fonction d'exécution unifiée (`server_execution.py`), worker `intent.execute` (`execution_worker.py`) — ✅ mergés |
| **Références** | [CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md](CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md) · [PHASE2_POC_LIFI_STANDALONE_SWAP.md](PHASE2_POC_LIFI_STANDALONE_SWAP.md) |

---

## Principe

Un swap déjà **quoté** (`QUOTE_RECEIVED` / `AWAITING_SIGNATURE`) lié à un intent orchestrateur
est exécuté **sans interaction client** :

```
intent.created → VALIDATED → QUEUED
  └─ swap CONFIRMED (signé client) ........ → enqueue intent.settle   (legacy/historique)
  └─ swap quoté non signé ................. → enqueue intent.execute  (NOUVEAU)
       └─ worker intent.execute
            prepare_execute → (approval ERC-20) → signature serveur (Privy délégué)
            → submit_signed_trade → poll + settlement
```

**Self-custody préservée** : l'utilisateur a délégué une fois la signature au quorum applicatif
via *Privy Session Signers*. Aucune clé privée n'est détenue par Vancelian.

### Garde-fou fail-safe (zéro régression)

Si la signature serveur est impossible, l'exécution **retombe sur `awaiting_signature`** et
l'événement est marqué **traité** (pas d'échec dur) — le flux client historique reste intact :

| `fallback_reason` | Cause |
| --- | --- |
| `delegated_signing_not_configured` | `PRIVY_AUTHORIZATION_KEY` / quorum absent |
| `wallet_not_delegated` | L'utilisateur n'a pas activé l'exécution automatique |
| `non_privy_signing_mode` | Wallet externe (pas embedded Privy) |
| `signing_wallet_unresolved` / `privy_wallet_id_unresolved` | Wallet introuvable |
| `transaction_unavailable` | `prepare_execute` n'a pas de payload signable |
| `sign_failed:<code>` | Erreur RPC Privy |

---

## Effet limité par allowlist (fail-closed)

```
exécution serveur(person) =
  LIFI_EXECUTION_WORKER_ENABLED = true
  ET LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS non vide
  ET email(person) ∈ allowlist
  ET wallet embedded délégué (flag Privy `delegated`)
```

Flag ON + allowlist vide → **personne** n'est exécuté côté serveur (tous restent client/legacy).

---

## Préconditions obligatoires (avant tout flag ON prod)

| # | Prérequis | Statut |
| --- | --- | --- |
| P1 | Secret `PRIVY_AUTHORIZATION_KEY` présent (AWS Secrets Manager `arquantix/prod/privy-*`) | ⏳ |
| P2 | `NEXT_PUBLIC_PRIVY_AUTHORIZATION_QUORUM_ID` injecté au build web (GitHub Actions) | ✅ codé |
| P3 | Bouton « Trading automatique » présent sur la page profil (`PortalProfileDelegationSection`) | ✅ codé |
| P4 | Orchestrateur LI.FI déjà piloté OK (Étapes 0–4 du runbook orchestrateur) | ⏳ |
| P5 | Compte pilote a **activé l'exécution automatique** (délégation Privy) | ❌ |
| P6 | **Go Rollout explicite** (ticket + opérateur + date) | ❌ **Non donné** |

---

## Flags production

| Variable | Valeur pilot | Effet |
| --- | --- | --- |
| `LIFI_INTENT_ORCHESTRATOR_ENABLED` | `true` | Intent à confirm + outbox `intent.created` |
| `LIFI_OUTBOX_WORKER_ENABLED` | `true` | Worker `intent.created` / `intent.settle` |
| `LIFI_EXECUTION_WORKER_ENABLED` | `true` | **Worker `intent.execute` (signature serveur)** |
| `LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS` | `gaelitier@gmail.com` | Allowlist partagée |
| `PRIVY_AUTHORIZATION_KEY` | `wallet-auth:<base64>` | Clé P-256 du quorum (secret) |

> `LIFI_EXECUTION_WORKER_ENABLED` est **OFF par défaut**. Tant qu'il est OFF, les événements
> `intent.execute` restent `pending` sans effet et le client peut toujours signer normalement.

---

## Contraintes périmètre (identiques au pilote orchestrateur)

| Règle | Valeur |
| --- | --- |
| Montant max par swap | **1–5 USDC** |
| Chaîne | **Base only** |
| Produit | LI.FI **standalone** (et legs bundle via la même fonction) |
| Compte | Allowlist uniquement |

---

## Étapes de rollout (séquentielles)

### Étape 0 — Baseline (worker OFF)

- [ ] `LIFI_EXECUTION_WORKER_ENABLED=false` confirmé sur ECS prod
- [ ] Orchestrateur déjà actif et vert (runbook orchestrateur Étapes 0–4)
- [ ] **Go Étape 0**

### Étape 1 — Délégation côté compte pilote

- [ ] Le compte pilote active « Trading automatique » sur la page profil
- [ ] Vérifier le flag Privy `delegated=true` sur le wallet embedded (API Privy / SQL ci-dessous)
- [ ] **Go Étape 1**

### Étape 2 — Mock / dry-run (aucune signature réelle)

- [ ] Tick DeFi en `dry_run` → étape `transaction_outbox_intent_execute` = `skipped`
- [ ] Tests verts (voir § Smoke tests)
- [ ] **Go Étape 2**

### Étape 3 — Activation worker (1 swap 1 USDC)

```bash
LIFI_EXECUTION_WORKER_ENABLED=true
```

- [ ] Redémarrer API/worker prod
- [ ] 1 swap **1 USDC** Base sur le compte pilote, **sans signer dans le navigateur**
- [ ] `intent.execute` → `processed`, transition `EXECUTED`, `signed_server_side=1`
- [ ] Swap → `CONFIRMED` puis settlement (1 débit + 1 crédit)
- [ ] Autre user → **aucun** `intent.execute` exécuté (allowlist)
- [ ] **Go Étape 3**

### Étape 4 — Montée progressive

- [ ] Jusqu'à **10 swaps** pilotes 1–5 USDC, exécutés serveur
- [ ] Contrôler 0 double-signature, 0 jambe orpheline
- [ ] **Go Rollout complet**

---

## STOP immédiat (rollback)

| Signal | Action |
| --- | --- |
| Un **autre user** est exécuté côté serveur (hors allowlist) | STOP · rollback · incident |
| Double signature / double submit d'un même swap | STOP |
| Signature serveur sur un wallet **non délégué** | STOP |
| Settlement double (débit/crédit en double) | STOP |
| `intent.execute` boucle en `failed` (DEAD_LETTER) | STOP · investiguer |

---

## Rollback

1. `LIFI_EXECUTION_WORKER_ENABLED=false`
2. Redémarrer API/worker prod
3. Les `intent.execute` `pending` restent sans effet
4. 1 swap **client** sur le compte pilote — doit fonctionner (signature navigateur)
5. (Optionnel) Le compte pilote peut **révoquer** la délégation depuis le profil

---

## Identification & vérification (prod, lecture seule)

```sql
-- privy_wallet_id du wallet embedded (requis pour la signature serveur)
SELECT id, address, provider, metadata_json->>'privy_wallet_id' AS privy_wallet_id
FROM person_crypto_wallets
WHERE person_id = :person_id
  AND lower(provider) = 'privy';

-- événements d'exécution serveur
SELECT o.id, o.status, o.payload_json->>'swap_id' AS swap_id, o.created_at
FROM transaction_outbox o
WHERE o.event_type = 'intent.execute'
ORDER BY o.created_at DESC
LIMIT 20;

-- transitions d'exécution
SELECT intent_id, phase, actor, created_at
FROM transaction_intent_transitions
WHERE phase IN ('EXECUTED', 'EXECUTE_DEFERRED')
ORDER BY created_at DESC
LIMIT 20;
```

> Le flag Privy `delegated` se vérifie via l'API Privy (`fetch_privy_user` → `linked_accounts[].delegated`),
> pas en base : la délégation est gérée nativement par Privy (pas de table dédiée).

---

## Smoke tests (avant Go Rollout)

```bash
cd services/arquantix/api
PYTHONPATH=. pytest \
  tests/test_privy_delegated_signer.py \
  tests/test_privy_wallet_delegation_status.py \
  tests/test_server_execution_swap.py \
  tests/test_orchestrator_intent_execute_worker.py \
  tests/test_e2e_intent_execute_chain.py \
  -q
```

---

## Sign-off

| Rôle | Nom | Date | Étape |
| --- | --- | --- | --- |
| Dev / Cursor | | | Délégation + worker + tests + doc |
| Ops prod | | | Étapes 0–4 |
| CTO | | | Go Rollout · périmètre allowlist |
