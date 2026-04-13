# Phone input — audit, validation métier, modale d’erreur

## Executive Summary

Le flux **téléphone inscription** s’appuie désormais sur une couche unique **`api/services/registration/phone_validation.py`** (libphonenumber / `phonenumbers`) : parse → possible → valide → **type SMS** (MOBILE ou FIXED_LINE_OR_MOBILE) → **policy juridiction** (indicatif autorisé + cohérence pays sélectionné). Les erreurs téléphone en **422** sur `POST .../submit` renvoient un **`detail` structuré** `{ code, message, field }` avec messages utilisateur en anglais (sans préfixe `[PHONE_*]`). **Flutter** affiche ces erreurs dans une **Modale** DS, sans texte d’erreur sous le champ ; le mapping utilisateur est dans **`registration_phone_user_errors.dart`**.

## Flutter Audit

### Chaîne `AppPhoneInput` → submit

- **Construction** : `normalizePhoneFieldToE164` (`core/phone_e164.dart`) concatène `dial_code` du pays choisi et les chiffres saisis ; supprime **un** `0` initial national ; si la saisie commence déjà par `+`, elle est renvoyée telle quelle.
- **Stockage** : `_formData[slug]` reçoit une chaîne **E.164** (ou `+…` brut) via `onPhoneChanged`.
- **Pays sélectionné** : `_formData['${slug}_country_code']` (ex. `phone_number_country_code`).
- **Liste pays** : `allowed_phone_countries` du backend est respectée dans le picker quand fournie.
- **Fragilités identifiées** :
  - Un seul `0` en tête est retiré ; cas marginaux multi-zéros non gérés par lib côté client (le **backend** re-parse avec libphonenumber).
  - Saisie `+` sans numéro complet peut produire des chaînes encore invalides : **corrigé côté API** par validation stricte.

### Root causes (UX message brut)

- Le backend renvoyait parfois **`[PHONE_COUNTRY_NOT_ALLOWED]`** pour une **simple erreur de parse** (`infer_iso2_from_e164` sur numéro non `+` ou invalide).
- **422 submit** utilisait `detail` **string**, que le client remettait dans les **erreurs inline** par champ.

## Backend Audit

### Avant

- **`jurisdiction_policy_submit`** : `infer_iso2_from_e164` exigeait `+` et `is_valid_number` ; échec → message **trompeur** « pays non autorisé ».
- **Aucun** filtre explicite **MOBILE / FIXED_LINE_OR_MOBILE** : une ligne fixe FR (+33 1…) pouvait passer si considérée valide selon le chemin.
- **`validators.py`** : regex large `PHONE_RE` sur `phone_input`, redondante et peu sémantique.
- **`interaction_helpers.normalize_to_e164`** : valide `is_valid_number` mais **pas** le type SMS ; message d’erreur obsolète (« leading 0 »).
- **`default_phone_region_from_session`** : utilisait `jurisdiction.code` comme région libphonenumber si 2 lettres → **`EU` invalide** pour `parse(..., "EU")`.

### Après (cible métier)

- **`phone_validation.validate_mobile_phone_basic`** : possible + valide + `number_type` ∈ { MOBILE, FIXED_LINE_OR_MOBILE } ; sinon `phone_number_not_mobile` ou `invalid_phone_number`.
- **`validate_mobile_phone_for_jurisdiction`** : en plus, si `enforce_jurisdiction_allowlist` : `is_phone_country_allowed` ; si `selected_country_iso2` renseigné : **cohérence** avec `region_code_for_number` → `phone_country_mismatch`.
- **Normalisation** : après succès, **`answers[slug]`** est remplacé par l’**E.164 canonique** en submit.
- **`phone_utils.normalize_to_e164`** : délègue à `phone_validation` (mêmes règles mobile).
- **`default_phone_region_iso2`** : `EU` → `FR`, `UAE` → `AE`, sinon code ISO2 à 2 lettres, défaut `FR`.

## Validation Rule Chosen

Un numéro est **accepté** pour l’OTP mobile si :

1. Parse libphonenumber réussi (avec région par défaut issue de la juridiction ou pays sélectionné pour les numéros nationaux).
2. `is_possible_number` **true**
3. `is_valid_number` **true**
4. `phonenumbers.number_type(n)` ∈ **{ MOBILE, FIXED_LINE_OR_MOBILE }**
5. Si policy téléphone active pour la juridiction : pays du numéro **autorisé** ; si `*_country_code` fourni : **égal** au pays déduit du numéro.

