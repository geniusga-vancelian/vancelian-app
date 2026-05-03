/**
 * Initialise la page CMS « exclusive-offer » (gabarit détail offre exclusive, sous le hub projets)
 * + sections par défaut : slot Vault + partage social.
 *
 * Usage: npx tsx scripts/init-exclusive-offer-template-page.ts
 *
 * (Comme `next dev` : .env chargé, puis .env.local qui surcharge — ex. DATABASE_URL.)
 */

import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { Prisma, PrismaClient, ContentStatus } from '@prisma/client'
import { randomUUID } from 'node:crypto'
import { SECTION_TYPES, type SectionType } from '../src/lib/sections/library'

const OFFER_LOCALES = ['fr', 'en', 'it'] as const
type OfferLocale = (typeof OFFER_LOCALES)[number]

const PAGE_SLUG = 'exclusive-offer'
const PAGE_TEMPLATE = 'exclusive_offer'

const PAGE_I18N: Record<OfferLocale, { title: string; description: string }> = {
  fr: {
    title: 'Gabarit offre exclusive (toutes les offres)',
    description:
      'Modules communs aux pages de détail des offres exclusives. Le contenu Vault de chaque offre se gère dans Admin → Exclusive Offers / Vault Builder.',
  },
  en: {
    title: 'Exclusive offer layout (all offers)',
    description:
      'Shared layout modules for exclusive offer pages. Editorial Vault content for each offer is managed in Admin → Exclusive Offers / Vault Builder.',
  },
  it: {
    title: 'Layout offerta esclusiva (tutte le offerte)',
    description:
      'Moduli di layout condivisi per le pagine offerta esclusiva. Il contenuto Vault di ogni offerta è in Admin → Exclusive Offers / Vault Builder.',
  },
}

const SHARE_TITLE: Record<OfferLocale, string> = {
  fr: 'Partager',
  en: 'Share',
  it: 'Condividi',
}

const SHARE_A11Y: Record<OfferLocale, [string, string, string, string]> = {
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

type OfferTemplateSectionKey = 'exclusive_offer_vault' | 'share_sm'

const SECTION_KEYS: OfferTemplateSectionKey[] = ['exclusive_offer_vault', 'share_sm']

function buildSectionData(
  sectionKey: OfferTemplateSectionKey,
  locale: OfferLocale,
  sectionType: SectionType,
): Prisma.InputJsonValue {
  const base = sectionType.defaultData
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
  'Gabarit de mise en page pour la lecture d’une offre exclusive (modules CMS + Vault Builder).'

async function getPagesColumnNames(): Promise<Set<string>> {
  const r = await prisma.$queryRaw<Array<{ column_name: string }>>`
    SELECT column_name::text AS column_name
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'pages'
  `
  return new Set(r.map((x) => x.column_name))
}

async function ensureExclusiveOfferPageRow(): Promise<{ id: string; slug: string }> {
  const col = await getPagesColumnNames()
  const has = (name: string) => col.has(name)

  const rows = await prisma.$queryRaw<{ id: string; slug: string }[]>`
    SELECT id::text AS id, slug FROM pages WHERE slug = ${PAGE_SLUG} LIMIT 1
  `
  if (rows.length > 0) {
    const sets: string[] = []
    if (has('title')) sets.push(`title = 'Offre exclusive (gabarit)'`)
    if (has('url_path')) sets.push(`url_path = '/exclusive-offer-template'`)
    if (has('template')) sets.push(`template = '${PAGE_TEMPLATE}'`)
    if (has('description')) {
      const esc = PAGE_DESCRIPTION.replace(/'/g, "''")
      sets.push(`description = '${esc}'`)
    }
    if (has('theme_color')) sets.push(`theme_color = 'light'`)
    if (has('show_in_nav')) sets.push(`show_in_nav = false`)
    if (has('updated_at')) sets.push(`updated_at = NOW()`)
    if (sets.length) {
      await prisma.$executeRawUnsafe(
        `UPDATE pages SET ${sets.join(', ')} WHERE slug = '${PAGE_SLUG.replace(/'/g, "''")}'`,
      )
    }
    return rows[0]
  }

  const id = `c${randomUUID().replace(/-/g, '').slice(0, 24)}`
  const insertCols: string[] = ['id', 'slug']
  const values: string[] = [`'${id.replace(/'/g, "''")}'`, `'${PAGE_SLUG}'`]
  if (has('url_path')) {
    insertCols.push('url_path')
    values.push(`'/exclusive-offer-template'`)
  }
  if (has('title')) {
    insertCols.push('title')
    values.push(`'Offre exclusive (gabarit)'`)
  }
  if (has('template')) {
    insertCols.push('template')
    values.push(`'${PAGE_TEMPLATE}'`)
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
  return { id, slug: PAGE_SLUG }
}

async function main() {
  console.log('🌱 Initializing exclusive-offer template page (CMS)…')

  let page: { id: string; slug: string }
  try {
    const p = await prisma.page.upsert({
      where: { slug: PAGE_SLUG },
      update: {
        template: PAGE_TEMPLATE,
        title: 'Offre exclusive (gabarit)',
        urlPath: '/exclusive-offer-template',
        themeColor: 'light',
      },
      create: {
        slug: PAGE_SLUG,
        template: PAGE_TEMPLATE,
        title: 'Offre exclusive (gabarit)',
        urlPath: '/exclusive-offer-template',
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
      page = await ensureExclusiveOfferPageRow()
    } else {
      throw e
    }
  }

  console.log(`✅ Page ${page.slug}`)

  const pageCols = await getPagesColumnNames()
  if (pageCols.has('parent_id') && pageCols.has('sort_order')) {
    try {
      const hub = await prisma.page.findFirst({
        where: { OR: [{ pageRole: 'PROJECTS_HUB' }, { slug: 'projects' }] },
        select: { id: true },
      })
      if (hub) {
        await prisma.page.update({
          where: { id: page.id },
          data: { parentId: hub.id, sortOrder: 0 },
        })
        console.log('  (hiérarchie : enfant du hub « projects »)')
      }
    } catch {
      console.log('  (hiérarchie parent « projects » non appliquée — erreur de mise à jour.)')
    }
  } else {
    console.log(
      '  (parent « projects » : colonnes parent_id / sort_order absentes — migrations Prisma si besoin.)',
    )
  }

  let pageI18nOk = true
  for (const loc of OFFER_LOCALES) {
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
        console.log('  (table page_i18n absente — migration Prisma requise.)')
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

    for (const loc of OFFER_LOCALES) {
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
    console.log(`  ✅ ${sectionKey} (brouillons + publiés : ${OFFER_LOCALES.join(', ')})`)
  }

  console.log(
    '\nNext: /admin/pages/exclusive-offer — contenus Vault par offre : Vault Builder / Exclusive Offers.',
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
