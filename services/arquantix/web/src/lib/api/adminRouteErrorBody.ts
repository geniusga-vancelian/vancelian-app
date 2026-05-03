import { Prisma } from '@prisma/client'

const MAX_PRISMA_MESSAGE_LEN = 1200

/**
 * Corps JSON pour les 500 sur routes admin : en prod, pas de fuite d’URL ;
 * on expose quand même les messages Prisma utiles (enum PG, 22P02, moteur…).
 */
export function adminRouteErrorBody(error: unknown): Record<string, unknown> {
  const body: Record<string, unknown> = { error: 'Internal server error' }
  if (error instanceof Prisma.PrismaClientKnownRequestError) {
    body.prismaCode = error.code
    if (error.meta != null) body.prismaMeta = error.meta
  } else if (error instanceof Prisma.PrismaClientValidationError) {
    body.prismaValidation = error.message.slice(0, MAX_PRISMA_MESSAGE_LEN)
  } else if (error instanceof Prisma.PrismaClientUnknownRequestError) {
    // ex. "invalid input value for enum" si la base n’a pas `MEDIA_IMAGE_CAROUSEL` dans l’enum PG
    body.prismaMessage = error.message.slice(0, MAX_PRISMA_MESSAGE_LEN)
  } else if (error instanceof Prisma.PrismaClientInitializationError) {
    body.prismaInit = error.message.slice(0, MAX_PRISMA_MESSAGE_LEN)
  } else if (error instanceof Error) {
    // Erreur générique côté route (hors Zod) — utile dès le build `next start` (NODE_ENV=production)
    if (process.env.ARQUANTIX_EXPOSE_ROUTE_ERROR === '1') {
      body.message = error.message.slice(0, MAX_PRISMA_MESSAGE_LEN)
    } else if (process.env.NODE_ENV === 'development') {
      body.message = error.message
    }
  }
  return body
}
