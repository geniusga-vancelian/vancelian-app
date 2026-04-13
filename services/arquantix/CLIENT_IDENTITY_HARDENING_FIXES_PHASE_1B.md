# CLIENT_IDENTITY_HARDENING_FIXES_PHASE_1B

## Executive Summary

Ce rapport documente les 3 corrections critiques identifiées après Phase 1B :

1. **Sécurisation des endpoints legacy** — `GET /api/persons/{id}` et `POST /{id}/fields` étaient encore ouverts sans auth
2. **AML placeholder cleanup** — `aml_ok = True` donnait un faux signal de conformité
3. **Eligibility gate global** — Aucune opération financière (exchange, lending) ne vérifiait l'éligibilité client

Les trois axes sont maintenant implémentés avec des feature flags pour transition progressive.

---

## Endpoint Security Fix

### Problème
`GET /api/persons/{id}` et `POST /api/persons/{id}/fields` acceptaient des requêtes sans authentification.

### Solution
- Nouvelle dépendance `get_current_user_or_legacy()` dans `services/auth/dependencies.py`
- Si JWT présent et valide → `AuthContext` retourné, ownership vérifié
- Si JWT présent et invalide → 401
- Si JWT absent et `ALLOW_LEGACY_UNAUTHENTICATED_KYC=True` → accès autorisé avec WARNING log
- Si JWT absent et `ALLOW_LEGACY_UNAUTHENTICATED_KYC=False` → 401

### Fichiers modifiés
- `services/auth/dependencies.py` — ajout de `get_current_user_or_legacy()`
- `services/persons/routes.py` — protection des 2 endpoints avec ownership check

### Flag
```
ALLOW_LEGACY_UNAUTHENTICATED_KYC=true  (default — backward-compatible)
```

### TODO
```python
# TODO Phase 1C: remove legacy unauthenticated access
```

---

## AML Placeholder Strategy

### Problème
`aml_ok = True` hardcodé dans `EligibilityService` donnait une illusion de conformité AML.

### Solution

#### Nouveau champ `aml_status`
```python
@dataclass
class EligibilityResult:
    eligible: bool
    reasons: List[str]
    kyc_ok: bool = False
    aml_ok: bool = False          # ← était True
    aml_status: str = "not_checked"  # ← NOUVEAU
    risk_ok: bool = True
```

#### Statuts AML possibles
| Statut | Signification |
|--------|--------------|
| `not_checked` | AML pas encore vérifié (défaut Phase 1B) |
| `pending` | Vérification en cours |
| `verified` | Vérifié OK |
| `failed` | Vérifié KO |

#### Logique
```
aml_ok = (aml_status == "verified")

Si ENABLE_AML_BLOCKING=False (défaut) :
  → aml_ok ignoré dans le calcul d'eligible
  → mais retourné dans la réponse API

Si ENABLE_AML_BLOCKING=True :
  → aml_ok=False bloque l'éligibilité
```

### Réponse API enrichie
```json
{
  "eligibility": {
    "eligible": true,
    "kyc_ok": true,
    "aml_ok": false,
    "aml_status": "not_checked",
    "risk_ok": true,
    "reasons": []
  }
}
```

### Flag
```
ENABLE_AML_BLOCKING=false  (default — non bloquant jusqu'à Sumsub Phase 2)
```

### Fichiers modifiés
- `services/compliance/eligibility_service.py` — `EligibilityResult` + logique AML
- `services/persons/routes.py` — `EligibilityDetail` schema + endpoint enrichi
- `core/env.py` — feature flags

---

## Eligibility Integration

### Problème
L'`EligibilityService` existait mais n'était branché sur aucun point d'entrée produit.

### Solution

