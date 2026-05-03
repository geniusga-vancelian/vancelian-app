import { NextRequest, NextResponse } from 'next/server'
import { getHelpCollectionBrowse } from '@/lib/help/get-help-data'

function previewToArticleJson(a: {
  id: string
  slug: string
  title: string
  standfirst: string | null
  updatedAt: Date
  publishedAt: Date | null
  targetTags: unknown[]
  collectionTags: string[]
}) {
  return {
    id: a.id,
    slug: a.slug,
    question: a.title,
    standfirst: a.standfirst,
    targetTags: a.targetTags,
    collectionTags: a.collectionTags,
    updatedAt: a.updatedAt,
    publishedAt: a.publishedAt,
  }
}

/**
 * Hub mobile Help : regroupements dérivés des tags d’articles (`collection_tags`),
 * ou liste plate si un seul groupe distinct.
 */
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection: string }> },
) {
  try {
    const { collection } = await params
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || undefined

    const browse = await getHelpCollectionBrowse(collection, localeParam)
    if (!browse) {
      return NextResponse.json(
        { error: 'Collection not found', displayMode: null, tagGroups: [], articles: [] },
        { status: 404 },
      )
    }

    return NextResponse.json({
      collection: browse.collection,
      displayMode: browse.displayMode,
      tagGroups: browse.tagGroups,
      articles: browse.articles.map(previewToArticleJson),
    })
  } catch (error) {
    console.error('[Help Browse API] Error:', error)
    return NextResponse.json(
      { error: 'Internal server error', displayMode: null, tagGroups: [], articles: [] },
      { status: 500 },
    )
  }
}
