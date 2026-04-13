import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const updateTemplateSchema = z.object({
  name: z.string().min(1).max(200).optional(),
  description: z.string().optional(),
  heroPolicy: z.enum(['REQUIRED', 'OPTIONAL']).optional(),
  headerModuleId: z.string().uuid().optional(),
  footerModuleId: z.string().uuid().optional(),
  fixedModuleIds: z.array(z.string().uuid()).optional(),
  bodyTemplate: z.any().optional(),
  lockPolicy: z.any().optional(),
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

    const template = await prisma.emailTemplateEntity.findUnique({
      where: { id: params.id },
      include: {
        headerModule: {
          select: {
            id: true,
            slug: true,
            name: true,
            moduleType: true,
            status: true,
          },
        },
        footerModule: {
          select: {
            id: true,
            slug: true,
            name: true,
            moduleType: true,
            status: true,
          },
        },
      },
    })

    if (!template) {
      return NextResponse.json({ error: 'Template not found' }, { status: 404 })
    }

    return NextResponse.json(template)
  } catch (error) {
    console.error('Error fetching email template:', error)
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

    // Check if template exists and is DRAFT
    const existing = await prisma.emailTemplateEntity.findUnique({
      where: { id: params.id },
    })

    if (!existing) {
      return NextResponse.json({ error: 'Template not found' }, { status: 404 })
    }

    if (existing.status !== 'DRAFT') {
      return NextResponse.json(
        { error: 'Only DRAFT templates can be updated' },
        { status: 400 }
      )
    }

    const body = await request.json()
    const {
      name,
      description,
      heroPolicy,
      headerModuleId,
      footerModuleId,
      fixedModuleIds,
      bodyTemplate,
      lockPolicy,
    } = updateTemplateSchema.parse(body)

    const updateData: any = {}
    
    if (name !== undefined) {
      updateData.name = name
    }
    if (description !== undefined) {
      updateData.description = description || null
    }
    if (heroPolicy !== undefined) {
      updateData.heroPolicy = heroPolicy
    }
    
    // Validate and update header module if provided
    if (headerModuleId !== undefined) {
      const headerModule = await prisma.emailModule.findUnique({
        where: { id: headerModuleId },
      })
      if (!headerModule) {
        return NextResponse.json(
          { error: 'Header module not found' },
          { status: 404 }
        )
      }
      if (headerModule.moduleType !== 'HEADER') {
        return NextResponse.json(
          { error: 'Header module must be of type HEADER' },
          { status: 400 }
        )
      }
      if (headerModule.status !== 'VALIDATED') {
        return NextResponse.json(
          { error: 'Header module must be VALIDATED' },
          { status: 400 }
        )
      }
      updateData.headerModuleId = headerModuleId
    }
    
    // Validate and update footer module if provided
    if (footerModuleId !== undefined) {
      const footerModule = await prisma.emailModule.findUnique({
        where: { id: footerModuleId },
      })
      if (!footerModule) {
        return NextResponse.json(
          { error: 'Footer module not found' },
          { status: 404 }
        )
      }
      if (footerModule.moduleType !== 'FOOTER') {
        return NextResponse.json(
          { error: 'Footer module must be of type FOOTER' },
          { status: 400 }
        )
      }
      if (footerModule.status !== 'VALIDATED') {
        return NextResponse.json(
          { error: 'Footer module must be VALIDATED' },
          { status: 400 }
        )
      }
      updateData.footerModuleId = footerModuleId
    }
    
    // Validate fixed modules if provided
    if (fixedModuleIds !== undefined) {
      if (fixedModuleIds.length > 0) {
        for (const fixedModuleId of fixedModuleIds) {
          const fixedModule = await prisma.emailModule.findUnique({
            where: { id: fixedModuleId },
          })
          if (!fixedModule) {
            return NextResponse.json(
              { error: `Fixed module ${fixedModuleId} not found` },
              { status: 404 }
            )
          }
          if (fixedModule.status !== 'VALIDATED') {
            return NextResponse.json(
              { error: `Fixed module ${fixedModuleId} must be VALIDATED` },
              { status: 400 }
            )
          }
        }
      }
      updateData.fixedModuleIds = fixedModuleIds.length > 0 ? fixedModuleIds : null
    }
    
    if (bodyTemplate !== undefined) {
      updateData.bodyTemplate = bodyTemplate
      // Auto-generate lockPolicy if not provided
      if (lockPolicy !== undefined) {
        updateData.lockPolicy = lockPolicy
      } else {
        updateData.lockPolicy = generateLockPolicyFromBodyTemplate(bodyTemplate)
      }
    } else if (lockPolicy !== undefined) {
      updateData.lockPolicy = lockPolicy
    }

    const template = await prisma.emailTemplateEntity.update({
      where: { id: params.id },
      data: updateData,
    })

    return NextResponse.json(template)
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating email template:', error)
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

    await prisma.emailTemplateEntity.delete({
      where: { id: params.id },
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error deleting email template:', error)
    if ((error as any).code === 'P2003') {
      return NextResponse.json(
        { error: 'Template is referenced by one or more emails and cannot be deleted' },
        { status: 409 }
      )
    }
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * Generate lockPolicy from bodyTemplate
 */
function generateLockPolicyFromBodyTemplate(bodyTemplate: any): any {
  const coreBlocks = bodyTemplate.core_blocks || []
  const optionalSlots = bodyTemplate.optional_slots || {}
  
  return {
    core_blocks: coreBlocks.map((block: any) => ({
      type: block.type,
      variant: block.variant || 'default',
    })),
    optional_slots: optionalSlots,
  }
}


