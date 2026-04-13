'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { X, Plus } from 'lucide-react'

interface TranslationGlossary {
  brandTerms?: Array<{ term: string; keep: boolean }>
  preferred?: Array<{ from: string; to: string }>
}

export default function AdminTranslationSettingsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState({
    supportedLocales: supportedLocales as readonly Locale[],
    defaultLocale: defaultLocale as Locale,
    translationGlossary: null as TranslationGlossary | null,
  })

  const [newBrandTerm, setNewBrandTerm] = useState('')
  const [newPreferredFrom, setNewPreferredFrom] = useState('')
  const [newPreferredTo, setNewPreferredTo] = useState('')

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/admin/settings/translation')
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch settings')
      }

      const data = await response.json()
      setSettings({
        supportedLocales: data.settings.supportedLocales || supportedLocales,
        defaultLocale: data.settings.defaultLocale || defaultLocale,
        translationGlossary: data.settings.translationGlossary || null,
      })
    } catch (error) {
      console.error('Error fetching settings:', error)
      toastError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await fetch('/api/admin/settings/translation', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supportedLocales: settings.supportedLocales,
          defaultLocale: settings.defaultLocale,
          translationGlossary: settings.translationGlossary,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save settings')
      }

      toastSuccess('Saved')
      await fetchSettings()
    } catch (error: any) {
      toastError(error.message || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const addBrandTerm = () => {
    if (!newBrandTerm.trim()) return

    const glossary = settings.translationGlossary || { brandTerms: [], preferred: [] }
    const brandTerms = glossary.brandTerms || []

    if (brandTerms.some((t) => t.term.toLowerCase() === newBrandTerm.trim().toLowerCase())) {
      toastError('This term already exists')
      return
    }

    setSettings({
      ...settings,
      translationGlossary: {
        ...glossary,
        brandTerms: [...brandTerms, { term: newBrandTerm.trim(), keep: true }],
      },
    })
    setNewBrandTerm('')
  }

  const removeBrandTerm = (index: number) => {
    const glossary = settings.translationGlossary || { brandTerms: [], preferred: [] }
    const brandTerms = glossary.brandTerms || []
    setSettings({
      ...settings,
      translationGlossary: {
        ...glossary,
        brandTerms: brandTerms.filter((_, i) => i !== index),
      },
    })
  }

  const addPreferred = () => {
    if (!newPreferredFrom.trim() || !newPreferredTo.trim()) return

    const glossary = settings.translationGlossary || { brandTerms: [], preferred: [] }
    const preferred = glossary.preferred || []

    if (preferred.some((p) => p.from.toLowerCase() === newPreferredFrom.trim().toLowerCase())) {
      toastError('This preferred translation already exists')
      return
    }

    setSettings({
      ...settings,
      translationGlossary: {
        ...glossary,
        preferred: [...preferred, { from: newPreferredFrom.trim(), to: newPreferredTo.trim() }],
      },
    })
    setNewPreferredFrom('')
    setNewPreferredTo('')
  }

  const removePreferred = (index: number) => {
    const glossary = settings.translationGlossary || { brandTerms: [], preferred: [] }
    const preferred = glossary.preferred || []
    setSettings({
      ...settings,
      translationGlossary: {
        ...glossary,
        preferred: preferred.filter((_, i) => i !== index),
      },
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading settings...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Translation Settings</h1>
          <p className="text-sm text-gray-500 mt-1">Configure translation glossary and settings</p>
        </div>
        <Link
          href="/admin/settings"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Settings
        </Link>
      </div>

      {/* Supported Locales */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4">Supported Locales</h2>
        <div className="flex flex-wrap gap-2">
          {supportedLocales.map((locale) => (
            <span
              key={locale}
              className={`px-3 py-1 rounded-full text-sm ${
                settings.supportedLocales.includes(locale)
                  ? 'bg-indigo-100 text-indigo-800'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {locale.toUpperCase()}
            </span>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Supported locales are configured in code. Default: {settings.defaultLocale.toUpperCase()}
        </p>
      </div>

      {/* Glossary */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4">Translation Glossary</h2>

        {/* Brand Terms */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Do Not Translate (Brand Terms)
          </label>
          <p className="text-xs text-gray-500 mb-3">
            Terms that should remain unchanged during translation (e.g., "Arquantix", "Vancelian")
          </p>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newBrandTerm}
              onChange={(e) => setNewBrandTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && addBrandTerm()}
              placeholder="Enter brand term"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            <button
              onClick={addBrandTerm}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {(settings.translationGlossary?.brandTerms || []).map((term, index) => (
              <span
                key={index}
                className="inline-flex items-center gap-2 px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm"
              >
                {term.term}
                <button
                  onClick={() => removeBrandTerm(index)}
                  className="text-green-600 hover:text-green-800"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        </div>

        {/* Preferred Translations */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Preferred Translations
          </label>
          <p className="text-xs text-gray-500 mb-3">
            Force specific translations (e.g., "vault" → "coffre")
          </p>
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={newPreferredFrom}
              onChange={(e) => setNewPreferredFrom(e.target.value)}
              placeholder="From (source)"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            <input
              type="text"
              value={newPreferredTo}
              onChange={(e) => setNewPreferredTo(e.target.value)}
              placeholder="To (target)"
              className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
            <button
              onClick={addPreferred}
              className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
          <div className="space-y-2">
            {(settings.translationGlossary?.preferred || []).map((pref, index) => (
              <div
                key={index}
                className="flex items-center justify-between px-3 py-2 bg-blue-50 rounded-md"
              >
                <span className="text-sm">
                  <span className="font-medium">{pref.from}</span> →{' '}
                  <span className="font-medium">{pref.to}</span>
                </span>
                <button
                  onClick={() => removePreferred(index)}
                  className="text-blue-600 hover:text-blue-800"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}









