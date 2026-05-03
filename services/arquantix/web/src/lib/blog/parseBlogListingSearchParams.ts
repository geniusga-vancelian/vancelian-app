/** Query string partagée entre `/[locale]/blog` et `/preview/blog` (feed, mosaïque, filtres). */
export function parseBlogListingSearchParams(searchParams: {
  category?: string | string[]
  page?: string | string[]
  mosaicPage?: string | string[]
  segment?: string | string[]
}): {
  category: string | undefined
  pageNum: number
  mosaicPageNum: number
  segment: string | undefined
} {
  const category = Array.isArray(searchParams.category)
    ? searchParams.category[0]
    : searchParams.category
  const pageRaw = Array.isArray(searchParams.page) ? searchParams.page[0] : searchParams.page
  const mosaicPageRaw = Array.isArray(searchParams.mosaicPage)
    ? searchParams.mosaicPage[0]
    : searchParams.mosaicPage
  const segment = Array.isArray(searchParams.segment)
    ? searchParams.segment[0]
    : searchParams.segment

  let pageNum = parseInt(pageRaw || '1', 10)
  if (!Number.isFinite(pageNum) || pageNum < 1) pageNum = 1

  let mosaicPageNum = parseInt(mosaicPageRaw || '1', 10)
  if (!Number.isFinite(mosaicPageNum) || mosaicPageNum < 1) mosaicPageNum = 1

  return { category, pageNum, mosaicPageNum, segment }
}
