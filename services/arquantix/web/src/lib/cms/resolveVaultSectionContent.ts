/**
 * Résolution unique du `SectionContent` Vault (`vault_builder_v1`) par locale.
 * Partagée par le rendu web offre et les APIs mobile `/api/mobile/flutter/vaults`.
 *
 * Règle de fallback (mode `either`, comportement historique page publique web) :
 * 1. Locale demandée : PUBLISHED puis DRAFT
 * 2. Si vide et locale demandée ≠ locale par défaut : locale par défaut, PUBLISHED puis DRAFT
 * 3. Dernier recours : n’importe quelle locale — PUBLISHED puis DRAFT
 *
 * Mode `either_draft_first` (aperçu CMS) :
 * 1. Locale demandée : DRAFT puis PUBLISHED
 * 2. Même logique de fallback de locale, puis DRAFT / PUBLISHED en dernier recours.
 *
 * Modes stricts (`PUBLISHED` ou `DRAFT` uniquement) : mêmes paliers de locale,
 * sans mélanger les statuts ; dernier recours = première ligne au statut demandé
 * en privilégiant l’ordre locale demandée → défaut → autres.
 */
import { ContentStatus } from '@prisma/client'

export type VaultSectionContentLike = {
  locale: string
  status: ContentStatus
}

export type ResolveVaultSectionContentMode =
  | 'either'
  | 'either_draft_first'
  | typeof ContentStatus.PUBLISHED
  | typeof ContentStatus.DRAFT

export type ResolveVaultSectionContentOptions = {
  requestedLocale: string
  defaultLocale: string
  /**
   * - `either` : publié puis brouillon à chaque palier (détail offre web).
   * - `either_draft_first` : brouillon puis publié (aperçu Vault Builder authentifié).
   * - `PUBLISHED` / `DRAFT` : uniquement ce statut à chaque palier (liste mobile, détail mobile).
   */
  mode: ResolveVaultSectionContentMode
}

function pickEitherInBucket<T extends VaultSectionContentLike>(rows: T[]): T | undefined {
  return (
    rows.find((c) => c.status === ContentStatus.PUBLISHED) ||
    rows.find((c) => c.status === ContentStatus.DRAFT)
  )
}

function pickDraftFirstInBucket<T extends VaultSectionContentLike>(rows: T[]): T | undefined {
  return (
    rows.find((c) => c.status === ContentStatus.DRAFT) ||
    rows.find((c) => c.status === ContentStatus.PUBLISHED)
  )
}

function pickStrictInBucket<T extends VaultSectionContentLike>(
  rows: T[],
  status: typeof ContentStatus.PUBLISHED | typeof ContentStatus.DRAFT,
): T | undefined {
  return rows.find((c) => c.status === status)
}

function byLocale<T extends VaultSectionContentLike>(contents: T[], locale: string): T[] {
  return contents.filter((c) => c.locale === locale)
}

function pickFinalStrictAnyLocale<T extends VaultSectionContentLike>(
  contents: T[],
  status: typeof ContentStatus.PUBLISHED | typeof ContentStatus.DRAFT,
  requestedLocale: string,
  defaultLocale: string,
): T | undefined {
  const order = new Set<string>()
  order.add(requestedLocale)
  if (defaultLocale !== requestedLocale) order.add(defaultLocale)
  for (const loc of order) {
    const hit = pickStrictInBucket(byLocale(contents, loc), status)
    if (hit) return hit
  }
  return contents.find((c) => c.status === status)
}

/**
 * Sélectionne un contenu section Vault parmi les lignes `contents` (toutes locales / statuts).
 */
export function resolveVaultSectionContent<T extends VaultSectionContentLike>(
  contents: T[],
  options: ResolveVaultSectionContentOptions,
): T | null {
  if (!contents.length) return null

  const { requestedLocale, defaultLocale, mode } = options

  if (mode === 'either_draft_first') {
    let content = pickDraftFirstInBucket(byLocale(contents, requestedLocale))
    if (content) return content

    if (requestedLocale !== defaultLocale) {
      content = pickDraftFirstInBucket(byLocale(contents, defaultLocale))
      if (content) return content
    }

    const anyDraft = contents.find((c) => c.status === ContentStatus.DRAFT)
    const anyPub = contents.find((c) => c.status === ContentStatus.PUBLISHED)
    return anyDraft || anyPub || null
  }

  if (mode === 'either') {
    let content = pickEitherInBucket(byLocale(contents, requestedLocale))
    if (content) return content

    if (requestedLocale !== defaultLocale) {
      content = pickEitherInBucket(byLocale(contents, defaultLocale))
      if (content) return content
    }

    const anyPub = contents.find((c) => c.status === ContentStatus.PUBLISHED)
    const anyDraft = contents.find((c) => c.status === ContentStatus.DRAFT)
    return anyPub || anyDraft || null
  }

  const strict =
    mode === ContentStatus.PUBLISHED ? ContentStatus.PUBLISHED : ContentStatus.DRAFT

  let content = pickStrictInBucket(byLocale(contents, requestedLocale), strict)
  if (content) return content

  if (requestedLocale !== defaultLocale) {
    content = pickStrictInBucket(byLocale(contents, defaultLocale), strict)
    if (content) return content
  }

  return pickFinalStrictAnyLocale(contents, strict, requestedLocale, defaultLocale) ?? null
}
