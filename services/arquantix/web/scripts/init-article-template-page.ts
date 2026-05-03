/**
 * Initialise la page CMS « article » (gabarit détail article, sous le blog dans l’arborescence)
 * + sections par défaut : reader + recommandations.
 *
 * Usage: npx tsx scripts/init-article-template-page.ts
 *
 * (Comme `next dev` : .env chargé, puis .env.local qui surcharge — ex. DATABASE_URL
 *  sinon l’init écrit sur une autre base que le serveur et GET /api/admin/pages/article 404.)
 */

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { Prisma, PrismaClient, ContentStatus } from '@prisma/client'
import { randomUUID } from 'node:crypto'
import { SECTION_TYPES, type SectionType } from '../src/lib/sections/library'

const ARTICLE_LOCALES = ['fr', 'en', 'it'] as const
type ArticleLocale = (typeof ARTICLE_LOCALES)[number]

const PAGE_I18N: Record<ArticleLocale, { title: string; description: string }> = {
  fr: {
    title: 'Gabarit lecture article (tous les posts)',
    description:
      'Modules communs aux pages de détail du blog. Le texte éditorial de chaque article se gère dans Admin → Articles.',
  },
  en: {
    title: 'Article reading layout (all posts)',
    description:
      'Shared layout modules for blog article pages. Editorial copy for each post is managed in Admin → Articles.',
  },
  it: {
    title: 'Layout di lettura articolo (tutti i post)',
    description:
      'Moduli di layout condivisi per le pagine articolo del blog. Il testo di ogni articolo vive in Admin → Articoli.',
  },
}

const READER_I18N: Record<
  ArticleLocale,
  { blogLabel: string; tocTitle: string; documentsTitle: string; readingTimeLabel: string }
> = {
  fr: {
    blogLabel: 'Blog',
    tocTitle: 'Dans cet article',
    documentsTitle: 'Documents',
    readingTimeLabel: '{{minutes}} min de lecture',
  },
  en: {
    blogLabel: 'Blog',
    tocTitle: 'In this article',
    documentsTitle: 'Documents',
    readingTimeLabel: '{{minutes}} min read',
  },
  it: {
    blogLabel: 'Blog',
    tocTitle: 'In questo articolo',
    documentsTitle: 'Documenti',
    readingTimeLabel: '{{minutes}} min di lettura',
  },
}

const RELATED_I18N: Record<ArticleLocale, { title: string; ctaLabel: string; emptyTitle: string }> =
  {
    fr: {
      title: 'Vous aimerez aussi',
      ctaLabel: 'Voir tous les articles',
      emptyTitle: 'Aucun article suggéré pour le moment.',
    },
    en: {
      title: 'You may also like',
      ctaLabel: 'View all articles',
      emptyTitle: 'No suggested articles at the moment.',
    },
    it: {
      title: 'Potrebbe interessarti',
      ctaLabel: 'Vedi tutti gli articoli',
      emptyTitle: 'Nessun articolo suggerito al momento.',
    },
  }

const SHARE_TITLE: Record<ArticleLocale, string> = {
  fr: 'Partager',
  en: 'Share',
  it: 'Condividi',
}

const SHARE_A11Y: Record<ArticleLocale, [string, string, string, string]> = {
  fr: [
    'Partager sur Facebook',
    'Partager sur X',
    'Partager sur LinkedIn',
    'Partager sur Threads',
  ],
  en: ['Share on Facebook', 'Share on X', 'Share on LinkedIn', 'Share on Threads'],
  it: [
    'Condividi su Facebook',
    'Condividi su X',
    'Condividi su LinkedIn',
    'Condividi su Threads',
  ],
}

type ArticleTemplateSectionKey = 'blog_article_reader' | 'share_sm' | 'blog_article_related'

const SECTION_KEYS: ArticleTemplateSectionKey[] = [
  'blog_article_reader',
  'share_sm',
  'blog_article_related',
]

