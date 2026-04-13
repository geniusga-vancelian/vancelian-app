# Rapport — SIEM Tier 1 (production fintech)

## Objectif

Industrialiser la **collecte**, la **corrélation multi-dimensionnelle** (IP / device / utilisateur), l’**export vers un SIEM externe**, et l’**alerting** avec traçabilité en base, aligné sur un usage **fintech**.

## Architecture

| Composant | Emplacement |
|-----------|-------------|
| Pipeline unifié | `api/services/security/security_event_pipeline.py` |
| Sinks (abstraction) | `api/services/security/security_event_sink.py` |
| Moteur de corrélation (scores 0–100) | `api/services/security/security_correlation_engine.py` |
| Alertes | `api/services/security/security_alert_service.py` |
| Rétention | `api/services/security/security_events_retention.py` (réexport purge TTL) |
| Persistance historique | `auth_security_events` + `services/auth/security_events_service.py` |
| Compat / réexport | `api/services/auth/security_event_pipeline.py`, `security_alerting.py` |

## Pipeline — `emit_security_event`

Signature principale :

```text
emit_security_event(event_type, user_id, device_id, ip, metadata=None, risk_level="LOW", *, user_agent=None, db=None)
```

- `user_id` : chaîne numérique admin → entier en base ; sinon `user_id_external` dans les métadonnées.
- Métadonnées **normalisées** : `risk_level`, `email_sha256` si un champ email est présent dans `metadata`.
- Horodatage UTC et schéma export SIEM : **`arquantix.security.event.v2`**.
- Anonymisation export : réutilisation de `security_event_anonymize` (IP partielle, device tronqué, metadata masquée) + **empreinte email** (`email_sha256`) pour corrélation sans exposer l’adresse.

La persistance passe par `persist_auth_security_event` ; le forward SIEM est déclenché après écriture.

## Sinks — `SECURITY_EVENTS_SINK`

| Valeur | Classe |
|--------|--------|
| `datadog` | `DatadogSink` → `push_datadog_log` |
| `opensearch` / `elasticsearch` / `elastic` | `OpenSearchSink` |
| `none` (défaut) | `NoopSink` |

Factory : `get_security_event_sink()`.

## Corrélation — `security_correlation_engine`

Fonctions (sur `Session` + `auth_security_events`) :

- `detect_ip_anomaly(user_id)` — trop d’IP distinctes.
- `detect_multi_device_abuse(user_id)` — trop de `device_id` distincts.
- `detect_bruteforce(ip)` — volume d’échecs auth par IP.
- `detect_refresh_abuse(device_id)` — refresh rejetés / rafales.
- `detect_geo_velocity(user_id)` — changement de pays (metadata) trop rapide.
- `detect_geo_velocity_from_ip_sequence(...)` — placeholder GeoIP (extension).

Agrégation : `aggregate_signals` → `CorrelationAssessment` avec **`risk_score` 0–100** et **`risk_level`** (LOW / MEDIUM / HIGH / CRITICAL).

Vue globale dashboard : `assess_global_peers(db)` (compose bruteforce / burst device / geo jump hérités du moteur auth).

## Alerting — `emit_siem_alert`

- **HIGH** : log structuré + **événement** `security.siem.alert` via `emit_security_event` (si `AUTH_SECURITY_EVENTS_ENABLED`).
- **CRITICAL** : idem + **webhook** JSON (`SECURITY_ALERT_WEBHOOK_URL`, compatible **Slack** Incoming Webhook) + **email SES** si `SECURITY_ALERT_EMAIL_TO` et `SES_FROM_EMAIL` / `AWS_SES_FROM` sont définis.

L’ancien module `services/auth/security_alerting.py` délègue à `emit_siem_alert` (compatibilité `send_security_alert` / corrélation existante).

## API admin

Préfixe **`/admin/security`** (JWT admin) — inchangé côté chemins, enrichi :

- `GET /events`, `GET /events/summary`
- `GET /anomalies` : ajout `global_risk_index`, `global_risk_level`, `engine_signals`
- `GET /user-risk/{user_id}` : ajout `risk_index` (0–100), `engine_signals` ; `risk_score` reflète le **niveau** moteur agrégé.

## Rétention

- TTL : `AUTH_SECURITY_EVENTS_RETENTION_DAYS` (7–730, défaut 90).
- Purge : thread applicatif (hors mode `testing`) + `purge_old_auth_security_events` importable depuis `services.security.security_events_retention`.

## Variables d’environnement (synthèse)

| Variable | Rôle |
|----------|------|
| `SECURITY_EVENTS_SINK` | `datadog` \| `opensearch` \| … \| `none` |
| `DATADOG_API_KEY` / `DD_API_KEY`, `DD_SITE` | Datadog |
| `OPENSEARCH_URL`, `OPENSEARCH_INDEX_PREFIX` | OpenSearch |
| `SECURITY_ALERT_WEBHOOK_URL` | Webhook CRITICAL (Slack, etc.) |
| `SECURITY_ALERT_EMAIL_TO` | Destinataire alerte CRITICAL (SES) |
| `AUTH_SECURITY_EVENTS_ENABLED` | Active la persistance + stockage alertes HIGH/CRITICAL |
| `SECURITY_CORRELATION_ON_EMIT` | Corrélation rapide après chaque événement (défaut true) |

## Tests

```bash
cd api && pytest tests/test_security_siem.py -v
```

Couverture : rétention, corrélation auth + **moteur Tier 1**, sinks Datadog/OpenSearch mockés, noop sink, alertes webhook CRITICAL, API admin enrichie.

## Évolutions recommandées

- **GeoIP** sur `detect_geo_velocity_from_ip_sequence`.
- **Streaming** (Kafka / Kinesis) via nouveau `SecurityEventSink`.
- **Règles métier** (seuils par tenant) externalisées en config.
- **Schéma OpenSearch** / index template dédié + ILM.
