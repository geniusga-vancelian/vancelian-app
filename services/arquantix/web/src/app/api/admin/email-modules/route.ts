import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { EmailSpec } from '@/components/ai-email/types'
import { EmailSpecSchema } from '@/components/ai-email/schema'

const createModuleSchema = z.object({
  slug: z.string().min(1).max(200),
  name: z.string().min(1).max(200),
  description: z.string().optional(),
  moduleType: z.enum(['HEADER', 'FOOTER', 'LEGAL', 'SIGNATURE', 'SOCIAL', 'DISCLAIMER', 'CUSTOM']),
  theme: z.string().default('arquantix_v1'),
  spec: z.any(), // EmailSpec, validated later
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { slug, name, description, moduleType, theme, spec } = createModuleSchema.parse(body)

    // Validate EmailSpec
    let validatedSpec: EmailSpec
    try {
      const normalizedSpec = {
        ...spec,
        preheader: spec.preheader === undefined || spec.preheader === '' ? null : spec.preheader,
        theme: spec.theme || theme || 'arquantix_v1',
        locale: spec.locale || 'fr',
      }
      
      validatedSpec = EmailSpecSchema.parse(normalizedSpec) as EmailSpec
      
      // Validate module type constraints
      await validateModuleSpec(moduleType, validatedSpec)
    } catch (error: any) {
      console.error('[POST /api/admin/email-modules] Validation error:', error)
      return NextResponse.json(
        { 
          error: 'Invalid EmailSpec format', 
          details: error.issues || error.message,
          receivedSpec: spec,
        },
        { status: 400 }
      )
    }

    // Create module
    try {
      const module = await prisma.emailModule.create({
        data: {
          slug,
          name,
          description: description || null,
          moduleType,
          theme: theme || 'arquantix_v1',
          spec: validatedSpec as any,
          status: 'DRAFT',
        },
      })

      return NextResponse.json(module)
    } catch (dbError: any) {
      console.error('[POST /api/admin/email-modules] Database error:', dbError)
      if (dbError.code === 'P2002') {
        return NextResponse.json(
          { error: 'Module with this slug already exists' },
          { status: 409 }
        )
      }
      throw dbError
    }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error creating email module:', error)
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
    const moduleType = searchParams.get('moduleType')
    const status = searchParams.get('status')

    const where: any = {}
    if (moduleType) {
      where.moduleType = moduleType
    }
    if (status) {
      where.status = status
    }

    const modules = await prisma.emailModule.findMany({
      where,
      orderBy: { updatedAt: 'desc' },
      select: {
        id: true,
        slug: true,
        name: true,
        description: true,
        moduleType: true,
        theme: true,
        status: true,
        createdAt: true,
        updatedAt: true,
        _count: {
          select: {
            translations: true,
          },
        },
      },
    })

    // Ensure we return [] not null
    return NextResponse.json(modules || [])
  } catch (error) {
    console.error('Error fetching email modules:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

/**
 * Validate module spec against module type constraints
 */
import { validateModuleSpec, getAllowedBlockTypes } from './validate'

