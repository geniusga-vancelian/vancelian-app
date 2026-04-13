import { NextRequest, NextResponse } from 'next/server'

import { Prisma } from '@prisma/client'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

type JsonRecord = Record<string, unknown>

function asRecord(value: unknown): JsonRecord | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as JsonRecord
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const { id } = await params
    const component = await prisma.dsComponent.findUnique({
      where: { id },
      include: {
        chapter: {
          select: { id: true, slug: true, name: true },
        },
      },
    })
    if (!component) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }
    return NextResponse.json(component)
  } catch (error) {
    console.error('[api/admin/widget-builder/[id] GET]', error)
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const { id } = await params
    const body = (await request.json()) as {
      name?: string
      slug?: string
      schemaJson?: unknown
    }

    const existing = await prisma.dsComponent.findUnique({
      where: { id },
      select: { id: true, slug: true },
    })
    if (!existing) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 })
    }

    const nextName = typeof body.name === 'string' && body.name.trim().length > 0
      ? body.name.trim()
      : undefined
    const nextSlug = typeof body.slug === 'string' && body.slug.trim().length > 0
      ? body.slug.trim()
      : undefined
    const nextSchema = asRecord(body.schemaJson)

    if (body.schemaJson !== undefined && !nextSchema) {
      return NextResponse.json({ error: 'schemaJson must be a JSON object' }, { status: 400 })
    }

    if (nextSlug && nextSlug !== existing.slug) {
      const duplicate = await prisma.dsComponent.findFirst({
        where: {
          slug: nextSlug,
          id: { not: existing.id },
        },
        select: { id: true },
      })
      if (duplicate) {
        return NextResponse.json({ error: `Slug already exists: "${nextSlug}"` }, { status: 409 })
      }
    }

    const updated = await prisma.dsComponent.update({
      where: { id },
      data: {
        ...(nextName ? { name: nextName } : {}),
        ...(nextSlug ? { slug: nextSlug } : {}),
        ...(nextSchema ? { schemaJson: nextSchema as Prisma.InputJsonValue } : {}),
      },
      include: {
        chapter: {
          select: { id: true, slug: true, name: true },
        },
      },
    })

    return NextResponse.json(updated)
  } catch (error) {
    console.error('[api/admin/widget-builder/[id] PUT]', error)
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const { id } = await params
    await prisma.dsComponent.delete({ where: { id } })
    return NextResponse.json({ ok: true })
  } catch (error) {
    console.error('[api/admin/widget-builder/[id] DELETE]', error)
    return NextResponse.json({ error: 'Internal error' }, { status: 500 })
  }
}
