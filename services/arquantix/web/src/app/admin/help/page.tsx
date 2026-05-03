'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { FolderOpen, Tag, FileText, ArrowRight } from 'lucide-react'

export default function AdminHelpPage() {
  const router = useRouter()

  useEffect(() => {
    // Check if user is authenticated
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
        }
      })
      .catch(() => {
        router.push('/admin/login')
      })
  }, [router])

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Help Center</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Gérer le Centre d&apos;aide</h2>
        <p className="text-gray-600 mb-4">
          Organisez vos articles d&apos;aide en collections et catégories.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Link
          href="/admin/articles/collections#collections-help"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow group"
        >
          <div className="flex items-center justify-between mb-4">
            <FolderOpen className="w-8 h-8 text-indigo-600" />
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 transition-colors" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Collections</h3>
          <p className="text-gray-600 text-sm">
            Créez et gérez les collections d&apos;articles depuis la page unifiée{' '}
            <span className="font-mono text-[11px]">Articles · Collections</span> (ancre Help).
          </p>
        </Link>

        <Link
          href="/admin/help/categories"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow group"
        >
          <div className="flex items-center justify-between mb-4">
            <Tag className="w-8 h-8 text-indigo-600" />
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 transition-colors" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Catégories</h3>
          <p className="text-gray-600 text-sm">
            Organisez les articles par catégories au sein de chaque collection
          </p>
        </Link>

        <Link
          href="/admin/articles?type=HELP"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow group"
        >
          <div className="flex items-center justify-between mb-4">
            <FileText className="w-8 h-8 text-indigo-600" />
            <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-indigo-600 transition-colors" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Articles</h3>
          <p className="text-gray-600 text-sm">
            Les articles d&apos;aide sont désormais gérés depuis l&apos;éditeur unifié
            (<code className="rounded bg-gray-100 px-1 text-[11px]">/admin/articles</code>{' '}
            avec le filtre HELP).
          </p>
        </Link>
      </div>
    </div>
  )
}









