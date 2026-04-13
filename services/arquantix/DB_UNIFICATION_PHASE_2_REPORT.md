# Rapport — Phase 2 : fusion `arquantix_quant` + `arquantix_admin` → `arquantix`

**Date :** 2026-04-01  
**Objectif :** une seule base PostgreSQL, API + Alembic + Prisma alignés, sans perte de données ni collision de tables.

---

## Executive Summary

- **Collision résolue :** l’API exposait une table SQLAlchemy `pages` (id entier, JSON) alors que Prisma utilise une table `pages` différente (cuid, `url_path`, etc.). La migration **Alembic 105** renomme l’ancienne table en **`legacy_json_pages`** lorsque la colonne `id` est de type entier.
- **Base cible :** **`arquantix`** (même host/port qu’avant, typiquement `localhost:5443`).
- **Script de fusion :** `scripts/db_merge_quant_admin.py` — sauvegarde obligatoire avant exécution, mode `--dry-run` pour valider le plan.
- **Garde-fous :** `make doctor-db` échoue si le **nom de base** diffère entre API et Web ; défaut `DB_NAME` / audit mis à jour vers `arquantix`.
- **Fichiers sensibles :** `api/.env`, `web/.env` dans ce dépôt pointent vers `…/arquantix` (à reproduire sur chaque poste / CI).

---

## Initial State

| Élément | Avant |
|---------|--------|
| API / Alembic | Base `arquantix_quant` |
| Web / Prisma | Base `arquantix_admin` |
| Conflit nominal | Deux tables `pages` incompatibles si même base |

---

## Target State

| Élément | Après |
|---------|--------|
| `DATABASE_URL` (API + Web) | `…/arquantix` |
| Pages legacy API | Table `legacy_json_pages` |
| Pages CMS Prisma | Table `pages` |
| `alembic_version` | Inchangé logiquement (état quant + migration 105 sur la base fusionnée) |
| `_prisma_migrations` | Copié depuis l’admin avec les tables Prisma |

---

## Migration Strategy

1. **Sauvegardes** : `pg_dump -Fc` des deux bases sources.
2. **Sur `arquantix_quant`** : `cd api && alembic upgrade head` jusqu’à **105** (rename `pages` → `legacy_json_pages`).
3. **Créer** la base `arquantix` (vide) si besoin (`createdb` ou superuser).
4. **Restaurer** le dump complet de `arquantix_quant` dans `arquantix`.
5. **Tables présentes uniquement sur l’admin** : DDL puis données via `pg_dump -t` (ordre topologique FK).
6. **Tables en recouvrement** (`email_modules`, `email_module_i18n`, `email_template_entities`) : **données admin prioritaires** — `TRUNCATE … CASCADE` sur la cible puis réimport depuis l’admin.

---

## Tables Mapping

### Collision traitée

| table_name | Origine | Collision ? | Action |
|------------|---------|---------------|--------|
| `pages` | Quant (SQLAlchemy) + Admin (Prisma) | **Oui** (schémas incompatibles) | Renommer quant → `legacy_json_pages` (105) ; conserver `pages` pour Prisma |

### Recouvrement (admin gagne sur les données)

| table_name | Quant | Admin | Action |
|------------|-------|-------|--------|
| `email_modules` | Possible (Alembic cc6123) | Oui (Prisma) | TRUNCATE cible + données admin |
| `email_module_i18n` | idem | idem | idem |
| `email_template_entities` | idem | idem | idem |

### Sans collision (résumé)

- **Côté Alembic / SQLAlchemy (database.py + services)** : `global_settings`, `legacy_json_pages` (ex-`pages`), `news`, `contact_submissions`, `admin_users`, `market_data_*`, `bundles*`, `backtest_*`, `field_definitions`, `persons`, `two_factor_challenges`, `audit_events`, `jurisdiction_*`, `documents`, `chatbot_*`, `registration_*`, `country_directory`, `pe_*`, `custody_*`, `crypto_*`, `exchange_*`, `lending_*`, `loans*`, `pool_*`, `notifications`, `price_alerts`, `presentation_*`, `client_favorites`, `app_runtime_settings`, etc.
- **Côté Prisma (`@@map`)** : `users`, `sessions`, `pages`, `sections`, `section_contents`, `media`, `projects`, `investment_categories`, `investment_types`, `portfolio_product_configs`, `key_information_categories`, `project_i18n`, `project_media`, `article_*`, `help_*`, `menus*`, `app_settings`, `translation_logs`, `emails`, `email_i18n`, `email_modules`, `email_module_i18n`, `email_template_entities`, `ds_component_chapters`, `ds_components`.

