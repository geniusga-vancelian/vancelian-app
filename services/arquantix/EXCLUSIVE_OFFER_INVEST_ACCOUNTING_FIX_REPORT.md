# Exclusive Offer Invest — Accounting Fix Report

## Executive Summary

Après un investissement de 1000 EUR dans une Exclusive Offer (asset cible USDC),
les 1155.07 USDC convertis apparaissaient **en double** :
- dans la section **Crypto** (via `crypto_positions.balance`)
- dans la section **Placements** (via `pool_supply_commitments`)

Causant un total wealth gonflé de ~100%.

**Fix** : modifier `get_crypto_positions()` pour utiliser `available_balance`
(solde libre) au lieu de `balance` (solde total incluant les engagements lending),
éliminant le double comptage.

---

## Expected Accounting Flow

```
1000 EUR
  │
  ├─ ExchangeService.buy(EUR → USDC)
  │   ├─ custody_accounts.available_balance -= 1000 EUR    ✓
  │   ├─ exchange_orders (side=buy, completed)              ✓
  │   └─ crypto_positions:
  │       ├─ balance += 1155.07 USDC                        ✓
  │       └─ available_balance += 1155.07 USDC              ✓
  │
  └─ OfferService.subscribe() → PoolLendingService.create_supply_commitment()
      ├─ crypto_positions:
      │   ├─ balance = 1155.07 (INCHANGÉ — design P2P)      ← ROOT CAUSE
      │   └─ available_balance -= 1155.07 → 0               ✓
      └─ pool_supply_commitments:
          └─ amount = 1155.07, status = active               ✓
```

## Root Cause #1 — Crypto/Placements Duplication

### Design du pool_service

Le `create_supply_commitment()` suit le design P2P :
> "Supply commitment = funds stay in spot but available_balance is REDUCED"

Ce design est correct pour le modèle P2P (le borrow phase va débiter `balance`),
mais crée un double comptage côté UI.

### État DB après investissement

```
crypto_positions (USDC):
  balance            = 1155.068986    ← PAS débité
  available_balance  = 0.000000       ← Réduit par commitment

pool_supply_commitments:
  amount             = 1155.068986    ← Même montant
  status             = active
```

### Lecture par chaque section UI

| Section | Source | Champ lu | Montant | Bug |
|---------|--------|----------|---------|-----|
| Crypto | `get_crypto_positions()` | `pos.balance` | 1155 USDC | **Double comptage** |
| Placements | `get_earn_positions()` | `commitment.available_amount` | 1155 USDC | Correct |

### Code fautif (avant fix)

```python
# service.py L360-363
for pos in positions:
    balance = Decimal(str(pos.balance))  # ← utilise balance totale
    if balance <= 0:
        continue
```

Valorisation (L393) :
```python
val_eur = (balance * p_eur).quantize(...)  # ← valorise sur balance totale
```

## Root Cause #2 — Wrong Placements Valuation

**Conclusion : pas de bug.**

L'affichage "Placements = 1000 EUR" semblait incorrect, mais c'est le résultat correct :
- 1155.07 USDC × 0.8654 EUR/USDC = **999.90 EUR** ≈ 1000 EUR
- Le backend calcule `idle_amount × price_eur` (correct)
- Ce n'est PAS le `funding_amount` (1000 EUR) qui est utilisé — c'est une coïncidence numérique

---

## Fix Applied

### Backend — `services/test_clients/service.py`

**1 fichier modifié, 0 nouveau fichier.**

Modification de `get_crypto_positions()` :

```python
# AVANT (bug)
balance = Decimal(str(pos.balance))
if balance <= 0:
    continue
val_eur = (balance * p_eur).quantize(...)

# APRÈS (fix)
total_balance = Decimal(str(pos.balance))
free_balance = Decimal(str(pos.available_balance))
if total_balance <= 0:
    continue
display_balance = free_balance if free_balance >= 0 else total_balance
if display_balance <= 0:
    continue
val_eur = (display_balance * p_eur).quantize(...)
```

Ajout du champ `total_balance` dans la réponse (backward compat) pour permettre
au Flutter d'afficher le solde total si nécessaire.

### Flutter

**Aucune modification nécessaire.** Les modèles Flutter utilisent déjà les
bons champs du backend. Le fix backend suffit.

---

## Source of Truth — After Fix

| Concept | Source de vérité | Table/Vue |
|---------|-----------------|-----------|
| **Crypto spot libre** | `crypto_positions.available_balance` | Section Crypto |
| **Placements (lending)** | `pool_supply_commitments + lending atoms` | Section Placements |
| **Total wealth** | Σ(cash + crypto libre + placements) | Dashboard |

### Invariant comptable

```
crypto_positions.balance = available_balance + Σ(active commitments)
```

Après fix :
- Crypto affiche : `available_balance` (libre)
- Placements affiche : `Σ(active commitments)` (engagé)
- Total : pas de double comptage

---

## Verification

### Avant fix

```
GET /api/app/crypto-positions
  positions: [{ asset: USDC, balance: 1155.07, value_eur: ~1000 }]
  total_value_eur: ~1000

GET /api/app/lending/earn/positions
  positions: [{ asset: USDC, total_supplied: 1155.07, value_eur: 999.90 }]
  total_earn_value_eur: 999.90

TOTAL AFFICHÉ: ~2000 EUR (FAUX — double comptage)
```

### Après fix

```
GET /api/app/crypto-positions
  positions: []
  total_value_eur: 0.00

GET /api/app/lending/earn/positions
  positions: [{ asset: USDC, total_supplied: 1155.07, value_eur: 999.90 }]
  total_earn_value_eur: 999.90

TOTAL AFFICHÉ: ~1000 EUR (CORRECT)
```

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| ExchangeService inchangé | ✅ |
| PoolLendingService inchangé | ✅ |
| LendingInvestOrchestrator inchangé | ✅ |
| Moteur lending inchangé | ✅ |
| crypto_positions table inchangée | ✅ |
| Seule la vue/agrégation est modifiée | ✅ |
| Python imports OK | ✅ |
| API crypto-positions retourne 0 positions (correct) | ✅ |
| API earn/positions retourne 1 position (correct) | ✅ |
