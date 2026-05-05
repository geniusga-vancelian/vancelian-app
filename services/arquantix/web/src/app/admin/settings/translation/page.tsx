'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supportedLocales, defaultLocale, isValidLocale, type Locale } from '@/config/locales'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { X, Plus } from 'lucide-react'

interface TranslationGlossary {
  brandTerms?: Array<{ term: string; keep: boolean }>
  preferred?: Array<{ from: string; to: string }>
}

const LOCALE_LABEL: Record<Locale, string> = {
  en: 'English',
  fr: 'Français',
  it: 'Italiano',
}

export default function AdminTranslationSettingsPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settings, setSettings] = useState({
    supportedLocales: [...supportedLocales] as Locale[],
    defaultLocale: defaultLocale as Locale,
    multilingualEnabled: true,
    translationGlossary: null as TranslationGlossary | null,
  })

  const [newBrandTerm, setNewBrandTerm] = useState('')
  const [newPreferredFrom, setNewPreferredFrom] = useState('')
  const [newPreferredTo, setNewPreferredTo] = useState('')

  useEffect(() => {
    void fetchSettings()
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
      const rawSupported = (data.settings.supportedLocales || supportedLocales) as string[]
      const parsedSupported = rawSupported.filter((l): l is Locale => isValidLocale(l))
      const dl = isValidLocale(data.settings.defaultLocale)
        ? data.settings.defaultLocale
        : defaultLocale
      setSettings({
        supportedLocales: parsedSupported.length ? parsedSupported : [...supportedLocales],
        defaultLocale: dl,
        multilingualEnabled: data.settings.multilingualEnabled !== false,
        translationGlossary: data.settings.translationGlossary || null,
      })
    } catch (error) {
      console.error('Error fetching settings:', error)
      toastError('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const toggleLocale = (loc: Locale) => {
    setSettings((prev) => {
      const has = prev.supportedLocales.includes(loc)
      let next = has
        ? prev.supportedLocales.filter((l) => l !== loc)
        : [...prev.supportedLocales, loc]
      next = [...new Set(next)].filter(isValidLocale)
      if (next.length === 0) {
        toastError('At least one locale is required')
        return prev
      }
      let def = prev.defaultLocale
      if (!next.includes(def)) {
        def = next[0]
      }
      return { ...prev, supportedLocales: next, defaultLocale: def }
    })
  }

  const handleSave = async () => {
    if (!settings.supportedLocales.includes(settings.defaultLocale)) {
      toastError('Default language must be one of the enabled locales')
      return
    }
    setSaving(true)
    try {
      const response = await fetch('/api/admin/settings/translation', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supportedLocales: settings.supportedLocales,
          defaultLocale: settings.defaultLocale,
          multilingualEnabled: settings.multilingualEnabled,
          translationGlossary: settings.translationGlossary,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save settings')
      }

      toastSuccess('Saved')
      await fetchSettings()
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to save settings'
      toastError(message)
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
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Translation Settings</h1>
          <p className="text-sm text-gray-500 mt-1">
            Canonical copy is English-first; machine translation uses the default language as
            source. Disable multilingual to hide the public language switcher.
          </p>
        </div>
        <Link
          href="/admin/settings"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Settings
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 space-y-6">
        <h2 className="text-xl font-semibold">Site languages</h2>

        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={settings.multilingualEnabled}
              onChange={(e) =>
                setSettings((s) => ({ ...s, multilingualEnabled: e.target.checked }))
              }
              className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
            />
            Multilingual public site (language switcher in header)
          </label>
        </div>
        <p className="text-xs text-gray-500">
          When off, the globe control is hidden on the public site (desktop and mobile drawer).
        </p>

        <div>
          <span className="block text-sm font-medium text-gray-700 mb-2">Enabled locales</span>
          <div className="flex flex-wrap gap-3">
            {supportedLocales.map((locale) => (
              <label
                key={locale}
                className="inline-flex items-center gap-2 text-sm text-gray-700 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={settings.supportedLocales.includes(locale)}
                  onChange={() => toggleLocale(locale)}
                  className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                />
                {LOCALE_LABEL[locale]} ({locale.toUpperCase()})
              </label>
            ))}
          </div>
        </div>

        <div>
          <label htmlFor="default-locale" className="block text-sm font-medium text-gray-700 mb-2">
            Default (canonical) language
          </label>
          <select
            id="default-locale"
            value={settings.defaultLocale}
            onChange={(e) =>
              setSettings((s) => ({
                ...s,
                defaultLocale: e.target.value as Locale,
              }))
            }
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            {settings.supportedLocales.map((loc) => (
              <option key={loc} value={loc}>
                {LOCALE_LABEL[loc]} ({loc})
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-2">
            CMS copy operations and translation sources use this locale as primary.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold mb-4">Translation Glossary</h2>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Do Not Translate (Brand Terms)
          </label>
          <p className="text-xs text-gray-500 mb-3">
            Terms that should remain unchanged during translation (e.g., &quot;Arquantix&quot;)
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
              type="button"
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
                  type="button"
                  onClick={() => removeBrandTerm(index)}
                  className="text-green-600 hover:text-green-800"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Preferred Translations
          </label>
          <p className="text-xs text-gray-500 mb-3">
            Force specific translations (source → target wording hints for the model)
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
              type="button"
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
                  type="button"
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

      <div className="flex justify-end">
        <button
          type="button"
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
