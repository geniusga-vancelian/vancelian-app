import { PrismaClient } from '@prisma/client'

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
        slug: 'dashboard_layout',
      },
    },
    select: {
      id: true,
      schemaJson: true,
    },
  })
  if (!layout) throw new Error('dashboard_layout not found')

  const schema = asRecord(layout.schemaJson) ?? {}
  const structure = asRecord(schema.structure) ?? {}
  const body = asRecord(structure.body) ?? {}
  const widgetsRaw = Array.isArray(body.widgets) ? body.widgets : []
  const widgets = widgetsRaw
    .filter((w): w is Record<string, unknown> => w != null && typeof w === 'object')
    .map((w) => ({ ...w }))

  const alreadyExists = widgets.some((w) => String(w.key ?? '').trim() === 'top10research_widget')
  if (!alreadyExists) {
    widgets.push({
      key: 'top10research_widget',
      type: 'widget_builder_widget',
      title: 'Research',
      widgetSlug: 'top10research',
    })
  }

  const nextSchema = {
    ...schema,
    structure: {
      ...structure,
      body: {
        ...body,
        widgets,
      },
    },
  }

  await prisma.dsComponent.update({
    where: { id: layout.id },
    data: { schemaJson: nextSchema },
  })

  console.log('dashboard_layout updated with top10research_widget')
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
