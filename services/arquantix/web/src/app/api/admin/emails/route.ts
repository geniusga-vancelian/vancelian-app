import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { EmailSpec } from '@/components/ai-email/types'
import { EmailSpecSchema } from '@/components/ai-email/schema'

const createEmailSchema = z.object({
  name: z.string().min(1).max(200),
  templateId: z.string().min(1),
  locale: z.string().regex(/^[a-z]{2}$/),
  spec: z.any(), // EmailSpec, validated later
})

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    console.log('[POST /api/admin/emails] Request body:', JSON.stringify(body, null, 2))
    
    const { name, templateId, locale, spec } = createEmailSchema.parse(body)
    console.log('[POST /api/admin/emails] Parsed:', { name, templateId, locale, specKeys: Object.keys(spec || {}) })

    // Validate EmailSpec
    let validatedSpec: EmailSpec
    try {
      // Normalize spec before validation
      const normalizedSpec = {
        ...spec,
        preheader: spec.preheader === undefined || spec.preheader === '' ? null : spec.preheader,
        theme: spec.theme || 'arquantix_v1',
        locale: spec.locale || 'fr',
      }
      
      console.log('[POST /api/admin/emails] Normalized spec:', JSON.stringify(normalizedSpec, null, 2))
      validatedSpec = EmailSpecSchema.parse(normalizedSpec) as EmailSpec
      console.log('[POST /api/admin/emails] Validation successful')
    } catch (error: any) {
      console.error('[POST /api/admin/emails] EmailSpec validation error:', error)
      console.error('[POST /api/admin/emails] Original spec:', JSON.stringify(spec, null, 2))
      console.error('[POST /api/admin/emails] Normalized spec:', JSON.stringify({
        ...spec,
        preheader: spec.preheader === undefined || spec.preheader === '' ? null : spec.preheader,
        theme: spec.theme || 'arquantix_v1',
        locale: spec.locale || 'fr',
      }, null, 2))
      // Return detailed validation errors
      if (error.issues) {
        return NextResponse.json(
          { 
            error: 'Invalid EmailSpec format', 
            details: error.issues,
            message: error.message || 'Validation failed',
            receivedSpec: spec, // Include for debugging
          },
          { status: 400 }
        )
      }
      return NextResponse.json(
        { 
          error: 'Invalid EmailSpec format', 
          details: error.message || String(error),
          receivedSpec: spec, // Include for debugging
        },
        { status: 400 }
      )
    }

    // Create email
    try {
      console.log('[POST /api/admin/emails] Creating email in database...')
      console.log('[POST /api/admin/emails] Prisma client check:', {
        hasEmail: typeof prisma.email !== 'undefined',
        emailMethods: typeof prisma.email !== 'undefined' ? Object.keys(prisma.email).slice(0, 5) : 'N/A'
      })
      
      if (!prisma.email) {
        throw new Error('Prisma Email model not available. Please restart the Next.js server after running: npx prisma generate')
      }
      
      const email = await prisma.email.create({
        data: {
          name,
          templateId,
          theme: validatedSpec.theme || 'arquantix_v1',
          locale,
          spec: validatedSpec as any,
          status: 'DRAFT',
        },
      })
      console.log('[POST /api/admin/emails] Email created successfully:', email.id)

      return NextResponse.json(email)
    } catch (dbError: any) {
      console.error('Database error creating email:', dbError)
      // Check if it's a table not found error
      if (dbError.code === 'P2001' || dbError.message?.includes('does not exist') || dbError.message?.includes('relation') && dbError.message?.includes('does not exist')) {
        return NextResponse.json(
          { 
            error: 'Database table not found. Please run: npx prisma db push',
            details: 'The Email table may not exist yet. Run migrations or db push to create it.'
          },
          { status: 500 }
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
    console.error('Error creating email:', error)
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

    const emails = await prisma.email.findMany({
      orderBy: { updatedAt: 'desc' },
      select: {
        id: true,
        name: true,
        templateId: true,
        locale: true,
        status: true,
        updatedAt: true,
        createdAt: true,
        _count: {
          select: {
            translations: true,
          },
        },
      },
    })

    return NextResponse.json(emails)
  } catch (error) {
    console.error('Error fetching emails:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

