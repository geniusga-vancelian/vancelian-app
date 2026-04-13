# Phase 4C — Plan de dépréciation des endpoints « persons » legacy

## Executive Summary

Les routes **historiques** `GET /api/persons/{person_id}` et `POST /api/persons/{person_id}/fields` restent nécessaires pour la **rétrocompatibilité**, mais divergent du modèle actuel (**identité consolidée**, Zero Trust, auth continue sur `GET .../identity`).  

Cette phase **ne supprime rien** : elle documente, marque **OpenAPI** + **HTTP** (`Deprecation`, `Link` successor), centralise les TODO, et décrit la **sortie progressive** pilotée par `ALLOW_LEGACY_UNAUTHENTICATED_KYC`.

---

## 1. Audit des routes auditées

| Méthode | Chemin | Module | Statut |
|---------|--------|--------|--------|
| GET | `/api/persons/{person_id}` | `services/persons/routes.py` | **Legacy** — dépréciation explicite (Phase 4C) |
| POST | `/api/persons/{person_id}/fields` | `services/persons/routes.py` | **Legacy** — dépréciation explicite (Phase 4C) |
| GET | `/api/persons/{person_id}/identity` | `services/persons/routes.py` | **Cible** — non legacy ; auth continue + ZT |
| POST | `/api/persons` | idem | Création admin — hors périmètre « legacy read » |
| PATCH | `/api/persons/{person_id}/kyc-status` | idem | Admin — hors legacy GET/POST brut |
| POST | `/api/persons/{person_id}/link-client` | idem | Admin — hors legacy |

### Routes adjacentes (même préfixe `/api/persons`)

| Chemin | Module | Note |
|--------|--------|------|
| `.../onboarding/next-step`, `.../onboarding/submit-step` | `services/onboarding/routes.py` | **Pas** les endpoints legacy personne ; auth encore TODO — dette **distincte** |
| `.../risk/compute`, `.../risk/latest` | `services/aml_risk/routes.py` | Idem — risque AML, pas profil ORM brut |

---

## 2. Données exposées et chevauchement

| Endpoint legacy | Données | Chevauchement avec `GET .../identity` |
|------------------|---------|--------------------------------------|
| **GET** `/api/persons/{id}` | Entité ORM `Person` (dont `profile_json`, statuts, métadonnées) | **Partiel** : la vue `/identity` agrège **person + client + éligibilité + risque** ; le GET brut est une **fuite de surface** sans les garde-fous récents |
| **POST** `/api/persons/{id}/fields` | Écriture champ métier + `audit_event` | **Pas** d’équivalent direct sur `/identity` (lecture seule) ; la migration = **flux onboarding / API métier authentifiés** |

---

## 3. Usage (tests & clients probables)

| Consommateur | Observation |
|--------------|-------------|
| `api/tests/test_legacy_endpoint_security.py` | Feature flag + en-têtes de dépréciation |
| `api/tests/test_client_identity_api.py` (`TestBackwardCompatibleGetPerson`) | Compatibilité schéma |
| `api/scripts/smoke_test_endpoints.py` | POST `/fields` |
| `web/src/app/api/client/onboarding/*` | Passe par le **web** Next vers onboarding — **pas** le GET personne legacy |

**Conclusion :** suppression **non** sûre sans inventaire runtime (logs, métriques clients). Prochaine étape = **observabilité** (compteur d’appels + `Deprecation` déjà présent).

---

## 4. Changements code (Phase 4C)

- **Module** `persons/routes.py` : docstring Phase 4C ; helper `_apply_legacy_person_deprecation_headers` ; `deprecated=True` + `summary` / `description` OpenAPI sur GET/POST legacy ; en-têtes `Deprecation: true` et `Link: </api/persons/{id}/identity>; rel="successor-version"` sur GET 200 ; `Deprecation` sur POST 200.
- **`core/env.py`** : docstring `allow_legacy_unauthenticated_kyc` liée au plan.
- **`auth/dependencies.py`** : `get_current_user_or_legacy` documenté comme **réservé** aux routes legacy.
- **`onboarding/routes.py`**, **`aml_risk/routes.py`** : clarification qu’ils ne sont **pas** les routes legacy Phase 4C.

---

## 5. Migration recommandée

1. **Lecture** : migrer les appelants vers `GET /api/persons/{person_id}/identity` (Bearer, ZT, auth continue selon config).
2. **Écriture de champs** : identifier le flux métier (onboarding, back-office) ; authentifier systématiquement ; retirer la dépendance au mode sans JWT.
3. **Exploitation** : `ALLOW_LEGACY_UNAUTHENTICATED_KYC=false` en **staging** puis **prod** après fenêtre d’observation.
4. **Retrait** : une fois trafic nul / logs vides, retirer `get_person` / `set_field` ou les restreindre à **usage interne** (réseau / clé API service).

---

## 6. Prochaine étape de suppression « safe »

| Étape | Action |
|-------|--------|
| **4C (fait)** | Signaux dépréciation + docs |
| **4D (proposé)** | Métrique / log structuré `legacy_persons_endpoint_hit` (compteur par route + `person_id` hash) |
| **4E (proposé)** | `ALLOW_LEGACY_UNAUTHENTICATED_KYC` défaut `false` en **nouveaux** déploiements ; `true` uniquement legacy explicite |
| **5.x** | Suppression des handlers **après** confirmation produit |

---

## 7. Risques résiduels

- Clients ignorants des en-têtes HTTP continuent d’appeler les URLs legacy.
- POST `/fields` sans JWT reste dangereux tant que le flag est `true`.
- Onboarding / AML partagent le préfixe URL — confusion possible ; commentaires de module ajoutés.

---

## 8. Fichiers touchés (livraison)

| Fichier |
|---------|
| `api/services/persons/routes.py` |
| `api/core/env.py` |
| `api/services/auth/dependencies.py` |
| `api/services/onboarding/routes.py` |
| `api/services/aml_risk/routes.py` |
| `api/tests/test_legacy_endpoint_security.py` |
| `PHASE_4C_LEGACY_PERSONS_DEPRECATION_PLAN.md` (ce document) |
