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

// Vérif serveur uniquement (évite toute exécution si le module était bundlé côté client par erreur).
if (
  typeof window === 'undefined' &&
  process.env.NODE_ENV === 'development' &&
  typeof prisma.email === 'undefined'
) {
  console.error('[Prisma] WARNING: Email model is not available. Run: npx prisma generate')
}

