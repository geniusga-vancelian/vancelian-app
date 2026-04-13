# Composant `address_step` (Registration Flow)

Écran composite **search-first** (type Revolut) : recherche d’adresse (Google Places proxy), suggestions, fallback manuel, champs postaux liés aux slugs métier existants.

## Schéma `props_json` recommandé (stable)

Les textes visibles doivent utiliser les clés **`*_i18n`** (objets `locale → string`, typiquement `en` et `fr`).

| Clé | Type | Description |
|-----|------|-------------|
| `title_i18n` | `Record<string, string>` | Titre principal dans le widget |
| `subtitle_i18n` | `Record<string, string>` | Sous-titre |
| `search_label_i18n` | `Record<string, string>` | Libellé au-dessus de la barre de recherche |
| `manual_entry_label_i18n` | `Record<string, string>` | Lien « adresse introuvable » |
| `field_labels_i18n` | `Record<fieldKey, string \| Record<locale, string>>` | Labels des champs (voir clés ci-dessous) |
| `field_placeholders_i18n` | idem | Texte d’aide sous les champs (équivalent « Eg: … » côté mobile) |
| `search_enabled` | `boolean` | Défaut `true` |
| `search_min_chars` | `int` | 1–20, défaut côté config `2` |
| `search_debounce_ms` | `int` | 50–5000 |
| `address_line_2_optional` | `boolean` | Défaut `true` |
| `binding_slugs` | `object` | Voir [Bindings](#bindings) |
| `allowed_countries` | `array` | Optionnel ; enrichi par la juridiction si absent |
| `metadata_slug` / `store_place_id` | | Identique à `address_autocomplete` (traçabilité Places) |

**Clés autorisées** pour `field_labels_i18n` et `field_placeholders_i18n` :

- `postal_code`
- `address_line_1`
- `address_line_2`
- `city`
- `country_of_residence`

Chaque entrée peut être :

- une **chaîne** (même texte pour toutes les locales après normalisation API), ou
- un **objet** `{ "en": "...", "fr": "..." }`.

### Exemple minimal

```json
{
  "required": true,
  "title_i18n": { "en": "Home address", "fr": "Adresse du domicile" },
  "subtitle_i18n": {
    "en": "Enter your address as on your ID.",
    "fr": "Indiquez votre adresse comme sur votre pièce d’identité."
  },
  "search_label_i18n": { "en": "Search address", "fr": "Rechercher une adresse" },
  "manual_entry_label_i18n": { "en": "My address is not here", "fr": "Mon adresse ne figure pas ici" },
  "field_labels_i18n": {
    "postal_code": { "en": "Postal code", "fr": "Code postal" },
    "address_line_1": { "en": "Street, building", "fr": "Rue, bâtiment" },
    "address_line_2": { "en": "Floor, unit", "fr": "Étage, appartement" },
    "city": { "en": "City", "fr": "Ville" },
    "country_of_residence": { "en": "Country of residence", "fr": "Pays de résidence" }
  },
  "field_placeholders_i18n": {
    "postal_code": { "en": "e.g. 75001", "fr": "ex. 75001" },
    "address_line_1": { "en": "e.g. 10 Downing Street", "fr": "ex. 10 rue de Rivoli" },
    "address_line_2": { "en": "e.g. Apt 4B", "fr": "ex. Appartement 4B" },
    "city": { "en": "e.g. Paris", "fr": "ex. Paris" },
    "country_of_residence": { "en": "", "fr": "" }
  },
  "binding_slugs": {
    "postal_code": "postal_code",
    "address_line_1": "address_line_1",
    "address_line_2": "address_line_2",
    "city": "city",
    "country_of_residence": "country_of_residence"
  },
  "store_place_id": true,
  "metadata_slug": "address_metadata"
}
```

### Bindings

- **`binding_slug` du composant** (field catalog) = **`address_line_1`** (slug primaire, comme `street` pour `address_autocomplete`).

## Compatibilité ascendante (legacy)

Les anciennes configs peuvent encore définir uniquement des **chaînes plates** :

- `title`
- `subtitle`
- `search_label`
- `manual_entry_label`

Comportement :

1. **Validation (gouvernance)** : ces clés restent **optionnelles** ; si présentes, elles doivent être des **strings**.
2. **Normalisation API** (`normalize_address_step_props`, appliquée à l’enrichissement session côté `address_step`) : les chaînes legacy sont **fusionnées** dans les maps `*_i18n` pour les locales manquantes (`en`, puis `fr`).
3. **Admin Web** : à l’enregistrement, les `*_i18n` nettoyés sont écrits **et** des alias legacy (`title`, `search_label`, …) sont remplis avec une valeur de repli (priorité `en` → `fr`) pour les consommateurs qui ne lisent que les anciennes clés.
4. **Flutter** : résolution dans l’ordre **`…_i18n` (locale)** → **clé legacy string** → **libellé par défaut** dans le code.

Les flows déjà publiés avec seulement `title` / `subtitle` / … continuent donc d’afficher correctement le texte, tout en pouvant être migrés progressivement vers `*_i18n`.

## Validation stricte (API)

`validate_address_step_props_json` (appelé depuis `governance.validate_component_family`) impose :

- si `title_i18n` (ou les autres `*_i18n` listés) est présent → objet dont les clés sont des codes langue 2 lettres et les valeurs des chaînes ;
- `field_labels_i18n` / `field_placeholders_i18n` : clés de champ autorisées uniquement ; valeur = string ou objet locale → string.

## Prévisualisation admin

Dans l’éditeur de flow (`web/src/app/admin/registration/flows/[id]/edit/page.tsx`), un bloc **Aperçu mobile (statique)** apparaît sous la configuration `address_step` : rendu sans réseau, chaîne i18n `navigateur → en → fr`, prise en compte de `search_enabled` et `address_line_2_optional`.

## Fichiers de référence

- Schéma + normalisation : `api/services/registration/address_step_props.py`
- Gouvernance : `api/services/registration/governance.py`
- Enrichissement session : `api/services/registration/jurisdiction_policies.py` (`normalize_address_step_props`)
- Mobile : `mobile/lib/features/registration/widgets/registration_address_step.dart`
- Admin : `web/src/app/admin/registration/flows/[id]/edit/page.tsx`

## Tests manuels suggérés

1. Nouveau composant `address_step` depuis l’admin : vérifier préremplissage EN/FR, enregistrement, rechargement de l’éditeur.
2. Flow existant avec **seulement** `title` / `subtitle` (sans `*_i18n`) : session mobile → textes corrects après enrichissement.
3. Modifier uniquement le français dans `title_i18n` : app en français affiche le bon titre ; legacy `title` côté JSON reste cohérent si ré-enregistré depuis l’admin.
4. `field_placeholders_i18n` : texte d’aide visible sous les `AppTextInput` ; pays sans placeholder ne montre rien.
5. Santé du flow / publish : aucune erreur de validation sur un `props_json` conforme.

## Voir aussi

- [address_autocomplete.md](./address_autocomplete.md) — variante champs + recherche intégrée (slugs `street` / `postal` / …).