Aucun autre nom de table n’était partagé entre les deux modèles sous le même schéma.

---

## Data Migration Steps

```bash
# 0. Backups
pg_dump --no-owner --no-acl -Fc -f backup_quant.dump "postgresql://USER:PASS@HOST:PORT/arquantix_quant"
pg_dump --no-owner --no-acl -Fc -f backup_admin.dump "postgresql://USER:PASS@HOST:PORT/arquantix_admin"

# 1. Mettre quant à jour (incl. 105)
cd services/arquantix/api
alembic upgrade head

# 2. Dry-run du plan de fusion
cd ..
python3 scripts/db_merge_quant_admin.py --dry-run \
  --quant-url "postgresql://USER:PASS@HOST:PORT/arquantix_quant" \
  --admin-url "postgresql://USER:PASS@HOST:PORT/arquantix_admin" \
  --target-name arquantix \
  --superuser-url "postgresql://postgres:PASS@HOST:PORT/postgres"

# 3. Exécution réelle (sans --dry-run)
python3 scripts/db_merge_quant_admin.py \
  --quant-url "..." \
  --admin-url "..." \
  --target-name arquantix \
  --superuser-url "..."

# 4. Pointer les apps
# api/.env* et web/.env → .../arquantix

# 5. Vérifications
make doctor-db
cd api && alembic current
cd web && npx prisma migrate status
```

---

## Config Changes

| Fichier / zone | Modification |
|----------------|--------------|
| `api/database.py` | `DB_NAME` défaut `arquantix` ; `Page` → `legacy_json_pages` |
| `api/.env` | `DATABASE_URL` → `…/arquantix` |
| `web/.env` | idem |
| `scripts/db_config_audit.py` | Erreur si noms de base API ≠ Web ; défaut `arquantix` |
| `scripts/arquantix-relance-tout.sh` | `DB_NAME=arquantix` |
| `scripts/arquantix-boot.sh` | Exemple `POSTGRES_DB=arquantix` |
| `api/services/diagnostics/routes.py` | Champ `canonical_unified_db` |
| `api/scripts/migrate_quant_db.py`, `switch_env_to_quant.py`, `create_db_quant.py` | Textes / cible `arquantix` |
| `docs/ARCHITECTURE.md`, `docs/canonical/60_DATABASE_ALEMBIC.md` | Base unique documentée |

---

## Alembic / Prisma alignment

- **Alembic** : ne pas « rejouer » l’historique sur la base fusionnée ; conserver la ligne `alembic_version` issue du restore quant (puis appliquer 105 **avant** le dump si ce n’était pas déjà fait).
- **Prisma** : après fusion, `npx prisma migrate status` doit refléter les migrations déjà présentes dans `_prisma_migrations` (copiées depuis l’admin). Si besoin d’aligner un drift : `prisma db pull` en **analyse** uniquement, puis décision manuelle (pas automatisé ici).

---

## Tests Performed

À exécuter après bascule sur chaque environnement :

- [ ] `make doctor-db` — aucune erreur, pas de mismatch nom de base  
- [ ] API démarre, `[API]` log DB = `arquantix`  
- [ ] `GET /api/diagnostics/db-status` — `alembic_version` cohérent  
- [ ] `npm run db:info` — même base  
- [ ] Admin Next : login, édition page / section  
- [ ] Flows registration / 2FA (selon périmètre produit)  
- [ ] Endpoints legacy utilisant `Page` / `legacy_json_pages` si encore utilisés  

*(Les tests automatiques n’ont pas été exécutés dans cet environnement sans PostgreSQL actif.)*

---

## Rollback Plan

1. Arrêter API et Web.  
2. Repointer `DATABASE_URL` vers `arquantix_quant` et `arquantix_admin` respectivement (sauvegardes `.env`).  
3. Restaurer les dumps `backup_quant.dump` / `backup_admin.dump` si les bases sources ont été altérées.  
4. Optionnel : `DROP DATABASE arquantix;` sur la cible si elle ne doit plus exister.

---

## Final Validation

- Une seule base **`arquantix`** pour développement et documentation canonique.  
- Noms **`arquantix_quant`** / **`arquantix_admin`** réservés à l’historique et aux warnings de migration.  
- Script **`scripts/db_merge_quant_admin.py`** + ce rapport = procédure reproductible.

---

## Fichiers ajoutés / modifiés (code)

| Fichier | Rôle |
|---------|------|
| `api/alembic/versions/105_rename_legacy_api_pages_table.py` | Rename conditionnel |
| `scripts/db_merge_quant_admin.py` | Fusion pilotée |
| `DB_RUNBOOK_UPDATED.md` | Runbook opérationnel |
