# Country of residence → Home address : handoff & titres

## Executive summary

Deux correctifs ont été appliqués sur le flux d’inscription mobile :

1. **Transmission du pays** : `_formData` est désormais hydraté à partir de **tout** `collected_data` de session, puis enrichi avec les défauts des composants de l’écran courant. Auparavant, seuls les slugs correspondant au `binding_slug` des composants **de l’écran affiché** étaient recopiés depuis `collected_data`, ce qui excluait `country_of_residence` sur l’écran `address_step` (dont le `binding_slug` principal est typiquement `address_line_1`).

2. **Titres dupliqués** : lorsque l’écran affiche déjà un titre **ou** un sous-titre (`RegistrationFlowScreen`), le composant `address_step` **ne réaffiche plus** son bloc titre / sous-titre interne (`embedTitleAndSubtitle: false`). La source visuelle unique est l’en-tête d’écran.

## Root cause of country handoff issue

Dans `RegistrationFlowScreen._applySessionData`, la reconstruction de `_formData` faisait :

- pour chaque composant du **screen courant** avec un `binding_slug` non nul,
- copier `collected_data[slug]` **uniquement si** cette clé existait.

Sur l’écran Home address, la liste des composants ne contient en général que `address_step` avec `binding_slug: address_line_1`. La clé `country_of_residence` n’était donc **jamais** recopiée depuis `collected_data`, même si le backend l’avait bien persistée après le submit de l’écran Country.

Résultat : `RegistrationAddressStep` lisait `formData['country_of_residence']` vide → bannière « Country of residence should be set on the previous step ».

## Fix applied

- Nouveau module `registration_form_hydration.dart` avec `hydrateRegistrationFormData(RegistrationSessionState state)` :
  - base = copie complète de `state.collectedData` ;
  - puis application des mêmes règles de défaut que précédemment pour `country_picker` et `phone_input` sur les composants de l’écran courant.
- `_applySessionData` appelle cette fonction à la place de l’ancienne double boucle limitée aux seuls `binding_slug` du screen.

Aucun changement requis sur le submit : le backend continuait déjà à stocker `country_of_residence` dans `collected_data` ; c’est uniquement la **réhydratation client** qui était incomplète.

## Title/subtitle deduplication strategy

- **Règle** : un seul couple titre / sous-titre visible sur l’écran Home address.
- **Choix produit** : l’en-tête structurant reste celui du **screen** (`title` / `subtitle` renvoyés par l’API et rendus par `RegistrationFlowScreen` via `AppPageTitle` + `Text`).
- **Implémentation** : `RegistrationFlowScreen` calcule `screenProvidesPageHeading` (titre non vide **ou** sous-titre non vide) et le passe à `RegistrationFlowRenderer` (`screenProvidesPageHeading`). Pour `address_step`, le renderer instancie `RegistrationAddressStep(..., embedTitleAndSubtitle: !screenProvidesPageHeading)`.
- **Cas limites** :
  - Écran sans titre ni sous-titre : le widget `address_step` garde ses textes embarqués (`embedTitleAndSubtitle` reste `true`).
  - Écran avec seulement un sous-titre : on supprime aussi le bloc embarqué pour éviter deux descriptions (même logique « heading copy »).

## Files modified

| Fichier | Changement |
|---------|------------|
| `mobile/lib/features/registration/data/registration_form_hydration.dart` | **Nouveau** — hydratation `_formData` |
| `mobile/lib/features/registration/screens/registration_flow_screen.dart` | Utilise `hydrateRegistrationFormData`, passe `screenProvidesPageHeading` au renderer |
| `mobile/lib/features/registration/widgets/registration_flow_renderer.dart` | Paramètre `screenProvidesPageHeading`, transmission à `RegistrationAddressStep` |
| `mobile/lib/features/registration/widgets/registration_address_step.dart` | Paramètre `embedTitleAndSubtitle` (défaut `true`) |
| `mobile/test/registration/registration_form_hydration_test.dart` | **Nouveau** — tests handoff pays |
| `mobile/test/registration/registration_address_step_test.dart` | Test masquage titre embarqué |

## Manual test checklist

1. Flow avec écran **Country** puis **Home address** (titres renseignés côté admin sur les deux écrans).
2. Choisir un pays → Continuer → vérifier : **pas** de bannière pays manquant ; recherche d’adresse disponible.
3. Vérifier visuellement : **un seul** grand titre et **une seule** description sur Home address (pas de répétition du bloc titre du widget).
4. (Optionnel) Écran adresse sans titre d’écran dans l’admin : le titre / sous-titre du composant `address_step` doivent réapparaître.

## Remaining risks

- **Données sensibles / volume** : `_formData` contient désormais toutes les clés de `collected_data`. C’est cohérent avec un parcours multi-écrans ; si le backend renvoie des champs très larges, ils restent en mémoire côté client (comportement analogue à « session complète »).
- **Titres vides côté admin** : si l’écran Home address n’a ni titre ni sous-titre mais le composant en a, seul le composant les affiche — à documenter pour les éditeurs de flow.
- **Autres composites** : tout champ requis sur un écran B mais collecté sur un écran A avec un slug absent des `binding_slug` du screen B bénéficie du même mécanisme (merge global de `collected_data`).
