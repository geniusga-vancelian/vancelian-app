import { redirect } from 'next/navigation'
import { getPageSections } from '@/lib/cms/content'
import { getSessionFromCookie } from '@/lib/auth'
import { getLocaleOrDefault } from '@/config/locales'

interface PreviewPageProps {
  params: { slug: string }
  searchParams: { locale?: string }
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

  // For now, just display the sections data as JSON
  // In production, you would render the actual page components
  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-4xl mx-auto">
        <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-6">
          <strong>Preview Mode</strong> - Showing draft content for locale: {locale}
        </div>

        <h1 className="text-3xl font-bold mb-6">Preview: {params.slug}</h1>

        {sections.length === 0 ? (
          <div className="bg-white rounded-lg shadow p-6">
            <p className="text-gray-500">No sections found for this page.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {sections.map((section) => (
              <div key={section.id} className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h2 className="text-xl font-semibold">{section.key}</h2>
                    <p className="text-sm text-gray-500">
                      Order: {section.order} • Schema: {section.schemaVersion} • Status: {section.status}
                    </p>
                  </div>
                </div>
                <pre className="bg-gray-50 p-4 rounded text-sm overflow-auto">
                  {JSON.stringify(section.data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}

        <div className="mt-8">
          <a
            href="/admin/pages"
            className="text-indigo-600 hover:text-indigo-900"
          >
            ← Back to Admin
          </a>
        </div>
      </div>
    </div>
  )
}

