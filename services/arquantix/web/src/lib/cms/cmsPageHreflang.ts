import { ContentStatus, Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import {
  defaultLocale,
  isValidLocale,
  supportedLocales,
  type Locale,
} from '@/config/locales'
import { getSiteOrigin } from '@/lib/metadata/siteOrigin'

function hasText(s: string | null | undefined): boolean {
  return Boolean(s?.trim())
}

function isPageI18nTableMissing(e: unknown): boolean {
  return (
    e instanceof Prisma.PrismaClientKnownRequestError &&
    e.code === 'P2021' &&
    typeof (e.meta as { table?: string } | undefined)?.table === 'string' &&
    String((e.meta as { table: string }).table).includes('page_i18n')
  )
}

/**
 * Locales éligibles au hreflang pour une page CMS (phase 2C — règle stricte) :
 *
 * 1. Au moins une ligne `SectionContent` **PUBLISHED** pour cette page et cette locale
 *    (contenu réellement publié dans la langue).
 * 2. **Et** signal SEO pour cette locale :
 *    - si `locale === defaultLocale` : `PageI18n(fr)` avec titre ou description **ou** legacy `Page.title` / `description` ;
 *    - sinon : `PageI18n(locale)` avec titre **ou** description non vide (pas de variante « metadata vide » annoncée).
 *
 * Ainsi on n’émet pas de hreflang vers une langue sans contenu publié ni sans métadonnées éditoriales pour les locales non défaut.
 */
export async function getLocalesQualifiedForHreflang(pageId: string): Promise<Locale[]> {
  const page = await prisma.page.findUnique({
    where: { id: pageId },
    select: { title: true, description: true },
  })
  if (!page) return []

  let publishedLocales: { locale: string }[]
  let i18nRows: Awaited<ReturnType<typeof prisma.pageI18n.findMany>>

  try {
    ;[publishedLocales, i18nRows] = await Promise.all([
      prisma.sectionContent.findMany({
        where: {
          status: ContentStatus.PUBLISHED,
          section: { pageId },
        },
        select: { locale: true },
        distinct: ['locale'],
      }),
      prisma.pageI18n.findMany({ where: { pageId } }),
    ])
  } catch (e) {
    if (isPageI18nTableMissing(e)) {
      publishedLocales = await prisma.sectionContent.findMany({
        where: {
          status: ContentStatus.PUBLISHED,
          section: { pageId },
        },
        select: { locale: true },
        distinct: ['locale'],
      })
      i18nRows = []
    } else {
      throw e
    }
  }

  const withPublished = new Set(
    publishedLocales.map((r) => r.locale).filter((l): l is Locale => isValidLocale(l)),
  )

  const i18nByLocale = Object.fromEntries(i18nRows.map((r) => [r.locale, r])) as Record<
    string,
    (typeof i18nRows)[0]
  >

  const qualified: Locale[] = []
  for (const loc of supportedLocales) {
    if (!withPublished.has(loc)) continue

    const row = i18nByLocale[loc]
    if (loc === defaultLocale) {
      const seo =
        hasText(row?.title) ||
        hasText(row?.description) ||
        hasText(page.title) ||
        hasText(page.description)
      if (seo) qualified.push(loc)
    } else if (hasText(row?.title) || hasText(row?.description)) {
      qualified.push(loc)
    }
  }

  return qualified
}

/**
 * URLs absolues pour `alternates.languages` (+ `x-default` → locale par défaut).
 * Retourne `undefined` si pas d’origine site (`NEXT_PUBLIC_SITE_URL` / `VERCEL_URL`) — pas de hreflang relatif.
 */
export function buildHreflangLanguageUrls(
  qualifiedLocales: Locale[],
  pathForLocale: (loc: Locale) => string,
): Record<string, string> | undefined {
  const origin = getSiteOrigin()
  if (!origin || qualifiedLocales.length === 0) return undefined

  const out: Record<string, string> = {}
  for (const loc of qualifiedLocales) {
    try {
      const path = pathForLocale(loc)
      const p = path.startsWith('/') ? path : `/${path}`
      out[loc] = new URL(p, `${origin}/`).toString()
    } catch {
      /* ignore */
    }
  }

  if (qualifiedLocales.includes(defaultLocale)) {
    try {
      const p = pathForLocale(defaultLocale)
      const path = p.startsWith('/') ? p : `/${p}`
      out['x-default'] = new URL(path, `${origin}/`).toString()
    } catch {
      /* optional */
    }
  }

  return Object.keys(out).length > 0 ? out : undefined
}
