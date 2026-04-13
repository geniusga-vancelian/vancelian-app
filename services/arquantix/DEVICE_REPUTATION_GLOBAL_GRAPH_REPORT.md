# Device Reputation & Global Graph — Rapport

## Executive Summary

Un **système de réputation par identité device composite** (hash SHA-256 dérivé de `device_id`, `fingerprint_hash`, `install_id` optionnel) a été ajouté au-dessus de l’auth existante. Il persiste les agrégats (`auth_device_reputation`), les arêtes d’usage (`auth_device_usage_edges`), la **blacklist explicite** (admin uniquement), et les **findings** d’analyse graphe (`auth_device_graph_findings`). L’intégration **login / refresh** applique des règles progressives : liste noire → blocage ; réputation **HIGH** → step-up OTP ; **CRITICAL** → step-up, avec blocage optionnel via `DEVICE_REPUTATION_CRITICAL_BLOCKS_AUTH`. Le **risk engine** peut intégrer une contribution bornée depuis les devices récemment vus par l’utilisateur (`DEVICE_REPUTATION_RISK_ENGINE_INTEGRATION`). Aucune **blacklist automatique** au premier signal.

## Data Model

| Table | Rôle |
|--------|------|
| `auth_device_reputation` | PK `device_hash`, scores agrégés, niveaux, compteurs, timestamps |
| `auth_device_usage_edges` | Événements liant `device_hash`, `user_id?`, `session_id?`, `ip`, `event_type` |
| `auth_device_blacklist` | Entrées manuelles, `blocked_until` nullable (permanent si null) |
| `auth_device_graph_findings` | Findings typés + `severity` + `metadata_json` |

Migration Alembic : **`115_auth_device_reputation_graph.py`**.

## Device Identity Strategy

Module : `api/services/security/device_reputation/device_identity.py`.

- Priorité à la **fingerprint** quand présente, puis `device_id` non-legacy, puis `X-Install-ID`.
- Canonique concaténée puis **SHA-256 hex** (64 caractères).
- Documenté en docstring (audit / explicabilité).

## Reputation Scoring

Service : `device_reputation_service.py`.

- Formules **linéaires plafonnées** sur : `unique_user_count`, `unique_ip_count`, `suspicious_event_count`, sessions distinctes.
- Types d’événements « suspects » listés explicitement (`SUSPICIOUS_EDGE_EVENTS`).
- **Blacklist** → score 100, niveau `BLOCKED`.
- Seuils de niveaux : LOW / MEDIUM / HIGH / CRITICAL (et `BLOCKED` si blacklist).
- **Findings progressifs** : seuils configurables (`DEVICE_REPUTATION_SHARED_USER_FINDING_MIN`, etc.) — pas de finding au premier edge isolé pour les règles multi-utilisateurs.

## Graph Analysis

Module : `device_graph_analysis.py` : `find_shared_devices`, `find_dense_ip_device_clusters`, `detect_device_farms`, `detect_cross_user_high_risk_devices`, `run_all_graph_detections` (option `persist_findings`). Les IP dans les métadonnées exportées utilisent des **préfixes masqués** pour limiter l’exposition.

## Auth Integration

- `refresh_session.issue_fresh_auth_session` : résolution `device_hash`, `evaluate_auth_impact`, enregistrement d’arête `auth.session.opened`, métadonnées événements enrichies (`device_reputation_score`, `device_reputation_level`).
- Échecs login : arête `auth.login.failed` via session isolée (même logique que les events sécu).
- Refresh : réévaluation ; en cas de blocage, **révocation** de la session courante + 403.
- Pipeline SIEM : champs racine `device_reputation_score` / `device_reputation_level` dans `build_sink_payload` (les IP restent anonymisées côté sink existant).

## Admin Controls

Router : `/admin/security/devices` (`device_reputation_admin_routes.py`).

- `GET /admin/security/devices/` — filtres : `reputation_level`, `user_id`, `ip`, `blocked_only`
- `GET /admin/security/devices/high-risk`
- `GET /admin/security/devices/findings`
- `GET /admin/security/devices/{device_hash}`
- `POST /admin/security/devices/blacklist` — corps : `device_hash`, `reason`, `blocked_until?`
- `POST /admin/security/devices/unblacklist`

## Tests

Fichier : `api/tests/test_device_reputation.py` (hash stable, multi-utilisateurs, findings, blacklist, graphe, boost risk engine).

## Garde-fous

- Pas d’auto-blacklist sur signal unique.
- Journalisation `logger` sur blocages / blacklist.
- Export graphe : IP masquées dans les findings `dense_ip` ; sink SIEM réutilise l’anonymisation existante.

## Remaining Gaps / Next Iteration

- Corrélation directe **device_hash** dans `auth_security_events` (aujourd’hui enrichissement au moment login/refresh via métadonnées).
- **blocked_until** sur `auth_device_reputation` réservé pour extensions (actuellement synchronisation logique via blacklist + niveau).
- **Job planifié** pour `run_all_graph_detections(persist_findings=True)`.
- **Modèles de clustering** plus avancés (Louvain, etc.) si volumétrie importante.
- **RLS / rétention** des arêtes (TTL) pour limiter la croissance des tables.
