import { prisma } from './prisma'
import bcrypt from 'bcryptjs'
import { cookies } from 'next/headers'
import crypto from 'crypto'

const SESSION_COOKIE_NAME = 'arq_admin_session'
const SESSION_DURATION_MS = 7 * 24 * 60 * 60 * 1000 // 7 days

export async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, 10)
}

export async function verifyPassword(
  password: string,
  hash: string
): Promise<boolean> {
  return bcrypt.compare(password, hash)
}

export async function createSession(userId: string): Promise<string> {
  // Generate a secure random token
  const token = crypto.randomBytes(32).toString('hex')
  const expiresAt = new Date(Date.now() + SESSION_DURATION_MS)

  await prisma.session.create({
    data: {
      userId,
      token,
      expiresAt,
    },
  })

  return token
}

/** Session admin web + lien API Python (`users.admin_user_id` → `admin_users.id`). */
export type AdminWebSession = {
  userId: string
  userEmail: string
  userRole: string
  /** FK vers `admin_users.id` — seule source pour le `sub` JWT côté BFF (pas de lookup email). */
  adminUserId: number | null
}

/**
 * Remplit `users.admin_user_id` si une ligne `admin_users` existe avec le même e-mail
 * (recherche insensible à la casse, `findFirst` — index unique partiel SQL sur email).
 * Appelée au login et à chaque lecture de session pour éviter le 403 BFF sans re-login.
 */
export async function ensureCmsUserLinkedToAdminUser(user: {
  id: string
  email: string
  adminUserId: number | null
}): Promise<number | null> {
  if (user.adminUserId != null) {
    return user.adminUserId
  }

  const au = await prisma.adminUser.findFirst({
    where: {
      email: { equals: user.email, mode: 'insensitive' },
    },
    orderBy: { id: 'asc' },
  })
  if (!au) {
    return null
  }

  try {
    const updated = await prisma.user.update({
      where: { id: user.id },
      data: { adminUserId: au.id },
    })
    return updated.adminUserId
  } catch (e) {
    console.warn(
      '[auth] ensureCmsUserLinkedToAdminUser: liaison users → admin_users impossible (conflit FK / autre user ?)',
      e
    )
    return null
  }
}

export async function getSessionFromToken(
  token: string
): Promise<AdminWebSession | null> {
  const session = await prisma.session.findUnique({
    where: { token },
    include: { user: true },
  })

  if (!session) {
    return null
  }

  // Check if session is expired
  if (session.expiresAt < new Date()) {
    // Delete expired session
    await prisma.session.delete({ where: { id: session.id } })
    return null
  }

  const adminUserId = await ensureCmsUserLinkedToAdminUser(session.user)

  return {
    userId: session.userId,
    userEmail: session.user.email,
    userRole: session.user.role,
    adminUserId,
  }
}

export async function deleteSession(token: string): Promise<void> {
  await prisma.session.deleteMany({
    where: { token },
  })
}

export async function getSessionFromCookie(): Promise<AdminWebSession | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get(SESSION_COOKIE_NAME)?.value

  if (!token) {
    return null
  }

  return getSessionFromToken(token)
}

export function setSessionCookie(token: string, isProduction: boolean = false) {
  const cookieStore = cookies()
  cookieStore.set(SESSION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: isProduction,
    sameSite: 'lax',
    maxAge: SESSION_DURATION_MS / 1000, // Convert to seconds
    path: '/',
  })
}

export function clearSessionCookie() {
  const cookieStore = cookies()
  cookieStore.delete(SESSION_COOKIE_NAME)
}

export async function cleanupExpiredSessions(): Promise<void> {
  await prisma.session.deleteMany({
    where: {
      expiresAt: {
        lt: new Date(),
      },
    },
  })
}


