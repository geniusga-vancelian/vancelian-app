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

    const email = await prisma.email.findUnique({
      where: { id: params.id },
    })

    if (!email) {
      return NextResponse.json({ error: 'Email not found' }, { status: 404 })
    }

    if (email.status === 'VALIDATED') {
      return NextResponse.json(
        { error: 'Email is already validated' },
        { status: 400 }
      )
    }

    // Change status to VALIDATED (locks structure permanently)
    const updated = await prisma.email.update({
      where: { id: params.id },
      data: {
        status: 'VALIDATED',
      },
    })

    return NextResponse.json(updated)
  } catch (error) {
    console.error('Error validating email:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}









