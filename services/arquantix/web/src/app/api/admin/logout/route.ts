import { NextRequest, NextResponse } from 'next/server'
import { deleteSession, getSessionFromCookie } from '@/lib/auth'
import { cookies } from 'next/headers'

export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()

    if (session) {
      // Get token from cookie
      const cookieStore = await cookies()
      const token = cookieStore.get('arq_admin_session')?.value

      if (token) {
        await deleteSession(token)
      }
    }

    const response = NextResponse.json({ success: true })

    // Clear cookie
    response.cookies.delete('arq_admin_session')

    return response
  } catch (error) {
    console.error('Logout error:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
