import { NextResponse } from 'next/server'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'

/**
 * Politique i18n publique (pas d’auth). Cache court : même valeur pour tous les visiteurs.
 */
export async function GET() {
  const s = await getSiteI18nSettingsUncached()
  return NextResponse.json(
    {
      multilingual: s.multilingualEnabled,
      defaultLocale: s.defaultLocale,
      supportedLocales: s.supportedLocales,
    },
    {
      headers: {
        'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=120',
      },
    },
  )
}
