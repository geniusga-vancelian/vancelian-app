# Phase 4C.4 — Readiness shutdown (legacy persons / `ALLOW_LEGACY_UNAUTHENTICATED_KYC`)

## Objectif

Fournir une **évaluation go/no-go explicite** pour décider de passer à `ALLOW_LEGACY_UNAUTHENTICATED_KYC=false` (puis retrait ultérieur des routes), en s’appuyant sur les compteurs Phase 4C.3 et des **seuils configurables**, sans framework lourd ni enforcement automatique.

## Variables d’environnement (seuils)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `LEGACY_SHUTDOWN_MAX_TOTAL_HITS` | `0` | `0` = pas de plafond sur le volume total ; sinon `total_hits` doit rester ≤ cette valeur. |
| `LEGACY_SHUTDOWN_MAX_UNAUTHENTICATED_HITS` | `0` | Plafond agrégé des hits `authenticated=false` ; `0` = exiger zéro trafic non authentifié. |
| `LEGACY_SHUTDOWN_MAX_ADMIN_HITS` | `-1` | `-1` = critère désactivé ; `0` = aucun hit `caller_category=admin`. |
| `LEGACY_SHUTDOWN_MAX_OWNER_HITS` | `-1` | Idem pour `owner`. |
| `LEGACY_SHUTDOWN_REQUIRE_SUCCESSOR_EVIDENCE` | `false` | Si `true`, exiger `successor_identity_hits` (query ou script). |
| `LEGACY_SHUTDOWN_MIN_SUCCESSOR_IDENTITY_HITS` | `1` | Seuil minimal pour la preuve successeur. |
| `LEGACY_SHUTDOWN_MANUAL_OVERRIDE_READY` | `false` | Force `ready=true` (hors métriques). |
| `LEGACY_SHUTDOWN_MANUAL_OVERRIDE_BLOCK` | `false` | Force `ready=false`. |

## Critères de readiness (modèle)

| Critère | Comportement |
|---------|----------------|
| **Flag déjà coupé** | Si `ALLOW_LEGACY_UNAUTHENTICATED_KYC` est déjà `false` → `ready=true`, `recommendation=already_disabled`. |
| **Override manuel blocage** | `LEGACY_SHUTDOWN_MANUAL_OVERRIDE_BLOCK=true` → `ready=false`, raison `manual_override_block` (rollback / prudence). |
| **Override manuel GO** | `LEGACY_SHUTDOWN_MANUAL_OVERRIDE_READY=true` → `ready=true`, `recommendation=manual_override_ready` (hors critères métriques). |
| **Trafic non authentifié** | Somme des séries avec `authenticated=false` ; doit être **≤** `LEGACY_SHUTDOWN_MAX_UNAUTHENTICATED_HITS` (défaut **0** = aucun hit). |
| **Volume total** | Si `LEGACY_SHUTDOWN_MAX_TOTAL_HITS` **> 0**, le total des hits legacy doit être **≤** ce plafond ; `0` = **pas de plafond** sur le total. |
| **Usage admin / owner** | Si `LEGACY_SHUTDOWN_MAX_ADMIN_HITS` (resp. `MAX_OWNER_HITS`) **≥ 0**, les hits agrégés `caller_category=admin` (resp. `owner`) ne doivent pas dépasser le max ; **-1** = critère désactivé. |
| **Preuve successeur** | Si `LEGACY_SHUTDOWN_REQUIRE_SUCCESSOR_EVIDENCE=true`, le paramètre `successor_identity_hits` (query admin ou script) doit être **≥** `LEGACY_SHUTDOWN_MIN_SUCCESSOR_IDENTITY_HITS`. |

**Limite importante** : les compteurs in-process sont **cumulatifs depuis le démarrage du process** (sauf reset). Le champ `observation_note` du JSON le rappelle ; pour une **fenêtre temporelle**, croiser avec métriques externes / SIEM / agrégations Prometheus sur `GET .../identity`.

## Choix d’implémentation

