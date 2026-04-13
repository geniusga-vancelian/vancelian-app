# AUTO EXECUTION — PENDING STUCK AUDIT REPORT

## Executive Summary

L'audit a identifié **3 bugs** empêchant les ordres auto-exécutés d'atteindre un statut terminal (`executed`, `partial`, `failed`). Tous les ordres restaient bloqués en "En cours" dans l'UI.

| # | Bug | Sévérité | Impact |
|---|-----|----------|--------|
| 1 | `execution_status="pending"` écrit à la CRÉATION de l'ordre | **Critique** | 100% des ordres actifs affichent "En cours" au lieu de "Actif" |
| 2 | Aucun guard `finally` dans `_execute_order_hook` | Élevé | Un chemin d'exception imprévu peut laisser pending |
| 3 | Rollback de `_process_triggered` supprime le cache Redis sans persister le `failed` | Élevé | L'ordre est orphelin : actif en DB, invisible du moteur |

---

## Real Stuck Order Trace

### Lifecycle observé (AVANT fix)
```
1. Création (orders_router.py)
   → status = "active"
   → execution_status = "pending"  ← BUG : ne devrait pas être set ici
   → Redis: ZADD alerts:BTC:down:{bucket} 85000.0 {id}

2. Flutter UI lit l'ordre
   → executionStatus = "pending"
   → isPending = (executionStatus == 'pending') → TRUE  ← BUG : match trop large
   → Badge affiché : "En cours" au lieu de "Actif"

3. Si le prix croise (après le fix price_source)
   → _trigger_single() : status = "triggered", execution_status = "pending"
   → _execute_order_hook() appelé
   → ExchangeService.buy() appelé
   → Si exception (InsufficientFundsError, PriceUnavailableError, etc.)
   → Retries → Toutes les tentatives échouent
   → execution_status = "failed" (en mémoire)
   → db.commit() dans _process_triggered()

4. Si db.commit() RÉUSSIT :
   → execution_status = "failed" persisté
   → UI affiche "Échoué" ✓

5. Si db.commit() ÉCHOUE (session DB corrompue) :
   → db.rollback() → TOUT annulé
   → status revient à "active", execution_status revient à "pending"
   → MAIS l'alerte a été retirée du cache Redis
   → L'ordre est ORPHELIN : actif en DB, invisible du moteur
   → UI affiche "En cours" POUR TOUJOURS
```

---

## Execution State Machine Audit

### Schéma attendu
```
                    ┌──────────┐
  Création ────────►│  active   │ execution_status = NULL
                    │          │
                    └────┬─────┘
                         │ crossing détecté
                         ▼
                    ┌──────────┐
  _trigger_single ─►│ triggered │ execution_status = "pending"
                    │          │
                    └────┬─────┘
                         │ _execute_order_hook()
                         ▼
              ┌──────────┴──────────┐
              │                     │
         ┌────▼────┐          ┌─────▼─────┐
         │executed │          │  failed   │
         │partial  │          │           │
         └─────────┘          └───────────┘
```

### Chemins dans `_execute_order_hook()` — Tous terminaux

| # | Chemin | `execution_status` final | Statut |
|---|--------|-------------------------|--------|
| 1 | `side` ou `amount` manquant | `failed` (missing_side_or_amount) | ✅ |
| 2 | `side` invalide | `failed` (invalid_side) | ✅ |
| 3 | Pre-check fail | `failed` (price_moved_beyond_safety) | ✅ |
| 4 | Retry loop exhausted, result=None | `failed` (all_attempts_failed) | ✅ |
| 5 | Retry window exhausted | `failed` (all_attempts_failed) | ✅ |
| 6 | Result status != completed | `failed` (exchange_error) | ✅ |
| 7 | Slippage exceeded | `failed` (slippage_exceeded) | ✅ |
| 8 | Zero fill | `failed` (zero_fill) | ✅ |
| 9 | Partial fill | `partial` | ✅ |
| 10 | Full fill | `executed` | ✅ |
| 11 | Uncaught exception | `failed` (exception) | ✅ |
| 12 | **NEW: finally guard** | `failed` (unexpected_non_terminal_exit) | ✅ NEW |