**Refus explicites** : FIXED_LINE seul, UNKNOWN, TOLL_FREE, PREMIUM_RATE, VOIP, PAGER, UAN, VOICEMAIL, etc. (tout ce qui n’est pas dans l’ensemble autorisé ci-dessus).

## Europe Coverage Notes

Tests unitaires **`test_registration_phone_validation.py`** : E.164 **mobile** acceptés pour **FR, DE, ES, IT, BE, NL, PT, IE, AE** ; ligne fixe FR **+33123456789** refusée (`phone_number_not_mobile`) ; national `0612345678` + région **FR** → `+33612345678`.

## Error Model (API)

| `code` | Usage |
|--------|--------|
| `invalid_phone_number` | Parse / possible / valide |
| `phone_number_not_mobile` | Type non compatible SMS |
| `unsupported_phone_country` | Policy juridiction (indicatif) |
| `phone_country_mismatch` | ISO2 sélectionné ≠ pays du numéro |

**422 submit** : `detail = { "code", "message", "field": "<binding_slug>" }` pour les erreurs téléphone structurées. Les erreurs **résidence / nationalité** conservent pour l’instant un `detail` **string** legacy.

## Modal UX Changes

- **`RegistrationFlowScreen._submitAndAdvance`** : si `errorCode` ∈ ensemble téléphone et `field` = slug `phone_input` courant → **`Modale.show`** avec titres / textes via **`RegistrationPhoneUserErrors`** ; **pas** de `_fieldErrors[slug]` pour ce cas → plus de ligne rouge de texte sous le champ.
- **`AppPhoneInput.showInlineError: false`** dans **`RegistrationFlowRenderer`** pour `phone_input` : même en cas d’erreur résiduelle, pas de sous-texte inline.
- **Debug panel** : inchangé — visible seulement si `RegistrationFlowScreen(showDebugPanel: true)` ; le launcher test utilise `kDebugMode`.

## Tests Added

- **Backend** : `tests/test_registration_phone_validation.py` (pays EU + AE, fixe FR, national FR).
- **Backend** : `test_phone_country_mismatch_fr_number_de_selected` dans `test_registration_jurisdiction_country_policies.py`.
- **Flutter** : `mobile/test/core/phone_e164_test.dart` (construction E.164 + `0` national).
- Tests existants **interaction SMS** / **jurisdiction** / **phase2c validation** mis à jour (messages, `unsupported_phone_country`).

## Remaining Gaps / Next Steps

- **422 non structuré** (ex. `Validation failed: slug: …` pour email) : toujours bannière / parsing `fieldErrors` ; pas de modale unifiée.
- **i18n** : textes modale actuellement **EN** dans `RegistrationPhoneUserErrors` ; brancher sur `AppLocalizations` si disponible.
- **Écran interaction SMS** : erreurs `prepare` / OTP peuvent encore utiliser d’autres canaux UI ; hors périmètre « champ téléphone formulaire » de ce rapport.
- **Couverture widget** : pas de test d’intégration Flutter de la modale (nécessite mock API).

## Exemples concrets

| Cas | Résultat |
|-----|----------|
| FR mobile `+33612345678`, juridiction EU, policy OK | OK → E.164 stocké |
| FR fixe `+33123456789` | `phone_number_not_mobile` |
| AE mobile en juridiction EU (tests JTEST) | `unsupported_phone_country` |
| Numéro FR avec pays sélectionné **DE** | `phone_country_mismatch` |
| Saisie `abc` | `invalid_phone_number` |

## Fichiers principaux modifiés / ajoutés

- `api/services/registration/phone_validation.py` (**nouveau**)
- `api/services/registration/phone_utils.py`, `jurisdiction_policy_submit.py`, `interaction_helpers.py`, `validators.py`, `jurisdiction_policies.py`, `service.py` (`ValidationError`), `runtime_router.py` (submit)
- `mobile/lib/features/registration/registration_phone_user_errors.dart` (**nouveau**)
- `mobile/lib/features/registration/data/registration_api.dart`, `registration_flow_screen.dart`, `registration_flow_renderer.dart`, `app_phone_input.dart`
