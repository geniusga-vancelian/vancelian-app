import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { prisma } from '@/lib/prisma'

const LANDING_TEMPLATE_DB = 'landing_builder'
const LANDING_SECTION_KEY = 'landing_builder_v1'

/**
 * GET /api/mobile/flutter/landing-pages/[slug]?locale=fr&status=draft|published
 * Endpoint public pour prévisualiser un runtime landing page Flutter.
 */
export async function GET(
  request: Request,
  { params }: { params: { slug: string } }
) {
  try {
    const requestedSlug = (params.slug ?? '').trim()
    if (!requestedSlug) {
      return NextResponse.json({ error: 'Invalid slug' }, { status: 400 })
    }

    const { searchParams } = new URL(request.url)
    const locale = (searchParams.get('locale') || 'fr').trim()
    const requestedStatus = (searchParams.get('status') || 'draft').toLowerCase()
    const status =
      requestedStatus === 'published' ? ContentStatus.PUBLISHED : ContentStatus.DRAFT

    const page = await prisma.page.findFirst({
      where: {
        slug: requestedSlug,
        template: LANDING_TEMPLATE_DB,
      },
      include: {
        sections: {
          where: { key: LANDING_SECTION_KEY },
          include: {
            contents: {
              where: { locale, status },
              take: 1,
            },
          },
          take: 1,
        },
      },
    })

    if (!page) {
      return NextResponse.json({ error: 'Landing page not found' }, { status: 404 })
    }

    const content = page.sections[0]?.contents[0]
    if (!content) {
      return NextResponse.json(
        { error: `No ${requestedStatus} content for locale "${locale}"` },
        { status: 404 }
      )
    }

    return NextResponse.json(
      {
        page: {
          id: page.id,
          slug: page.slug,
          title: page.title,
          description: page.description,
          urlPath: page.urlPath,
          template: page.template,
        },
        landing: content.data,
        meta: {
          locale,
          status: requestedStatus,
        },
      },
      {
        headers: {
          'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
          Pragma: 'no-cache',
          Expires: '0',
        },
      }
    )
  } catch (error) {
    console.error('[api/mobile/flutter/landing-pages/[slug]]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
