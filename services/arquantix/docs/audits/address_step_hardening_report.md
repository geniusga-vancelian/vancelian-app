# Rapport — Hardening métier `address_step`

**Date :** 2026-04-01  
**Périmètre :** validation submit (API registration), gouvernance admin (health flow), observabilité produit (client + API adresse + événements registration).

---

## Executive summary

L’écran **`address_step`** agrège plusieurs slugs (ligne 1, ville, code postal, pays, etc.) via `props.binding_slugs`, alors que la ligne composant a un `binding_slug` principal (souvent `address_line_1`) et un `policy_scope` résolu en **`none`**. En conséquence, la **politique de résidence** (`jurisdiction_country_policies`) ne s’appliquait pas au pays soumis dans `answers` pour `country_of_residence` (ni pour le pays lié à **`address_autocomplete`**), contrairement à un `country_picker` avec `policy_scope: residence`.

Ce rapport documente la **correction conservatrice** : une passe dédiée après la boucle `resolve_policy_scope` qui lit le slug pays effectif depuis les helpers `resolved_address_step_binding_slugs` / `resolved_binding_slugs` et applique `is_residence_country_allowed` lorsque la juridiction a des politiques de résidence.

En parallèle, la validation **`validate_screen_answers`** applique désormais un **format strict ISO 3166-1 alpha-2** (deux lettres) sur le slug pays des composites adresse, ce qui était auparavant ignoré (`continue`).

Côté **admin**, un **avertissement** de santé de flow signale les écrans **form** constitués **uniquement** d’un composant `address_step` sans `config_json.builder_preset == "address_step"` (heuristique « probable preset adresse »).

Côté **observabilité**, l’app mobile n’expose pas encore de couche analytics dédiée ; les journaux structurés **`arquantix.address_lookup`** et les événements **`registration.fields.submitted`** (résumé des sources d’adresse) couvrent une partie du besoin. Des types d’événements registration optionnels sont documentés dans `execution_events.py` pour une implémentation ultérieure.

---

## Current submit validation analysis

### Ordre d’exécution (runtime)

Dans `RegistrationService.submit_screen` (`api/services/registration/service.py`) :

1. Champs requis (`_validate_required_fields`).
2. **`validate_jurisdiction_policies_on_submit`** (téléphone, nationalité, résidence par `policy_scope`, puis **nouvelle** passe composites adresse).
3. Persistance `RegistrationSessionData` + émission `registration.fields.submitted` / `registration.screen.submitted`.
4. **`validate_screen_answers`** (formats, contraintes légères).
5. Navigation (`next_screen`).

Conséquence : une valeur pays **invalide au sens politique** est rejetée **avant** écriture en base ; un format pays **non ISO2** peut encore passer la passe juridiction (longueur ≠ 2 ignorée dans la passe composite) puis être rejeté à l’étape **`validate_screen_answers`** — les données n’atteignent pas l’état « validé et avancé » sans passer cette dernière étape (sinon erreur et log `registration.validation.failed`).

### Avant hardening

| Couche | `country_picker` + `policy_scope: residence` | `address_step` / `address_autocomplete` |
|--------|-----------------------------------------------|----------------------------------------|
| `validate_jurisdiction_policies_on_submit` | Contrôle `is_residence_country_allowed` | **Aucun** (scope `none`, slug pays pas le `binding_slug` du composant) |
| `validate_screen_answers` | Selon `component_type` | Pays **exclu** de toute validation de format |

### Après hardening

- **`jurisdiction_policy_submit.py`** : fonction `_validate_residence_for_address_composite_components` — même message d’erreur métier `[RESIDENCE_COUNTRY_NOT_ALLOWED]` que pour le picker.
- **`validators.py`** : `validate_country_iso2_value` — chaîne non vide = exactement **2 lettres** `[A-Za-z]{2}` (casse libre en entrée, normalisation métier ailleurs en majuscules).

### Compatibilité

- Les clients qui envoient déjà **ISO2** (`FR`, `AE`) : **aucun changement** de contrat.
- Valeurs non conformes (ex. `FRA`, `999`) : **rejet** explicite à `validate_screen_answers` (nouveau comportement **plus strict**, attendu pour la robustesse réglementaire et la cohérence avec la politique résidence).

---

## Admin governance analysis

### Détection implémentée

Dans `check_flow_health` → `_check_components` (`api/services/registration/governance.py`) :

- Si `effective_screen_type(screen) == "form"`.
- Si l’écran contient **exactement un** composant et que ce composant est de type **`address_step`**.
- Si `config_json.builder_preset` ≠ **`address_step`** (ou config absente / non-objet).