#### Nouvelle méthode gate
```python
EligibilityService.require_eligible_by_client_id(db, client_id)
```
- Résout `person` depuis `client_id`
- Évalue l'éligibilité
- Lève `ClientNotEligibleError` si bloqué (HTTP 403)
- Log audit event `CLIENT_BLOCKED_BY_ELIGIBILITY`
- Respecte `DISABLE_ELIGIBILITY_CHECKS` flag (bypass d'urgence)

#### Points d'entrée protégés

| Service | Méthode | Gate |
|---------|---------|------|
| `ExchangeService` | `buy()` | ✅ |
| `ExchangeService` | `sell()` | ✅ |
| `ExchangeService` | `swap()` | ✅ |
| `ExchangeService` | `sell_all()` | ✅ |
| `LendingService` | `create_loan()` | ✅ |
| `PoolLendingService` | `create_supply_commitment()` | ✅ |
| `PoolLendingService` | `borrow_from_pool()` | ✅ |
| `OfferService` | `subscribe()` | ✅ |
| `LendingInvestOrchestrator` | `invest_into_product()` | ✅ |

#### Gestion d'erreur HTTP
`ClientNotEligibleError` est capturé dans tous les routeurs concernés :
- `exchange/router.py` — 403
- `exchange/error_mapper.py` — 403
- `test_clients/router.py` (mobile) — 403
- `lending/router.py` — 403
- `lending/pool_router.py` — 403
- `lending/offer_router.py` — 403

### Flag
```
DISABLE_ELIGIBILITY_CHECKS=false  (default — checks actifs)
```

### Audit
Chaque blocage crée un `AuditEvent` :
```json
{
  "event_type": "CLIENT_BLOCKED_BY_ELIGIBILITY",
  "payload": {
    "person_id": "...",
    "client_id": "...",
    "eligible": false,
    "kyc_ok": false,
    "aml_ok": false,
    "aml_status": "not_checked",
    "risk_ok": true,
    "reasons": ["kyc_status is 'in_progress', expected 'approved'"]
  }
}
```

---

## Tests

### Nouveaux fichiers de tests

| Fichier | Couverture |
|---------|-----------|
| `test_legacy_endpoint_security.py` | Flag ON/OFF, admin toujours autorisé |
| `test_aml_placeholder.py` | aml_status explicit, ENABLE_AML_BLOCKING ON/OFF, API response |
| `test_product_gating.py` | Exchange buy/sell bloqué, lending create_loan/supply/borrow bloqué, bypass flag, audit event |

### Tests existants mis à jour

| Fichier | Changement |
|---------|-----------|
| `test_eligibility_engine.py` | `aml_ok` assertion → `False` (was `True`) |

### Matrice de couverture

| Scénario | Couvert |
|----------|---------|
| Legacy GET sans auth + flag ON | ✅ |
| Legacy GET sans auth + flag OFF | ✅ |
| Legacy POST sans auth + flag ON/OFF | ✅ |
| Admin toujours autorisé | ✅ |
| AML status = not_checked par défaut | ✅ |
| AML non bloquant quand flag OFF | ✅ |
| AML bloquant quand flag ON | ✅ |
| API response inclut aml_status | ✅ |
| Exchange buy bloqué si KYC != approved | ✅ |
| Exchange sell bloqué si KYC != approved | ✅ |
| Exchange buy passe si KYC = approved | ✅ |
| Exchange buy bypass si DISABLE_ELIGIBILITY_CHECKS | ✅ |
| Lending create_loan bloqué | ✅ |
| Pool supply bloqué | ✅ |
| Pool borrow bloqué | ✅ |
| Audit event créé sur blocage | ✅ |

---

## Flags & Rollout Strategy

| Flag | Default | Prod recommandé | Phase de suppression |
|------|---------|----------------|---------------------|
| `ALLOW_LEGACY_UNAUTHENTICATED_KYC` | `true` | `false` dès que tous les clients envoient JWT | Phase 1C |
| `ENABLE_AML_BLOCKING` | `false` | `true` après intégration Sumsub | Phase 2 |
| `DISABLE_ELIGIBILITY_CHECKS` | `false` | `false` (urgence uniquement) | Permanent (emergency) |

### Rollout recommandé
1. **Immédiat** : Déployer avec les defaults (zéro breaking change)
2. **Semaine 1** : Monitorer les logs `legacy_unauthenticated_access` + `eligibility_check_bypassed`
3. **Semaine 2** : Passer `ALLOW_LEGACY_UNAUTHENTICATED_KYC=false` en staging
4. **Semaine 3** : Passer en production
5. **Phase 2** : Activer `ENABLE_AML_BLOCKING=true` après Sumsub

---

## Next Steps

1. **Phase 1C** : Supprimer `ALLOW_LEGACY_UNAUTHENTICATED_KYC` et rendre auth obligatoire partout
2. **Phase 2** : Intégration Sumsub → `aml_status` réel → activer `ENABLE_AML_BLOCKING`
3. **Phase 2** : Risk scoring dynamique → enrichir `risk_ok` avec un scoring réel
4. **Monitoring** : Dashboard des audit events `CLIENT_BLOCKED_BY_ELIGIBILITY`
