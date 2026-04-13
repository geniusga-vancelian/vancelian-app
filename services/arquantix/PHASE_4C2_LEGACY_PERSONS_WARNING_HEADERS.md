# Phase 4C.2 — En-têtes HTTP `Warning` explicites (persons legacy)

## Objectif

Renforcer le signal de dépréciation sur les routes legacy en ajoutant un en-tête **`Warning`** (RFC 7234, code **299**) en complément des en-têtes **Phase 4C** déjà présents (`Deprecation`, `Link` sur GET).

## Fichiers modifiés

| Fichier | Modification |
|---------|--------------|
| `api/services/persons/routes.py` | Constantes `_LEGACY_WARNING_POST_FIELDS`, fonction `_legacy_warning_get_identity`, extension de `_apply_legacy_person_deprecation_headers` pour définir `Warning` selon GET vs POST. |
| `api/tests/test_legacy_endpoint_security.py` | Assertions sur `Warning`, conservation de `Deprecation` / `Link` ; POST 200 sans `Link`. |
| `api/tests/test_legacy_persons_observability.py` | Assertion `Warning` sur GET 200 (cohérence avec Phase 4C.1). |

## En-têtes HTTP exacts (réponses succès où les helpers Phase 4C s’appliquent déjà)

### `GET /api/persons/{person_id}` — HTTP 200

| En-tête | Valeur |
|---------|--------|
| `Deprecation` | `true` (inchangé) |
| `Link` | `</api/persons/{person_id}/identity>; rel="successor-version"` (inchangé) |
| `Warning` | `299 - "Deprecated API. Use GET /api/persons/{person_id}/identity"` |

Le `{person_id}` dans l’URL du message est l’UUID réel de la ressource (lisible dans l’en-tête, cohérent avec le `Link`).

### `POST /api/persons/{person_id}/fields` — HTTP 200

| En-tête | Valeur |
|---------|--------|
| `Deprecation` | `true` (inchangé) |
| `Link` | **absent** (inchangé — pas d’équivalent « successor » unique côté API) |
| `Warning` | `299 - "Deprecated API. Use authenticated onboarding or business APIs."` |

Le texte POST **ne** renvoie **pas** vers `GET .../identity` comme substitut d’écriture : la cible documentée reste les flux **onboarding authentifiés** / **API métier**, aligné sur `PHASE_4C_LEGACY_PERSONS_DEPRECATION_PLAN.md`.

### Cas non couverts par ces en-têtes

Les réponses **401 / 403 / 404** (GET) ou **400 / 500** (POST) n’invoquent pas `_apply_legacy_person_deprecation_headers` : comportement inchangé par rapport à Phase 4C.

## Différences GET vs POST (texte `Warning`)

| Route | Message | Rationale |
|-------|---------|-----------|
| GET | Successeur explicite : `GET .../identity` | Lecture consolidée documentée. |
| POST | Orientation processus : onboarding / APIs métier | Pas de successeur HTTP unique pour l’écriture champ à champ. |

## Tests

- **`test_legacy_endpoint_security.py`** : pour chaque scénario GET réussi, `Warning` = valeur GET attendue ; pour POST 200, `Warning` = chaîne POST fixe et pas d’en-tête `Link`.
- **`test_legacy_persons_observability.py`** : GET succès vérifie aussi `Warning`.

## Déploiement / rollout

- **Compatibilité** : ajout d’un en-tête ; les corps de réponse ne changent pas. Les clients RFC 7234 peuvent afficher ou journaliser `Warning` ; les clients qui ignorent les en-têtes inconnus ne sont pas impactés.
- **Stabilité** : libellés figés dans des constantes ; toute évolution ultérieure devrait rester rare et documentée (éviter le spam de variantes).
- **Observabilité** : les proxies / WAF / agrégateurs de logs peuvent filtrer sur `Warning: 299` pour suivre encore l’usage legacy en complément de Phase 4C.1 (`legacy_persons_endpoint_hit`).

## Référence

- Plan Phase 4C : `PHASE_4C_LEGACY_PERSONS_DEPRECATION_PLAN.md`
- Observabilité runtime : `PHASE_4C1_LEGACY_PERSONS_RUNTIME_OBSERVABILITY.md`
