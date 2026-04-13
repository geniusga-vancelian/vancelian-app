# Rapport d’implémentation — pipeline sécurité / SIEM

## Objectif

Centraliser les événements de sécurité auth, les exporter vers un SIEM (Datadog ou OpenSearch/ELK), appliquer des règles de corrélation heuristiques, alerter (log + webhook ciblé), exposer une API admin de lecture, et appliquer une rétention TTL avec purge automatique.

## Fichiers principaux

| Composant | Fichier |
|-----------|---------|
| Pipeline (DB → JSON → sink + corrélation rapide) | `api/services/auth/security_event_pipeline.py` |
| Persistance + forward | `api/services/auth/security_events_service.py` |
| Anonymisation export | `api/services/auth/security_event_anonymize.py` |
| Sink Datadog | `api/services/auth/datadog_sink.py` |
| Sink OpenSearch / Elasticsearch | `api/services/auth/opensearch_sink.py` |
| Corrélation | `api/services/auth/security_correlation_service.py` |
| Alertes | `api/services/auth/security_alerting.py` |
| Rétention / purge | `api/services/auth/security_events_retention.py` |
| API admin | `api/services/auth/security_admin_routes.py` |
| Schémas réponses | `api/schemas.py` |
| Thread purge | `api/main.py` (démarrage hors `testing`) |
| Tests | `api/tests/test_security_siem.py` |

## Variables d’environnement

| Variable | Rôle |
|----------|------|
| `SECURITY_EVENTS_SINK` | `datadog` \| `opensearch` \| `elasticsearch` \| `elastic` \| `none` |
| `DATADOG_API_KEY` / `DD_API_KEY` | Clé API logs Datadog |
| `DD_SITE` / `DATADOG_SITE` | Site Datadog (US/EU/US3/US5) |
| `SECURITY_EVENTS_DATADOG_SERVICE` | Nom du service (défaut `arquantix-auth-security`) |
| `OPENSEARCH_URL` / `ELASTICSEARCH_URL` | URL du cluster |
| `OPENSEARCH_INDEX_PREFIX` | Préfixe d’index (défaut `auth-security-events`) |
| `OPENSEARCH_USER` / `OPENSEARCH_PASSWORD` | Auth basique optionnelle |
| `SECURITY_ALERT_WEBHOOK_URL` | Webhook JSON (Slack-compatible) — **uniquement pour les alertes CRITICAL** |
| `SECURITY_CORRELATION_ON_EMIT` | `true`/`false` — corrélation légère après chaque événement (défaut `true`) |
| `AUTH_SECURITY_EVENTS_RETENTION_DAYS` | TTL en jours (7–730, défaut 90) |
| `AUTH_SECURITY_EVENTS_PURGE_INTERVAL_SEC` | Intervalle du thread de purge (défaut 86400) |
| `AUTH_SECURITY_EVENTS_ENABLED` | Active/désactive l’écriture en base |

## Format d’événement (sink)

- JSON structuré, horodatage UTC (`@timestamp` ISO Z).
- Champ `schema`: `arquantix.auth.security_event.v1`.
- Anonymisation partielle via `security_event_anonymize` (IP, device, UA, métadonnées sensibles).

## Corrélation

Règles implémentées (`security_correlation_service.py`) :

- **multiple_ip_sessions** — plusieurs IP distinctes pour un utilisateur sur une fenêtre.
- **device_event_burst** — volume anormal par `device_id`.
- **bruteforce_pattern** — échecs login / refresh / passkey par IP.
- **geo_jump** — si `country` ou `geo_country` est présent dans `metadata`.
- **quick_check_after_event** — rafale d’échecs sur 5 minutes par IP (seuil 40) → alerte **CRITICAL**.

Scores : `LOW` / `MEDIUM` / `HIGH` / `CRITICAL` (agrégation via `max_severity`).

`evaluate_and_alert(db)` exécute toutes les règles et appelle `send_security_alert` avec la sévérité max : **log pour toute alerte** ; **webhook seulement si la sévérité normalisée est CRITICAL** (y compris agrégat corrélation si le max est CRITICAL).

## API admin (JWT admin)

Préfixe : `/admin/security`.

| Méthode | Route | Description |
|---------|--------|-------------|
| GET | `/events` | Liste filtrée des événements |
| GET | `/events/summary` | Compteurs + drapeaux legacy Phase 3.1 |
| GET | `/anomalies` | Résultat du moteur de corrélation (sans envoi de webhook) |
| GET | `/user-risk/{user_id}` | Profil risque synthétique + findings récents |

## Rétention

- TTL : `AUTH_SECURITY_EVENTS_RETENTION_DAYS`.
- Purge : `purge_old_auth_security_events` ; en production, thread daemon dans `main.py` (non actif si `create_app(testing=True)`).
- Paramètre interne `do_commit=False` réservé aux tests pour rester dans une transaction rollback.

## Tests

`pytest api/tests/test_security_siem.py` : rétention, règles de corrélation, mocks sinks, webhook CRITICAL uniquement, routes admin.

## Limites connues

- Corrélation heuristique, pas de ML ; pas de blocage automatique des comptes.
- **Geo** : nécessite que les clients enrichissent `metadata` avec le pays.
- Charge SIEM : chaque événement persistant déclenche un push si le sink est actif — surveiller les quotas et la latence réseau.
