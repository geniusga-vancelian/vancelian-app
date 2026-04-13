# Financial profile — refactor UI & flow (onboarding guidé)

## Contexte

Passage à une présentation type **onboarding guidé** (références Revolut / Mobbin) : listes **directement visibles**, **module blanc unique** par écran de choix, **suppression des libellés de champ redondants** sous le titre d’écran, et **séparation secteur / détails professionnels**.

## Modifications Flutter

### Composants (`lib/core/ui/`)

- **`SelectableSingleList`**  
  - Mode **`encapsulateInCard: true`** (défaut) : un **bloc blanc** (coins 16, ombre légère), **séparateurs** entre les lignes, ligne sélectionnée en **teinte indigo** légère.  
  - **À droite** : `chevron_right` si non sélectionné, **check** si sélectionné (aligné référence « income »).  
  - Mode `encapsulateInCard: false` : ancien rendu par carte séparée (secours).

- **`SelectableMultiList`**  
  - Même **module blanc** et séparateurs.  
  - **À droite** : icônes `check_box_rounded` / `check_box_outline_blank_rounded`, couleur cohérente avec le single-select.

### Données (`registration_models.dart`)

- **`RegistrationComponent.hideInlineLabel`** : `props['hide_inline_label'] == true` — permet de **ne pas afficher** le petit titre « Employment status * », « Sources * », etc. lorsque le **titre d’écran** suffit.

### Renderer (`registration_flow_renderer.dart`)

- Pour `select` et `multi_select` : le libellé au-dessus de la liste n’est affiché que si **`!comp.hideInlineLabel`**.  
- Passage à **`encapsulateInCard: true`** sur les deux listes.

### Comportement inchangé

- Valeurs soumises (`binding_slug`, `value` des options) **identiques**.  
- Validation `Continue` / `_allRequiredFilled` **inchangée**.

## Modifications backend (Alembic `125`)

**Fichier :** `api/alembic/versions/125_financial_profile_work_sector_split_ui.py`

### Nouvel écran `work_sector_form`

- **Position** : `1` dans le module `financial_profile` (entre `employment_status_form` et `work_details_form`).  
- **Titres** : `What sector do you work in?` / `Choose the industry that best matches your role.`  
- **`visibility_rule_json`** : copié depuis `work_details_form` (même visibilité : **employed / self-employed** uniquement).  
- **Composant** : `select` / `work_sector`, `hide_inline_label: true`, options secteur inchangées (finance, technology, …).

### Écran `work_details_form`

- **Suppression** du composant `work_sector` (liste secteur).  
- **Sous-titre** : `Add your job title and employer or business name.`  
- Contenu réservé aux **champs texte** (job title, employeur / nom commercial selon règles de visibilité existantes).

### `hide_inline_label` sur les listes « financial »

Mise à jour `props_json` pour :

| `screen_key` | `binding_slug` |
|--------------|----------------|
| `employment_status_form` | `employment_status` |
| `annual_income_form` | `annual_income_range` |
| `net_worth_form` | `net_worth_range` |
| `source_of_wealth_form` | `source_of_wealth` |

### Ce qui n’a pas été modifié

- **Pas de changement** de `registration_progress.py` : `work_sector` reste requis pour le profil employé / indépendant avec la même logique (`_profile_work_details`).  
- **Pas de nouvelle clé d’étape** : `work_sector` reste un champ collecté ; seul l’**écran** est nouveau.  
- **Flux EU v4** : `step_key` du module toujours `financial_profile` ; ordre des **écrans** = `position` sur `registration_step_screens` (7 écrans après migration au lieu de 6).

### Ordre des écrans financial (après 125)

1. `employment_status_form`  
2. `work_sector_form` **(nouveau)**  
3. `work_details_form`  
4. `annual_income_form`  
5. `net_worth_form`  
6. `source_of_wealth_form`  
7. `financial_acknowledgements_form`  

À mettre à jour en commentaire dans le code si vous maintenez une liste manuelle (ex. `124` `FINANCIAL` — à étendre avec `work_sector_form` pour la doc).

## Supprimé / déprécié côté UX

- **Dropdown / bottom sheet** (déjà retirés dans un refactor précédent via `AppSelect` / `AppMultiDelete`).  
- **Libellés redondants** au-dessus des listes lorsque `hide_inline_label` est actif (contrôlé par CMS / migration).  
- **Liste secteur** sur l’écran « Where do you work? » — déplacée vers **Work sector**.

## Déploiement

1. Appliquer la migration : `alembic upgrade head` (API).  
2. Rebuild / lancer l’app Flutter sur le flux **EU v4** actif.  
3. Vérifier un parcours **employé** : Employment → **Sector** → **Work details** → Income → …

## Validations recommandées

- [ ] Aucun libellé du type « Employment status * » / « Sources * » sur les écrans concernés (après migration).  
- [ ] Module blanc visible sur Employment, Income, Net worth, Source of wealth, Work sector.  
- [ ] Parcours **étudiant** : pas d’écran secteur / détails pro (règles de visibilité inchangées).  
- [ ] Soumission et `registration_progress` cohérents après complétion.
