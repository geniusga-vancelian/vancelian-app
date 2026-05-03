# Check all module language (Vault Builder)

## Rôle

Outil admin pour une **langue cible** : analyser le contenu Vault (champs texte **allowlistés**), détecter les incohérences linguistiques (`classifyTextForTargetLocale`), puis **optionnellement** retraduire vers la cible via OpenAI **champ par champ** — **écriture DRAFT uniquement** (et `PageI18n` pour cette locale). Le **PUBLISHED** n’est jamais modifié par cet outil.

## Où l’utiliser

- **Admin** → Vault Builder → bloc **« Check all module language »** (langue = **langue d’édition** sélectionnée dans la barre de locale).
- **API** (session admin) :
  - `POST /api/admin/vaults/[slug]/check-module-language/scan` — lecture seule.
  - `POST /api/admin/vaults/[slug]/check-module-language/apply` — correction + persistance DRAFT.

## Pipeline

1. **SCAN** — `scanVaultModuleLanguage` : parcours `collectAllowlistedVaultTextFields`, une entrée par champ avec statut, locale détectée, confiance ; résumé `integrity` via `verifyTranslatedVaultDraft` (même famille que l’audit vault existant).
2. **DETECT** — intégré au scan (`classifyTextForTargetLocale`).
3. **TRANSLATE** — `applyVaultLanguageFixesToDraft` : uniquement `WRONG_LANGUAGE` et `MIXED_LANGUAGE` ; `translateText` / `translateMarkdown` selon le type ; pas de blob JSON libre.
4. **VERIFY** — après apply : `verifyTranslatedVaultDraft` + nouveau `scanVaultModuleLanguage` sur le brouillon corrigé (réponse `scanAfter`).

## Champs couverts

Définis dans `vaultAllowlistedTextFields.ts` (alignés sur l’auto-traduction Vault). Incluent notamment titres, sous-titres, markdown, FAQ, labels Funding, CTA, tags éditoriaux, `pageTitle` / `fixedBottomCta`, et **`pageI18n.title` / `pageI18n.description`**.

Exclus par conception : ids, slugs, URLs, médias, enums, structure JSON, nombres, booléens, champs non listés — via allowlist + `shouldSkipPlainString`.

## Ce que la correction ne fait pas

- Ne modifie pas **MISSING**, **OK**, **NEEDS_REVIEW** (ex. textes trop courts), **NON_TRANSLATABLE**.
- Ne touche pas au contenu **PUBLISHED** ; upsert uniquement `sectionContent` avec `status: DRAFT`.

## Pourquoi une relecture reste nécessaire

La détection heuristique peut se tromper sur les textes courts ou mixtes ; la traduction automatique peut alourdir ou déplacer le ton. Le rapport et les compteurs « à surveiller » reflètent cela honnêtement.

## Validation manuelle suggérée

1. Choisir la langue cible (édition), lancer **Analyser**, lire le JSON de rapport.
2. Lancer **Corriger le brouillon**, recharger la page vault.
3. Vérifier le brouillon dans l’éditeur ; comparer au publié (inchangé).
4. Relancer **Analyser** pour voir la baisse des champs hors `OK`.
