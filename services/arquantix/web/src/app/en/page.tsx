import { api } from '@/lib/strapi'

async function getHomePageData() {
  try {
    const global = await api.getGlobal()
    const pages = await api.getPages('en', 'home')
    return { global, page: pages[0] || null }
  } catch (error) {
    console.error('Error fetching data:', error)
    return { global: null, page: null }
  }
}

export default async function EnHomePage() {
  const { global, page } = await getHomePageData()

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-white">
      <div className="container mx-auto px-4 py-16">
        <h1 className="text-5xl font-bold text-slate-900 mb-4">
          {global?.branding?.name || 'Arquantix'}
        </h1>
        <p className="text-xl text-slate-600 mb-2">
          {global?.branding?.tagline || 'Coming soon'}
        </p>
        {page && (
          <div className="mt-8">
            <h2 className="text-2xl font-semibold mb-4">{page.title}</h2>
          </div>
        )}
        <p className="text-lg text-slate-500 mt-4">Bientôt disponible</p>
      </div>
    </main>
  )
}
