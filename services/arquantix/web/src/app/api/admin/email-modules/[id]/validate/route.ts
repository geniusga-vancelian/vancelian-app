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

    const module = await prisma.emailModule.findUnique({
      where: { id: params.id },
    })

    if (!module) {
      return NextResponse.json({ error: 'Module not found' }, { status: 404 })
    }

    if (module.status === 'VALIDATED') {
      return NextResponse.json(
        { error: 'Module is already validated' },
        { status: 400 }
      )
    }

    const validated = await prisma.emailModule.update({
      where: { id: params.id },
      data: { status: 'VALIDATED' },
    })

    return NextResponse.json(validated)
  } catch (error) {
    console.error('Error validating email module:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









