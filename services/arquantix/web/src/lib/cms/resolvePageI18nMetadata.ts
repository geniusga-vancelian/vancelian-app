import { Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import { defaultLocale, type Locale } from '@/config/locales'

/** Base Alembic / hors historique Prisma : table `page_i18n` parfois absente tant que la migration n’est pas appliquée. */
function isPageI18nTableMissing(e: unknown): boolean {
  return (
    e instanceof Prisma.PrismaClientKnownRequestError &&
    e.code === 'P2021' &&
    typeof (e.meta as { table?: string } | undefined)?.table === 'string' &&
    String((e.meta as { table: string }).table).includes('page_i18n')
  )
}

/** Champs SEO résolus pour une page et une locale (Phase 2A). */
export type ResolvedPageSeoFields = {
  title: string | null
  description: string | null
  ogTitle: string | null
  ogDescription: string | null
}

function trimOrNull(v: string | null | undefined): string | null {
  const t = v?.trim()
  return t ? t : null
}

/** Champs titre / description alignés sur `Page` ou lignes `PageI18n`. */
export type PageTitleDescriptionFields = {
  title: string | null
  description: string | null
}

/**
 * Titre et description affichables pour une locale, sans requête DB.
 * Règle (identique au reste du CMS / `resolvePageSeoFields`) :
 * 1. `PageI18n` locale demandée
 * 2. sinon `PageI18n` locale par défaut
 * 3. sinon `Page.title` / `Page.description`
 */
export function resolvePageTitleDescriptionWithFallback(
  page: PageTitleDescriptionFields,
  primary: PageTitleDescriptionFields | null | undefined,
  fallbackI18n: PageTitleDescriptionFields | null | undefined,
): PageTitleDescriptionFields {
  return {
    title:
      trimOrNull(primary?.title) ??
      trimOrNull(fallbackI18n?.title) ??
      trimOrNull(page.title) ??
      null,
    description:
      trimOrNull(primary?.description) ??
      trimOrNull(fallbackI18n?.description) ??
      trimOrNull(page.description) ??
      null,
  }
}

/**
 * Résolution metadata pour une page :
 * 1. `PageI18n` pour la locale demandée
 * 2. sinon `PageI18n` pour la locale par défaut (`fr`)
 * 3. sinon `Page.title` / `Page.description`
 *
 * Les champs OG reprennent les champs principaux si les OG dédiés sont absents.
 */
export async function resolvePageSeoFields(pageId: string, locale: Locale): Promise<ResolvedPageSeoFields> {
  const page = await prisma.page.findUnique({
    where: { id: pageId },
    select: { title: true, description: true },
  })
  if (!page) {
    return { title: null, description: null, ogTitle: null, ogDescription: null }
  }

  let primary: Awaited<ReturnType<typeof prisma.pageI18n.findUnique>>
  let fallbackI18n: Awaited<ReturnType<typeof prisma.pageI18n.findUnique>> | null

  try {
    ;[primary, fallbackI18n] = await Promise.all([
      prisma.pageI18n.findUnique({
        where: { pageId_locale: { pageId, locale } },
      }),
      locale !== defaultLocale
        ? prisma.pageI18n.findUnique({
            where: { pageId_locale: { pageId, locale: defaultLocale } },
          })
        : Promise.resolve(null),
    ])
  } catch (e) {
    if (isPageI18nTableMissing(e)) {
      const title = trimOrNull(page.title) ?? null
      const description = trimOrNull(page.description) ?? null
      return {
        title,
        description,
        ogTitle: title,
        ogDescription: description,
      }
    }
    throw e
  }

  const { title, description } = resolvePageTitleDescriptionWithFallback(page, primary, fallbackI18n)

  const ogTitle =
    trimOrNull(primary?.ogTitle) ??
    trimOrNull(primary?.title) ??
    trimOrNull(fallbackI18n?.ogTitle) ??
    trimOrNull(fallbackI18n?.title) ??
    trimOrNull(page.title) ??
    null

  const ogDescription =
    trimOrNull(primary?.ogDescription) ??
    trimOrNull(primary?.description) ??
    trimOrNull(fallbackI18n?.ogDescription) ??
    trimOrNull(fallbackI18n?.description) ??
    trimOrNull(page.description) ??
    null

  return { title, description, ogTitle, ogDescription }
}
