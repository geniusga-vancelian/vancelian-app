import { redirect } from 'next/navigation'
import { getPageSections } from '@/lib/cms/content'
import { getSessionFromCookie } from '@/lib/auth'
import { getLocaleOrDefault } from '@/config/locales'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { Navigation } from '@/components/sections/Navigation'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'

interface PreviewPageProps {
  params: { slug: string }
  searchParams: { locale?: string; raw?: string }
}

export default async function PreviewPage({
  params,
  searchParams,
}: PreviewPageProps) {
  // Check if user is authenticated (admin only)
  const session = await getSessionFromCookie()
  if (!session) {
    redirect('/admin/login')
  }

  const locale = getLocaleOrDefault(searchParams.locale)
  const sections = await getPageSections(params.slug, locale, 'draft')
  const menuItems = await getPrimaryMenu(locale)

  const showRaw = searchParams.raw === 'true'

  return (
    <div className="min-h-screen bg-black text-white">

      {sections.length === 0 ? (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <p className="text-xl text-gray-400 mb-4">No sections found for this page.</p>
            <a
              href="/admin/pages"
              className="text-indigo-400 hover:text-indigo-300 underline"
            >
              Go to Admin
            </a>
          </div>
        </div>
      ) : showRaw ? (
        // Raw JSON view
        <div className="max-w-4xl mx-auto p-8">
          <div className="space-y-6">
            {sections.map((section) => (
              <div key={section.id} className="bg-gray-900 rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-xl font-semibold">{section.key}</h2>
                    <p className="text-sm text-gray-400">
                      Order: {section.order} • Schema: {section.schemaVersion} • Status: {section.status}
                    </p>
                  </div>
                </div>
                <pre className="bg-gray-800 p-4 rounded text-sm overflow-auto text-gray-300">
                  {JSON.stringify(section.data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      ) : (
        // Rendered view
        <>
          <Navigation menuItems={menuItems} />
          <main>
            {sections.map((section) => (
              <SectionRenderer key={section.id} section={section} />
            ))}
          </main>
        </>
      )}
    </div>
  )
}

