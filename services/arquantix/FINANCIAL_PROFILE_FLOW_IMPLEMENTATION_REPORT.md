# Financial Profile (Wealth & Employment) — implémentation

## Executive summary

Un **module `financial_profile`** a été ajouté **après** le bloc fondation EU existant (identity → … → **terms**), sous forme de **flux EU v3** en base. Les écrans utilisent **uniquement** les `component_type` déjà supportés (`select`, `text_input`, `multi_select`, `checkbox`). La **modale de succès** finale n’est **pas** un nouvel écran : le signal est porté par `config_json.show_success_modal_on_complete` sur l’écran `financial_acknowledgements`, et **Flutter** affiche la **Modale** DS existante après `completeSession` réussi.

---

## Structure du flow (EU v3)

| Position | `step_key` | Visibilité | Données normalisées (binding) |
|----------|------------|------------|-------------------------------|
| 7 | `employment_status` | toujours | `employment_status` |
| 8 | `work_details` | `employment_status ∈ {employed, self_employed}` | `job_title`, `employer_name`, `work_sector` |
| 9 | `annual_income` | toujours | `annual_income_range` |
| 10 | `net_worth` | toujours | `net_worth_range` |
| 11 | `source_of_wealth` | toujours | `source_of_wealth` (liste) |
| 12 | `financial_acknowledgements` | toujours | `info_true_and_accurate`, `compliance_usage_ack`, `not_us_person` |

**Employeur** : deux composants `text_input` avec le **même** `binding_slug` `employer_name` et des `component_key` distincts (`employer_name_employed` / `employer_name_self`), avec **règles de visibilité** mutuellement exclusives (`employment_status` = employed vs self_employed). Le moteur ne sérialise que les composants **visibles** → un seul champ employeur à l’écran.

---

## Mapping « produit » → moteur

| Spécification | Implémentation |
|---------------|----------------|
| `single_select_list` | `select` + `props.options` `{value, label}` |
| `dropdown_select` | `select` (identique) |
| `multi_select_list` | `multi_select` |
| `checkbox_list` | plusieurs `checkbox` (un slug par case) |
| Métadonnées module | `config_json.step_metadata` : `module`, `step_key`, `description`, `required` |
| Modale succès | `config_json.show_success_modal_on_complete` + `success_modal` {title, description, primary_label} |

---

## Fichiers modifiés / ajoutés

| Fichier | Rôle |
|---------|------|
| `api/alembic/versions/123_eu_registration_flow_v3_financial_profile.py` | Archive EU v2, clone vers v3, insère 6 étapes financial |
| `api/services/customers_admin/registration_progress.py` | Jalons + profil pour les 6 étapes + `work_details` conditionnel |
| `api/services/customers_admin/schemas.py` | Champs optionnels sur `RegistrationStateFlags` |
| `mobile/lib/features/registration/data/registration_models.dart` | Getters `showSuccessModalOnComplete`, `successModalConfig` |
| `mobile/lib/features/registration/screens/registration_flow_screen.dart` | Modale après `completeSession` si config |
| `FINANCIAL_PROFILE_FLOW_IMPLEMENTATION_REPORT.md` | Ce rapport |

---

## Persistance & scoring

Les réponses sont stockées comme le reste du moteur : `registration_session_data` puis projection vers `persons.profile_json["collected"]` au **complete**. Les slugs sont **stables** pour un usage scoring backend (ex. `annual_income_range`, `net_worth_range`, `source_of_wealth`).

**Exemple** (agrégat attendu côté profil) :

```json
{
  "employment_status": "employed",
  "job_title": "Engineer",
  "employer_name": "Acme",
  "work_sector": "technology",
  "annual_income_range": "between_50k_100k",
  "net_worth_range": "between_100k_250k",
  "source_of_wealth": ["salary", "savings"]
}
```

---

## Tests & validation

- **Automatisé** : les tests existants `RegistrationStateFlags` restent compatibles (nouveaux champs avec défaut `False`). Relancer la suite `api/tests/test_customers_admin_registration_progress.py` après déploiement.
- **Manuel** :
  1. Appliquer la migration `123` sur une base qui contient déjà le flux EU v2 (`c8a4f0e1-…`).
  2. Démarrer une session EU : le **active flow** doit être **v3** (version 3).
  3. Parcourir jusqu’aux étapes financial ; vérifier que **work_details** est **sauté** si statut ≠ employed/self_employed.
  4. Dernier écran acknowledgements → **complete** → **modale** « Profile updated successfully » → **Continue** → shell.

---

## Limites / suites possibles

- **i18n** : libellés des options et titres d’étapes sont en **anglais** dans la migration ; on peut reprendre le modèle de la `122` (UPDATE `title_i18n` / `subtitle_i18n` / props) sans changer la structure.
- **Champ définitions** : pas de nouvelles entrées `field_definitions` obligatoires pour fonctionner ; ajout possible pour l’admin catalogue.
- **Admin web preview** : les types utilisés sont déjà dans la liste autorisée ; pas de changement requis pour le rendu de base.

---

## Déploiement

```bash
cd services/arquantix/api && alembic upgrade head
```

Le flux **v2** est **archivé** ; les **sessions** déjà liées à **v2** restent sur **v2** ; les **nouvelles** sessions résolvent le flux **actif** le plus récent (**v3**).
