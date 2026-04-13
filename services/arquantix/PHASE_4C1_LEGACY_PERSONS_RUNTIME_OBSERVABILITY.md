# Phase 4C.1 — Observabilité runtime des endpoints persons legacy

## Objectif

Mesurer le trafic réel sur les routes legacy avant leur désactivation progressive, sans modifier les réponses ni casser la compatibilité.

## Fichiers modifiés / ajoutés

| Fichier | Rôle |
|---------|------|
| `api/services/persons/legacy_observability.py` | **Nouveau** — enregistrement du signal `legacy_persons_endpoint_hit` (log structuré + SIEM optionnel). |
| `api/services/persons/routes.py` | Appel à `record_legacy_persons_endpoint_hit` en tête de `get_person` et `set_field` ; injection `http_request: Request` (le corps POST reste `request: SetFieldRequest`). |
| `api/tests/test_legacy_persons_observability.py` | **Nouveau** — couverture des signaux, métadonnées, absence d’UUID brut dans le log d’observabilité, persistance SIEM si table présente, comportement HTTP inchangé. |

## Nom du signal / événement

- **Constante / `event_type` (auth_security_events)** : `legacy_persons_endpoint_hit`
- **Logger** : `arquantix.persons.legacy` — chaque ligne INFO contient le nom du signal puis un **JSON** (trié par clés) dans le message.

Quand `AUTH_SECURITY_EVENTS_ENABLED=true`, le même `event_type` et les mêmes métadonnées sont passés à `persist_auth_security_event` (même mécanisme que les autres événements de sécurité / SIEM).

## Champs émis (`metadata` / payload JSON)

| Champ | Description |
|-------|-------------|
| `legacy_persons_event` | Toujours `legacy_persons_endpoint_hit` (redondant avec le nom d’événement, utile en parsing de logs). |
| `legacy` | `true` |
| `endpoint_name` | `GET /api/persons/{person_id}` ou `POST /api/persons/{person_id}/fields` |
| `method` | `GET` ou `POST` |
| `authenticated` | `true` / `false` selon la présence d’un `AuthContext` |
| `allow_legacy_unauthenticated_kyc` | État runtime de `allow_legacy_unauthenticated_kyc()` (`core.env`) |
| `person_id_fingerprint` | Empreinte **SHA-256** tronquée (16 hex) sur `person:{uuid}` — **pas d’UUID en clair** |
| `caller_category` | `unauthenticated` \| `admin` \| `owner` (déduit de `auth`) |
| `successor_endpoint` | Pour GET : `/api/persons/{person_id}/identity` ; pour POST : `null` |

Les enregistrements SIEM reprennent aussi les champs habituels du modèle (`user_id`, `device_id`, `ip_address`, `user_agent` le cas échéant).

## Tests ajoutés

Fichier : `api/tests/test_legacy_persons_observability.py`

- GET legacy : présence du log structuré et des champs attendus (dont `successor_endpoint` pour GET).
- POST legacy : idem (sans successeur unique côté API).
- Le message du logger `arquantix.persons.legacy` ne contient **pas** l’UUID personne en clair.
- Avec `AUTH_SECURITY_EVENTS_ENABLED=true` et table `auth_security_events` : +1 ligne `AuthSecurityEvent` par hit, métadonnées cohérentes, pas d’UUID brut dans `metadata_payload`.
- Comportement HTTP inchangé : 401 sans JWT quand le flag legacy KYC est off ; admin toujours 200 sur GET avec `caller_category` = `admin`.

Les tests existants `test_legacy_endpoint_security.py` restent verts.

## Lien avec la décision de shutdown (Phase 4C suite)

- Agrégation des compteurs / requêtes sur `legacy_persons_endpoint_hit` (logs centralisés ou table `auth_security_events`) pour estimer **volume**, **profil d’appelants** (`caller_category`, authentifié ou non), et **dépendance au flag** `allow_legacy_unauthenticated_kyc`.
- Permet de fixer une fenêtre où le trafic est négligeable avant de retirer les routes ou de couper le flag, avec une base **objective** plutôt qu’hypothétique.
