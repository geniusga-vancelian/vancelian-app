import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { EmailSpec } from '@/components/ai-email/types'
import { EmailSpecSchema } from '@/components/ai-email/schema'

const updateEmailSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  spec: z.any().optional(), // EmailSpec, validated later
})

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const email = await prisma.email.findUnique({
      where: { id: params.id },
      include: {
        translations: {
          orderBy: { locale: 'asc' },
        },
      },
    })

    if (!email) {
      return NextResponse.json({ error: 'Email not found' }, { status: 404 })
    }

    return NextResponse.json(email)
  } catch (error) {
    console.error('Error fetching email:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const email = await prisma.email.findUnique({
      where: { id: params.id },
    })

    if (!email) {
      return NextResponse.json({ error: 'Email not found' }, { status: 404 })
    }

    // Refuse update if status is VALIDATED
    if (email.status === 'VALIDATED') {
      return NextResponse.json(
        { error: 'Cannot update validated email. Structure is locked.' },
        { status: 400 }
      )
    }

    const body = await request.json()
    const { name, spec } = updateEmailSchema.parse(body)

    const updateData: any = {}
    if (name !== undefined) {
      updateData.name = name
    }
    if (spec !== undefined) {
      // Validate EmailSpec
      try {
        const validatedSpec = EmailSpecSchema.parse(spec) as EmailSpec
        updateData.spec = validatedSpec as any
        updateData.theme = validatedSpec.theme || 'arquantix_v1'
      } catch (error) {
        return NextResponse.json(
          { error: 'Invalid EmailSpec format', details: error },
          { status: 400 }
        )
      }
    }

    const updated = await prisma.email.update({
      where: { id: params.id },
      data: updateData,
    })

    return NextResponse.json(updated)
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating email:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const email = await prisma.email.findUnique({
      where: { id: params.id },
    })

    if (!email) {
      return NextResponse.json({ error: 'Email not found' }, { status: 404 })
    }

    await prisma.email.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ message: 'Email deleted' })
  } catch (error) {
    console.error('Error deleting email:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









