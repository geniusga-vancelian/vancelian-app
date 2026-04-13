import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'

export async function POST(
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
        headerModule: true,
        footerModule: true,
      },
    })

    if (!template) {
      return NextResponse.json({ error: 'Template not found' }, { status: 404 })
    }

    if (template.status === 'VALIDATED') {
      return NextResponse.json(
        { error: 'Template is already validated' },
        { status: 400 }
      )
    }

    // Ensure modules are still VALIDATED
    if (template.headerModule.status !== 'VALIDATED') {
      return NextResponse.json(
        { error: 'Header module must be VALIDATED' },
        { status: 400 }
      )
    }
    if (template.footerModule.status !== 'VALIDATED') {
      return NextResponse.json(
        { error: 'Footer module must be VALIDATED' },
        { status: 400 }
      )
    }

    const validated = await prisma.emailTemplateEntity.update({
      where: { id: params.id },
      data: { status: 'VALIDATED' },
    })

    return NextResponse.json(validated)
  } catch (error) {
    console.error('Error validating email template:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









