/**
 * Détail offre web + catalogue / vault mobile : `resolveVaultSectionContentForExclusiveOfferPayload`
 * / `resolveVaultSectionContentForCatalog` servent une autre locale lorsque la
 * locale demandée a une ligne présente mais `modules[]` vide (voir implémentation).
 *
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

function rawVaultModulesLength(data: unknown): number {
  const r =
    data != null && typeof data === 'object' && !Array.isArray(data)
      ? (data as Record<string, unknown>)
      : null
  const m = r?.modules
  return Array.isArray(m) ? m.length : 0
}

/**
 * Sélection intra-locale (pas de saut vers une autre langue).
 * Réplique pour une locale donnée :
 * même base que `either`, avec **repli brouillon** si la ligne publiée n’a aucun module
 * alors qu’un brouillon en a.
 */
export function pickCatalogVaultRowForLocale<T extends VaultSectionContentLike & { data: unknown }>(
  contents: T[],
  locale: string,
): T | null {
  const bucket = byLocale(contents, locale)
  if (!bucket.length) return null
  const either = pickEitherInBucket(bucket)
  if (!either) return null
  if (rawVaultModulesLength(either.data) > 0) return either
  if (either.status !== ContentStatus.PUBLISHED) return either
  const draft = bucket.find((c) => c.status === ContentStatus.DRAFT)
  if (draft && rawVaultModulesLength(draft.data) > 0) return draft
  return either
}

/**
 * Intra-locale, aligné sur l’aperçu CMS : brouillon rempli avant pub ; sinon meilleure ligne disponible.
 */
function pickExclusiveOfferPreviewVaultRowForLocale<
  T extends VaultSectionContentLike & { data: unknown },
>(contents: T[], locale: string): T | null {
  const bucket = byLocale(contents, locale)
  if (!bucket.length) return null
  const draft = bucket.find((c) => c.status === ContentStatus.DRAFT)
  const published = bucket.find((c) => c.status === ContentStatus.PUBLISHED)
  if (draft && rawVaultModulesLength(draft.data) > 0) return draft
  if (published && rawVaultModulesLength(published.data) > 0) return published
  return draft ?? published ?? null
}

function localeOrderForCatalog(contents: VaultSectionContentLike[], requestedLocale: string, defaultLocale: string): string[] {
  const trimmedReq = requestedLocale.trim() || defaultLocale.trim()
  const trimmedDef = defaultLocale.trim() || trimmedReq
  const distinct = [...new Set(contents.map((c) => c.locale.trim()).filter(Boolean))]
  const ordered: string[] = []
  const push = (loc: string) => {
    const t = loc.trim()
    if (t && !ordered.includes(t)) ordered.push(t)
  }
  push(trimmedReq)
  if (trimmedDef !== trimmedReq) push(trimmedDef)
  for (const loc of distinct) push(loc)
  return ordered
}

export type ResolveExclusiveOfferVaultContentOptions = {
  requestedLocale: string
  defaultLocale: string
  /** Aperçu admin iframe : même repli **inter-locales** que le public, mais brouillon rempli avant publié. */
  previewDraftFirst: boolean
}

/**
 * Page détail offre (`getExclusiveOfferVaultPayload`) — public et aperçu CMS.
 *
 * Aligné catalogue mobile : intra-locale **pub puis repli brouillon si modules vides**, plus
 * **repli inter-locales** si la ligne locale demandée a `modules.length === 0`.
 */
export function resolveVaultSectionContentForExclusiveOfferPayload<
  T extends VaultSectionContentLike & { data: unknown },
>(contents: T[], options: ResolveExclusiveOfferVaultContentOptions): T | null {
  if (!contents.length) return null
  const { requestedLocale, defaultLocale, previewDraftFirst } = options
  const pick = previewDraftFirst ? pickExclusiveOfferPreviewVaultRowForLocale<T> : pickCatalogVaultRowForLocale<T>
  const order = localeOrderForCatalog(contents, requestedLocale, defaultLocale)
  for (const loc of order) {
    const hit = pick(contents, loc)
    if (hit && rawVaultModulesLength(hit.data) > 0) return hit
  }
  return pick(contents, requestedLocale.trim() || defaultLocale.trim())
}

/**
 * Résolution catalogue / app mobile (`resolveVaultSectionContentForExclusiveOfferPayload` avec pub d’abord).
 */
export function resolveVaultSectionContentForCatalog<T extends VaultSectionContentLike & { data: unknown }>(
  contents: T[],
  options: { requestedLocale: string; defaultLocale: string },
): T | null {
  return resolveVaultSectionContentForExclusiveOfferPayload(contents, {
    ...options,
    previewDraftFirst: false,
  })
}
