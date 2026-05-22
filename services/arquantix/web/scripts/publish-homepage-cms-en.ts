/**
 * Traduit la homepage Vancelian (slug=home) vers l'anglais et publie en CMS :
 * - source : contenu FR PUBLISHED
 * - traduction champ par champ via OpenAI (politique `sectionI18nPolicy`)
 * - texte déjà en anglais → conservé tel quel
 * - localisation des href `/fr/…` → `/en/…`
 * - upsert SectionContent PUBLISHED locale=en + PageI18n en
 *
 * Prérequis : OPENAI_API_KEY, DATABASE_URL
 *
 * Usage : npx tsx scripts/publish-homepage-cms-en.ts
 */

import { PrismaClient, ContentStatus, Prisma, TranslationStatus } from '@prisma/client'
import { classifyTextForTargetLocale } from '@/lib/i18n/integrity/languageStatus'
import {
  getStringAtLot1Path,
  setStringAtLot1Path,
} from '@/lib/i18n/integrity/fieldPathAccess'
import { expandTranslatablePaths } from '@/lib/i18n/translatablePathExpansion'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { resolveSectionI18nPolicy } from '@/lib/sections/sectionI18nPolicy'
import { translateSectionData } from '@/lib/translate/translateSectionData'
import { translateText } from '@/lib/translate/translateText'
import { getGlossary } from '@/lib/translate/getGlossary'
import { replaceLeadingLocaleInPathname } from '@/lib/i18n/rootLocaleRedirect'
import type { Locale } from '@/config/locales'

const prisma = new PrismaClient()
const PAGE_SLUG = 'home'
const TARGET_LOCALE: Locale = 'en'
const SOURCE_LOCALE: Locale = 'fr'

const HREF_KEY = /^(href|.*Href)$/i
const FR_ACCENT_RE = /[éèêëàâîïôûùçœÉÈÊËÀÂÎÏÔÛÙÇŒ]/
const FR_WORD_RE =
  /\b(aujourd|télécharger|découvrir|famille|plusieurs|immobilier|téléchargements|gestion|intérêts|versés|offres|épargne|cryptos|carte|japon|émirats|indonésie|ouverte|étape|notre|votre|patrimoine|sécurité|inscription|application|ils|elles|nous|vous|parlent|parle|choisissons|devient|récoltez|trimestre|distribués|disponibles|sélectionnés|sélection|processus|compte|carte|épargne)\b/i

/** Ne conserve la source que si la langue anglaise est clairement détectée. */
function isAlreadyEnglish(text: string): boolean {
  const cls = classifyTextForTargetLocale(text, TARGET_LOCALE)
  if (cls.status === 'OK') return true
  if (cls.status === 'WRONG_LANGUAGE' && cls.detectedLocale === 'en') return true
  return false
}

function looksFrench(text: string): boolean {
  const cls = classifyTextForTargetLocale(text, TARGET_LOCALE)
  if (cls.status === 'WRONG_LANGUAGE' && cls.detectedLocale === 'fr') return true
  if (cls.status === 'OK' && cls.detectedLocale === 'en') return false
  return FR_ACCENT_RE.test(text) || FR_WORD_RE.test(text)
}

function localizeHrefs(value: unknown, locale: Locale): unknown {
  if (value == null) return value
  if (typeof value === 'string') {
    if (/^\/(fr|en|it)(\/|$)/.test(value)) {
      return replaceLeadingLocaleInPathname(value, locale)
    }
    return value
  }
  if (Array.isArray(value)) {
    return value.map((item) => localizeHrefs(item, locale))
  }
  if (typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
      if (HREF_KEY.test(key) && typeof child === 'string') {
        out[key] =
          /^\/(fr|en|it)(\/|$)/.test(child)
            ? replaceLeadingLocaleInPathname(child, locale)
            : child
      } else {
        out[key] = localizeHrefs(child, locale)
      }
    }
    return out
  }
  return value
}

