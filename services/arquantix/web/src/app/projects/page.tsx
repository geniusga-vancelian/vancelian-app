import { notFound } from 'next/navigation'
import { cookies } from 'next/headers'
import { Prisma } from '@prisma/client'
import { getPageSections, type SectionWithContent } from '@/lib/cms/content'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { prisma } from '@/lib/prisma'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'

export const dynamic = 'force-dynamic'

/** Slug CMS de la page `/projects` (même principe que la home). */
const PROJECTS_PAGE_SLUG = 'projects'

function projectGridResolvedOfferCount(sections: SectionWithContent[]): number {
  const grid = sections.find(
    (s) => (resolveCanonicalSectionKey(s.key) ?? s.key) === 'project_grid',
  )
  if (!grid?.data) return 0
  const rp = grid.data.resolvedProjects
  return Array.isArray(rp) ? rp.length : 0
}

function isDatabaseUnreachable(error: unknown): boolean {
  if (error instanceof Prisma.PrismaClientInitializationError) return true
  if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === 'P1001') return true
  if (error instanceof Error && error.message.includes("Can't reach database server")) return true
  return false
}

function DatabaseUnavailable() {
  return (
    <div className="min-h-screen bg-zinc-950 px-6 py-16 text-zinc-100">
      <div className="mx-auto max-w-lg rounded-lg border border-amber-500/30 bg-zinc-900/80 p-8 shadow-lg">
        <h1 className="text-xl font-semibold text-amber-100">Base de données inaccessible</h1>
        <p className="mt-4 text-sm leading-relaxed text-zinc-300">
          Next.js ne parvient pas à joindre PostgreSQL (voir <code className="rounded bg-zinc-800 px-1">DATABASE_URL</code> dans{' '}
          <code className="rounded bg-zinc-800 px-1">services/arquantix/web/.env</code>).
        </p>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-zinc-400">
          <li>
            Avec Docker : démarrer le daemon Docker, puis à la racine du dépôt&nbsp;:
            <code className="mt-1 block rounded bg-zinc-800 p-2 text-xs text-zinc-200">
              docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-db
            </code>
            (le port hôte est celui de <code className="rounded bg-zinc-800 px-1">DB_PORT</code> dans{' '}
            <code className="rounded bg-zinc-800 px-1">.env.arquantix</code>, souvent 5443.)
          </li>
          <li>
            Postgres en local : adapter <code className="rounded bg-zinc-800 px-1">DATABASE_URL</code> dans{' '}
            <code className="rounded bg-zinc-800 px-1">.env.local</code> (ex. port 5432).
          </li>
        </ul>
        <p className="mt-6 text-xs text-zinc-500">
          Ensuite : <code className="rounded bg-zinc-800 px-1">npx prisma migrate deploy</code> si besoin, et{' '}
          <code className="rounded bg-zinc-800 px-1">npm run db:seed</code> pour les données initiales.
        </p>
      </div>
    </div>
  )
}

export default async function ProjectsPage({
  searchParams,
}: {
  searchParams?: Record<string, string | string[] | undefined>
}) {
  try {
    const page = await prisma.page.findUnique({
      where: { slug: PROJECTS_PAGE_SLUG },
    })

    if (!page) {
      notFound()
    }

    const cookieStore = await cookies()
    const locale = resolvePublicLocale({ cookieStore, searchParams })

    let sections = await getPageSections(PROJECTS_PAGE_SLUG, locale, 'published')
    if (sections.length === 0 || sections.every((s) => !s.data || Object.keys(s.data).length === 0)) {
      sections = await getPageSections(PROJECTS_PAGE_SLUG, locale, 'draft')
    } else if (process.env.NODE_ENV === 'development') {
      /** Brouillon souvent en avance sur le publié : évite une grille vide en local si le publish section n’a pas été fait. */
      const pubCount = projectGridResolvedOfferCount(sections)
      if (pubCount === 0) {
        const draftSections = await getPageSections(PROJECTS_PAGE_SLUG, locale, 'draft')
        if (projectGridResolvedOfferCount(draftSections) > pubCount) {
          sections = draftSections
        }
      }
    }

    if (sections.length === 0) {
      notFound()
    }

    return (
      <main className="flex flex-col">
        {sections.map((section) => (
          <SectionRenderer key={section.id} section={section} />
        ))}
      </main>
    )
  } catch (error) {
    if (isDatabaseUnreachable(error)) {
      return <DatabaseUnavailable />
    }
    throw error
  }
}
