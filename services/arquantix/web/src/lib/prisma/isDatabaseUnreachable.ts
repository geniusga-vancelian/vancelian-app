import { Prisma } from '@prisma/client'

/** Erreurs Prisma typiques quand PostgreSQL n’est pas joignable (dev, DB arrêtée). */
export function isDatabaseUnreachable(error: unknown): boolean {
  if (error instanceof Prisma.PrismaClientInitializationError) return true
  if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P1001') return true
  if (error instanceof Error && error.message.includes("Can't reach database server")) return true
  return false
}
