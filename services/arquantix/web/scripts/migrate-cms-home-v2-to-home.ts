/**
 * Remplace le contenu CMS de la page `home` (urlPath `/`) par une copie fidèle
 * des sections et SectionContent de la page `home-v2`.
 *
 * Ne modifie pas `src/app/page.tsx` : `/` continue de lire `slug = home`.
 *
 * Prérequis : page `home-v2` peuplée (legacy). Le flux actuel : `scripts/seed-cms-home.ts` cible directement `home`.
 *
 * Exécution (même DATABASE_URL que Next) :
 *   cd services/arquantix/web && npx tsx scripts/migrate-cms-home-v2-to-home.ts
 *
 * Supprimer la page `home-v2` après copie (optionnel) :
 *   MIGRATE_REMOVE_HOME_V2=1 npx tsx scripts/migrate-cms-home-v2-to-home.ts
 */

import { PrismaClient, Prisma } from '@prisma/client'
import { config as loadEnv } from 'dotenv'
import path from 'path'

loadEnv({ path: path.resolve(process.cwd(), '.env') })
loadEnv({ path: path.resolve(process.cwd(), '.env.local'), override: true })

const prisma = new PrismaClient()

async function main() {
  const removeV2 = process.env.MIGRATE_REMOVE_HOME_V2 === '1'

  const home = await prisma.page.findUnique({ where: { slug: 'home' } })
  const v2 = await prisma.page.findUnique({
    where: { slug: 'home-v2' },
    include: {
      sections: {
        orderBy: { order: 'asc' },
        include: { contents: true },
      },
    },
  })

  if (!home) {
    throw new Error('Page slug "home" introuvable. Exécuter le seed Prisma (home) avant.')
  }
  if (home.urlPath !== '/') {
    throw new Error(`Page home a urlPath="${home.urlPath}" (attendu "/"). Abandon.`)
  }
  if (!v2) {
    throw new Error(
      'Page slug "home-v2" introuvable. Ancienne base : peupler home-v2 puis relancer ; sinon utiliser scripts/seed-cms-home.ts sur `home`.'
    )
  }
  if (v2.sections.length === 0) {
    throw new Error('Page home-v2 sans sections. Rien à copier.')
  }

  await prisma.$transaction(async (tx) => {
    await tx.section.deleteMany({ where: { pageId: home.id } })

    for (const s of v2.sections) {
      const created = await tx.section.create({
        data: {
          pageId: home.id,
          key: s.key,
          order: s.order,
          schemaVersion: s.schemaVersion,
        },
      })

      for (const c of s.contents) {
        await tx.sectionContent.create({
          data: {
            sectionId: created.id,
            locale: c.locale,
            status: c.status,
            data: c.data as Prisma.InputJsonValue,
            translationStatus: c.translationStatus,
            updatedByUserId: c.updatedByUserId,
          },
        })
      }
    }

    await tx.page.update({
      where: { id: home.id },
      data: {
        title: v2.title,
        description: v2.description,
        themeColor: v2.themeColor,
        template: v2.template,
      },
    })

    if (removeV2) {
      await tx.page.delete({ where: { id: v2.id } })
    }
  })

  console.log(
    removeV2
      ? 'OK : contenu home-v2 copié vers home ; page home-v2 supprimée.'
      : 'OK : contenu home-v2 copié vers home ; page home-v2 conservée (archive / comparaison).'
  )
  console.log(`Home : ${home.id} → / (${v2.sections.length} sections copiées)`)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
