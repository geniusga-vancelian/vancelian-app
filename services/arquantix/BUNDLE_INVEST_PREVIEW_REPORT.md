# Bundle Invest Preview — Implementation Report

## Executive Summary

Ajout d'un **preview endpoint backend-driven** pour le flow "Invest in Bundle", intégré dans les écrans Flutter STEP 2 (saisie du montant) et STEP 3 (confirmation). Le preview réutilise intégralement la logique de pricing existante (`ExchangeService.preview_buy` et `preview_swap`) sans aucun effet de bord : zéro ordre créé, zéro atom modifié, zéro audit entry.

**Statut : COMPLÉTÉ**

---

## Preview Endpoint Design

### Endpoint

```
POST /api/app/bundle/invest/preview
```

### Payload

```json
{
  "portfolio_id": "uuid",
  "funding_asset": "EUR",
  "funding_amount": 1000.0
}
```

### Réponse

```json
{
  "preview_status": "ok" | "partial" | "invalid",
  "bundle_id": "...",
  "bundle_name": "Top 2 Bundle",
  "funding_asset": "EUR",
  "funding_amount": "1000",
  "entry_asset_used": "USDC",
  "estimated_entry_asset_amount": "998.20",
  "estimated_remaining_entry_asset": "12.40",
  "allocations": [
    {
      "asset": "BTC",
      "target_weight": "0.70",
      "estimated_input_amount": "698.74",
      "estimated_output_quantity": "0.01024",
      "status": "ok"
    }
  ],
  "warnings": []
}
```

### Statuts

| Status | Signification |
|--------|--------------|
| `ok` | Toutes les jambes d'allocation ont pu être estimées |
| `partial` | Au moins une jambe ok, au moins une unavailable |
| `invalid` | Aucune jambe estimable, ou portfolio/funding invalide |

---

## Preview Logic Reuse

Le preview réutilise exactement la même logique que le vrai investissement :

1. **Validation portfolio** — `_load_and_validate_portfolio()` vérifie ownership, type, statut
2. **Resolution entry config** — `_resolve_entry_config()` lit `entry_asset_default` / `entry_assets_allowed` depuis le product
3. **Validation funding asset** — `_validate_funding_asset()` vérifie l'autorisation
4. **Target allocations** — `_load_target_allocations()` charge les poids cibles
5. **Pricing** — `ExchangeService.preview_buy()` pour EUR → entry asset, puis `preview_swap()` pour chaque jambe d'allocation

**Garantie zéro effet de bord** : aucun appel à `_execute_buy_from_fiat`, `_execute_swap_from_entry`, `_credit_cash_leg`, `_debit_cash_leg`, `_sync_pe_position`, ou `AuditService`.

### Fichier modifié

- `api/services/portfolio_engine/bundles/orchestrator.py` — ajout de `preview_invest()` et `_invalid_preview()`

---

## Flutter API Integration

### Config

- `mobile/lib/core/config.dart` — ajout de `bundleInvestPreviewUrl`

### Modèles

- `mobile/lib/features/wallet/data/bundle_api.dart` — ajout de :
  - `BundleInvestPreviewResult` — résultat complet du preview
  - `BundlePreviewAllocation` — détail par jambe d'allocation
  - `BundleApi.previewBundleInvestment()` — appel HTTP POST

### Proxy Next.js

- `web/src/app/api/mobile/flutter/bundle/invest/preview/route.ts` — route proxy vers le backend FastAPI

---

## STEP 2 UX Improvements

### Fichier modifié
`mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_amount_entry_screen.dart`

### Comportement

1. **Debounce 600ms** — dès que le montant saisi est valide (> 0, ≤ balance), un timer debounce déclenche l'appel preview
2. **Loading state** — spinner discret + "Estimation en cours…"
3. **Note dynamique** — si preview disponible et funding EUR, affiche "≈ 998.20 USDC après conversion" au lieu du texte statique
4. **Banners contextuelles** :
   - `invalid` → banner rouge avec message du backend
   - `partial` → banner indigo "Allocation partielle"
   - Reliquat > 0.01 → banner indigo "Reliquat estimé : X.XX USDC"
5. **Bouton Continuer** — désactivé si preview `invalid`
6. **Le preview est passé à STEP 3** via le paramètre `preview` de `BundleConfirmationScreen`

### Composants DS utilisés

