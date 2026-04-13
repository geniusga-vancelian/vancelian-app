# Audit : pays de résidence vs Google Places (recherche d’adresse)

## Executive summary

Le message **« Address search is not available for this country »** peut apparaître alors que l’utilisateur a correctement choisi un pays sur l’écran **Country of residence**, pour **deux causes principales** identifiées dans le code :

1. **Backend — troncature silencieuse de `allowed_countries`** : `_parse_allowed_countries_param` ne conservait que les **5 premiers** codes ISO2 de la chaîne requête. Le client envoie souvent une liste **triée** (ex. union de pays UE). Un pays comme **FR** peut se retrouver **au-delà de la 5ᵉ position** ; il disparaît alors de la liste parsée. La route `/api/address/autocomplete` exige ensuite que `country` soit **membre** de cette liste tronquée → **422 `country_not_in_allowed_list`**, alors que `country=FR` est valide.

2. **Contrat client / serveur — incohérence `country` vs `allowed_countries`** : le backend rejetait si `country` n’était pas inclus dans `allowed_countries`. Les props du step `address_step` peuvent exposer une allowlist **héritée ou plus étroite** que les options réellement proposées à l’étape `country_picker` (ou une liste triée longue + troncature côté serveur). Le Flutter bloquait aussi l’UI si le pays parsé n’était pas dans `allowed_countries`, ce qui doublait le risque de faux négatifs.

Les correctifs appliqués : **ne plus tronquer** la liste lors du parse (la limite Google « 5 pays » ne concerne que l’appel Places ; la route force déjà `countries = [country_iso]` pour l’autocomplete), **fusion explicite** du pays de résidence dans l’allowlist côté Flutter pour les requêtes, **assouplissement** de la validation serveur (le paramètre `country` est la source de vérité pour le périmètre Places), et **alignement UX** (recherche affichée dès qu’un ISO2 valide est présent dans `formData`).

---

## Current country data flow

### Flutter (registration)

1. **Écran précédent** : l’utilisateur renseigne `country_of_residence` (souvent ISO2 ou objet avec `iso2`) dans `formData` / session.
2. **`RegistrationAddressStep`** (`registration_address_step.dart`) :
   - Lit le slug via `binding_slugs.country_of_residence` (défaut `country_of_residence`).
   - **`parseIso2CountryCode(formData[slug])`** → `_parsedResidenceIso2`.
   - Lit **`allowed_countries`** depuis `comp.props` → `allowedIso2CodesFromProps` (liste ISO2 triée, cap 25 côté client).
   - **Avant correctif** : `_residenceAllowedForPlacesApi` exigeait `allowed.isEmpty || allowed.contains(p)` ; sinon pas de section recherche et message « pays non disponible ».
   - **Modale** (`address_search_modal.dart`) : appelle `addressAutocomplete` avec `countryIso2: residenceIso2` et `allowedCountriesIso2` dérivé des props (sans fusion résidence avant correctif).
3. **`RegistrationApi`** : query `country` + optionnel `allowed_countries=XX,YY,...`.

### Backend

1. **`GET /api/address/autocomplete`** et **`GET /api/address/details`** (`services/address/routes.py`) :
   - Parse `allowed_countries` → liste ISO2.
   - Parse `country` → ISO2 unique.
   - **Avant correctif** : si `country` et liste non vide et `country not in liste` → **422** ; liste **tronquée à 5** à la parse → faux « not in list ».
   - Puis pour autocomplete : `countries = [country_iso]` passé à Google (un seul pays).

---

## Expected vs actual country value

| Étape | Attendu | Problème observé (avant fix) |
|--------|---------|-------------------------------|
| Session / `formData` | ISO2 du pays choisi (ex. `FR`) | Parfois correct mais API quand même en erreur si allowlist tronquée ou disjointe |
| Parse ISO2 | `FR` depuis string ou `{iso2: FR}` | OK si données cohérentes |
| Query autocomplete | `country=FR` + allowlist cohérente | `country=FR` mais allowlist parsée sans `FR` (troncature) → 422 |
| Garde-fou Flutter | Ne pas bloquer si le pays est celui choisi en amont | Blocage si `FR ∉ allowed_countries` du step |

