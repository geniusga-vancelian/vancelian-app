import { notFound } from 'next/navigation'
import { getPageSections } from '@/lib/cms/content'

export const dynamic = 'force-dynamic'
import { defaultLocale } from '@/config/locales'
import { getLocaleFromCookies } from '@/lib/i18n/locale-server'
import { cookies } from 'next/headers'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { Navigation } from '@/components/sections/Navigation'
import { prisma } from '@/lib/prisma'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'
import { Prisma } from '@prisma/client'

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

export default async function HomePage() {
  try {
    const page = await prisma.page.findUnique({
      where: { slug: 'home' },
    })

    if (!page) {
      notFound()
    }

    // Verify it's the home page (urlPath should be "/")
    if (page.urlPath !== '/') {
      notFound()
    }

    // Get locale from cookie
    const cookieStore = await cookies()
    const locale = (await getLocaleFromCookies(cookieStore)) || defaultLocale

    // Try published first, fallback to draft if no published content
    let sections = await getPageSections('home', locale, 'published')
    if (sections.length === 0 || sections.every((s) => !s.data || Object.keys(s.data).length === 0)) {
      sections = await getPageSections('home', locale, 'draft')
    }

    if (process.env.NODE_ENV === 'development') {
      const heroSection = sections.find((s) => s.key === 'hero')
      if (heroSection) {
        console.log('[HomePage] Hero section data:', JSON.stringify(heroSection.data, null, 2))
      }
    }

    const menuItems = await getPrimaryMenu(locale)
    const themeColor =
      page.themeColor && (page.themeColor === 'dark' || page.themeColor === 'light')
        ? (page.themeColor as 'dark' | 'light')
        : 'dark'

    if (sections.length === 0) {
      notFound()
    }

    return (
      <div className="min-h-screen bg-black text-white">
        <Navigation menuItems={menuItems} themeColor={themeColor} />
        <main>
          {sections.map((section) => (
            <SectionRenderer key={section.id} section={section} />
          ))}
        </main>
      </div>
    )
  } catch (error) {
    if (isDatabaseUnreachable(error)) {
      return <DatabaseUnavailable />
    }
    throw error
  }
}

