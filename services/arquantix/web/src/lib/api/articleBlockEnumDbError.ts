import { Prisma } from '@prisma/client'

/**
 * Détecte l'erreur PostgreSQL « invalid input value for enum » quand le schéma Prisma
 * connaît KEY_INFORMATION / VIDEO_BLOCK_ARTICLE / STEPS_MODULE mais pas l'enum PG.
 */
export function isArticleBlockEnumDatabaseError(error: unknown): boolean {
  if (error instanceof Prisma.PrismaClientUnknownRequestError) {
    return /invalid input value for enum|ArticleBlockType/i.test(error.message)
  }
  if (error instanceof Error) {
    return /invalid input value for enum/i.test(error.message)
  }
  return false
}

export function articleBlockEnumHintPayload() {
  return {
    error: 'Type de bloc inconnu côté base de données',
    hint: "Exécutez `npx prisma migrate deploy` depuis `services/arquantix/web` pour appliquer les migrations (enum `ArticleBlockType` : Infos clés, Vidéos poster, Étapes).",
  } as const
}