- **Module** `api/services/persons/legacy_persons_shutdown_readiness.py` : `LegacyPersonsShutdownReadinessConfig`, `evaluate_legacy_persons_shutdown_readiness`, `summarize_traffic_from_metrics_snapshot`, `build_legacy_persons_shutdown_readiness_report`.
- **Variables d’environnement** : préfixe `LEGACY_SHUTDOWN_*` (lus dans le module, pas d’explosion de `core/env.py`).
- **Endpoint admin** (déjà authentifié admin) : `GET /admin/security/legacy-persons/shutdown-readiness?successor_identity_hits=0` — même garde que les autres routes `/admin/security/*`.

## Fichiers modifiés / ajoutés

| Fichier | Rôle |
|---------|------|
| `api/services/persons/legacy_persons_shutdown_readiness.py` | **Nouveau** — logique d’évaluation + rapport dict. |
| `api/services/auth/security_admin_routes.py` | Route GET `legacy-persons/shutdown-readiness`. |
| `api/tests/test_legacy_persons_shutdown_readiness.py` | **Nouveau** — tests unitaires + smoke admin. |

## Recommandations (`recommendation`)

| Valeur | Signification indicative |
|--------|----------------------------|
| `already_disabled` | Le flag legacy est déjà à `false`. |
| `keep_enabled` | Critères non remplis ou blocage manuel. |
| `manual_override_ready` | GO forcé par override. |
| `disable_in_staging_first` | Critères OK et `is_dev_mode()` — valider d’abord hors prod. |
| `ready_to_disable_production` | Critères OK en contexte non-dev — prêt à planifier la coupure prod. |

## Exemples de sortie JSON

### Cas « prêt » (métriques vides, flag encore true)

```json
{
  "ready": true,
  "blocking_reasons": [],
  "traffic_summary": {
    "total_hits": 0,
    "unauthenticated_hits": 0,
    "admin_hits": 0,
    "owner_hits": 0
  },
  "recommendation": "disable_in_staging_first",
  "observation_note": "Compteurs in-process cumulatifs depuis le démarrage (Phase 4C.3), sauf reset. Pour une fenêtre temporelle, utiliser des métriques externes ou SIEM en complément.",
  "allow_legacy_unauthenticated_kyc": true,
  "config_effective": {
    "max_total_hits": 0,
    "max_unauthenticated_hits": 0,
    "max_admin_hits": -1,
    "max_owner_hits": -1,
    "require_successor_identity_evidence": false,
    "min_successor_identity_hits": 1,
    "manual_override_ready": false,
    "manual_override_block": false
  }
}
```

### Cas « pas prêt » (trafic non authentifié)

```json
{
  "ready": false,
  "blocking_reasons": ["unauthenticated_traffic_above_threshold"],
  "traffic_summary": {
    "total_hits": 2,
    "unauthenticated_hits": 2,
    "admin_hits": 0,
    "owner_hits": 0
  },
  "recommendation": "keep_enabled",
  "observation_note": "...",
  "allow_legacy_unauthenticated_kyc": true,
  "config_effective": { "...": "..." }
}
```

## Procédure de rollout recommandée

1. **Staging** : fixer les seuils (`LEGACY_SHUTDOWN_*`), observer les compteurs / SIEM sur une fenêtre, appeler l’endpoint admin (ou `build_legacy_persons_shutdown_readiness_report()` en script).
2. **Décision** : si `ready=true` et `recommendation` adaptée à l’environnement → basculer `ALLOW_LEGACY_UNAUTHENTICATED_KYC=false` sur staging, surveiller erreurs 401 côté clients legacy.
3. **Production** : répéter après validation métier ; en cas d’incident, `LEGACY_SHUTDOWN_MANUAL_OVERRIDE_BLOCK=true` ou remettre le flag à `true` (rollback).
4. **Suite** : retrait des routes (hors périmètre 4C.4) une fois trafic négligeable (cf. Phase 4C.1 / 4C.3).

## Références

- Plan dépréciation : `PHASE_4C_LEGACY_PERSONS_DEPRECATION_PLAN.md`
- Métriques : `PHASE_4C3_LEGACY_PERSONS_AGGREGATED_METRICS.md`
- Observabilité : `PHASE_4C1_LEGACY_PERSONS_RUNTIME_OBSERVABILITY.md`
