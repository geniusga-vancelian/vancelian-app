import { Prisma, PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

const prismaLog =
  process.env.NODE_ENV === 'development' && process.env.PRISMA_LOG_QUERIES === '1'
    ? (['query', 'error', 'warn'] as const)
    : (['error', 'warn'] as const)

export const prisma =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: [...prismaLog] as Prisma.LogLevel[],
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