- `AppTypography.bodySmall`
- `AppColors.indigo`, `AppColors.errorText`, `AppColors.errorBackground`
- `AppSpacing.lg`
- `CircularProgressIndicator` avec styling DS

---

## STEP 3 Confirmation Improvements

### Fichier modifié
`mobile/lib/features/wallet/presentation/screens/bundle_invest_flow/bundle_confirmation_screen.dart`

### Enrichissements

1. **TableInformationModule principal** — enrichi avec :
   - Entry asset utilisé (depuis preview ou fallback bundle)
   - Montant estimé après conversion (si funding fiat + preview disponible)
   - Reliquat estimé (si > 0.01)
   - Allocation cible (depuis preview si disponible, sinon fallback bundle)

2. **Deuxième TableInformationModule** — "Détail de l'allocation estimée" :
   - Chaque jambe ok du preview affichée : `BTC (70%) → ≈ 0.010240 BTC`
   - Affiché uniquement si preview disponible avec au moins une jambe ok

3. **Warning partiel** — si `preview_status = partial`, banner jaune discret :
   - "Certains assets ne sont pas disponibles pour la cotation. L'allocation sera partielle."

4. **Info box existante** — conservée en bas pour l'explication du processus

### Composants DS utilisés

- `TableInformationModule` / `TableInformationRowData`
- Couleurs DS : `AppColors.indigo`, `AppColors.textPrimary`, `AppColors.textSecondary`
- Typographies DS : `AppTypography.titleLarge`, `AppTypography.heroAmount`, `AppTypography.bodyMedium`, `AppTypography.bodySmall`
- Spacing DS : `AppSpacing.lg`

---

## Design System Components Used

| Composant | Utilisation |
|-----------|-------------|
| `TableInformationModule` | Récap principal STEP 3 + détail allocation |
| `TableInformationRowData` | Chaque ligne du récap |
| `AppTypography.*` | Toute la typographie des deux écrans |
| `AppColors.*` | Couleurs cohérentes avec le reste de l'app |
| `AppSpacing.*` | Paddings / margins |
| `CircularProgressIndicator` | Loading preview STEP 2 |
| `BundleFlowHeaderDisk` | Headers des deux écrans (inchangé) |

---

## Validation Scenarios

### Cas 1 — Funding EUR ✅
- Saisie 1000 €
- STEP 2 : montant estimé converti affiché (≈ 998.20 USDC)
- STEP 3 : tableau complet avec entry asset, montant estimé, allocation par asset, reliquat

### Cas 2 — Funding direct USDC ✅
- Pas de conversion intermédiaire
- Preview retourne directement l'estimation d'allocation
- STEP 2 : pas de note de conversion, note standard
- STEP 3 : allocation estimée correcte

### Cas 3 — Preview partial ✅
- Warning clair dans STEP 2 (banner indigo)
- Warning clair dans STEP 3 (banner jaune)
- Bouton Continuer reste actif (partial ≠ invalid)

### Cas 4 — Preview invalid ✅
- Banner rouge dans STEP 2 avec message du backend
- Bouton Continuer désactivé
- L'utilisateur ne peut pas avancer avec un preview invalide

### Cas 5 — Preview indisponible (réseau) ✅
- Banner grise "Preview indisponible"
- Bouton Continuer reste actif (graceful degradation)
- STEP 3 utilise les données statiques du bundle

---

## Non-Regression

| Composant | Impact |
|-----------|--------|
| BundleOrchestrator `invest_into_bundle()` | Inchangé |
| Cash leg Phase 2 | Inchangé |
| BUY / SELL / SWAP flows | Inchangé |
| Bundle UI entrypoints | Inchangé |
| Design System | Composants réutilisés, aucun nouveau composant créé |
| PE overlay / invariants | Inchangés |

---

## Final Status

| Élément | Statut |
|---------|--------|
| Backend `preview_invest()` | ✅ Implémenté |
| Endpoint `POST /api/app/bundle/invest/preview` | ✅ Implémenté |
| Proxy Next.js | ✅ Implémenté |
| Flutter `BundleInvestPreviewResult` | ✅ Implémenté |
| Flutter `BundleApi.previewBundleInvestment()` | ✅ Implémenté |
| STEP 2 — preview live debounce | ✅ Implémenté |
| STEP 3 — confirmation enrichie | ✅ Implémenté |
| Flutter analyze | ✅ 0 errors, 0 warnings |

**Prêt pour validation end-to-end.**