function buildSectionData(
  sectionKey: ArticleTemplateSectionKey,
  locale: ArticleLocale,
  sectionType: SectionType,
): Prisma.InputJsonValue {
  const base = sectionType.defaultData
  if (sectionKey === 'blog_article_reader') {
    const r = READER_I18N[locale]
    return {
      ...base,
      ...r,
      showToc: true,
      tocMinHeadings: 3,
      showDocuments: true,
      showAuthorByPrefix: true,
      showUpdatedDate: true,
    } as Prisma.InputJsonValue
  }
  if (sectionKey === 'blog_article_related') {
    return {
      ...base,
      ...RELATED_I18N[locale],
      ctaHref: typeof base === 'object' && base && 'ctaHref' in base ? (base as { ctaHref?: string }).ctaHref : '',
      limit: 4,
    } as Prisma.InputJsonValue
  }
  if (sectionKey === 'share_sm') {
    const b = base as { title?: string; items?: Array<Record<string, unknown>> }
    const items = Array.isArray(b.items) ? [...b.items] : []
    const labels = SHARE_A11Y[locale]
    for (let j = 0; j < items.length; j++) {
      if (typeof labels[j] === 'string') {
        items[j] = { ...items[j], label: labels[j] }
      }
    }
    return { title: SHARE_TITLE[locale], items } as Prisma.InputJsonValue
  }
  return base as Prisma.InputJsonValue
}

/** Même ordre que Next : .env, puis .env.local (surcharge). */
function loadWebEnvFromCwd() {
  const root = process.cwd()
  for (const file of ['.env', '.env.local'] as const) {
    const p = join(root, file)
    if (!existsSync(p)) continue
    const text = readFileSync(p, 'utf8')
    for (const line of text.split('\n')) {
      let t = line.trim()
      if (!t || t.startsWith('#')) continue
      if (t.startsWith('export ')) t = t.slice(7).trim()
      const eq = t.indexOf('=')
      if (eq === -1) continue
      const key = t.slice(0, eq).trim()
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(key)) continue
      let v = t.slice(eq + 1).trim()
      if (
        (v.startsWith('"') && v.endsWith('"')) ||
        (v.startsWith("'") && v.endsWith("'"))
      ) {
        v = v.slice(1, -1)
      }
      process.env[key] = v
    }
  }
}
loadWebEnvFromCwd()

const prisma = new PrismaClient()

const PAGE_DESCRIPTION =
  "Gabarit de mise en page pour la lecture d'un article de blog (modules CMS)."

async function getPagesColumnNames(): Promise<Set<string>> {
  const r = await prisma.$queryRaw<Array<{ column_name: string }>>`
    SELECT column_name::text AS column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'pages'
  `
  return new Set(r.map((x) => x.column_name))
}

/**
 * Upsert page « article » en SQL, uniquement sur les colonnes réellement présentes
 * (bases partiellement migrées, sans `migrate deploy` possible).
 */
