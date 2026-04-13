import { api } from '@/lib/strapi'

async function getNews() {
  try {
    return await api.getNews('en', 10)
  } catch (error) {
    console.error('Error fetching news:', error)
    return []
  }
}

export default async function EnNewsPage() {
  const news = await getNews()

  return (
    <main className="min-h-screen bg-white">
      <div className="container mx-auto px-4 py-16">
        <h1 className="text-4xl font-bold text-slate-900 mb-8">News</h1>
        {news.length === 0 ? (
          <p className="text-slate-600">No news at the moment.</p>
        ) : (
          <div className="space-y-6">
            {news.map((item) => (
              <article key={item.id} className="border-b border-slate-200 pb-6">
                <h2 className="text-2xl font-semibold mb-2">{item.title}</h2>
                <p className="text-slate-600 mb-2">{item.excerpt}</p>
                <time className="text-sm text-slate-500">
                  {new Date(item.published_at).toLocaleDateString('en-US')}
                </time>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}
