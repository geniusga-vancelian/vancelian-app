# Vault Builder — auto-translate FR → EN / IT (brouillon)

## Rôle

Action admin **FR → EN (brouillon)** et **FR → IT (brouillon)** qui enchaîne logiquement :

1. **COPY** — lecture du brouillon ou publié **FR** (même source que « copie vers langue »).
2. **TRANSLATE** — traduction **OpenAI** des champs **allowlistés** uniquement ; structure JSON préservée.
3. **VERIFY** — contrôle linguistique sur le brouillon **cible** (`collectVaultDraftFindings`, statuts OK / WRONG_LANGUAGE / MIXED_LANGUAGE / NEEDS_REVIEW / MISSING).

Une **seule écriture** en base après traduction réussie : `SectionContent` **DRAFT** pour la locale cible + `PageI18n` pour cette locale. **Aucune** mise à jour du **PUBLISHED**.

## Langues

- Source fixe : **fr**
- Cibles : **en**, **it**

## Ce que l’action ne fait pas

- Ne modifie pas le publié, ni les autres langues.
- Ne traduit pas le footer, menu, pages CMS génériques, articles, help.
- Ne garantit pas une traduction finale : **relecture humaine** requise.
- N’invente pas de champs : uniquement les chemins prévus dans l’allowlist.

## Variables d’environnement

- `OPENAI_API_KEY` (requis, comme le reste du site)
- `OPENAI_MODEL`, `OPENAI_TRANSLATION_TEMPERATURE`, `OPENAI_TRANSLATION_MAX_CHARS` (optionnels, voir `lib/openai/client.ts`)

## Endpoint

`POST /api/admin/vaults/{slug}/auto-translate-locale`  
Corps JSON : `{ "targetLocale": "en" | "it" }`  
Session admin requise. Réponse : phases `copy` (source FR draft vs published), `translate` (compteurs champs / tokens approximatifs), `verify` (agrégats `collectVaultDraftFindings` + échantillon de constats).

## Fichiers principaux

- `src/lib/admin/vaultAutoTranslateAllowlist.ts` — heuristiques d’exclusion (URL, UUID, nombre court).
- `src/lib/admin/vaultAutoTranslateModules.ts` — allowlist par **type de module** (champs traduits explicitement).
- `src/lib/admin/vaultAutoTranslateEngine.ts` — racine vault (`pageTitle.text`, `fixedBottomCta.label`), PageI18n, agrégation stats, vérif.
- `src/app/api/admin/vaults/[slug]/auto-translate-locale/route.ts` — persistance **DRAFT** + `PageI18n` uniquement.

## Modules non reconnus

Les types absents du switch dans `vaultAutoTranslateModules.ts` sont **laissés intacts** (pas de traduction globale du JSON).
