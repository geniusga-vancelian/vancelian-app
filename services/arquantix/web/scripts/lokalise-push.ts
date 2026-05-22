/* eslint-disable no-console */
import { ContentStatus, PrismaClient } from '@prisma/client'

import {
  lokaliseUploadArb,
  readLokaliseConfig,
} from '../src/lib/i18n/uiStrings/lokaliseClient'

/**
 * CLI : `npm run i18n:lokalise:push`
 *
 * Reconstruit un fichier ARB par locale à partir de la table `cms_ui_strings`
 * (status DRAFT) et l'upload vers Lokalise. Lokalise mergera les keys côté
 * serveur (préservant les traductions existantes) et notifiera les
 * collaborateurs des nouveaux strings à traduire.
 *
 * Mode opt-in : si `LOKALISE_API_TOKEN` ou `LOKALISE_PROJECT_ID` est absent,
 * on log un warning et on quitte avec code 0 (pas une erreur).
 */
async function main() {
  const cfg = readLokaliseConfig()
  if (!cfg) {
    console.warn(
      '[i18n:lokalise:push] LOKALISE_API_TOKEN / LOKALISE_PROJECT_ID not set — skipping. ' +
        'Set both env vars to enable Lokalise sync.',
    )
    process.exit(0)
  }

  const prisma = new PrismaClient()
  try {
    /// On groupe par locale, en ne retenant que les rows DRAFT (= la "source
    /// of truth" admin actuelle). PUBLISHED est un sous-ensemble et n'est pas
    /// utilisé pour l'export — on veut envoyer toutes les keys, traduites ou
    /// non, pour que Lokalise ait une vue complète.
    const rows = await prisma.cmsUiString.findMany({
      where: { status: ContentStatus.DRAFT },
      orderBy: [{ locale: 'asc' }, { key: 'asc' }],
    })
    if (rows.length === 0) {
      console.warn('[i18n:lokalise:push] no rows in cms_ui_strings (DRAFT) — nothing to push.')
      process.exit(0)
    }

    const byLocale = new Map<string, typeof rows>()
    for (const r of rows) {
      const list = byLocale.get(r.locale) ?? []
      list.push(r)
      byLocale.set(r.locale, list)
    }

    for (const [locale, items] of byLocale) {
      /// Reconstitution d'un ARB conforme à la spec Flutter (clé + metadata).
      const arb: Record<string, unknown> = { '@@locale': locale }
      for (const it of items) {
        arb[it.key] = it.value
        const metaKey = `@${it.key}`
        const meta: Record<string, unknown> = {}
        if (it.description) meta.description = it.description
        if (it.placeholders && typeof it.placeholders === 'object') {
          meta.placeholders = it.placeholders
        }
        if (Object.keys(meta).length > 0) arb[metaKey] = meta
      }
      const arbContent = JSON.stringify(arb, null, 2)
      console.log(`[i18n:lokalise:push] uploading ${items.length} keys for locale=${locale}…`)
      const res = await lokaliseUploadArb(cfg, {
        filename: `app_${locale}.arb`,
        arbContent,
        langIso: locale,
      })
      console.log(`  → process_id=${res.processId}`)
    }

    console.log('[i18n:lokalise:push] done.')
  } finally {
    await prisma.$disconnect()
  }
}

main().catch((err) => {
  console.error('[i18n:lokalise:push] fatal:', err)
  process.exit(1)
})
