import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

/**
 * GET /api/mobile/flutter/activation-hero-image
 *
 * Compatibilité : l’app utilise surtout `activation_journey.hero_image_url` (API Python)
 * et [Config.activationHeaderHeroUrl] côté Flutter. Optionnel : `ACTIVATION_JOURNEY_HERO_IMAGE_URL`
 * (même valeur que l’API / profil).
 */
export async function GET() {
  const url = (process.env.ACTIVATION_JOURNEY_HERO_IMAGE_URL ?? '').trim()
  return NextResponse.json({ imageUrl: url.length > 0 ? url : null })
}
