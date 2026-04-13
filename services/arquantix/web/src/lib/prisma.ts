import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  })

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = prisma

// Verify Email model is available (for debugging)
if (process.env.NODE_ENV === 'development' && typeof prisma.email === 'undefined') {
  console.error('[Prisma] WARNING: Email model is not available. Run: npx prisma generate')
}

