# Rapport — bundle « Top 5 Crypto » (CRYPTO_BUNDLE_TOP5)

## Partie 1 — Audit rapide de l’existant

### 1. Où les bundles / produits crypto sont modélisés

| Couche | Emplacement | Rôle |
|--------|-------------|------|
| **Portfolio Engine (PostgreSQL)** | `pe_product_definitions` (`ProductDefinition`) | Catalogue produit : `product_code`, `name`, `description`, `product_type` (`crypto_bundle`), `is_public`, `status`, `metadata` (JSONB). |
| **Templates** | `pe_portfolio_templates` + `pe_template_allocations` | Répartition cible par instrument (`instrument_id`, `target_weight`). |
| **Anciennes tables « market data »** | `bundles`, `bundle_allocations` | Backtests / market data — **pas** le flux principal des bundles investissables documentés dans les audits PE. |
| **CMS Next.js** | `portfolio_product_configs` (Prisma) | **UI** Vault Builder : modules (titre, graphique, allocation), médias, `sortOrder` — utilisé par `GET /api/mobile/flutter/portfolio-products/configs`. |

### 2. Comment les allocations sont stockées

- Poids **décimaux** sur `pe_template_allocations.target_weight` (somme = 1 ± tolérance côté Bundle Engine).
- Jointure vers `pe_instruments` (ex. `BTC-SPOT`) puis `pe_assets.symbol` (ex. `BTC`).
- **L’USDC n’a pas de ligne d’allocation** dans le template : seuls les actifs cibles du panier sont pondérés.

### 3. Comment le wallet / asset de dépôt est défini

- **Concept métier** : `entry_asset_default` et `entry_assets_allowed` dans **`pe_product_definitions.metadata`** (JSONB).
- **Orchestrateur bundle** (`services/portfolio_engine/bundles/orchestrator.py`) : si ces clés manquent, repli **`USDC`** / `["USDC"]`.
- Ce n’est **pas** une colonne SQL dédiée ; c’est cohérent avec le **Bundle Engine v1** et le schéma `BundleCreate` (`entry_asset_default`, `entry_assets_allowed`).

### 4. Où le bundle apparaît

| Couche | Accès / endpoint |
|--------|------------------|
| **Backend** | `GET /api/portfolio-engine/product-catalog` (catalogue public), détail produit selon routes PE. |
| **Test client / bootstrap** | `GET /api/test/bootstrap/bundle/catalog` (proxy catalogue). |
| **Admin** | Création possible via `POST /api/admin/portfolio-engine/bundles` (proxy FastAPI) ; édition Vault Builder par `productCode`. |
| **Flutter** | Catalogue produit + **intersection** avec `portfolio_product_configs` (voir commentaire dans `portfolio-products/configs/route.ts`). |
| **Web** | Pages admin Vault Builder, routes BFF `/api/mobile/flutter/portfolio-products/*`. |

### 5. Champs obligatoires pour visibilité + souscription

- **Catalogue public** (`CatalogService.get_public_catalog`) : `is_public == true`, `status == active`, `product_type` filtrable (`crypto_bundle`).
- **Souscription / invest** : produit actif + template + allocations ; `entry_asset_*` dans les métadonnées pour affichage et validation côté orchestrateur (USDC).
- **Affichage Flutter** (cartes + landing) : **en plus**, une ligne dans **`portfolio_product_configs`** avec le **même `product_code`** que le produit FastAPI, sinon les écrans qui croisent catalogue × config ne montrent pas le produit correctement.

---

## Partie 2 — Bundle créé

| Champ | Valeur |
|-------|--------|
| **product_code** | `CRYPTO_BUNDLE_TOP5` |
| **Nom** | Top 5 Crypto Bundle |
| **Statut** | `active`, `is_public` true |
| **Slug logique** | identique au `product_code` (convention projet) |

### Allocation retenue (somme = 100 %)

| Actif | Poids |
|-------|------|
| BTC | 50 % |
| ETH | 20 % |
| SOL | 10 % |
| XRP | 10 % |
| BNB | 10 % |

