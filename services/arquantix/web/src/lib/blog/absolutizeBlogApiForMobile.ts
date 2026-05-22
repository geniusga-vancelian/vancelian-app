/**
 * Le client Flutter résout les images contre une URL absolue ; les champs
 * relatifs (`/media/...`) ou post-presign partiel doivent être préfixés
 * par l’origine de la requête API (ex. http://192.168.x.x:3000).
 */
import { absolutizeMediaUrlForApiClient } from '@/lib/catalog/packagedCatalogHelpers'

import type { ArticleBlockApi, ArticleDetailApi, ArticlePreview, BlogFeedResult } from '@/lib/blog/articleService'

function absOrEmpty(url: string | null | undefined, origin: string | null): string {
  return absolutizeMediaUrlForApiClient(url, origin) ?? ''
}

function absOptional(url: string | null | undefined, origin: string | null): string | null {
  if (url == null || String(url).trim() === '') return url ?? null
  return absolutizeMediaUrlForApiClient(url, origin) ?? url
}

export function absolutizeArticlePreviewForMobile(p: ArticlePreview, origin: string | null): ArticlePreview {
  return {
    ...p,
    coverUrl: absOrEmpty(p.coverUrl, origin),
  }
}

export function absolutizeBlogFeedResultForMobile(feed: BlogFeedResult, origin: string | null): BlogFeedResult {
  const list = (xs: ArticlePreview[]) => xs.map((p) => absolutizeArticlePreviewForMobile(p, origin))
  return {
    ...feed,
    featured: feed.featured ? absolutizeArticlePreviewForMobile(feed.featured, origin) : null,
    highlighted: list(feed.highlighted),
    companyNews: list(feed.companyNews),
    articles: list(feed.articles),
  }
}

function absolutizeArticleBlockDataUrls(
  data: Record<string, unknown>,
  origin: string | null,
): Record<string, unknown> {
  const out: Record<string, unknown> = { ...data }
  for (const key of ['url', 'posterImageUrl', 'thumbnailUrl', 'imageMediaUrl'] as const) {
    if (typeof out[key] === 'string') {
      const u = absolutizeMediaUrlForApiClient(out[key] as string, origin)
      if (u) out[key] = u
    }
  }
  if (Array.isArray(out.carouselItems)) {
    out.carouselItems = (out.carouselItems as Array<Record<string, unknown>>).map((item) => {
      if (item && typeof item === 'object' && typeof item.url === 'string') {
        const url = absolutizeMediaUrlForApiClient(item.url, origin)
        return url ? { ...item, url } : item
      }
      return item
    })
  }
  if (Array.isArray(out.documentItems)) {
    out.documentItems = (out.documentItems as Array<Record<string, unknown>>).map((item) => {
      if (item && typeof item === 'object' && typeof item.downloadUrl === 'string') {
        const downloadUrl = absolutizeMediaUrlForApiClient(item.downloadUrl as string, origin)
        return downloadUrl ? { ...item, downloadUrl } : item
      }
      return item
    })
  }
  if (Array.isArray(out.items)) {
    out.items = (out.items as Array<Record<string, unknown>>).map((row) => {
      if (!row || typeof row !== 'object' || Array.isArray(row)) return row
      const copy = { ...row }
      if (typeof copy.posterImageUrl === 'string') {
        const u = absolutizeMediaUrlForApiClient(copy.posterImageUrl, origin)
        if (u) copy.posterImageUrl = u
      }
      return copy
    })
  }
  if (Array.isArray(out.steps)) {
    out.steps = (out.steps as Array<Record<string, unknown>>).map((row) => {
      if (!row || typeof row !== 'object' || Array.isArray(row)) return row
      const copy = { ...row }
      if (typeof copy.imageMediaUrl === 'string') {
        const u = absolutizeMediaUrlForApiClient(copy.imageMediaUrl, origin)
        if (u) copy.imageMediaUrl = u
      }
      return copy
    })
  }
  return out
}

function absolutizeArticleBlockForMobile(block: ArticleBlockApi, origin: string | null): ArticleBlockApi {
  const imageUrl =
    block.imageUrl != null && String(block.imageUrl).trim() !== ''
      ? absolutizeMediaUrlForApiClient(block.imageUrl, origin) ?? block.imageUrl
      : block.imageUrl
  return {
    ...block,
    imageUrl,
    data: absolutizeArticleBlockDataUrls(block.data, origin),
  }
}

export function absolutizeArticleDetailApiForMobile(
  article: ArticleDetailApi,
  origin: string | null,
): ArticleDetailApi {
  return {
    ...article,
    coverUrl: absOrEmpty(article.coverUrl, origin),
    videoUrl: absOptional(article.videoUrl, origin),
    galleryUrls: article.galleryUrls.map((u) => absolutizeMediaUrlForApiClient(u, origin) ?? u),
    documents: article.documents.map((d) => ({
      ...d,
      url: d.url ? absolutizeMediaUrlForApiClient(d.url, origin) ?? d.url : null,
    })),
    blocks: article.blocks.map((b) => absolutizeArticleBlockForMobile(b, origin)),
  }
}
