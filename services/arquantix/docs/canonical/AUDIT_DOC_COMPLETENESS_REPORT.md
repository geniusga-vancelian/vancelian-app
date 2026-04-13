# Audit de Complétude Documentation Canonique

**Date**: 2026-01-11 09:30:14  
**Répertoire**: `docs/canonical/`

---

## Résumé

- **Fichiers audités**: 8
- **Issues trouvées**: 72
- **Mots-clés incomplets**: 71
- **Titres vides**: 1
- **Liens cassés**: 0

---

## Issues par Type


### Mots-clés Incomplets (UNKNOWN, TODO, TBD, etc.)

- **00_OVERVIEW.md:33** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Fonctionnalités futures non vérifiables dans le code actuel :
  ```

- **00_OVERVIEW.md:33** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Fonctionnalités futures non vérifiables dans le code actuel :
  ```

- **00_OVERVIEW.md:33** - Mot-clé: `non vérifiables`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Fonctionnalités futures non vérifiables dans le code actuel :
  ```

- **00_OVERVIEW.md:36** - Mot-clé: `TODO`
  ```
  - Backtests asynchrones (TODO dans `api/services/backtest/routes.py:151`)
  ```

- **10_FRONTEND_NEXTJS.md:101** - Mot-clé: `UNKNOWN`
  ```
  **Note**: UNKNOWN si le parsing HTML Yahoo Finance est implémenté dans le backend (non vérifié dans 
  ```

- **10_FRONTEND_NEXTJS.md:101** - Mot-clé: `non vérifié`
  ```
  **Note**: UNKNOWN si le parsing HTML Yahoo Finance est implémenté dans le backend (non vérifié dans 
  ```

- **10_FRONTEND_NEXTJS.md:284** - Mot-clé: `UNKNOWN`
  ```
  - **Bundle de bundles (composite)**: Supporté dans la DB (`bundle_components.component_type = 'bundl
  ```

- **10_FRONTEND_NEXTJS.md:285** - Mot-clé: `UNKNOWN`
  ```
  - **Bundles dynamiques**: Type `dynamic` existe, mais UNKNOWN si les règles sont implémentées
  ```

- **10_FRONTEND_NEXTJS.md:286** - Mot-clé: `UNKNOWN`
  ```
  - **Parsing HTML Yahoo Finance**: UNKNOWN si implémenté dans le backend
  ```

- **20_BACKEND_FASTAPI.md:29** - Mot-clé: `UNKNOWN`
  ```
  └── ai_email/                  # UNKNOWN (non vérifié dans ce contexte)
  ```

- **20_BACKEND_FASTAPI.md:29** - Mot-clé: `non vérifié`
  ```
  └── ai_email/                  # UNKNOWN (non vérifié dans ce contexte)
  ```

- **20_BACKEND_FASTAPI.md:296** - Mot-clé: `UNKNOWN`
  ```
  - **409 Conflict**: UNKNOWN (non vérifié)
  ```

- **20_BACKEND_FASTAPI.md:296** - Mot-clé: `non vérifié`
  ```
  - **409 Conflict**: UNKNOWN (non vérifié)
  ```

- **20_BACKEND_FASTAPI.md:364** - Mot-clé: `UNKNOWN`
  ```
  **Durée**: `ACCESS_TOKEN_EXPIRE_MINUTES` (valeur: UNKNOWN, vérifier `api/auth.py`).
  ```

- **20_BACKEND_FASTAPI.md:394** - Mot-clé: `TODO`
  ```
  - **Backtest asynchrone**: TODO dans `api/services/backtest/routes.py:151` ("In production, this sho
  ```

- **20_BACKEND_FASTAPI.md:395** - Mot-clé: `UNKNOWN`
  ```
  - **Bundle resolver**: UNKNOWN si implémenté (composite bundles, cycles)
  ```

- **20_BACKEND_FASTAPI.md:396** - Mot-clé: `UNKNOWN`
  ```
  - **Bundles dynamiques**: Type `dynamic` existe, mais UNKNOWN si les règles sont implémentées
  ```

- **30_MARKET_DATA.md:28** - Mot-clé: `UNKNOWN`
  ```
  - `equity` - Actions (UNKNOWN si utilisé)
  ```

- **30_MARKET_DATA.md:105** - Mot-clé: `UNKNOWN`
  ```
  **Library**: `yfinance` (version: UNKNOWN, vérifier `api/requirements.txt`)
  ```

- **30_MARKET_DATA.md:157** - Mot-clé: `UNKNOWN`
  ```
  - **Preview**: UNKNOWN (non vérifié)
  ```

- **30_MARKET_DATA.md:157** - Mot-clé: `non vérifié`
  ```
  - **Preview**: UNKNOWN (non vérifié)
  ```

- **30_MARKET_DATA.md:183** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Le parsing HTML Yahoo Finance n'est pas vérifié dans le code ac
  ```

- **30_MARKET_DATA.md:183** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Le parsing HTML Yahoo Finance n'est pas vérifié dans le code ac
  ```

- **30_MARKET_DATA.md:187** - Mot-clé: `UNKNOWN`
  ```
  **Backend**: UNKNOWN si endpoint existe pour parser HTML.
  ```

- **30_MARKET_DATA.md:204** - Mot-clé: `UNKNOWN`
  ```
  **Insertion**: Si barre existe déjà (même `instrument_id` + `date`), comportement UNKNOWN (upsert ou
  ```

- **30_MARKET_DATA.md:206** - Mot-clé: `UNKNOWN`
  ```
  **Référence**: UNKNOWN (non vérifié dans `api/scripts/load_market_data.py`)
  ```

- **30_MARKET_DATA.md:206** - Mot-clé: `non vérifié`
  ```
  **Référence**: UNKNOWN (non vérifié dans `api/scripts/load_market_data.py`)
  ```

- **30_MARKET_DATA.md:214** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Option `--check-only` mentionnée dans les commentaires mais UNK
  ```

- **30_MARKET_DATA.md:214** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Option `--check-only` mentionnée dans les commentaires mais UNK
  ```

- **30_MARKET_DATA.md:231** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Logique de merge/overwrite des données existantes non vérifiée.
  ```

- **30_MARKET_DATA.md:231** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Logique de merge/overwrite des données existantes non vérifiée.
  ```

- **30_MARKET_DATA.md:231** - Mot-clé: `non vérifié`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Logique de merge/overwrite des données existantes non vérifiée.
  ```

- **30_MARKET_DATA.md:299** - Mot-clé: `UNKNOWN`
  ```
  - **Parsing HTML Yahoo Finance**: UNKNOWN si implémenté
  ```

- **30_MARKET_DATA.md:300** - Mot-clé: `UNKNOWN`
  ```
  - **Upsert intelligent**: UNKNOWN si implémenté (merge des données existantes)
  ```

- **30_MARKET_DATA.md:301** - Mot-clé: `UNKNOWN`
  ```
  - **Gestion des gaps**: Détection des jours manquants, mais UNKNOWN si automatique
  ```

- **40_BUNDLES.md:47** - Mot-clé: `UNKNOWN`
  ```
  ### `composite_fixed` (supporté dans DB, UNKNOWN si implémenté)
  ```

- **40_BUNDLES.md:60** - Mot-clé: `UNKNOWN`
  ```
  **Status**: Table et contraintes existent, mais UNKNOWN si le resolver est implémenté.
  ```

- **40_BUNDLES.md:64** - Mot-clé: `UNKNOWN`
  ```
  ### `dynamic` (supporté dans DB, UNKNOWN si implémenté)
  ```

- **40_BUNDLES.md:70** - Mot-clé: `UNKNOWN`
  ```
  **Exemple**: UNKNOWN (non vérifié dans le code).
  ```

- **40_BUNDLES.md:70** - Mot-clé: `non vérifié`
  ```
  **Exemple**: UNKNOWN (non vérifié dans le code).
  ```

- **40_BUNDLES.md:72** - Mot-clé: `UNKNOWN`
  ```
  **Status**: Table `bundle_dynamic_rules` existe, mais UNKNOWN si le moteur d'exécution est implément
  ```

- **40_BUNDLES.md:128** - Mot-clé: `UNKNOWN`
  ```
  ### `bundle_allocations` (UNKNOWN si utilisée)
  ```

- **40_BUNDLES.md:139** - Mot-clé: `UNKNOWN`
  ```
  ### `bundle_dynamic_rules` (UNKNOWN si utilisée)
  ```

- **40_BUNDLES.md:146** - Mot-clé: `UNKNOWN`
  ```
  **Status**: Table existe, mais UNKNOWN si le moteur d'exécution est implémenté.
  ```

- **40_BUNDLES.md:183** - Mot-clé: `UNKNOWN`
  ```
  ## 5. Resolver (UNKNOWN si implémenté)
  ```

- **40_BUNDLES.md:187** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Aucune fonction `resolve_bundle_effective_weights` trouvée dans
  ```

- **40_BUNDLES.md:187** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Aucune fonction `resolve_bundle_effective_weights` trouvée dans
  ```

- **40_BUNDLES.md:189** - Mot-clé: `non vérifié`
  ```
  **Comportement attendu** (hypothèse, non vérifié):
  ```

- **40_BUNDLES.md:195** - Mot-clé: `NON VÉRIFIÉ`
  ```
  **Status**: NON VÉRIFIÉ dans le code actuel.
  ```

- **40_BUNDLES.md:201** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Endpoint `/api/bundles/{id}/preview` non trouvé dans le code.
  ```

- **40_BUNDLES.md:201** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Endpoint `/api/bundles/{id}/preview` non trouvé dans le code.
  ```

- **40_BUNDLES.md:203** - Mot-clé: `non vérifié`
  ```
  **Comportement attendu** (hypothèse, non vérifié):
  ```

- **40_BUNDLES.md:208** - Mot-clé: `NON VÉRIFIÉ`
  ```
  **Status**: NON VÉRIFIÉ.
  ```

- **40_BUNDLES.md:278** - Mot-clé: `UNKNOWN`
  ```
  - **Bundle resolver (composite)**: UNKNOWN si implémenté (résolution bundles de bundles)
  ```

- **40_BUNDLES.md:279** - Mot-clé: `UNKNOWN`
  ```
  - **Détection de cycles**: UNKNOWN si implémentée
  ```

- **40_BUNDLES.md:280** - Mot-clé: `UNKNOWN`
  ```
  - **Bundles dynamiques**: Table `bundle_dynamic_rules` existe, mais UNKNOWN si moteur d'exécution im
  ```

- **50_BACKTESTS.md:116** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Si un prix est manquant le jour de rééquilibrage, le rebalance 
  ```

- **50_BACKTESTS.md:116** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Si un prix est manquant le jour de rééquilibrage, le rebalance 
  ```

- **50_BACKTESTS.md:249** - Mot-clé: `TODO`
  ```
  **Important**: Exécution **synchrone** actuellement (TODO pour async dans production).
  ```

- **50_BACKTESTS.md:383** - Mot-clé: `TODO`
  ```
  - **Exécution asynchrone**: TODO dans `api/services/backtest/routes.py:151` (actuellement synchrone)
  ```

- **50_BACKTESTS.md:384** - Mot-clé: `UNKNOWN`
  ```
  - **Skip rebalance si prix manquant**: UNKNOWN (forward fill utilisé, mais rebalance skippé ?)
  ```

- **70_RUNBOOK_DEV.md:131** - Mot-clé: `non vérifié`
  ```
  - `DATABASE_URL` - Prisma DATABASE_URL (pour CMS, non vérifié)
  ```

- **70_RUNBOOK_DEV.md:134** - Mot-clé: `UNKNOWN`
  ```
  - `NEXT_PUBLIC_*` - Variables publiques Next.js (UNKNOWN si utilisées)
  ```

- **70_RUNBOOK_DEV.md:197** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.
  ```

- **70_RUNBOOK_DEV.md:197** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.
  ```

- **70_RUNBOOK_DEV.md:197** - Mot-clé: `Non vérifié`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.
  ```

- **70_RUNBOOK_DEV.md:259** - Mot-clé: `UNKNOWN`
  ```
  **Script**: `./scripts/arquantix-status.sh` (UNKNOWN si existe)
  ```

- **70_RUNBOOK_DEV.md:275** - Mot-clé: `UNKNOWN`
  ```
  **Script**: `./stop-all.sh` (UNKNOWN si existe)
  ```

- **70_RUNBOOK_DEV.md:311** - Mot-clé: `UNKNOWN`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.
  ```

- **70_RUNBOOK_DEV.md:311** - Mot-clé: `needs confirmation`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.
  ```

- **70_RUNBOOK_DEV.md:311** - Mot-clé: `Non vérifié`
  ```
  ⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.
  ```


### Titres Vides

- **70_RUNBOOK_DEV.md:327** - ### Appliquer migrations
  Contenu: 36 caractères


---

## Checklist de Remediation

- [ ] **71 issues** - Remplacer les mots-clés incomplets par du contenu réel
- [ ] **1 issues** - Ajouter du contenu sous les titres vides

---

*Généré par: `tools/audit_doc_completeness.py`*