**Vérification** : `0.5 + 0.2 + 0.1 + 0.1 + 0.1 = 1.0` (script `bootstrap_crypto_bundle_top5.py` vérifie la somme avant insertion).

---

## Partie 3 — USDC comme asset de dépôt / entrée

| Mécanisme | Détail |
|-----------|--------|
| **Métadonnées produit** | `entry_asset_default: "USDC"`, `entry_assets_allowed: ["USDC"]` dans `metadata` du `ProductDefinition`. |
| **Hors allocation** | Aucune ligne `TemplateAllocation` pour `USDC-SPOT` — l’USDC sert de **funding** vers les swaps / achats des actifs cibles, pas comme slice du panier. |
| **Texte produit** | `subscription_note` dans les métadonnées ; intro du module d’allocation côté Prisma précise que l’USDC est la devise d’entrée. |

Termes équivalents dans le code : **entry asset** (défaut + liste autorisée), aligné sur la doc **Bundle Engine** et **Phase 2A.12** (exclusive offers) pour le même concept métier sous un autre produit.

---

## Partie 4 — Métadonnées produit

- **Description courte** : `short_description` dans les métadonnées (texte institutionnel fourni, sans promesse de performance).
- **Description longue** : `description` sur le produit + phrase de prudence (performances passées, risque).
- **Catégorie** : `product_category: "crypto_bundle"` dans les métadonnées (usage libre / affichage futur).
- **Rééquilibrage** : `available_rebalance_frequencies` : weekly, monthly, quarterly (standard catalogue).

---

## Partie 5 — Fichiers créés / modifiés

| Fichier | Rôle |
|---------|------|
| `services/arquantix/api/scripts/bootstrap_crypto_bundle_top5.py` | Crée / met à jour `CRYPTO_BUNDLE_TOP5`, template, allocations, métadonnées USDC. |
| `services/arquantix/web/scripts/seed-crypto-top5-portfolio-config.ts` | Upsert `portfolio_product_configs` (modules TitlePage, PerformanceChart, AllocationModule). |
| `services/arquantix/web/package.json` | Script `db:seed:crypto-top5-ui`. |
| `services/arquantix/CRYPTO_TOP5_BUNDLE_REPORT.md` | Ce rapport. |

Aucune modification des fichiers cœur (routers, orchestrateur) — **réutilisation des patterns** existants (`bootstrap_crypto_bundle_top2.py`, config Vault).

---

## Partie 6 — Validations effectuées

1. **Script Python** exécuté avec succès : produit + template + 5 allocations créés.
2. **CatalogService** : `CRYPTO_BUNDLE_TOP5` listé avec `entry_asset_default == USDC`, allocations BTC/ETH/SOL/XRP/BNB aux bons poids ; **pas d’USDC** dans les lignes d’allocation.
3. **Prisma** : `portfolio_product_configs` upsert pour `CRYPTO_BUNDLE_TOP5`.
4. **Doublon** : contrainte unique sur `product_code` — un seul produit par code.

À valider manuellement selon environnement :

- `GET` catalogue HTTP (URL FastAPI réelle) et `GET /api/mobile/flutter/portfolio-products/configs` côté Next (avec `MARKET_DATA_BASE_URL` / `BACKEND` pointant vers la bonne API).
- Parcours invest Flutter (wallet USDC → bundle) sur device / staging.

---

## Partie 7 — Points à compléter manuellement

- **Médias** : `header_media_id` / `detail_media_id` non renseignés — ajouter via admin Vault pour visuels premium.
- **Performance 1d** : l’API BFF tente de résoudre une courbe si l’endpoint chart backend existe — peut rester `null` en local.
- **Ré-exécution** : `python3 scripts/bootstrap_crypto_bundle_top5.py` depuis `services/arquantix/api` ; puis `npm run db:seed:crypto-top5-ui` depuis `web`.
- **Instruments manquants** : si le bootstrap échoue sur `*-SPOT`, lancer `python3 scripts/seed_pe_crypto_assets.py` (prérequis `market_data_instruments`).

---

*Rapport généré pour le bundle « Top 5 Crypto » — CRYPTO_BUNDLE_TOP5.*
