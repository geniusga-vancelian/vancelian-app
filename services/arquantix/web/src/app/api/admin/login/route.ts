import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { prisma } from '@/lib/prisma'
import {
  verifyPassword,
  createSession,
  setSessionCookie,
  ensureCmsUserLinkedToAdminUser,
} from '@/lib/auth'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
})

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { email, password } = loginSchema.parse(body)

    // Find user by email
    const user = await prisma.user.findUnique({
      where: { email },
    })

    if (!user) {
      return NextResponse.json(
        { error: 'Invalid email or password' },
        { status: 401 }
      )
    }

    // Verify password
    const isValidPassword = await verifyPassword(password, user.passwordHash)

    if (!isValidPassword) {
      return NextResponse.json(
        { error: 'Invalid email or password' },
        { status: 401 }
      )
    }

    // Liaison users.admin_user_id → admin_users.id (même logique que [ensureCmsUserLinkedToAdminUser]).
    await ensureCmsUserLinkedToAdminUser(user)
    const userForSession = await prisma.user.findUniqueOrThrow({
      where: { id: user.id },
    })

    // Create session
    const token = await createSession(userForSession.id)

    // Set cookie
    const response = NextResponse.json({
      user: {
        id: user.id,
        email: user.email,
        role: user.role,
      },
    })

    // Set cookie in response
    const isProduction = process.env.NODE_ENV === 'production'
    response.cookies.set('arq_admin_session', token, {
      httpOnly: true,
      secure: isProduction,
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60, // 7 days in seconds
      path: '/',
    })

    return response
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', details: error.issues },
        { status: 400 }
      )
    }

    console.error('Login error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

