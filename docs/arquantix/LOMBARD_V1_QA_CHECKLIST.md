# Lombard V1 — QA checklist (controlled live beta)

Checklist manuelle avant le **premier emprunt réel** (montant test : **50–100 USDC max**).

Références : [`LOMBARD_V1_RUNBOOK.md`](./LOMBARD_V1_RUNBOOK.md)

---

## 0. Prérequis environnement

### Flags à activer

```bash
LOMBARD_V1_ENABLED=true
LOMBARD_V1_BETA_ENABLED=true
LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET=25000
LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL=250000
LOMBARD_V1_BETA_ALLOWED_WALLETS=0xVOTRE_WALLET
```

Optionnel :

```bash
LOMBARD_V1_RECONCILIATION_TOLERANCE_BPS=200
LOMBARD_V1_DEBUG_PANEL_FOR_ADMINS=true   # défaut : panel QA pour admins en prod
```

### Smoke automatisé

```bash
cd services/arquantix/web
pnpm lombard:smoke

# Avec endpoints HTTP authentifiés :
LOMBARD_SMOKE_BASE_URL=http://localhost:3000 \
LOMBARD_SMOKE_PORTAL_COOKIE="portal_access_token=..." \
LOMBARD_SMOKE_WALLET_ADDRESS=0x... \
LOMBARD_SMOKE_ADMIN_COOKIE="session=..." \
pnpm lombard:smoke
```

Attendu : tous les checks `OK` (HTTP optionnels skippés si cookies absents).

### QA locale sans Morpho (mock)

```bash
# web/.env.local
LOMBARD_V1_MOCK_ENABLED=true
LOMBARD_V1_MOCK_POSITION_ENABLED=true
LOMBARD_V1_BETA_ENABLED=false   # optionnel — pas d'allowlist en mock local

pnpm lombard:mock
pnpm dev
```

Parcours : `/app/borrow?collateral=cbBTC` → quote 75 USDC → confirm (sans signature réelle) → carte active loan si `MOCK_POSITION_ENABLED=true`.

### Validation env production (pre-deploy)

```bash
LOMBARD_V1_ENABLED=true \
LOMBARD_V1_BETA_ENABLED=true \
LOMBARD_V1_BETA_LIMITS_ENABLED=true \
LOMBARD_V1_BETA_ALLOWED_WALLETS=0x... \
LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET=25000 \
LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL=250000 \
BASE_RPC_URL_PRIMARY=https://... \
PRIVY_APP_ID=... PRIVY_APP_SECRET=... \
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=... \
pnpm lombard:smoke:prod-env
```

---

## 1. Wallet & actifs requis

| Item | Attendu |
|------|---------|
| Chain | **Base** (8453) sélectionnée dans le portail |
| Garantie | **cbBTC** ou **cbETH** sur le wallet d'exécution |
| Gas | **ETH** sur Base pour approve + open loan |
| Allowlist | Wallet présent dans `LOMBARD_V1_BETA_ALLOWED_WALLETS` |
| Montant test | **50–100 USDC** empruntés (pas plus pour le 1er test) |

---

## 2. Parcours utilisateur attendu

### Entrée

1. Ouvrir `/app/wallet/crypto/cbbtc` (ou `cbeth`)
2. Vérifier le CTA **« Borrow USDC »** (ou message deposit si balance 0)
3. Clic → redirection `/app/borrow?collateral=cbBTC`

### Quote (étape montant)

| Check | Attendu |
|-------|---------|
| Montant saisi | ex. `75` USDC |
| Quote live | garantie cbBTC/cbETH calculée |
| Capacité max | ≤ 70 % LTV utilisateur |
| Warning | si LTV projeté > 60 % → warning (pas de blocage) |
| Blocage | si LTV > 70 %, liquidité insuffisante, cap beta, wallet non allowlisté |
| UX | pas de jargon DeFi ; « Powered by Morpho » en détail uniquement |

### Summary & disclaimer

