import { NextResponse } from 'next/server'

import { resolveIntroVideoUrl } from '@/lib/admin/resolveIntroVideoUrl'
import { getPresignedUrl, getPublicUrl } from '@/lib/storage/storageClient'

export const dynamic = 'force-dynamic'

/**
 * GET /api/mobile/flutter/welcome
 *
 * Retourne l’URL du visuel d’accueil (image) + optionnellement la vidéo d’intro (même source que /admin/login0 : dernier média vidéo Admin ou env).
 * Priorité image : WELCOME_HERO_IMAGE_URL → clé R2 (WELCOME_HERO_R2_KEY).
 */
export async function GET() {
  const heroVideoUrl = await resolveIntroVideoUrl()

  const direct = process.env.WELCOME_HERO_IMAGE_URL?.trim()
  if (direct) {
    return NextResponse.json({ heroImageUrl: direct, heroVideoUrl: heroVideoUrl ?? null })
  }

  const key =
    process.env.WELCOME_HERO_R2_KEY?.trim() ||
    'media/1775206317914-mtsym61mcto.png'
  // Par défaut : URL présignée (le domaine pub-*.r2.dev renvoie souvent 401 si le bucket n’est pas public).
  const usePublicUrl =
    process.env.WELCOME_HERO_USE_PRESIGNED === 'false' ||
    process.env.WELCOME_HERO_USE_PRESIGNED === '0'

  try {
    const heroImageUrl = usePublicUrl
      ? getPublicUrl(key)
      : await getPresignedUrl(key, 7 * 24 * 60 * 60)
    return NextResponse.json({ heroImageUrl, heroVideoUrl: heroVideoUrl ?? null })
  } catch (e) {
    console.error('[api/mobile/flutter/welcome]', e)
    return NextResponse.json(
      {
        heroImageUrl: null,
        heroVideoUrl: heroVideoUrl ?? null,
        error:
          'Configurez WELCOME_HERO_IMAGE_URL ou R2 (WELCOME_HERO_R2_KEY + credentials).',
      },
      { status: 503 },
    )
  }
}