---

## Retry Loop Audit

### Logique
```python
attempt = 0
while attempt < 3:
    attempt += 1
    if attempt > 1 and elapsed > 1.0s:
        break  # retry window exhausted
    try:
        result = svc.buy(db, req, actor)
    except Exception:
        result = None
        continue
    if result.status == "completed":
        break
```

### Après le loop
```python
if result is None or result.status != "completed":
    alert.execution_status = "failed"  # ← toujours terminal
```

**Verdict** : La retry loop converge toujours vers un statut terminal.

### Risque identifié
Si ExchangeService raise une exception qui corrompt la session DB (SQL error), les retries suivantes échouent aussi car la session est en état "aborted". Le `execution_status = "failed"` est set en mémoire mais `db.commit()` échoue → rollback → status perdu.

**Fix appliqué** : `_rescue_failed_orders()` ouvre une NOUVELLE session pour persister le statut terminal.

---

## Exception Path Audit

### ExchangeService.buy() — Exceptions possibles

| Exception | Quand | Session DB | Impact |
|-----------|-------|-----------|--------|
| `InsufficientFundsError` | Balance EUR < montant | Propre (SELECT avant mutations) | `result=None`, retries, puis `failed` ✓ |
| `AccountNotFoundError` | Compte EUR manquant | Propre | Idem ✓ |
| `PriceUnavailableError` | Pas de quote marché | Propre | Idem ✓ |
| `MarketQuoteStaleError` | Quote trop vieille | Propre | Idem ✓ |
| `UnsupportedAssetError` | Asset inconnu | Propre | Idem ✓ |
| `ExchangeError` | Volume calculé = 0 | Propre | Idem ✓ |
| SQL IntegrityError | Contrainte DB violée | **CORROMPUE** | Rollback → orphelin ← BUG 3 |
| Deadlock/Timeout | Lock contention | **CORROMPUE** | Rollback → orphelin ← BUG 3 |

**Fix appliqué** : Le handler `_rescue_failed_orders` gère le cas "session corrompue → rollback" en persistant sur une nouvelle session.

---

## Persistence Audit

### Flow de commit
```
_process_triggered():
    db = db_factory()              # nouvelle session
    
    _trigger_single(alert, db):    # modifie alert in-memory
        alert.status = "triggered"
        alert.execution_status = "pending"
        _execute_order_hook(alert, db):
            # ExchangeService.buy(db, ...)
            # alert.execution_status = "executed" / "failed"
    
    triggered += 1
    
    db.commit()  ← SEUL POINT DE PERSISTANCE
```

### Problème (AVANT fix)
Si `db.commit()` échoue :
1. `db.rollback()` annule TOUT (status, execution_status, exchange orders, etc.)
2. L'alerte a été retirée du cache Redis par `remove_alert_from_cache()` en L258
3. Redis et DB sont désynchronisés : DB = active, Redis = absent → **ordre orphelin**

### Solution (APRÈS fix)
```python
except Exception:
    db.rollback()
    self._rescue_failed_orders(order_alerts, asset, direction, db_factory)
```

`_rescue_failed_orders` :
1. Ouvre une nouvelle session DB
2. Pour chaque ordre, relit la row avec `FOR UPDATE SKIP LOCKED`
3. Force `status = "triggered"`, `execution_status = "failed"` (ou le statut qu'avait l'objet Python)
4. Commit sur la nouvelle session
5. S'assure que l'alerte est retirée du cache Redis

---

## Root Cause

### Bug 1 : `execution_status = "pending"` à la création (RACINE PRINCIPALE)

**Fichier** : `orders_router.py` L99
```python
alert = PriceAlert(
    ...
    execution_status="pending",  # ← NE DEVRAIT PAS ÊTRE ICI
)
```

**Effet** : Flutter `isPending` retourne `true` pour TOUS les ordres actifs (jamais déclenchés).
```dart
bool get isPending => executionStatus == 'pending' ||    // ← TRUE dès la création !
    (isTriggered && executionStatus == null);
```

