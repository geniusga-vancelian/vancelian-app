/**
 * Complète ou crée un module Vault [FaqAccordionModule] avec des slugs Help valides
 * (seed help-center typique : getting-started / investing-basics / what-is-investing)
 * pour que l’app mobile affiche la FAQ sur l’offre exclusive (items avec les 4 champs requis).
 *
 * Usage (depuis ce package) :
 *   npx tsx scripts/fill-vault-faq-for-packaged-product.ts eo-1778482181050
 */
import type { PackagedProduct, Section } from '@prisma/client'
import { PrismaClient } from '@prisma/client'

const prisma = new PrismaClient()

const VAULT_SECTION_KEY = 'vault_builder_v1'

const FAQ_MODULE_CONTENT = {
  title: 'FAQ',
  intro: '',
  footerLinkLabel: 'Voir les FAQ du projet',
  footerCollectionSlug: 'getting-started',
  footerCategorySlug: 'investing-basics',
  footerFilterLabel: '',
  items: [
    {
      question: 'Est-ce que je vais tout perdre ?',
      articleSlug: 'what-is-investing',
      collectionSlug: 'getting-started',
      categorySlug: 'investing-basics',
      standfirst:
        'Les investissements comportent des risques de perte en capital ; renseignez-vous avant d’investir.',
    },
    {
      question: 'Est-ce que je vais faire des millions ?',
      articleSlug: 'what-is-investing',
      collectionSlug: 'getting-started',
      categorySlug: 'investing-basics',
      standfirst:
        'Les rendements passés ne préjugent pas des performances futures ; aucun gains n’est garanti.',
    },
  ],
} as const

type VaultModuleLike = {
  id?: unknown
  type?: unknown
  enabled?: unknown
  content?: unknown
}

function asRecord(v: unknown): Record<string, unknown> {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : {}
}

async function resolvePageLinkedToSlug(slug: string): Promise<{
  packaged: PackagedProduct | null
  pageId: string
  resolvedSlug: string
}> {
  const packaged =
    (await prisma.packagedProduct.findUnique({
      where: { slug },
    })) ??
    (await prisma.packagedProduct.findFirst({
      where: { slug: { contains: slug, mode: 'insensitive' } },
    }))
  if (packaged) {
    return { packaged, pageId: packaged.pageId, resolvedSlug: packaged.slug }
  }
  const page = await prisma.page.findUnique({ where: { slug } })
  if (page) {
    return { packaged: null, pageId: page.id, resolvedSlug: page.slug }
  }
  throw new Error(`Aucun PackagedProduct ni Page trouvé pour le slug « ${slug} »`)
}

function patchModulesArray(modulesUnknown: unknown): Record<string, unknown>[] {
  const raw = Array.isArray(modulesUnknown) ? modulesUnknown : []
  const modules = raw.filter(
    (m): m is Record<string, unknown> => m != null && typeof m === 'object' && !Array.isArray(m),
  )

  const faqIdx = modules.findIndex((m) => String(m.type ?? '') === 'FaqAccordionModule')
  const next = [...modules]

  if (faqIdx >= 0) {
    const cur = modules[faqIdx]!
    next[faqIdx] = {
      ...cur,
      type: 'FaqAccordionModule',
      enabled: true,
      content: { ...FAQ_MODULE_CONTENT },
      id:
        typeof cur.id === 'string' && cur.id.trim().length > 0
          ? cur.id
          : `faq-${Date.now()}`,
    }
  } else {
    next.push({
      id: `faq-auto-${Date.now()}`,
      type: 'FaqAccordionModule',
      enabled: true,
      content: { ...FAQ_MODULE_CONTENT },
    })
  }

  return next
}

async function patchSectionContents(section: Section): Promise<number> {
  const rows = await prisma.sectionContent.findMany({
    where: { sectionId: section.id },
  })
  if (rows.length === 0) {
    console.warn(`Aucune SectionContent pour la section vault (page section id=${section.id})`)
    return 0
  }

  let n = 0
  for (const row of rows) {
    const data = asRecord(row.data)
    const modulesIn = patchModulesArray(data.modules)
    await prisma.sectionContent.update({
      where: { id: row.id },
      data: {
        data: {
          ...data,
          modules: modulesIn,
        } as object,
      },
    })
    n += 1
    console.log(
      `  OK SectionContent ${row.id} (locale=${row.locale}, status=${row.status}), modules=${modulesIn.length}`,
    )
  }
  return n
}

async function main() {
  const slugArg = process.argv[2]?.trim()
  const slug = slugArg && slugArg.length > 0 ? slugArg : 'eo-1778482181050'
  console.log(`Cible packaged / page slug: ${slug}`)

  const { packaged, pageId, resolvedSlug } = await resolvePageLinkedToSlug(slug)
  if (packaged) {
    console.log(`PackagedProduct trouvé : ${resolvedSlug} (pageId=${pageId})`)
  } else {
    console.log(`Page trouvée : ${resolvedSlug} (pageId=${pageId})`)
  }

  const section = await prisma.section.findUnique({
    where: { pageId_key: { pageId, key: VAULT_SECTION_KEY } },
  })
  if (!section) {
    throw new Error(`Pas de section « ${VAULT_SECTION_KEY} » pour pageId=${pageId}`)
  }

  console.log(`Section vault id=${section.id}`)
  const updated = await patchSectionContents(section)
  console.log(`Terminé : ${updated} ligne(s) SectionContent mises à jour (FAQ prête pour l’app + bandeau web).`)
}

main()
  .catch((e: unknown) => {
    console.error(e)
    process.exitCode = 1
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
