import { prisma } from '@/lib/prisma'
import { MenuItemType, Prisma, type PrismaClient } from '@prisma/client'

/** Client minimal pour cette routine (compatible `prisma` et `tx` de `$transaction`). */
export type PrimaryMenuWriteClient = Pick<PrismaClient, 'menu' | 'menuItem'>

/**
 * Détecte la valeur d’enum **sans** `CAST(... AS "MenuItemType")` : une requête Prisma
 * avec `type: LANGUAGE_SWITCHER` échoue en 22P02 si la migration n’est pas appliquée et
 * fait **échouer toute une transaction** Postgres ouverte (ex. `GET /api/admin/site-tree`).
 *
 * Ne filtre pas sur `public` : sur certains hébergeurs l’enum peut vivre dans un autre
 * schéma ; un filtre trop strict faisait croire que la migration manquait alors qu’elle
 * était OK → aucune ligne « Langue » créée.
 */
export async function menuItemTypeEnumHasLanguageSwitcher(): Promise<boolean> {
  const rows = await prisma.$queryRaw<Array<{ ok: boolean }>>(
    Prisma.sql`
      SELECT EXISTS (
        SELECT 1
        FROM pg_enum e
        INNER JOIN pg_type t ON t.oid = e.enumtypid
        WHERE t.typname = 'MenuItemType'
          AND e.enumlabel::text = 'LANGUAGE_SWITCHER'
      ) AS ok
    `,
  )
  return Boolean(rows[0]?.ok)
}

/**
 * Garantit une entrée `LANGUAGE_SWITCHER` dans le menu primaire (une seule),
 * pour pouvoir la réordonner avec les boutons d’action côté admin.
 *
 * Nécessite la migration Prisma qui ajoute la valeur d’enum `LANGUAGE_SWITCHER`
 * (`prisma/migrations/20260425140000_menu_item_language_switcher`). Sans elle,
 * l’app continue de fonctionner grâce au repli côté `getPrimaryMenu` ; seules cette
 * persistance et le réordonnancement admin de la ligne « Langue » sont ignorés.
 *
 * @param db — Passer le `tx` d’un `prisma.$transaction` pour lire le menu dans la
 * même unité que la création (évite un GET sur réplique « en retard » derrière un pooler).
 */
export async function ensurePrimaryMenuLanguageSwitcher(
  db: PrimaryMenuWriteClient = prisma,
): Promise<void> {
  try {
    if (!(await menuItemTypeEnumHasLanguageSwitcher())) {
      console.warn(
        '[ensurePrimaryMenuLanguageSwitcher] Enum Postgres `MenuItemType` sans valeur LANGUAGE_SWITCHER — exécutez `npx prisma migrate deploy` sur la **même** base que `DATABASE_URL` du serveur Next (migration 20260425140000_menu_item_language_switcher).',
      )
      return
    }

    const menu = await db.menu.findUnique({
      where: { key: 'primary' },
      include: { menuItems: true },
    })
    if (!menu) {
      console.warn(
        '[ensurePrimaryMenuLanguageSwitcher] Menu `key=primary` introuvable — exécutez le seed ou créez le menu primaire.',
      )
      return
    }

    const langItems = menu.menuItems.filter((i) => i.type === MenuItemType.LANGUAGE_SWITCHER)
    if (langItems.length > 1) {
      const sorted = [...langItems].sort((a, b) => a.order - b.order)
      await db.menuItem.deleteMany({
        where: { id: { in: sorted.slice(1).map((d) => d.id) } },
      })
    }
    const stillThere = await db.menuItem.count({
      where: { menuId: menu.id, type: MenuItemType.LANGUAGE_SWITCHER },
    })
    if (stillThere > 0) return

    const maxOrder = menu.menuItems.reduce((m, i) => Math.max(m, i.order), -1)
    await db.menuItem.create({
      data: {
        menuId: menu.id,
        label: 'Langue',
        type: MenuItemType.LANGUAGE_SWITCHER,
        order: maxOrder + 1,
        enabled: true,
        isRoot: false,
        pageId: null,
      },
    })
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    if (msg.includes('LANGUAGE_SWITCHER') || msg.includes('22P02')) {
      console.warn(
        '[ensurePrimaryMenuLanguageSwitcher] Enum MenuItemType sans LANGUAGE_SWITCHER en base — exécutez `npx prisma migrate deploy` sur la **même** base que `DATABASE_URL` du serveur Next (migration 20260425140000_menu_item_language_switcher).',
      )
      return
    }
    throw err
  }
}
