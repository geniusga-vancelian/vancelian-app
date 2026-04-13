'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, FileJson } from 'lucide-react'

interface DsComponentDetail {
  id: string
  slug: string
  name: string
  schemaJson: Record<string, unknown>
  createdAt: string
  chapter: {
    id: string
    name: string
    slug: string
  }
}

export default function AdminFlutterWidgetDetailPage() {
  const router = useRouter()
  const params = useParams()
  const id = params?.id as string
  const [component, setComponent] = useState<DsComponentDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) {
      setLoading(false)
      return
    }
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
          return
        }
        return fetch(`/api/admin/ds-components/${id}`, { credentials: 'include' })
      })
      .then((res) => {
        if (!res) return
        if (!res.ok) {
          setError(res.status === 404 ? 'Composant introuvable' : 'Erreur lors du chargement')
          return
        }
        return res.json()
      })
      .then((data) => {
        if (data) setComponent(data)
      })
      .catch(() => setError('Erreur réseau'))
      .finally(() => setLoading(false))
  }, [id, router])

  if (loading) {
    return (
      <div className="space-y-6">
        <Link
          href="/admin/flutter"
          className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour à Flutter
        </Link>
        <p className="text-gray-500">Chargement…</p>
      </div>
    )
  }

  if (error || !component) {
    return (
      <div className="space-y-6">
        <Link
          href="/admin/flutter"
          className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour à Flutter
        </Link>
        <p className="text-red-600">{error ?? 'Composant introuvable'}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Link
        href="/admin/flutter"
        className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour à Flutter
      </Link>

      <div className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-3">
          <FileJson className="w-6 h-6 text-indigo-600" />
          <div>
            <h1 className="text-xl font-bold text-gray-900">{component.name}</h1>
            <p className="text-sm text-gray-500">
              {component.chapter.name} · {component.slug}
            </p>
          </div>
        </div>
        <div className="p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-2">Modèle JSON de fonctionnement</h2>
          <pre className="bg-gray-50 border border-gray-200 rounded-lg p-4 text-sm text-gray-800 overflow-x-auto overflow-y-auto max-h-[70vh] whitespace-pre-wrap break-words">
            {JSON.stringify(component.schemaJson, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  )
}
