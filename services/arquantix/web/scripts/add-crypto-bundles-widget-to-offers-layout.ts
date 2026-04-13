import { PrismaClient, type Prisma } from '@prisma/client'

const prisma = new PrismaClient()

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

async function main() {
  const chapter = await prisma.dsComponentChapter.findUnique({
    where: { slug: 'component_ds_flutter' },
    select: { id: true },
  })
  if (!chapter) throw new Error('Chapter "component_ds_flutter" not found')

  const layout = await prisma.dsComponent.findUnique({
    where: {
      chapterId_slug: {
        chapterId: chapter.id,
        slug: 'offers_layout',
      },
    },
    select: {
      id: true,
      schemaJson: true,
    },
  })
  if (!layout) throw new Error('offers_layout not found')

  const schema = asRecord(layout.schemaJson) ?? {}
  const structure = asRecord(schema.structure) ?? {}
  const body = asRecord(structure.body) ?? {}
  const widgetsRaw = Array.isArray(body.widgets) ? body.widgets : []
  const widgets = widgetsRaw
    .filter((w): w is Record<string, unknown> => w != null && typeof w === 'object')
    .map((w) => ({ ...w }))

  const alreadyExists = widgets.some((w) => String(w.key ?? '').trim() === 'crypto_bundles_widget')
  if (!alreadyExists) {
    widgets.push({
      key: 'crypto_bundles_widget',
      type: 'widget_builder_widget',
      title: 'Thematic investing',
      widgetSlug: 'crypto-bundles-widget',
    })
  }

  const desiredOrder = [
    'saving_vaults_widget',
    'crypto_bundles_widget',
    'investment_categories',
    'exclusive_offers',
  ]
  const byKey = new Map(
    widgets.map((w) => [String(w.key ?? '').trim(), w] as const)
  )
  const orderedKnown = desiredOrder
    .map((key) => byKey.get(key))
    .filter((w): w is Record<string, unknown> => Boolean(w))
  const unknown = widgets.filter(
    (w) => !desiredOrder.includes(String(w.key ?? '').trim())
  )
  const finalWidgets = [...orderedKnown, ...unknown]

  const nextSchema = {
    ...schema,
    structure: {
      ...structure,
      body: {
        ...body,
        widgets: finalWidgets,
      },
    },
  }

  await prisma.dsComponent.update({
    where: { id: layout.id },
    data: { schemaJson: nextSchema as Prisma.InputJsonValue },
  })

  console.log('offers_layout updated with crypto_bundles_widget')
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
