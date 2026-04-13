# Phase 4B — Durcissement de la politique `view_sensitive_data`

## Objectif

Rendre l’accès aux lectures protégées par `action_key=view_sensitive_data` **plus strict** (KYC, vues risque admin, intelligence de session, passkeys en liste) **sans** introduire de nouveau moteur de policy ni modifier le contrat d’erreur structuré (`detail.code`, `reason_codes`, `next_step`, `policy`).

---

## Changements de politique (`sensitive_action_map.py`)

| Champ | Avant | Après |
|--------|--------|--------|
| `requires_step_up` | `False` | `True` |
| `requires_recent_auth_seconds` | `None` | `600` (10 min) |
| `allowed_if_device_trusted_only` | `True` | `True` (inchangé) |
| `required_auth_level` | `MEDIUM` | `MEDIUM` (inchangé) |

**Interprétation produit :** un **step-up récent** (horodatage `last_step_up_at` côté session intelligence, fenêtre **600 s**) est exigé ; les appareils **non trusted** déclenchent toujours une friction supplémentaire (`device_not_trusted`), comme avant.

---

## Ajustement moteur (`continuous_auth_engine.py`) — minimal

**Constat :** avec l’ancienne combinaison « `requires_step_up=True` » **et** « `requires_recent_auth_seconds` » sur d’autres actions, le moteur appliquait **deux** règles redondantes : la première rendait `require_step_up` **toujours** vrai dès que `policy.requires_step_up`, ce qui **empêchait** toute autorisation même après OTP récent.

**Correction :** si `requires_recent_auth_seconds` est **défini**, seule la **fenêtre de fraîcheur** du step-up (`_recent_auth_satisfied`) impose le refus (`recent_auth_required`). Sinon, `requires_step_up` seul conserve le comportement « friction permanente » pour les politiques **sans** fenêtre explicite.

Effet **collatéral positif** : les actions **HIGH** déjà mappées avec `step_up=True` **et** `recent` (ex. retrait, transfert) **ne sont plus bloquées de façon permanente** lorsque le step-up est récent et que les autres garde-fous passent — aligné avec l’intention « OTP dans les N dernières secondes ».

---

## Endpoints impactés (toujours `view_sensitive_data`)

Tous utilisent déjà `Depends(require_continuous_auth_for_action("view_sensitive_data"))` :

| Zone | Fichiers / routes |
|------|-------------------|
| Auth | `GET /auth/sessions`, `GET /auth/passkeys` |
| Identité | `GET /api/persons/{id}/identity`, `GET /api/portfolio-engine/clients/{id}/identity` |
| Admin sécurité | `GET /admin/security/user-risk/{user_id}`, `GET .../auth-orchestrator/preview`, `GET .../auth-orchestrator/decision-log`, `GET .../session-intelligence/logs`, `GET .../session-intelligence/{session_id}`, probe continuous auth |

**Contrat HTTP inchangé :** en cas de refus, `403` avec `detail.code == "session.step_up_required"` ou `401` avec `session.reauth_required` selon la décision existante.

---

## Tests ajoutés / mis à jour (`tests/test_session_intelligence.py`)

- `test_policy_view_sensitive_data_strict_recent_and_step_up` — valeurs de policy.
- `test_view_sensitive_data_allow_when_recent_step_up_and_trusted_device` — accès autorisé si step-up récent + appareil trusted.
- `test_view_sensitive_data_recent_auth_stale_forces_step_up` — `recent_auth_required` si `last_step_up_at` trop ancien.
- `test_view_sensitive_data_reauth_when_engine_requires_full_reauth` — `country_changed` → reauth (priorité sur step-up).
- `test_device_not_trusted_forces_step_up` — `last_step_up_at` récent pour isoler le chemin **device** (sinon `recent_auth_required` masquerait `device_not_trusted`).

Les tests d’intégration HTTP existants (Phase 4, custody) **mockent** toujours `evaluate_request_security_context` ; ils restent valides.

---

## Impact utilisateur (UX)

- Avec **auth continue + intelligence de session** activées et JWT lié à une session (`sid`), les utilisateurs doivent avoir effectué un **step-up récent (≤ 10 min)** pour les lectures sensibles, en plus d’un **appareil trusted** lorsque la policy l’exige.
- Sans step-up récent : **403** `session.step_up_required` (comportement attendu, plus fréquent qu’avant pour ces routes).
- Si les flags sont désactivés ou sans `sid` / sans ligne d’intelligence : comportement **inchangé** (court-circuits historiques dans `require_continuous_auth_for_action`).

---

## Risques résiduels

- **Clients** doivent mettre à jour `last_step_up_at` après OTP / passkey ; sinon refus récurrent sur les lectures sensibles.
- **Politiques** avec `requires_step_up=True` **sans** `requires_recent_auth_seconds` restent des cas « friction à chaque requête » (peu ou pas dans la carte actuelle).
- Tests **E2E** réels avec intelligence DB non couverts ici ; seule la logique moteur + policy est garantie par les tests unitaires.

---

## Fichiers modifiés

| Fichier | Rôle |
|---------|------|
| `api/services/security/sensitive_action_map.py` | Politique `view_sensitive_data` |
| `api/services/security/continuous_auth_engine.py` | Fusion logique step-up / fenêtre récente |
| `api/tests/test_session_intelligence.py` | Tests Phase 4B |

---

## Synthèse

- **Policy :** step-up explicite + fenêtre **600 s** + trusted device conservé.
- **Moteur :** correction de cohérence pour que « step-up + fenêtre » soit **utilisable**.
- **Routes :** aucun renommage d’`action_key` ; contrat d’erreur préservé.
