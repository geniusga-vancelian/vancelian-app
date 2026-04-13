# Crypto Available Balance Unification Fix

## Objectif

Uniformiser toute la surface produit pour que la section Crypto
représente uniquement les fonds disponibles (`available_balance`),
et non le solde total (`balance` qui inclut les montants engagés en lending).

---

## Endpoints impactés

| # | Endpoint | Source | Fix |
|---|----------|--------|-----|
| 1 | `GET /api/app/crypto-positions` | `crypto_positions.balance` → `available_balance` | `service.py` — `get_crypto_positions()` |
| 2 | `GET /api/app/crypto-positions/{asset}` | `crypto_positions.balance` → `available_balance` | `service.py` — `get_crypto_wallet_detail()` |
| 3 | `GET /api/app/crypto-positions/direct` | `PositionAtom.quantity` → `quantity - lending_reserved` | `router.py` — `get_direct_crypto_positions()` |

### Endpoints NON impactés (lecture correcte)

| Endpoint | Raison |
|----------|--------|
| `GET /api/app/lending/earn/positions` | Lit `PoolSupplyCommitment` + `PositionAtom(lending)` — correct |
| `GET /api/app/lending/dashboard` | Agrège les earn positions — correct |
| `GET /api/app/cash` | Lit `CustodyAccount` — pas de lending sur fiat |
| `GET /api/app/crypto-positions/{asset}/transactions` | Historique brut — pas de filtrage balance |

---

## Corrections appliquées

### 1. `get_crypto_positions()` (service.py)

```
AVANT: balance = Decimal(str(pos.balance))
APRÈS: display_balance = Decimal(str(pos.available_balance))
       if display_balance <= 0: continue
```

Valorisation basée sur `display_balance`, pas `balance`.
Positions entièrement engagées : exclues de la liste.

### 2. `get_crypto_wallet_detail()` (service.py)

```
AVANT: balance = Decimal(str(pos.balance))
       balance_str = f"{balance:.{precision}f}"
APRÈS: display_balance = free_balance if free_balance >= 0 else total_balance
       if display_balance <= 0: return {"client": client, "detail": None}
```

Si toute la balance est engagée en lending → `detail: None`.
Valorisation (`total_value_eur`, `cost_basis_eur`) basée sur `display_balance`.

### 3. `get_direct_crypto_positions()` (router.py)

```
AVANT: qty = D(str(atom.quantity))
       val_eur = (qty * p_eur).quantize(...)
APRÈS: reserved = lending_reserved.get(asset_symbol, D("0"))
       display_qty = qty - reserved
       if display_qty <= 0: continue
       val_eur = (display_qty * p_eur).quantize(...)
```

La map `lending_reserved` est construite depuis `crypto_positions`:
```python
for cp in all_crypto_pos:
    reserved = balance - available_balance
    lending_reserved[asset] = reserved
```

---

## Invariant produit

```
Crypto visible au client = available_balance uniquement
                         = balance - Σ(active lending commitments)

Placements = Σ(active commitments) + Σ(lending atoms)

Total wealth = cash + crypto_libre + placements (sans double comptage)
```

---

## Vérification end-to-end

### Scénario : invest 1000 EUR → 1155 USDC → lending commitment

| Endpoint | Résultat |
|----------|----------|
| `crypto-positions` | 0 positions, 0.00 EUR |
| `crypto-positions/USDC` | detail: None |
| `crypto-positions/direct` | 0 positions, 0.00 EUR |
| `lending/earn/positions` | 1 position USDC, 999.91 EUR |
| **Total** | **999.91 EUR (correct, zéro duplication)** |

---

## Non-régression

| Invariant | Vérifié |
|-----------|---------|
| ExchangeService inchangé | ✅ |
| PoolLendingService inchangé | ✅ |
| Lending logic inchangée | ✅ |
| `balance` total inchangé en DB | ✅ |
| Seule la couche read (agrégation) modifiée | ✅ |
| Python imports OK | ✅ |
| Tous les endpoints API testés | ✅ |
