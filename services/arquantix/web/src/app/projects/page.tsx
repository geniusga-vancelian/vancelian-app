import { prisma } from '@/lib/prisma'
import { ContentStatus } from '@prisma/client'
import { getLocaleOrDefault, defaultLocale } from '@/config/locales'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import Link from 'next/link'
import { Navigation } from '@/components/sections/Navigation'
import { Footer } from '@/components/sections/Footer'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'

interface ProjectListItem {
  id: string
  slug: string
  coverMedia: {
    url: string
    alt: string | null
  } | null
  i18n: {
    title: string
    shortDescription: string | null
  } | null
}

interface ProjectsPageProps {
  searchParams: { locale?: string }
}

export default async function ProjectsPage({ searchParams }: ProjectsPageProps) {
  const locale = getLocaleOrDefault(searchParams.locale)
  const menuItems = await getPrimaryMenu(locale)

  // Fetch published projects with i18n for the locale
  const projects = await prisma.project.findMany({
    where: {
      status: ContentStatus.PUBLISHED,
    },
    include: {
      coverMedia: true,
      i18n: {
        where: {
          locale,
        },
        take: 1,
      },
    },
    orderBy: { updatedAt: 'desc' },
  })

  // Resolve i18n with fallback to defaultLocale
  const projectsWithI18n: ProjectListItem[] = await Promise.all(
    projects.map(async (project) => {
      let i18n = project.i18n[0] || null

      // Fallback to default locale if no i18n for requested locale
      if (!i18n && locale !== defaultLocale) {
        const defaultI18n = await prisma.projectI18n.findFirst({
          where: {
            projectId: project.id,
            locale: defaultLocale,
          },
        })
        if (defaultI18n) {
          i18n = defaultI18n
        }
      }

      // Resolve cover media URL (presigned if needed)
      let coverUrl = project.coverMedia?.url || null
      if (project.coverMedia) {
        try {
          coverUrl = await getPresignedUrl(project.coverMedia.key, 3600)
        } catch (error) {
          console.error(`Failed to get presigned URL for ${project.coverMedia.key}:`, error)
          coverUrl = project.coverMedia.url
        }
      }

      return {
        id: project.id,
        slug: project.slug,
        coverMedia: coverUrl
          ? {
              url: coverUrl,
              alt: project.coverMedia?.alt || i18n?.title || project.slug,
            }
          : null,
        i18n: i18n
          ? {
              title: i18n.title,
              shortDescription: i18n.shortDescription,
            }
          : null,
      }
    })
  )

  return (
    <div className="min-h-screen bg-black text-white">
      <Navigation menuItems={menuItems} />
      <main className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h1 className="text-4xl font-bold mb-4">Our Projects</h1>
            <p className="text-gray-400 text-lg">
              Discover our portfolio of premium real estate investments
            </p>
          </div>

          {projectsWithI18n.length === 0 ? (
            <div className="text-center py-16">
              <p className="text-gray-400 text-xl">No projects available yet.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
              {projectsWithI18n.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.slug}`}
                  className="group block bg-[#1A1A1A] rounded-lg overflow-hidden hover:scale-[1.02] transition-transform"
                >
                  {project.coverMedia && (
                    <div className="relative h-64 overflow-hidden">
                      <img
                        src={project.coverMedia.url}
                        alt={project.coverMedia.alt || ''}
                        className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
                      />
                      <div className="absolute inset-0 bg-black/30 group-hover:bg-black/20 transition-colors" />
                    </div>
                  )}
                  <div className="p-6">
                    <h2 className="text-xl font-semibold mb-2 text-white">
                      {project.i18n?.title || project.slug}
                    </h2>
                    {project.i18n?.shortDescription && (
                      <p className="text-gray-400 text-sm line-clamp-3">
                        {project.i18n.shortDescription}
                      </p>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </div>
  )
}

