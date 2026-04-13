# Séparation pays de résidence / adresse du domicile (registration)

## Résumé du parcours

1. **Country of residence** — écran dédié (preset admin **+ Country** ou composant `country_picker` sur un écran précédent), binding typique `country_of_residence`. La valeur est stockée dans la session / `formData` avant l’étape adresse.
2. **Home address** — écran avec un seul composant `address_step` : titre, sous-titre, recherche d’adresse (modale), saisie manuelle éventuelle, puis champs rue / complément / code postal / ville. **Aucun sélecteur pays** à l’écran.
3. La recherche Places utilise l’ISO2 déjà présent dans `formData` pour `binding_slugs.country_of_residence`. Après autofill, le slug pays est **réaligné sur la session** (pas sur le libellé Google seul).
4. Si le pays est absent au moment d’afficher `address_step`, une **bannière** explique que l’étape précédente doit fournir le pays (pas de picker sur cet écran).

## Fichiers modifiés

| Zone | Fichier |
|------|---------|
| Flutter | `mobile/lib/features/registration/widgets/registration_address_step.dart` |
| Flutter | `mobile/lib/features/registration/widgets/registration_flow_renderer.dart` (commentaire) |
| Tests | `mobile/test/registration/registration_address_step_test.dart` |
| Admin | `web/src/app/admin/registration/flows/[id]/edit/page.tsx` |

## Impacts

### Flutter

- Suppression de `AppCountryPicker` et des helpers d’édition pays dans `RegistrationAddressStep`.
- Conservation de `binding_slugs.country_of_residence` pour API, sources, override, surface `__reg_address_step_surface__`, validation `_allRequiredFilled` dans `registration_flow_screen.dart` (inchangé : le pays doit toujours être présent dans `formData` pour activer le CTA).
- `country_picker` reste rendu par `RegistrationFlowRenderer` sur **d’autres** écrans.

### Admin web

- Preset **+ Country** : écran `builder_preset: country_of_residence` + composant `country_picker` (`country_of_residence`).
- Preset **+ Address** : titres d’écran « Home address » / « Adresse du domicile » ; i18n des champs **sans** ligne pays dans le formulaire d’édition.
- Avertissement si le **même écran** contient `address_step` et un `country_picker` sur `country_of_residence`.
- Aperçu statique : note « pays à l’écran précédent », plus de ligne pays dans la liste des champs.

### Backend

- **Aucun changement** de contrat submit : `country_of_residence` reste un champ de session comme avant. Filtres autocomplete / details / allowlist inchangés côté API existante.

## Tests manuels suggérés

- Flux neuf : **+ Country** puis **+ Address**, ordre des étapes ; vérifier recherche dès l’ouverture de Home address (sans clavier sur le trigger, comme avant).
- Autofill : pays en base = pays choisi à l’étape 1 même si Google renvoie un libellé différent (tant que la validation métier passe).
- Retour arrière après changement de pays : réinitialisation des lignes d’adresse (comportement `didUpdateWidget` conservé).
- Flow legacy **sans** écran pays en amont : bannière jaune, CTA bloqué tant que `country_of_residence` est vide.
- Admin : ouverture d’un `address_step` sur un écran qui contient encore un `country_picker` → bandeau ambre.

## Risques restants

- **Flows existants** avec pays + adresse sur le **même** écran : l’app n’affiche plus le pays sur `address_step` → l’utilisateur peut être bloqué tant que l’admin n’a pas ajouté un écran pays en amont ou retiré l’adresse de cet écran.
- **Catalogue champs** : le preset **+ Country** exige une définition `country_of_residence` (comme **+ Address** exige `address_line_1`).
- Les anciennes clés i18n `field_labels_i18n.country_of_residence` dans le JSON persisté sont **ignorées** à l’édition (plus de champ admin) ; elles peuvent rester en base sans effet côté app.
