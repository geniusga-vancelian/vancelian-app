import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

async function main() {
  const chapter = await prisma.dsComponentChapter.findUnique({
    where: { slug: 'component_ds_flutter' },
    select: { id: true },
  })
  if (!chapter) {
    throw new Error('Chapter "component_ds_flutter" not found')
  }

  const schemaJson = {
    type: 'layout',
    key: 'offers_layout',
    title: 'Offers layout',
    structure: {
      header: {
        background: {
          imageUrl: 'media/1774391838266-slqzb6n7vfi.png',
        },
      },
      body: {
        widgets: [
          {
            key: 'saving_vaults_widget',
            type: 'widget_builder_widget',
            title: 'Saving Vaults',
            widgetSlug: 'widget-saving-vaults-marketing-paysage',
          },
          {
            key: 'investment_categories',
            type: 'investment_categories_filter',
            title: 'Investment categories',
          },
          {
            key: 'exclusive_offers',
            type: 'exclusive_offers_list_widget',
            title: 'Top exclusive offers',
          },
        ],
      },
    },
  } as const

  const upserted = await prisma.dsComponent.upsert({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'offers_layout',
      },
    },
    update: {
      name: 'Offers layout',
      schemaJson,
    },
    create: {
      chapterId: chapter.id,
      slug: 'offers_layout',
      name: 'Offers layout',
      schemaJson,
    },
  })

  console.log('Offers layout created/updated:', upserted.slug, upserted.id)
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
