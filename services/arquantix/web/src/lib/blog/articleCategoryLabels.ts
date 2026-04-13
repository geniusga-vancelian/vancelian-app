/**
 * Resolve display labels for article category slugs from both ArticleCategory and InvestmentCategory.
 */
import { prisma } from '@/lib/prisma'
import { resolveLabelWithFallback } from '@/lib/i18n/resolveLabel'

export type ResolvedArticleCategory = { id: string; slug: string; label: string }

/**
 * Returns one entry per slug in [categorySlugs] order when a matching row exists.
 */
export async function resolveArticleCategoryLabels(
  categorySlugs: string[],
  locale: string
): Promise<ResolvedArticleCategory[]> {
  if (categorySlugs.length === 0) return []

  const [articleCats, investmentCats] = await Promise.all([
    prisma.articleCategory.findMany({
      where: { slug: { in: categorySlugs }, isActive: true },
      include: { i18n: true },
    }),
    prisma.investmentCategory.findMany({
      where: { slug: { in: categorySlugs } },
    }),
  ])

  const acBySlug = new Map(articleCats.map((c) => [c.slug, c] as const))
  const icBySlug = new Map(investmentCats.map((c) => [c.slug, c] as const))

  const out: ResolvedArticleCategory[] = []
  for (const slug of categorySlugs) {
    const ac = acBySlug.get(slug)
    if (ac) {
      out.push({
        id: ac.id,
        slug: ac.slug,
        label: resolveLabelWithFallback({
          requestedLocale: locale,
          baseLabel: ac.label,
          i18nRows: ac.i18n.map((i) => ({ locale: i.locale, label: i.label })),
        }),
      })
      continue
    }
    const ic = icBySlug.get(slug)
    if (ic) {
      out.push({
        id: ic.id,
        slug: ic.slug,
        label: ic.label?.trim() ? ic.label : ic.slug,
      })
    }
  }
  return out
}
