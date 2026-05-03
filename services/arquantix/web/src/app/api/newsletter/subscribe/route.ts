import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'

import { prisma } from '@/lib/prisma'

const newsletterSchema = z.object({
  email: z.string().trim().email(),
  locale: z.string().trim().optional(),
  source: z.string().trim().optional(),
})

const NEWSLETTER_MARKER = '[NEWSLETTER]'

function parseClientIp(request: NextRequest): string | null {
  const forwardedFor = request.headers.get('x-forwarded-for')
  if (forwardedFor) {
    const firstIp = forwardedFor.split(',')[0]?.trim()
    if (firstIp) return firstIp
  }

  const realIp = request.headers.get('x-real-ip')?.trim()
  if (realIp) return realIp

  return null
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const parsed = newsletterSchema.safeParse(body)

    if (!parsed.success) {
      return NextResponse.json({ ok: false, error: 'invalid_payload' }, { status: 400 })
    }

    const { email, locale, source } = parsed.data

    const alreadySubscribed = await prisma.contactSubmissions.findFirst({
      where: {
        email,
        message: {
          startsWith: NEWSLETTER_MARKER,
        },
      },
      select: { id: true },
    })

    if (alreadySubscribed) {
      return NextResponse.json({ ok: true, status: 'already_subscribed' })
    }

    const markerDetails = [
      NEWSLETTER_MARKER,
      `source=${source || 'footer'}`,
      `locale=${locale || 'unknown'}`,
    ].join(' ')

    await prisma.contactSubmissions.create({
      data: {
        name: 'Newsletter Subscriber',
        email,
        message: markerDetails,
        ip: parseClientIp(request),
        userAgent: request.headers.get('user-agent')?.slice(0, 500) ?? null,
      },
    })

    return NextResponse.json({ ok: true, status: 'subscribed' })
  } catch (error) {
    console.error('[newsletter/subscribe] unexpected error', error)
    return NextResponse.json({ ok: false, error: 'internal_error' }, { status: 500 })
  }
}