| Check | Attendu |
|-------|---------|
| Liquidation warning | texte visible dans le récap |
| Checkbox | obligatoire avant confirmation |
| Bouton confirm | disabled sans checkbox |

### Exécution (états UI)

| Phase | Label utilisateur |
|-------|-------------------|
| preparing | Creating your loan… |
| authorizing | Authorising your guarantee… (Step 1) |
| locking / sending | Locking guarantee / Sending USDC (Steps 2–3) |
| confirming | Confirming on-chain… |
| confirmed | USDC received + CTA View wallet |

---

## 3. Ledger & position attendus

### Ledger (`onchain_vault_transactions`, `integration_mode=lombard_v1`)

| Champ | Attendu |
|-------|---------|
| `status` | `success` sur toutes les TX du groupe |
| `idempotencyKey` | UUID du flow |
| metadata | `borrow_amount_raw`, `guarantee_amount_raw`, `collateral` |
| post-confirm | `reconciliation_status`: `confirmed` ou `confirmed_with_delta` |

### Position read-only

| Surface | Attendu |
|---------|---------|
| Wallet hub | carte **Your active loan** |
| Détail actif | section emprunt actif |
| `/app/borrow/position` | LTV, montants, health label, APY |

---

## 4. Logs structurés (stdout ECS)

Préfixe `[lombard:ops]` — vérifier dans les logs web :

| Event | Quand |
|-------|-------|
| `lombard.quote_requested` | GET quote |
| `lombard.quote_blocked` | quote refusée (LTV, beta, liquidité…) |
| `lombard.prepare_requested` | POST prepare |
| `lombard.prepare_blocked` | prepare refusée |
| `lombard.tx_submitted` | chaque TX hash reçu au confirm |
| `lombard.confirm_success` | groupe confirmé success |
| `lombard.confirm_failed` | revert / failed |
| `lombard.reconciliation_delta` | écart > tolérance post-confirm |

Support alerts : préfixe `[lombard:support]`.

---

## 5. Panel QA debug (staff / non-prod uniquement)

Visible sur `/app/borrow` étapes **amount** et **summary** si :

- `NODE_ENV !== production`, **ou**
- personne portail liée à un compte admin (`/api/portal/lombard/qa-context` → `debugVisible: true`)

Champs affichés : marketId, wallet, LTV, caps beta restants, warnings, prepare status, ledger group id.

**Utilisateurs normaux en prod : ne voient rien.**

---

## 6. Monitoring admin

```bash
curl -s -b "$ADMIN_SESSION" https://<host>/api/admin/lombard/monitoring | jq
```

| Champ | Attendu après test |
|-------|-------------------|
| `totals.activePositions` | ≥ 1 |
| `totals.totalBorrowedUsdc` | ~ montant test |
| `ledger.pendingCount` | 0 |
| `ledger.failedCount` | 0 |
| `ledger.confirmedWithDeltaCount` | 0 (idéal) |

---

## 7. Rollback d'urgence

1. `LOMBARD_V1_ENABLED=false`
2. Redéployer / restart service web
3. Vérifier `GET /api/portal/lombard/markets` → `{ enabled: false }`
4. Positions existantes : read-only si réactivé ; pas de nouvel emprunt

---

## 8. Critères GO / NO-GO premier test live

| GO | NO-GO |
|----|-------|
| Smoke pass + allowlist OK | marketId non résolu |
| Wallet Base + cbBTC/cbETH + ETH gas | cap beta dépassé |
| Quote 50–100 USDC OK | quote_blocked répétitif |
| Confirm success + reconciliation `confirmed` | confirm_failed |
| Carte active loan visible < 1 min | monitoring pending > 15 min |
| Pas de `reconciliation_delta` | delta sans explication |

---

## 9. Support playbook (1er test)

1. Noter `groupKey` / tx hashes depuis logs `[lombard:ops]`
2. Vérifier position Morpho on-chain (Base)
3. Comparer monitoring admin vs UI portail
4. En cas d'échec : **ne pas retenter** sans diagnostic — voir runbook
