/** Champs minimaux pour trier la liste admin (featured → highlighted → reste). */
export type ArticleEditorialSortable = {
  isFeatured: boolean
  isHighlighted: boolean
  createdAt: string
  publishedAt?: string | null
}

function editorialRank(row: ArticleEditorialSortable): number {
  if (row.isFeatured) return 0
  if (row.isHighlighted) return 1
  return 2
}

function timestampDesc(iso: string | null | undefined): number {
  if (!iso) return 0
  const t = new Date(iso).getTime()
  return Number.isFinite(t) ? t : 0
}

export function compareArticlesEditorialOrder<T extends ArticleEditorialSortable>(
  a: T,
  b: T
): number {
  const rankA = editorialRank(a)
  const rankB = editorialRank(b)
  if (rankA !== rankB) return rankA - rankB

  if (rankA === 1) {
    return timestampDesc(b.publishedAt ?? b.createdAt) - timestampDesc(a.publishedAt ?? a.createdAt)
  }
  if (rankA === 2) {
    return timestampDesc(b.createdAt) - timestampDesc(a.createdAt)
  }
  return timestampDesc(b.publishedAt ?? b.createdAt) - timestampDesc(a.publishedAt ?? a.createdAt)
}

export function sortArticlesEditorialOrder<T extends ArticleEditorialSortable>(rows: T[]): T[] {
  return [...rows].sort(compareArticlesEditorialOrder)
}
