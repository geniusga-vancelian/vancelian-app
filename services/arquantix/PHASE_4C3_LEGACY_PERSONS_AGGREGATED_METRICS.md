# Phase 4C.3 — Métriques agrégées (legacy persons)

## Objectif

Compléter l’observabilité Phase 4C.1 (log structuré + SIEM optionnel) par des **compteurs agrégés** consultables rapidement pour les **dashboards** et les décisions de **coupure** des routes legacy, sans nouveau stack d’observabilité.

## Fichiers modifiés / ajoutés

| Fichier | Rôle |
|---------|------|
| `api/services/persons/legacy_persons_metrics.py` | **Nouveau** — singleton thread-safe, même philosophie que `services/price_alerts/metrics.py`. |
| `api/services/persons/legacy_observability.py` | Après construction du dict `meta`, appel unique à `get_legacy_persons_metrics().record_hit(...)` (pas de duplication de logique métier). |
| `api/tests/test_legacy_persons_metrics.py` | **Nouveau** — reset des compteurs entre tests, vérifs GET/POST, labels, absence d’UUID dans le snapshot. |

## Nom de métrique

- **`legacy_persons_endpoint_hit_total`** (constante `LEGACY_PERSONS_ENDPOINT_HIT_TOTAL` dans le code)

La clé JSON `legacy_persons_endpoint_hit_total` dans `snapshot()` est la **somme** de toutes les séries (total processus depuis le dernier reset — en prod, process lifetime).

## Labels (dimensions)

Toutes les valeurs sont des **chaînes** à cardinalité maîtrisée (pas d’IDs personne, pas de chemins dynamiques).

| Label | Valeurs typiques |
|-------|-------------------|
| `endpoint_name` | `GET /api/persons/{person_id}` ou `POST /api/persons/{person_id}/fields` (littéraux stables, pas l’UUID réel). |
| `method` | `GET` ou `POST` |
| `authenticated` | `true` ou `false` |
| `caller_category` | `unauthenticated`, `admin`, `owner` |
| `allow_legacy_unauthenticated_kyc` | `true` ou `false` (état runtime du flag) |

## Format `snapshot()`

```json
{
  "metric": "legacy_persons_endpoint_hit_total",
  "legacy_persons_endpoint_hit_total": 42,
  "series": [
    {
      "labels": {
        "endpoint_name": "GET /api/persons/{person_id}",
        "method": "GET",
        "authenticated": "false",
        "caller_category": "unauthenticated",
        "allow_legacy_unauthenticated_kyc": "true"
      },
      "value": 10
    }
  ]
}
```

## Intégration future (dashboards / scraping)

- **Côté code** : importer `get_legacy_persons_metrics().snapshot()` depuis un handler admin, un job, ou un export Prometheus texte (mapping manuel label → série) — pas d’endpoint HTTP ajouté dans cette phase pour garder un diff minimal.
- **Exemples d’agrégation** :
  - Trafic total legacy : champ `legacy_persons_endpoint_hit_total`.
  - Part non authentifiée : somme des `series` où `authenticated == "false"`.
  - Dépendance au flag : filtrer `allow_legacy_unauthenticated_kyc == "true"` vs `false`.
  - GET vs POST : filtrer `method` ou `endpoint_name`.

## Lien avec la décision de shutdown

- Comparer le **rythme** des hits (par fenêtre, via snapshots périodiques ou exporter vers une TSDB) avec les **objectifs produit** avant de couper `ALLOW_LEGACY_UNAUTHENTICATED_KYC` ou de retirer les routes.
- Croiser avec Phase 4C.1 : les événements SIEM restent la **preuve** par requête ; les métriques donnent la **vue agrégée** immédiate pour un go/no-go.

## Tests

- `tests/test_legacy_persons_metrics.py` : incrément GET / POST, labels attendus, `caller_category` admin sur GET avec JWT admin, snapshot sans UUID personne.
- Fixture `reset_for_tests()` : réservée aux tests pour isoler les compteurs.

## Contraintes respectées

- Pas de duplication du flux Phase 4C.1 (un seul point d’enregistrement dans `record_legacy_persons_endpoint_hit`).
- Log structuré et `persist_auth_security_event` inchangés dans leur rôle.
- Pas d’identifiant personne dans les labels ni dans le snapshot de test.
- Pas de nouvelle dépendance observabilité ; mécanisme léger, production-safe (verrou + dict), comme les alertes prix.

## Références

- Phase 4C.1 : `PHASE_4C1_LEGACY_PERSONS_RUNTIME_OBSERVABILITY.md`
- Dépréciation : `PHASE_4C_LEGACY_PERSONS_DEPRECATION_PLAN.md`
