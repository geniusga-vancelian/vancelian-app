import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'

/**
 * Dernière vidéo Admin Media, ou override env (même logique que /admin/login0).
 */
export async function resolveIntroVideoUrl(): Promise<string | undefined> {
  const fromEnv =
    process.env.ADMIN_LOGIN0_BG_VIDEO?.trim() ||
    process.env.NEXT_PUBLIC_ADMIN_LOGIN0_BG_VIDEO?.trim()
  if (fromEnv) return fromEnv

  try {
    const media = await prisma.media.findFirst({
      where: { mimeType: { startsWith: 'video/' } },
      orderBy: { createdAt: 'desc' },
    })
    if (!media) return undefined
    try {
      return await getPresignedUrl(media.key, 86_400)
    } catch {
      return media.url
    }
  } catch (e) {
    console.error('[intro-video] Impossible de résoudre la vidéo depuis Media:', e)
    return undefined
  }
}
