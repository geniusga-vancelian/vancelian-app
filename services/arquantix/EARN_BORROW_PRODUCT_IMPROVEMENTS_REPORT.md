# Earn / Borrow Product Surface — Improvements Report

## Objectif

Enrichir la surface produit Phase 2A.9 avec :
1. Distinction claire APY estimé vs APR
2. Séparation explicite earning (prêté) vs idle (non utilisé)
3. Backward compatibility complète

---

## Changements

### 1. Pools overview — APY clarification

**Avant :**
```json
{
  "supply_apr": 3.0,
  "borrow_apr": 5.0,
  "effective_apy": 1.5
}
```

**Après :**
```json
{
  "supply_apr": 3.0,
  "borrow_apr": 5.0,
  "effective_apy": 1.5,
  "is_apy_estimated": true,
  "apy_explanation": "APY estimé basé sur l'utilisation actuelle de la pool. Le rendement réel dépend du taux d'emprunt futur."
}
```

Le flag `is_apy_estimated: true` permet au frontend d'afficher un indicateur visuel (ex: icône info, tooltip) pour que le client comprenne que le rendement n'est pas garanti.

### 2. Earn positions — Earning vs Idle split

**Avant :** Deux listes séparées (`positions` pour earning, `pending_commitments` pour idle) sans lien entre elles.

**Après :** Positions unifiées par asset avec le détail earning/idle :

```json
{
  "total_earn_value_eur": 2760.00,
  "total_accrued_interest_eur": 12.34,
  "total_supplied_assets": 1,

  "earning": {
    "amount_eur": 1840.00,
    "accrued_interest_eur": 12.34
  },
  "idle": {
    "amount_eur": 920.00,
    "accrued_interest_eur": 0.0
  },

  "positions": [
    {
      "asset": "USDC",
      "total_supplied": 3000.0,
      "earning_amount": 2000.0,
      "idle_amount": 1000.0,
      "accrued_interest": 12.34,
      "total_value": 3012.34,
      "value_eur": 2760.00,
      "earning_value_eur": 1840.00,
      "idle_value_eur": 920.00,
      "accrued_interest_eur": 12.34,
      "apy": 1.5,
      "is_apy_estimated": true,
      "pool_utilization": 66.67,
      "supplied": 2000.0
    }
  ],

  "pending_commitments_count": 1,
  "pending_commitments": [...]
}
```

**Logique :**

| Source | Champ | Calcul |
|--------|-------|--------|
| Lending atoms | `earning_amount` | `atom.quantity` |
| Lending atoms | `accrued_interest` | `atom.accrued_income` |
| Pending commitments | `idle_amount` | `sum(commitment.available_amount)` par asset |
| Formule | `total_supplied` | `earning_amount + idle_amount` |
| Formule | `total_value` | `total_supplied + accrued_interest` |

### 3. Dashboard — Earn breakdown

**Avant :**
```json
{
  "earn": { "total_value_eur": 2760.00 },
  "borrow": { ... },
  "net_position_eur": 1840.00
}
```

**Après :**
```json
{
  "earn": { "total_value_eur": 2760.00, ... },
  "earn_breakdown": {
    "earning_value_eur": 1840.00,
    "idle_value_eur": 920.00,
    "accrued_interest_eur": 12.34
  },
  "borrow": { ... },
  "net_position_eur": 1840.00
}
```

---

## Backward compatibility

| Champ | Statut |
|-------|--------|
| `positions[].supplied` | Conservé (= `earning_amount`) |
| `pending_commitments` | Conservé (liste inchangée) |
| `total_earn_value_eur` | Conservé |
| `total_accrued_interest_eur` | Conservé |
| `positions_count` | Conservé |
| `pending_commitments_count` | Conservé |
| Tous les champs `borrow` | Inchangés |

Aucun champ supprimé. Seuls des champs additifs.

---

## Invariants

| # | Invariant | Vérifié |
|---|-----------|---------|
| 1 | `earning_amount + idle_amount = total_supplied` | ✅ |
| 2 | `earning_eur + idle_eur ≈ total_earn_value_eur` (± accrued) | ✅ |
| 3 | `idle.accrued_interest_eur = 0` (toujours) | ✅ |
| 4 | `is_apy_estimated = true` (toujours, V1) | ✅ |
| 5 | `utilization = 0 → effective_apy = 0` | ✅ |
| 6 | `no borrow → earning = 0, idle = total` | ✅ |
| 7 | `full borrow → idle = 0, earning = total` | ✅ |
| 8 | Moteur lending inchangé (read-only) | ✅ |

---

## Tests

### Résultats

```
27 passed — test_product_surface.py

106 passed — full regression (toutes suites lending + product)
```

### Couverture détaillée

| Catégorie | Tests | Statut |
|-----------|-------|--------|
| Pools overview + rates | 2 | ✅ |
| APY estimated flag | 2 | ✅ |
| APY formula (varying utilization) | 2 | ✅ |
| Earning vs idle split | 2 | ✅ |
| Accrued interest only on earning | 1 | ✅ |
| Backward compat (`supplied`) | 1 | ✅ |
| Pending commitments | 1 | ✅ |
| Total EUR values | 1 | ✅ |
| Borrow positions | 2 | ✅ |
| Dashboard + earn_breakdown | 3 | ✅ |
| Edge: empty, commit-only, zero util, full borrow | 4 | ✅ |
| Post-repay | 1 | ✅ |
| Multi-asset | 1 | ✅ |
| Earning + idle = total invariant | 1 | ✅ |
| EUR invariant (earning + idle ≈ total) | 1 | ✅ |
| Idle zero interest | 1 | ✅ |
| No borrow → all idle | 1 | ✅ |

---

## Fichiers modifiés

| Fichier | Modification |
|---------|-------------|
| `api/services/lending/product_surface.py` | Ajout APY flags, split earning/idle, earn_breakdown |
| `api/tests/test_product_surface.py` | 27 tests (14 → 27) |

Aucun autre fichier modifié. Moteur lending intact.
