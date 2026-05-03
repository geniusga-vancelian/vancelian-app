import type { Article, ArticleI18n } from '@prisma/client'
import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'
import { computeArticleLocaleCompleteness } from '@/lib/admin/pageLocaleCompleteness'
import { defaultLocale } from '@/config/locales'

const ARTICLE_GABARIT_SLUG = 'article'
const ARTICLE_GABARIT_TEMPLATE = 'article'

function articleDisplayTitle(article: Article & { i18n: ArticleI18n[] }): string {
  const row =
    article.i18n.find((i) => i.locale === defaultLocale) ?? article.i18n[0]
  return row?.title?.trim() || article.slug
}

function articleToVirtualTreeNode(
  article: Article & { i18n: ArticleI18n[] },
  sortOrder: number,
): SiteTreeNode {
  return {
    id: `blog-article:${article.id}`,
    slug: article.slug,
    title: articleDisplayTitle(article),
    urlPath: `/blog/${article.slug}`,
    template: 'blog_article',
    parentId: null,
    sortOrder,
    pageRole: 'STANDARD',
    showInNav: false,
    isSystemPage: false,
    children: [],
    packagedProduct: null,
    isVirtual: true,
    articleId: article.id,
    localeCompleteness: computeArticleLocaleCompleteness(article),
  }
}

/**
 * Ajoute chaque ligne `Article` comme enfant du gabarit CMS `article` (slug + template article).
 * Affichage admin uniquement — ne modifie pas `pages.parent_id`.
 */
export function injectBlogArticlesUnderArticleGabarit(
  roots: SiteTreeNode[],
  articles: Array<Article & { i18n: ArticleI18n[] }>,
): SiteTreeNode[] {
  if (articles.length === 0) return roots

  const sorted = [...articles].sort((a, b) => {
    const pa = a.publishedAt?.getTime() ?? 0
    const pb = b.publishedAt?.getTime() ?? 0
    if (pb !== pa) return pb - pa
    return b.updatedAt.getTime() - a.updatedAt.getTime()
  })

  const virtuals = sorted.map((a, idx) => articleToVirtualTreeNode(a, idx))

  const inject = (nodes: SiteTreeNode[]): { ok: boolean; out: SiteTreeNode[] } => {
    let ok = false
    const out = nodes.map((n) => {
      if (n.slug === ARTICLE_GABARIT_SLUG && n.template === ARTICLE_GABARIT_TEMPLATE) {
        ok = true
        return { ...n, children: [...n.children, ...virtuals] }
      }
      const sub = inject(n.children)
      if (sub.ok) {
        ok = true
        return { ...n, children: sub.out }
      }
      return n
    })
    return { ok, out }
  }

  const { ok, out } = inject(roots)
  return ok ? out : roots
}
