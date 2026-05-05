'use client'

import type { Locale } from '@/config/locales'
import { useAdminEditingLocale } from '@/components/admin/AdminEditingLocaleContext'
import { Languages } from 'lucide-react'

const LABEL: Record<Locale, string> = {
  fr: 'FR',
  en: 'EN',
  it: 'IT',
}

type Props = {
  contextLabel?: string
  className?: string
}

export function AdminEditingLocaleBar({ contextLabel, className = '' }: Props) {
  const { locale, setLocale, editingLocales } = useAdminEditingLocale()

  return (
    <div
      className={`flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-3 py-2 shadow-sm ${className}`}
    >
      <div className="flex items-center gap-2 text-slate-600">
        <Languages className="h-4 w-4 shrink-0 text-indigo-600" />
        <span className="text-xs font-medium text-slate-800">
          {contextLabel ? `${contextLabel} · ` : ''}Langue éditée
        </span>
      </div>
      {editingLocales.length <= 1 ? (
        <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-700">
          {LABEL[locale]}
        </span>
      ) : (
        <div className="flex flex-wrap gap-1">
          {editingLocales.map((loc) => (
            <button
              key={loc}
              type="button"
              onClick={() => setLocale(loc)}
              className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide transition ${
                locale === loc
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
              aria-pressed={locale === loc}
            >
              {LABEL[loc]}
            </button>
          ))}
        </div>
      )}
      <p className="text-[10px] text-slate-500">
        Aperçu et raccourcis utilisent cette locale.
      </p>
    </div>
  )
}