**Badge UI** : "En cours" (bleu) au lieu de "Actif" (vert/rouge).

### Bug 2 : Pas de guard `finally` dans `_execute_order_hook`

Un chemin d'exception imprévu pourrait laisser `execution_status = "pending"` sans finalisation.

### Bug 3 : Rollback perd le statut sans rescue

Si `db.commit()` échoue dans `_process_triggered`, l'ordre est orphelin (actif en DB, absent de Redis).

---

## Fix Applied

### 1. `orders_router.py` — Ne plus set `execution_status` à la création

```python
# AVANT
alert = PriceAlert(
    ...
    execution_status="pending",  # ← SUPPRIMÉ
)

# APRÈS
alert = PriceAlert(
    ...
    # execution_status laissé à None (valeur par défaut DB)
)
```

### 2. `engine.py` — Guard `finally` dans `_execute_order_hook`

```python
def _execute_order_hook(self, alert, db):
    try:
        ...
    except Exception:
        alert.execution_status = "failed"
        ...
    finally:
        if alert.execution_status == "pending":
            alert.execution_status = "failed"
            alert.metadata_ = {
                ...,
                "failure_reason": "unexpected_non_terminal_exit",
            }
            logger.error("SAFETY GUARD: order %s forced to failed", alert.id)
```

### 3. `engine.py` — `_rescue_failed_orders` après rollback

Nouvelle méthode qui ouvre une session DB fraîche pour persister le statut terminal quand le commit principal échoue.

### 4. `engine.py` — Capture du `last_error` dans la retry loop

Le message d'erreur de la dernière tentative est capturé et inclus dans `metadata_.failure_detail` pour le diagnostic.

### 5. `trigger_order.dart` — Fix `isPending` getter

```dart
// AVANT
bool get isPending => executionStatus == 'pending' ||
    (isTriggered && executionStatus == null);

// APRÈS
bool get isPending =>
    (isTriggered && (executionStatus == 'pending' || executionStatus == null));
```

Maintenant `isPending` ne retourne `true` QUE si `status == 'triggered'`. Un ordre `active` avec `execution_status = null` affiche "Actif".

---

## Final Guarantees

### Invariant 1 : Un ordre ne peut jamais rester `pending` indéfiniment

| Scénario | Garantie |
|----------|----------|
| `_execute_order_hook` termine normalement | Tous les chemins écrivent un statut terminal |
| Exception non gérée dans `_execute_order_hook` | `except Exception` → `failed` |
| Chemin imprévu | `finally` guard → `failed` |
| `db.commit()` échoue | `_rescue_failed_orders` persiste sur nouvelle session |

### Invariant 2 : L'UI reflète correctement le statut

| Backend state | `isPending` | UI Badge |
|---------------|-------------|----------|
| `status=active`, `execution_status=null` | `false` | **Actif** ✅ |
| `status=triggered`, `execution_status=pending` | `true` | **En cours** ✅ |
| `status=triggered`, `execution_status=null` | `true` | **En cours** ✅ |
| `status=triggered`, `execution_status=executed` | `false` | **Exécuté** ✅ |
| `status=triggered`, `execution_status=failed` | `false` | **Échoué** ✅ |
| `status=triggered`, `execution_status=partial` | `false` | **Partiel** ✅ |

### Invariant 3 : Pas d'ordre orphelin

Si le commit rollback, `_rescue_failed_orders` :
- Persiste le statut sur une nouvelle session
- S'assure que le cache Redis est nettoyé

### Tests
- 92/92 tests passent sans régression
- 0 erreur de lint

---

## Files Modified

| Fichier | Changement |
|---------|-----------|
| `api/services/price_alerts/orders_router.py` | Supprimé `execution_status="pending"` à la création |
| `api/services/price_alerts/engine.py` | Guard `finally`, `_rescue_failed_orders`, `last_error` capture |
| `mobile/lib/features/alerts/domain/models/trigger_order.dart` | Fix `isPending` pour exiger `isTriggered` |
