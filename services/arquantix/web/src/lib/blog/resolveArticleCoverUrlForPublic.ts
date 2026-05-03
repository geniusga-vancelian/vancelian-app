import { getPresignedUrl } from '@/lib/storage/storageClient'

type CoverMediaLike = { url: string; key: string | null } | null | undefined

/**
 * URL publique pour la cover d’un article (pré-signée si la ligne Media a un `key` S3).
 * Aligné sur `getPublicArticle` / `getArticleBySlug`.
 */
export async function resolveArticleCoverUrlForPublic(
  coverMedia: CoverMediaLike,
): Promise<string> {
  if (!coverMedia) return ''
  let coverUrl = coverMedia.url || ''
  if (coverMedia.key) {
    try {
      coverUrl = await getPresignedUrl(coverMedia.key, 3600)
    } catch {
      /* garde coverUrl */
    }
  }
  return coverUrl
}
