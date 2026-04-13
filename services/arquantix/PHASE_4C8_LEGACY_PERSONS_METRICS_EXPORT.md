# Phase 4C.8 — Export durable des métriques legacy persons

## Objectif

Réduire la dépendance au seul état **in-process** (perdu au redémarrage) en offrant un **export JSON** stable, consommable par un **scraping périodique**, des **jobs** ou des **scripts** qui écrivent vers S3, fichiers, ou une TSDB existante — **sans** nouveau backend d’observabilité.

## Fichiers modifiés / ajoutés

| Fichier | Rôle |
|---------|------|
| `api/services/persons/legacy_persons_metrics.py` | `LEGACY_PERSONS_METRICS_EXPORT_KIND`, `build_legacy_persons_metrics_export()`. |
| `api/services/auth/security_admin_routes.py` | `GET /admin/security/legacy-persons/metrics-export` (admin JWT). |
| `api/tests/test_legacy_persons_metrics_export.py` | **Nouveau** — structure d’export, alignement avec `snapshot()`, absence d’UUID, contrôle d’accès HTTP. |

## Mécanisme retenu

1. **Helper réutilisable** `build_legacy_persons_metrics_export()` — même résultat que l’endpoint HTTP, utilisable depuis un job Python dans le process API ou un script qui importe le module (même mémoire que l’app).
2. **Endpoint admin** — aligné sur `GET /admin/security/legacy-persons/shutdown-readiness` : `Depends(get_current_user)`, **pas** d’exposition publique.

Aucune duplication de la logique **readiness** (Phase 4C.4 / 4C.7) : l’export ne fait que **envelopper** `snapshot()`.

## Payload exemple

```json
{
  "export_kind": "legacy_persons_metrics_v1",
  "exported_at_utc": "2026-04-03T12:00:00.000000Z",
  "metrics": {
    "metric": "legacy_persons_endpoint_hit_total",
    "legacy_persons_endpoint_hit_total": 42,
    "last_24h_hits": 3,
    "last_7d_hits": 15,
    "series": [
      {
        "labels": {
          "endpoint_name": "GET /api/persons/{person_id}",
          "method": "GET",
          "authenticated": "false",
          "caller_category": "unauthenticated",
          "allow_legacy_unauthenticated_kyc": "true"
        },
        "value": 3
      }
    ]
  }
}
```

Les **labels** restent à **cardinalité bornée** (pas d’UUID personne). `exported_at_utc` permet d’ordonner les exports stockés côté durable.

## Accès et sécurité

| Aspect | Détail |
|--------|--------|
| **HTTP** | Préfixe `/admin/security/…`, authentification **admin** (JWT) comme les autres diagnostics. |
| **Secrets** | Aucun secret dans le payload ; ne pas logger les tokens dans les clients de scraping. |
| **Données sensibles** | Aucun identifiant personne ; les séries agrègent des compteurs par labels stables. |

## Continuité opérationnelle et shutdown

- **Après redémarrage** du process, les compteurs in-process repartent à zéro ; en **archivant** régulièrement l’export (fichier, objet S3, etc.), les équipes conservent une **courbe** et une **preuve** d’usage pour les décisions Phase 4C.4 / 4C.7.
- Le **readiness** peut continuer à s’appuyer sur le snapshot **live** ; l’export sert à **l’historique** et aux **dashboards** hors process.

## Appel depuis un job (exemple)

```bash
curl -sS -H "Authorization: Bearer <ADMIN_JWT>" \
  "https://<host>/admin/security/legacy-persons/metrics-export" \
  >> /var/log/legacy-persons-metrics.jsonl
```

Côté Python (même process que l’API) :

```python
from services.persons.legacy_persons_metrics import build_legacy_persons_metrics_export
payload = build_legacy_persons_metrics_export()
```

## Références

- Phase 4C.3 : `PHASE_4C3_LEGACY_PERSONS_AGGREGATED_METRICS.md`
- Phase 4C.5 : `PHASE_4C5_ROLLING_WINDOW_METRICS.md`
- Readiness : `PHASE_4C7_ROLLING_WINDOW_READINESS_INTEGRATION.md`
