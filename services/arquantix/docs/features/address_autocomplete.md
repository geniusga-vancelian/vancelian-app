# Smart Address Input (Google Places)

## Objectif

Aider l’utilisateur à saisir une adresse postale dans le **Registration Flow Engine** avec une barre de recherche type Revolut, tout en conservant les **slugs existants** (`address_line_1`, `postal_code`, `city`, `country_of_residence`) et la projection vers `persons.profile_json["collected"]`.

Google Places est une **aide à la saisie uniquement** : ce n’est pas une preuve légale ni une source KYC « verified ».

## UX

1. Champ principal « Search address » (debounce 300 ms).
2. Liste de suggestions (proxy `/api/address/autocomplete`).
3. Sélection → détails (`/api/address/details`) → remplissage des champs rue, code postal, ville, pays.
4. **AppCountryPicker** pour le pays (allowlist juridictionnelle inchangée côté backend au submit).
5. Édition manuelle toujours possible sur chaque champ.
6. Bouton **« My address is not listed »** : masque la recherche, mode 100 % manuel (`source: manual`).
7. Après auto-fill, si l’utilisateur modifie un champ → `hybrid` pour ce slug (côté client, envoyé dans `__reg_address_sources__`).

### Hardening UX (mobile)

- **429** : message avec délai approximatif si `retry_after` est fourni.
- **Pays hors allowlist** (`address_country_mismatch`) : message invitant à choisir une autre suggestion ou la saisie manuelle.
- **Aucun résultat** : hint sous la recherche + rappel du fallback manuel.
- **Réponse Google partielle** : `field_warnings` / `incomplete` → message invitant à vérifier CP et ville.

## Mapping Google → slugs

| Réponse normalisée API | Slug session / profil |
|------------------------|------------------------|
| `address_line_1` (numéro + rue) | `binding_slugs.street` (défaut `address_line_1`) |
| `postal_code` | `postal_code` |
| `city` (locality / fallbacks) | `city` |
| `country` (ISO2) | `country_of_residence` |

Configurable via `props_json.binding_slugs` sur le composant admin.

## `allowed_countries` (props_json)

- Tableau d’objets `{ "iso2": "FR", "label_en": "…", "label_fr": "…" }` (même forme que pour **AppCountryPicker**).
- **Flutter** : envoie `allowed_countries=FR,DE,…` (max 25 ISO2) sur autocomplete + details ; biais `region` = seul pays si la liste ne contient qu’un code.
- **Backend** : construit le filtre Google `components=country:XX|country:YY` (jusqu’à 5 pays côté Google). Au **details**, si le pays normalisé n’est pas dans la liste → **422** `address_country_mismatch` (défense en profondeur ; le submit reste soumis aux règles juridictionnelles).
- Validation admin : `governance.validate_component_family` (liste ≤ 60 entrées, ISO2 valides).

## Traçabilité (`registration_session_data.source`)

Le client peut envoyer dans le body de `POST .../submit` :

- `__reg_address_sources__` : `{ "address_line_1": "google_places" | "manual" | "hybrid", ... }`
- `__reg_address_override__` : bool (informationnel ; non persisté comme slug)

Ces clés sont **retirées** avant persistance des slugs métier. Pour chaque slug, `source` est :

- une des valeurs ci-dessus si présente dans la map ;
- sinon `user_input` (comportement historique).

### Observabilité (sans PII)

- **HTTP** : logs `address_autocomplete` / `address_details` avec `client_bucket` (hash tronqué de l’IP), longueur de requête, nombre de prédictions, statut — **pas** de texte d’adresse ni `place_id` en clair.
- **Registration** : événement `FIELDS_SUBMITTED` enrichi si adresse concernée : `address_sources_summary` (compteurs google_places / manual / hybrid / user_input) et `address_hybrid_or_override`.

## Métadonnées optionnelles

Si `store_place_id: true` (défaut dans l’admin web pour ce composant), le client peut persister un JSON sous le slug `address_metadata` (field definition `address-metadata`, migration `104`).

### Hardening persistance

- Toute valeur **dict** pour le slug métadonnées est **bornée** (`ADDRESS_METADATA_MAX_BYTES`, défaut 8192 octets JSON). La clé `raw` est **supprimée** si le client l’envoie (le backend ne persiste plus le blob Google brut dans les métadonnées).
- Réponse **details** : par défaut **sans** champ `raw`. Pour debug local uniquement : `ADDRESS_DETAILS_INCLUDE_RAW=true`.

