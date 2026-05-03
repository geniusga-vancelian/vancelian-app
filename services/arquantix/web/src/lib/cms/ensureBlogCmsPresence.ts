import { prisma } from '@/lib/prisma'

type EnsureBlogResult = {
  pageId: string
  menuId: string
  createdPage: boolean
  createdMenuItem: boolean
}

/**
 * Garantit la présence de la page CMS "blog" et d'une entrée dans le menu primary.
 * Idempotent: plusieurs appels ne créent pas de doublons.
 */
export async function ensureBlogCmsPresence(): Promise<EnsureBlogResult> {
  return prisma.$transaction(async (tx) => {
    const pageExistsBefore = await tx.page.findUnique({
      where: { slug: 'blog' },
      select: { id: true },
    })
    const createdPage = !pageExistsBefore
    let createdMenuItem = false

    const page = await tx.page.upsert({
      where: { slug: 'blog' },
      update: {},
      create: {
        slug: 'blog',
        urlPath: '/blog',
        title: 'Blog',
        description: 'Blog Arquantix',
        template: 'blog',
        showInNav: true,
      },
      select: { id: true },
    })

    const menu = await tx.menu.upsert({
      where: { key: 'primary' },
      update: {},
      create: {
        key: 'primary',
        name: 'Primary Menu',
      },
      select: { id: true },
    })

    const existingBlogMenuItem = await tx.menuItem.findFirst({
      where: {
        menuId: menu.id,
        OR: [
          { pageId: page.id },
          { externalUrl: '/blog' },
        ],
      },
      select: { id: true },
    })

    if (!existingBlogMenuItem) {
      const maxOrder = await tx.menuItem.aggregate({
        where: { menuId: menu.id },
        _max: { order: true },
      })
      const nextOrder = (maxOrder._max.order ?? -1) + 1

      await tx.menuItem.create({
        data: {
          menuId: menu.id,
          label: 'Blog',
          type: 'LINK',
          isRoot: false,
          pageId: page.id,
          order: nextOrder,
          enabled: true,
        },
      })
      createdMenuItem = true
    }

    return {
      pageId: page.id,
      menuId: menu.id,
      createdPage,
      createdMenuItem,
    }
  })
}

