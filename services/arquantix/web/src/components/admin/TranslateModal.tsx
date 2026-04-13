'use client'

import { useState } from 'react'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { toastSuccess, toastError, toastInfo } from '@/lib/admin/toast'

interface TranslateModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  sourceLocale: Locale
  onTranslate: (params: {
    sourceLocale: Locale
    targetLocales: Locale[]
    mode: 'missing' | 'force'
  }) => Promise<{
    results: {
      created: string[]
      updated: string[]
      skipped: string[]
      errors: Array<{ locale: string; error: string }>
    }
  }>
  hasGlossary?: boolean
}

export function TranslateModal({
  open,
  onOpenChange,
  sourceLocale,
  onTranslate,
  hasGlossary = false,
}: TranslateModalProps) {
  const [targetLocales, setTargetLocales] = useState<Locale[]>([])
  const [mode, setMode] = useState<'missing' | 'force'>('missing')
  const [loading, setLoading] = useState(false)

  const availableLocales = supportedLocales.filter((l) => l !== sourceLocale)

  const handleTranslate = async () => {
    if (targetLocales.length === 0) {
      toastError('Please select at least one target locale')
      return
    }

    setLoading(true)
    try {
      const response = await onTranslate({
        sourceLocale,
        targetLocales,
        mode,
      })

      const { results } = response
      const totalSuccess = results.created.length + results.updated.length
      const hasErrors = results.errors.length > 0
      const hasSkipped = results.skipped.length > 0

      if (totalSuccess > 0) {
        toastSuccess(
          `Translations completed: ${totalSuccess} locale(s) ${results.created.length > 0 ? 'created' : 'updated'} as MACHINE (needs approval)`
        )
      }

      if (hasSkipped) {
        toastInfo(`${results.skipped.length} locale(s) skipped (already exist)`)
      }

      if (hasErrors) {
        const firstError = results.errors[0]
        toastError(`Error translating ${firstError.locale}: ${firstError.error}`)
      }

      if (totalSuccess > 0 && !hasErrors) {
        onOpenChange(false)
        setTargetLocales([])
      }
    } catch (error: any) {
      toastError(error.message || 'Translation failed')
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
        <h3 className="text-xl font-semibold mb-4">Auto-translate</h3>

        <div className="space-y-4">
          {/* Source Locale */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Locale
            </label>
            <input
              type="text"
              value={sourceLocale.toUpperCase()}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
            />
          </div>

          {/* Target Locales */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Target Locales *
            </label>
            <div className="space-y-2">
              {availableLocales.map((locale) => (
                <label key={locale} className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={targetLocales.includes(locale)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setTargetLocales([...targetLocales, locale])
                      } else {
                        setTargetLocales(targetLocales.filter((l) => l !== locale))
                      }
                    }}
                    className="rounded"
                  />
                  <span className="text-sm">{locale.toUpperCase()}</span>
                </label>
              ))}
            </div>
            {targetLocales.length === 0 && (
              <p className="text-xs text-red-500 mt-1">Please select at least one target locale</p>
            )}
            {targetLocales.length > 10 && (
              <p className="text-xs text-red-500 mt-1">Maximum 10 locales at once</p>
            )}
          </div>

          {/* Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Mode</label>
            <div className="space-y-2">
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={mode === 'missing'}
                  onChange={() => setMode('missing')}
                  name="mode"
                />
                <span className="text-sm">Missing only (default)</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="radio"
                  checked={mode === 'force'}
                  onChange={() => setMode('force')}
                  name="mode"
                />
                <span className="text-sm">Force re-translate</span>
              </label>
            </div>
          </div>

          {/* Glossary Badge */}
          {hasGlossary && (
            <div className="px-3 py-2 bg-green-50 border border-green-200 rounded-md">
              <p className="text-xs text-green-800">
                ✓ Glossary enabled (brand terms and preferred translations will be applied)
              </p>
            </div>
          )}
        </div>

        <div className="flex gap-3 mt-6">
          <button
            onClick={handleTranslate}
            disabled={loading || targetLocales.length === 0 || targetLocales.length > 10}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {loading ? 'Translating...' : 'Translate'}
          </button>
          <button
            onClick={() => {
              onOpenChange(false)
              setTargetLocales([])
            }}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 disabled:opacity-50"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}

