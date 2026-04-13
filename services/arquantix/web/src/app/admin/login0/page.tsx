import Link from 'next/link'
import { resolveIntroVideoUrl } from '@/lib/admin/resolveIntroVideoUrl'
import { AdminLogin0Background } from './AdminLogin0Background'

export const dynamic = 'force-dynamic'

export default async function AdminLogin0Page() {
  const videoUrl = await resolveIntroVideoUrl()

  return (
    <div className="relative min-h-screen overflow-hidden">
      <AdminLogin0Background videoUrl={videoUrl} />
      <div
        className="absolute inset-0 bg-slate-900/35"
        aria-hidden
      />

      <div className="relative z-10 flex min-h-screen flex-col">
        <header
          className="h-12 shrink-0 bg-black/20 backdrop-blur-md sm:h-14"
          aria-label="Barre supérieure"
        />

        <div className="flex flex-1 flex-col items-center justify-center px-4 pb-12 pt-8 sm:pt-10">
          <div className="w-full max-w-sm space-y-8 rounded-lg border border-white/15 bg-white/95 p-8 shadow-lg backdrop-blur-sm">
            <div className="text-center">
              <h1 className="text-2xl font-bold text-gray-900">Arquantix CMS</h1>
              <p className="mt-2 text-sm text-gray-600">Choisissez une action</p>
            </div>
            <div className="flex flex-col gap-3">
              <Link
                href="/admin/login"
                className="flex justify-center rounded-md bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                Connexion
              </Link>
              <Link
                href="/admin/signup"
                className="flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
              >
                Inscription
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
