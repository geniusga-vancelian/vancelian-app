import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import type { Prisma } from '@prisma/client'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'

const createTemplateSchema = z.object({
  slug: z.string().min(1).max(200),
  name: z.string().min(1).max(200),
  description: z.string().optional(),
  theme: z.string().default('arquantix_v1'),
  heroPolicy: z.enum(['REQUIRED', 'OPTIONAL']).default('REQUIRED'),
  headerModuleId: z.string().uuid(),
  footerModuleId: z.string().uuid(),
  fixedModuleIds: z.array(z.string().uuid()).optional(),
  bodyTemplate: z.any(), // JSON defining allowed BODY structure
  lockPolicy: z.any().optional(), // JSON defining core vs optional slots
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const {
      slug,
      name,
      description,
      theme,
      heroPolicy,
      headerModuleId,
      footerModuleId,
      fixedModuleIds,
      bodyTemplate,
      lockPolicy,
    } = createTemplateSchema.parse(body)

    // Validate modules exist and are VALIDATED
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

    // Validate fixed modules if provided
    if (fixedModuleIds && fixedModuleIds.length > 0) {
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

    // Generate lockPolicy from bodyTemplate if not provided
    let finalLockPolicy = lockPolicy
    if (!finalLockPolicy && bodyTemplate) {
      finalLockPolicy = generateLockPolicyFromBodyTemplate(bodyTemplate)
    }

    const template = await prisma.emailTemplateEntity.create({
      data: {
        slug,
        name,
        description: description || null,
        theme: theme || 'arquantix_v1',
        heroPolicy: heroPolicy || 'REQUIRED',
        headerModuleId,
        footerModuleId,
        ...(fixedModuleIds !== undefined
          ? { fixedModuleIds: fixedModuleIds as Prisma.InputJsonValue }
          : {}),
        bodyTemplate: bodyTemplate as any,
        lockPolicy: finalLockPolicy as any,
        status: 'DRAFT',
      },
    })

    return NextResponse.json(template)
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating email template:', error)
    if ((error as any).code === 'P2002') {
      return NextResponse.json(
        { error: 'Template with this slug already exists' },
        { status: 409 }
      )
    }
    return NextResponse.json(
      { 
        error: 'Internal server error',
        message: error instanceof Error ? error.message : String(error)
      },
      { status: 500 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const status = searchParams.get('status')

    const where: any = {}
    if (status) {
      where.status = status
    }

    const templates = await prisma.emailTemplateEntity.findMany({
      where,
      orderBy: { updatedAt: 'desc' },
      include: {
        headerModule: {
          select: {
            id: true,
            slug: true,
            name: true,
            moduleType: true,
          },
        },
        footerModule: {
          select: {
            id: true,
            slug: true,
            name: true,
            moduleType: true,
          },
        },
      },
    })

    // Ensure we return [] not null
    return NextResponse.json(templates || [])
  } catch (error) {
    console.error('Error fetching email templates:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * Generate lockPolicy from bodyTemplate
 * bodyTemplate should define core_blocks and optional_slots
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

