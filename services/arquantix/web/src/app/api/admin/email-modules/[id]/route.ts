import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { EmailSpec } from '@/components/ai-email/types'
import { EmailSpecSchema } from '@/components/ai-email/schema'

const updateModuleSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
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

    const module = await prisma.emailModule.findUnique({
      where: { id: params.id },
      include: {
        translations: {
          select: {
            id: true,
            locale: true,
            spec: true,
            translationStatus: true,
            createdAt: true,
            updatedAt: true,
          },
        },
      },
    })

    if (!module) {
      return NextResponse.json({ error: 'Module not found' }, { status: 404 })
    }

    return NextResponse.json(module)
  } catch (error) {
    console.error('Error fetching email module:', error)
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

    // Check if module exists and is DRAFT
    const existing = await prisma.emailModule.findUnique({
      where: { id: params.id },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Module not found' }, { status: 404 })
    }

    if (existing.status !== 'DRAFT') {
      return NextResponse.json(
        { error: 'Only DRAFT modules can be updated' },
        { status: 400 }
      )
    }

    const body = await request.json()
    const { name, description, spec } = updateModuleSchema.parse(body)

    const updateData: any = {}
    
    if (name !== undefined) {
      updateData.name = name
    }
    if (description !== undefined) {
      updateData.description = description || null
    }
    
    if (spec !== undefined) {
      // Validate EmailSpec
      try {
        const normalizedSpec = {
          ...spec,
          preheader: spec.preheader === undefined || spec.preheader === '' ? null : spec.preheader,
          theme: spec.theme || existing.theme || 'arquantix_v1',
          locale: spec.locale || 'fr',
        }
        
        const validatedSpec = EmailSpecSchema.parse(normalizedSpec) as EmailSpec
        
        // Validate module type constraints
        await validateModuleSpec(existing.moduleType, validatedSpec)
        
        updateData.spec = validatedSpec as any
      } catch (error: any) {
        console.error('[PUT /api/admin/email-modules/[id]] Validation error:', error)
        return NextResponse.json(
          { 
            error: 'Invalid EmailSpec format', 
            details: error.issues || error.message,
          },
          { status: 400 }
        )
      }
    }

    const module = await prisma.emailModule.update({
      where: { id: params.id },
      data: updateData,
    })

    return NextResponse.json(module)
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating email module:', error)
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

    // Check if module is used by any templates
    const templatesUsingModule = await prisma.emailTemplateEntity.findFirst({
      where: {
        OR: [
          { headerModuleId: params.id },
          { footerModuleId: params.id },
        ],
      },
    })

    if (templatesUsingModule) {
      return NextResponse.json(
        { error: 'Module is used by one or more templates and cannot be deleted' },
        { status: 409 }
      )
    }

    await prisma.emailModule.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting email module:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

import { validateModuleSpec, getAllowedBlockTypes } from '../validate'

