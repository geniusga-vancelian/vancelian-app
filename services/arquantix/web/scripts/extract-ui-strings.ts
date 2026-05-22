/* eslint-disable no-console */
import path from 'node:path'

import { PrismaClient } from '@prisma/client'

import { readArbDirectory } from '../src/lib/i18n/uiStrings/arbReader'
import { extractArbToDb } from '../src/lib/i18n/uiStrings/extractor'

/// Lecture directe (CLI Node, hors React Server Components — on n'utilise donc
/// pas `siteI18nSettings.ts` qui dépend de `react.cache`).
async function readDefaultLocale(prisma: PrismaClient): Promise<string> {
  const row = await prisma.appSettings.findUnique({ where: { id: 'default' } })
  if (row?.defaultLocale && row.defaultLocale.trim().length > 0) {
    return row.defaultLocale.trim()
  }
  return 'en'
}

/**
 * CLI : `npm run i18n:extract`
 *
 * Lit tous les fichiers ARB du dossier `services/arquantix/mobile/lib/l10n`
 * et synchronise (idempotent) la table `cms_ui_strings` (status DRAFT).
 *
 * Idempotence : ne touche jamais aux overrides admin (cf. `extractor.ts`).
 */
async function main() {
  const arbDir = path.resolve(
    process.cwd(),
    '../mobile/lib/l10n',
  )
  console.log(`[i18n:extract] reading ARB files from ${arbDir}`)

  const arbs = await readArbDirectory(arbDir)
  if (arbs.length === 0) {
    console.error('[i18n:extract] no ARB files found.')
    process.exit(1)
  }

  console.log(
    `[i18n:extract] found ${arbs.length} locale(s): ${arbs.map((a) => a.locale).join(', ')}`,
  )

  const prisma = new PrismaClient()
  try {
    const defaultLocale = await readDefaultLocale(prisma)
    console.log(`[i18n:extract] default locale (admin) = ${defaultLocale}`)
    if (!arbs.some((a) => a.locale === defaultLocale)) {
      console.warn(
        `[i18n:extract] warning: ARB files do not contain default locale "${defaultLocale}". sourceText will fall back to per-locale value.`,
      )
    }

    const stats = await extractArbToDb(prisma, arbs, {
      defaultLocale,
      strictKeys: false,
    })

    console.log('[i18n:extract] done:')
    console.log(`  totalKeys      : ${stats.totalKeys}`)
    console.log(`  created (DRAFT): ${stats.created}`)
    console.log(`  updatedFull    : ${stats.updatedFull}`)
    console.log(`  updatedMetaOnly: ${stats.updatedMetaOnly}`)
    if (stats.invalidKeys.length > 0) {
      console.log(`  invalidKeys (kept as misc.*): ${stats.invalidKeys.length}`)
      console.log(`    ${stats.invalidKeys.slice(0, 10).join(', ')}${stats.invalidKeys.length > 10 ? '…' : ''}`)
    }
  } finally {
    await prisma.$disconnect()
  }
}

main().catch((err) => {
  console.error('[i18n:extract] fatal:', err)
  process.exit(1)
})