## Endpoints

| Méthode | Chemin | Rôle |
|---------|--------|------|
| GET | `/api/address/autocomplete?q=...&region=SG&allowed_countries=FR,DE` | Proxy Autocomplete |
| GET | `/api/address/details?place_id=...&allowed_countries=FR,DE` | Proxy Place Details |

- Clé : **`GOOGLE_MAPS_API_KEY`** (jamais exposée au mobile).

### Rate limiting

- **Autocomplete** et **details** ont des quotas **séparés** (fenêtre glissante 60 s par défaut).
- Variables : `ADDRESS_RL_AUTOCOMPLETE_MAX` (défaut **60**), `ADDRESS_RL_DETAILS_MAX` (défaut **30**), `ADDRESS_RL_WINDOW_SEC` (défaut **60**).
- Backend : `ADDRESS_RL_BACKEND=auto|redis|memory` — en **auto**, utilisation de **Redis** (`REDIS_URL`, `get_redis()`) si joignable, sinon **mémoire** (par processus).
- Réponse **429** standardisée :

```json
{
  "detail": {
    "error": {
      "code": "rate_limited",
      "message": "Too many address lookup requests. Please wait and try again.",
      "retry_after": 60
    }
  }
}
```

## Composant registration

- `component_type`: **`address_autocomplete`**
- `binding_slug` : doit correspondre au slug **rue** (ex. `address_line_1`).
- `props_json` typique :
  - `binding_slugs`: `{ street, postal, city, country }`
  - `store_place_id`, `metadata_slug`, `search_label`, `enable_manual_override`
  - **`allowed_countries`** (optionnel) : liste `{ iso2, label_en, label_fr }[]` — alignée picker + filtres Google.

## Contraintes KYC / compliance

- Les règles **`jurisdiction_policy_submit`** s’appliquent **au submit** comme pour un formulaire classique.
- Ne pas traiter les données Google comme vérifiées.

## Limitations

- API Google **Places legacy** (REST).
- Filtre **components** : jusqu’à **5** pays côté Google ; au-delà, tronquer côté API (les codes restants restent enforce au **details**).
- Rate limit **mémoire** : si Redis est indisponible, quotas **par worker** — activer Redis en prod multi-workers.

## Variables d’environnement

| Variable | Rôle |
|----------|------|
| `GOOGLE_MAPS_API_KEY` | Oblatoire pour 200 sur `/api/address/*` (sinon **503**) |
| `REDIS_URL` | Pool Redis partagé (rate limit auto + autres features) |
| `ADDRESS_RL_BACKEND` | `auto` / `redis` / `memory` |
| `ADDRESS_RL_AUTOCOMPLETE_MAX` | Max requêtes autocomplete / fenêtre / IP (ou clé Redis) |
| `ADDRESS_RL_DETAILS_MAX` | Idem details |
| `ADDRESS_RL_WINDOW_SEC` | Fenêtre glissante (secondes) |
| `ADDRESS_METADATA_MAX_BYTES` | Taille max JSON métadonnées adresse |
| `ADDRESS_DETAILS_INCLUDE_RAW` | `true` pour inclure `raw` dans la réponse details (debug) |

## Tests

**Backend**

```bash
cd services/arquantix/api
python3 -m pytest tests/test_address_routes.py tests/test_address_google_places.py -q
```

**Flutter**

```bash
cd services/arquantix/mobile
flutter test test/registration/address_registration_api_errors_test.dart
flutter test test/registration/address_autocomplete_props_test.dart
```

## Tests manuels

1. Sans clé : autocomplete → 503.
2. Avec clé : taper une adresse connue → suggestions → détails → champs remplis.
3. `allowed_countries` restreint : vérifier suggestions + 422 si lieu hors liste.
4. Saturation requêtes → 429 + message mobile.
5. « My address is not listed » → saisie manuelle → `source` `manual` en base.

## Variante `address_step`

Écran composite dédié (titre, sous-titre, ordre des champs type Revolut, `field_labels_i18n` / `field_placeholders_i18n`). Voir [address_step.md](./address_step.md).

## Considérations prod

- Activer **Redis** pour limiter globalement derrière plusieurs replicas.
- Ne pas activer `ADDRESS_DETAILS_INCLUDE_RAW` en prod.
- Surveiller les logs `address_autocomplete` / `address_details` (taux d’erreur upstream, 429).
- WAF / reverse proxy : limiter aussi `/api/address/*` par IP si besoin (couche additionnelle).