→ **Warning** `category: builder_preset` invitant à utiliser le flux **+ Address** du builder pour aligner la configuration et les outils admin.

### Limites (volontairement conservatrices)

- Pas d’avertissement si l’écran mélange `address_step` avec d’autres composants (risque de faux positifs).
- Pas de badge UI dans ce livrable (seulement **health API** / rapports de gouvernance) ; l’extension admin « badge » reste un chantier UX léger.

---

## Product observability recommendations

### Déjà en place

| Signal | Emplacement | Contenu utile |
|--------|-------------|----------------|
| Autocomplete / details HTTP | `api/services/address/observability.py` | `address_autocomplete`, `address_details` (statut, compteurs, **pas** de PII) |
| 429 adresse | `runtime_router` / rate limiter adresse | Logs / métriques infra |
| Sources à la soumission | `registration_address_submit_payload` + payload `registration.fields.submitted` | `address_sources_summary` (`google_places`, `manual`, `hybrid`, `user_input`), `address_hybrid_or_override` |
| Échec validation post-persistance | `registration.validation.failed` | `reason`, `errors[]` par slug |

### Manques côté client (Flutter)

Le module mobile **ne référence pas** aujourd’hui d’SDK analytics type Firebase Analytics / Segment. Les traces utiles (`_addressStepLog`) sont limitées au **`kDebugMode`**.

**Événements recommandés** (à brancher sur la stack produit choisie) :

1. **`address_autocomplete_used`** — au moins une sélection issue des prédictions Places sur l’écran.
2. **`address_manual_fallback`** — saisie sans sélection Places (ou bascule explicite « manuel seul » si applicable).
3. **`address_hybrid`** — champs modifiés après une sélection Places ou `__reg_address_override__` (aligné sur le résumé backend).
4. **`address_details_failed`** — échec `addressDetails` (code HTTP, **sans** `place_id` en clair).
5. **`address_rate_limited`** — réponse **429** sur autocomplete ou details.
6. **`address_screen_abandon`** — sortie du flow depuis l’écran courant **sans** submit réussi (définition produit : timeout session, retour arrière hors stack, fermeture app — à cadrer avec le PM).

### Taxonomie API (documentation)

Des entrées **optionnelles** ont été ajoutées en commentaire dans `api/services/registration/execution_events.py` pour homogénéiser les noms si l’équipe souhaite **émettre** ces événements via `safe_log_registration_event` à partir du client (via une future API « telemetry ») ou du serveur.

---

## Suggested changes

| Priorité | Changement | Statut |
|----------|------------|--------|
| P0 | Passe résidence pour `address_step` + `address_autocomplete` au submit | **Fait** (`jurisdiction_policy_submit.py`) |
| P1 | Validation ISO2 stricte du slug pays sur composites | **Fait** (`validators.py`) |
| P2 | Warning gouvernance « preset adresse » | **Fait** (`governance.py`) |
| P3 | Tests de non-régression résidence + format | **Fait** (`test_registration_jurisdiction_country_policies.py`) |
| P4 | Instrumentation Flutter + émissions registration dédiées | **À faire** (pas de stack analytics identifiée) |
| P5 | Réordonner validate_screen_answers **avant** persistance | **Hors scope** (refactor comportement API ; à étudier séparément) |

---

## Remaining risks

1. **Ordre validation / persistance** : la juridiction s’exécute avant `validate_screen_answers` mais les données sont **écrites** avant cette dernière validation. Un échec de format laisse théoriquement des lignes `RegistrationSessionData` incohérentes jusqu’à correction — comportement **pré-existant**, non aggravé par ce hardening.
2. **Heuristique admin** : seuls les écrans « un seul `address_step` » sont signalés ; les configurations atypiques restent hors radar.
3. **Pays non-alpha** : la regex exige des **lettres** ; si un jour un binding devait accepter un code non standard, il faudrait assouplir ou distinguer par juridiction.
4. **Doublon pays** : deux composants liant le même slug pays sur un même écran restent une anomalie de modélisation (warning **duplicate binding_slug** existant).

---

## Références code (principales)

- `api/services/registration/jurisdiction_policy_submit.py` — passe résidence composites.
- `api/services/registration/validators.py` — `validate_country_iso2_value`.
- `api/services/registration/governance.py` — warning `builder_preset`.
- `api/services/registration/address_autocomplete.py` — résolution des slugs.
- `api/services/address/observability.py` — logs autocomplete/details.
- `api/services/registration/execution_events.py` — taxonomie + extension documentaire adresse.
