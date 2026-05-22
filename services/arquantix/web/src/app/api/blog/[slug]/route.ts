import { NextRequest, NextResponse } from 'next/server'

import { logMobileApiFailure, mobileApiJsonError, safeApiMessageForClient } from '@/lib/api/mobile-json-error'
import { getLocaleOrDefault } from '@/config/locales'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { absolutizeArticleDetailApiForMobile } from '@/lib/blog/absolutizeBlogApiForMobile'
import { getArticleBySlug } from '@/lib/blog/articleService'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  try {
    const { slug } = await params
    const { searchParams } = new URL(request.url)
    const locale = getLocaleOrDefault(searchParams.get('locale'))

    const article = await getArticleBySlug(slug, locale, calculateReadingTime)

    if (!article) {
      return NextResponse.json({ error: 'Article not found' }, { status: 404 })
    }

    return NextResponse.json(absolutizeArticleDetailApiForMobile(article, request.nextUrl.origin))
  } catch (error) {
    logMobileApiFailure('[api/blog/[slug]] GET', error)
    return mobileApiJsonError(500, safeApiMessageForClient(error))
  }
}