async function ensureArticlePageRow(): Promise<{ id: string; slug: string }> {
  const col = await getPagesColumnNames()
  const has = (name: string) => col.has(name)

  const rows = await prisma.$queryRaw<{ id: string; slug: string }[]>`
    SELECT id::text AS id, slug FROM pages WHERE slug = 'article' LIMIT 1
  `
  if (rows.length > 0) {
    const sets: string[] = []
    if (has('title')) sets.push(`title = 'Article (gabarit)'`)
    if (has('url_path')) sets.push(`url_path = '/article-template'`)
    if (has('template')) sets.push(`template = 'article'`)
    if (has('description')) {
      const esc = PAGE_DESCRIPTION.replace(/'/g, "''")
      sets.push(`description = '${esc}'`)
    }
    if (has('theme_color')) sets.push(`theme_color = 'light'`)
    if (has('show_in_nav')) sets.push(`show_in_nav = false`)
    if (has('updated_at')) sets.push(`updated_at = NOW()`)
    if (sets.length) {
      await prisma.$executeRawUnsafe(`UPDATE pages SET ${sets.join(', ')} WHERE slug = 'article'`)
    }
    return rows[0]
  }

  const id = `c${randomUUID().replace(/-/g, '').slice(0, 24)}`
  const insertCols: string[] = ['id', 'slug']
  const values: string[] = [`'${id.replace(/'/g, "''")}'`, `'article'`]
  if (has('url_path')) {
    insertCols.push('url_path')
    values.push(`'/article-template'`)
  }
  if (has('title')) {
    insertCols.push('title')
    values.push(`'Article (gabarit)'`)
  }
  if (has('template')) {
    insertCols.push('template')
    values.push(`'article'`)
  }
  if (has('description')) {
    insertCols.push('description')
    values.push(`'${PAGE_DESCRIPTION.replace(/'/g, "''")}'`)
  }
  if (has('theme_color')) {
    insertCols.push('theme_color')
    values.push(`'light'`)
  }
  if (has('show_in_nav')) {
    insertCols.push('show_in_nav')
    values.push('false')
  }
  if (has('page_role')) {
    insertCols.push('page_role')
    values.push(`CAST('STANDARD' AS "PageRole")`)
  }
  if (has('is_system_page')) {
    insertCols.push('is_system_page')
    values.push('false')
  }
  if (has('created_at')) {
    insertCols.push('created_at')
    values.push('NOW()')
  }
  if (has('updated_at')) {
    insertCols.push('updated_at')
    values.push('NOW()')
  }

  await prisma.$executeRawUnsafe(
    `INSERT INTO pages (${insertCols.join(', ')}) VALUES (${values.join(', ')})`,
  )
  return { id, slug: 'article' }
}

async function main() {
  console.log('🌱 Initializing article template page (CMS)…')

  let page: { id: string; slug: string }
  try {
    const p = await prisma.page.upsert({
      where: { slug: 'article' },
      update: {
        template: 'article',
        title: 'Article (gabarit)',
        urlPath: '/article-template',
        themeColor: 'light',
      },
      create: {
        slug: 'article',
        template: 'article',
        title: 'Article (gabarit)',
        urlPath: '/article-template',
        description: PAGE_DESCRIPTION,
        themeColor: 'light',
        showInNav: false,
      },
    })
    page = { id: p.id, slug: p.slug }
  } catch (e) {
    if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2022') {
      console.log(
        '  (schéma DB partiel — upsert Prisma indisponible, utilisation du SQL de secours.)',
      )
      page = await ensureArticlePageRow()
    } else {
      throw e
    }
  }

  console.log(`✅ Page article: ${page.slug}`)

  const pageCols = await getPagesColumnNames()
  if (pageCols.has('parent_id') && pageCols.has('sort_order')) {
    try {
      const blog = await prisma.page.findUnique({ where: { slug: 'blog' }, select: { id: true } })
      if (blog) {
        await prisma.page.update({
          where: { id: page.id },
          data: { parentId: blog.id, sortOrder: 1 },
        })
        console.log('  (hiérarchie : enfant de la page « blog »)')
      }
    } catch {
      console.log('  (hiérarchie parent « blog » non appliquée — erreur de mise à jour.)')
    }
  } else {
    console.log(
      '  (parent « blog » : colonnes parent_id / sort_order absentes — exécutez les migrations Prisma si besoin.)',
    )
  }

  let pageI18nOk = true
  for (const loc of ARTICLE_LOCALES) {
    try {
      const meta = PAGE_I18N[loc]
      await prisma.pageI18n.upsert({
        where: { pageId_locale: { pageId: page.id, locale: loc } },
        update: { title: meta.title, description: meta.description },
        create: {
          pageId: page.id,
          locale: loc,
          title: meta.title,
          description: meta.description,
        },
      })
    } catch (e) {
      if (e instanceof Prisma.PrismaClientKnownRequestError && e.code === 'P2022') {
        console.log('  (table page_i18n absente — migration Prisma requise pour les titres par langue.)')
        pageI18nOk = false
        break
      }
      throw e
    }
  }
  if (pageI18nOk) {
    console.log('  ✅ page_i18n : fr, en, it')
  }

  for (let i = 0; i < SECTION_KEYS.length; i++) {
    const sectionKey = SECTION_KEYS[i]!
    const sectionType = SECTION_TYPES.find((t) => t.key === sectionKey)
    if (!sectionType) {
      console.warn(`⚠️  Section type "${sectionKey}" missing from library, skip`)
      continue
    }

    const section = await prisma.section.upsert({
      where: { pageId_key: { pageId: page.id, key: sectionKey } },
      update: { order: i, schemaVersion: sectionType.schemaVersion },
      create: {
        pageId: page.id,
        key: sectionKey,
        order: i,
        schemaVersion: sectionType.schemaVersion,
      },
    })

    for (const loc of ARTICLE_LOCALES) {
      const data = buildSectionData(sectionKey, loc, sectionType)
      for (const st of [ContentStatus.DRAFT, ContentStatus.PUBLISHED] as const) {
        await prisma.sectionContent.upsert({
          where: { sectionId_locale_status: { sectionId: section.id, locale: loc, status: st } },
          update: { data },
          create: {
            sectionId: section.id,
            locale: loc,
            status: st,
            data,
          },
        })
      }
    }
    console.log(
      `  ✅ ${sectionKey} (brouillons + publiés : ${ARTICLE_LOCALES.join(', ')})`,
    )
  }

  console.log(
    '\nNext: /admin/pages/article (réordonnancement, sections CTA, etc. — contenus de base déjà en fr/en/it).',
  )
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
