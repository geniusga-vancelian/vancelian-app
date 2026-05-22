import { createHash } from 'node:crypto'

import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'

/**
 * GET /api/mobile/flutter/ui-strings?locale=…
 *
 * Bundle public **opt-in d'overrides**. Renvoie uniquement les keys dont
 * `value` diffère de `sourceText` (i.e. quelqu'un a customisé la traduction
 * côté admin) et qui sont **PUBLISHED**.
 *
 * Conséquence importante :
 *  - L'app Flutter consomme normalement `AppLocalizations` (ARB compilé).
 *  - Pour chaque key présente dans ce bundle, le runtime `RemoteStringsService`
 *    surcharge.
 *  - **Si le bundle est vide ou n'arrive pas (offline), l'app fonctionne
 *    exactement comme aujourd'hui** (fallback ARB compilé).
 *
 * En-têtes :
 *  - `ETag` : SHA1 du payload — le client peut envoyer `If-None-Match`
 *    pour économiser la bande passante.
 *  - `Cache-Control: public, s-maxage=60, stale-while-revalidate=300` —
 *    cache CDN court (60 s), tolère 5 min d'obsolescence pendant refresh.
 *
 * Locale fallback : `requested → defaultLocale → any` (cf. landing-pages).
 *
 * Format de réponse :
 * ```
 * {
 *   "bundleVersion": "<sha1>",
 *   "locale": "fr",
 *   "strings": { "exclusiveOfferInvestCtaDefault": "Investir", ... },
 *   "meta": { defaultLocale, supportedLocales, contentLocale, count }
 * }
 * ```
 */
export async function GET(request: NextRequest) {
  try {
    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale

    /// 1) Tentative pour la locale demandée
    let rows = await fetchOverrides(requestedLocale)
    let contentLocale = requestedLocale

    /// 2) Fallback `defaultLocale` si vide
    if (rows.length === 0 && requestedLocale !== i18n.defaultLocale) {
      rows = await fetchOverrides(i18n.defaultLocale)
      contentLocale = i18n.defaultLocale
    }

    /// On expose le bundle même si vide : l'app saura que rien n'override.
    /// Pas de fallback "any locale" ici — si la locale n'a aucun override,
    /// renvoyer un bundle vide est exactement la sémantique attendue
    /// (utiliser ARB compilé partout).

    const stringsObj: Record<string, string> = {}
    for (const r of rows) stringsObj[r.key] = r.value

    /// ETag = SHA1 stable sur (locale, keys triées, valeurs). On utilise les
    /// keys triées pour assurer une stabilité indépendamment de l'ordre Prisma.
    const sortedEntries = Object.entries(stringsObj).sort(([a], [b]) => a.localeCompare(b))
    const canonical = JSON.stringify({ locale: contentLocale, entries: sortedEntries })
    const etag = `"W/${createHash('sha1').update(canonical).digest('hex')}"`

    /// HTTP 304 Not Modified si le client a déjà la version courante.
    const ifNoneMatch = request.headers.get('if-none-match')
    if (ifNoneMatch && ifNoneMatch === etag) {
      return new NextResponse(null, {
        status: 304,
        headers: {
          ETag: etag,
          'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300',
        },
      })
    }

    return NextResponse.json(
      {
        bundleVersion: etag.replace(/^"W\/|"$/g, ''),
        locale: contentLocale,
        strings: stringsObj,
        meta: {
          requestedLocale,
          contentLocale,
          defaultLocale: i18n.defaultLocale,
          supportedLocales: i18n.supportedLocales,
          count: sortedEntries.length,
        },
      },
      {
        headers: {
          ETag: etag,
          'Cache-Control': 'public, s-maxage=60, stale-while-revalidate=300',
          'Content-Type': 'application/json; charset=utf-8',
        },
      },
    )
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/mobile/flutter/ui-strings GET]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', message: 'The request could not be completed.' },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}

async function fetchOverrides(locale: string) {
  /// On ne renvoie que les keys overridées (value ≠ sourceText) — c'est la
  /// définition stricte d'un "override" dans notre modèle. Les keys identiques
  /// au source ARB n'ont aucune raison d'être renvoyées (l'app fallback dessus).
  return prisma.cmsUiString.findMany({
    where: {
      locale,
      status: ContentStatus.PUBLISHED,
      NOT: { value: { equals: prisma.cmsUiString.fields.sourceText } },
    },
    select: { key: true, value: true },
    orderBy: { key: 'asc' },
  })
}