async function translateSectionFromFr(
  frData: Record<string, unknown>,
  sectionKey: string,
  glossary: Awaited<ReturnType<typeof getGlossary>>,
): Promise<Record<string, unknown>> {
  const translated = (await translateSectionData(frData, sectionKey, {
    sourceLocale: SOURCE_LOCALE,
    targetLocale: TARGET_LOCALE,
    glossary: glossary ?? undefined,
  })) as Record<string, unknown>

  const canonicalKey = resolveCanonicalSectionKey(sectionKey)
  const policy = resolveSectionI18nPolicy(sectionKey, canonicalKey)
  if (policy.kind !== 'translatable') {
    return translated
  }

  const merged =
    typeof structuredClone !== 'undefined'
      ? structuredClone(translated)
      : (JSON.parse(JSON.stringify(translated)) as Record<string, unknown>)

  for (const abstractPath of policy.paths) {
    for (const concretePath of expandTranslatablePaths(frData, abstractPath)) {
      const lookupPath = `data.${concretePath}`
      const frValue = getStringAtLot1Path(frData, 'cms_section', lookupPath)
      if (typeof frValue !== 'string' || !frValue.trim()) continue

      const enValue = getStringAtLot1Path(merged, 'cms_section', lookupPath)
      if (typeof enValue !== 'string') continue

      if (isAlreadyEnglish(frValue)) {
        setStringAtLot1Path(merged, 'cms_section', lookupPath, frValue)
        continue
      }

      if (isAlreadyEnglish(enValue)) continue

      if (looksFrench(enValue) || enValue === frValue) {
        const retry = await translateText(frValue, {
          sourceLocale: SOURCE_LOCALE,
          targetLocale: TARGET_LOCALE,
          glossary: glossary ?? undefined,
        })
        setStringAtLot1Path(merged, 'cms_section', lookupPath, retry.translated)
      }
    }
  }

  return merged
}

async function main() {
  const glossary = await getGlossary()

  const page = await prisma.page.findUnique({
    where: { slug: PAGE_SLUG },
    include: {
      pageI18n: true,
      sections: {
        orderBy: { order: 'asc' },
        include: {
          contents: {
            where: { status: ContentStatus.PUBLISHED, locale: SOURCE_LOCALE },
          },
        },
      },
    },
  })

  if (!page) {
    throw new Error(`Page "${PAGE_SLUG}" introuvable`)
  }

  const frPageI18n = page.pageI18n.find((row) => row.locale === SOURCE_LOCALE)

  console.log(`Traduction homepage ${SOURCE_LOCALE} → ${TARGET_LOCALE} (${page.sections.length} sections)…`)

  let publishedSections = 0
  for (const section of page.sections) {
    const frPublished = section.contents[0]
    if (!frPublished?.data || typeof frPublished.data !== 'object' || Array.isArray(frPublished.data)) {
      console.warn(`  skip ${section.key} — pas de PUBLISHED ${SOURCE_LOCALE}`)
      continue
    }

    const frData = frPublished.data as Record<string, unknown>
    const translated = await translateSectionFromFr(frData, section.key, glossary)
    const localized = localizeHrefs(translated, TARGET_LOCALE) as Prisma.InputJsonObject

    await prisma.sectionContent.upsert({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: TARGET_LOCALE,
          status: ContentStatus.PUBLISHED,
        },
      },
      update: {
        data: localized,
        translationStatus: TranslationStatus.MACHINE,
      },
      create: {
        sectionId: section.id,
        locale: TARGET_LOCALE,
        status: ContentStatus.PUBLISHED,
        data: localized,
        translationStatus: TranslationStatus.MACHINE,
      },
    })
    publishedSections++
    console.log(`  published ${section.key}`)
  }

  const frTitle = frPageI18n?.title ?? page.title
  const frDescription = frPageI18n?.description ?? page.description

  let enTitle = frTitle
  let enDescription = frDescription ?? null

  if (frTitle && !isAlreadyEnglish(frTitle)) {
    enTitle = (
      await translateText(frTitle, {
        sourceLocale: SOURCE_LOCALE,
        targetLocale: TARGET_LOCALE,
        glossary: glossary ?? undefined,
      })
    ).translated
  }
  if (frDescription && !isAlreadyEnglish(frDescription)) {
    enDescription = (
      await translateText(frDescription, {
        sourceLocale: SOURCE_LOCALE,
        targetLocale: TARGET_LOCALE,
        glossary: glossary ?? undefined,
      })
    ).translated
  }

  await prisma.pageI18n.upsert({
    where: {
      pageId_locale: {
        pageId: page.id,
        locale: TARGET_LOCALE,
      },
    },
    update: {
      title: enTitle,
      description: enDescription,
      ogTitle: enTitle,
      ogDescription: enDescription,
    },
    create: {
      pageId: page.id,
      locale: TARGET_LOCALE,
      title: enTitle,
      description: enDescription,
      ogTitle: enTitle,
      ogDescription: enDescription,
    },
  })

  console.log(
    `Done. ${publishedSections} sections EN PUBLISHED + PageI18n. Visitez http://localhost:3100/en`,
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
