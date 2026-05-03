'use client'

import { supportedLocales, type Locale } from '@/config/locales'
import {
  localeCompletenessLabel,
  type LocaleCompletenessLevel,
} from '@/lib/admin/pageLocaleCompleteness'

const FLAG: Record<Locale, string> = {
  fr: '🇫🇷',
  en: '🇬🇧',
  it: '🇮🇹',
}

/** Pastilles drapeaux + point vert / ambre / rouge (complétude i18n), aligné sur l’esprit Builder / LocaleCompletenessStrip. */
export function HelpCollectionLocaleFlagStrip({
  levels,
}: {
  levels: Record<Locale, LocaleCompletenessLevel>
}) {
  return (
    <div className="inline-flex flex-wrap items-center gap-1">
      {supportedLocales.map((loc) => {
        const lv = levels[loc]
        const dot =
          lv === 'complete'
            ? 'bg-emerald-500'
            : lv === 'partial'
              ? 'bg-amber-500'
              : lv === 'missing'
                ? 'bg-red-500'
                : 'bg-slate-400'
        return (
          <span
            key={loc}
            title={`${loc.toUpperCase()} — ${localeCompletenessLabel(lv)}`}
            className="relative inline-flex h-7 w-7 items-center justify-center rounded-md border border-slate-200 bg-white text-[14px] leading-none shadow-sm"
          >
            <span aria-hidden>{FLAG[loc]}</span>
            <span
              className={`absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full ring-2 ring-white ${dot}`}
              aria-hidden
            />
          </span>
        )
      })}
    </div>
  )
}
