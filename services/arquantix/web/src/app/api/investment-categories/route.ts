import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'

/** Fallback quand la table n'existe pas encore (migration non appliquée). */
const FALLBACK_CATEGORIES = [
  { id: 'fallback-1', slug: 'real-estate', label: 'Real estate', imageUrl: null as string | null },
  { id: 'fallback-2', slug: 'energy', label: 'Energy', imageUrl: null },
  { id: 'fallback-3', slug: 'commodity', label: 'Commodity', imageUrl: null },
  { id: 'fallback-4', slug: 'art', label: 'Art', imageUrl: null },
  { id: 'fallback-5', slug: 'infrastructure', label: 'Infrastructure', imageUrl: null },
  { id: 'fallback-6', slug: 'private-equity', label: 'Private equity', imageUrl: null },
  { id: 'fallback-7', slug: 'crypto', label: 'Crypto', imageUrl: null },
]

async function resolveImageUrl(mediaId: string | null, imageUrl: string | null): Promise<string | null> {
  if (mediaId) {
    try {
      const media = await prisma.media.findUnique({ where: { id: mediaId } })
      if (media) {
        try {
          return await getPresignedUrl(media.key, 3600)
        } catch {
          return media.url
        }
      }
    } catch {
      // fallback to imageUrl
    }
  }
  return imageUrl
}

/**
 * GET /api/investment-categories — Liste des catégories d'investissement (API publique, ex. page Offres).
 * Retourne slug, label, imageUrl (résolu depuis media si mediaId présent).
 * Si la table n'existe pas, retourne une liste par défaut (pas de 500).
 */
export async function GET() {
  try {
    const categories = await prisma.investmentCategory.findMany({
      orderBy: { sortOrder: 'asc' },
      select: {
        id: true,
        slug: true,
        label: true,
        imageUrl: true,
        mediaId: true,
      },
    })

    const withResolvedImage = await Promise.all(
      categories.map(async (c) => ({
        id: c.id,
        slug: c.slug,
        label: c.label,
        imageUrl: await resolveImageUrl(c.mediaId, c.imageUrl),
      }))
    )

    return NextResponse.json({
      categories: withResolvedImage.map((c) => ({
        id: c.id,
        slug: c.slug,
        label: c.label,
        imageUrl: c.imageUrl ?? null,
      })),
    })
  } catch (error) {
    console.warn('Investment categories from DB failed, using fallback:', error)
    return NextResponse.json({
      categories: FALLBACK_CATEGORIES.map((c) => ({
        id: c.id,
        slug: c.slug,
        label: c.label,
        imageUrl: c.imageUrl,
      })),
    })
  }
}