---

## Flutter findings

- **`parseIso2CountryCode`** (`address_autocomplete_field.dart`) : comportement sain pour string 2 lettres ou map avec `iso2`.
- **`allowedIso2CodesFromProps`** : normalise en ISO2 majuscules ; **tri + cap 25** — le cap peut théoriquement retirer un pays en queue, mais le scénario le plus fréquent du 422 venait du **serveur (5 codes)**.
- **`_residenceAllowedForPlacesApi`** : couplage trop fort avec `allowed_countries` du **même** step que la recherche, sans garantie d’alignement avec le picker amont.
- **`address_search_modal`** : n’injectait pas le pays de résidence dans `allowed_countries` avant l’appel (incohérence possible avec le backend).
- **`_selectPrediction` / `addressDetails`** : utilisait déjà `countryIso2: residence` et une allowlist réduite à `[residence]` dans certains cas — meilleure cohérence que l’autocomplete avant correctif.

---

## Backend findings

- **`_parse_allowed_countries_param`** : **`return out[:5]`** était la cause directe de **rejets erronés** pour des listes longues triées (ex. `AT,BE,BG,HR,CY,...` sans `FR` dans les 5 premiers alors que `country=FR`).
- **Validation `country not in countries`** : légitime pour détecter des clients incohérents, mais **redondante** une fois que `country` est la contrainte Places finale ; avec troncature, elle devenait **toxique**.
- **`google_places_service._components_param`** : limite à 5 pays pour l’API Google — à appliquer **au moment du call Places**, pas au parse HTTP.

---

## Root cause hypothesis (confirmée)

1. **Principale** : troncature à **5** codes dans `_parse_allowed_countries_param`, combinée à une liste `allowed_countries` **triée** et longue → le **pays de résidence** peut être absent de la liste effective → **422 `country_not_in_allowed_list`** malgré un `country` correct.

2. **Secondaire** : allowlist du composant `address_step` **non alignée** avec le pays réellement sélectionné + validation stricte côté Flutter et serveur sans **fusion** avec le `country` demandé.

---

## Recommended fix plan (implémenté)

1. **Backend** : supprimer la troncature `[:5]` dans `_parse_allowed_countries_param` ; pour `/autocomplete` et `/details`, si `country` est fourni, **ne plus renvoyer 422** lorsque `country` manque dans `allowed_countries` — **fusionner** `country` dans l’ensemble logique puis continuer avec `countries = [country_iso]` pour Places / validation details.

2. **Flutter** : introduire **`allowedCountriesForPlacesQuery`** (union allowlist step + résidence) ; l’utiliser dans la modale, le step adresse (details), et idéalement `AddressAutocompleteField`.

3. **UX** : afficher la recherche dès **ISO2 résidence valide** + `search_enabled` ; retirer le message « non disponible pour ce pays » basé sur la seule allowlist du step ; retirer le **label dupliqué** au-dessus du trigger ; style **actif** pour le trigger et le champ modale.

4. **Tests** : mettre à jour les tests API et widget pour refléter la fusion et l’absence de faux 422 ; ajouter un cas « liste longue + country au-delà de l’ancienne coupure à 5 ».

---

## Fichiers touchés (référence)

- Rapport : `docs/audits/address_country_search_bug_audit.md` (racine monorepo)
- Backend : `services/arquantix/api/services/address/routes.py`, `services/arquantix/api/tests/test_address_routes.py`
- Flutter : `mobile/lib/features/registration/widgets/address_autocomplete_field.dart`, `registration_address_step.dart`, `address_search_modal.dart`, tests `mobile/test/registration/registration_address_step_test.dart`, `address_autocomplete_props_test.dart`
