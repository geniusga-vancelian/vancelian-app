'use client'

import { supportedLocales, type Locale } from '@/config/locales'
import {
  localeCompletenessLabel,
  type LocaleCompletenessLevel,
} from '@/lib/admin/pageLocaleCompleteness'

export function LocaleCompletenessStrip({
  levels,
  variant = 'default',
}: {
  levels?: Record<Locale, LocaleCompletenessLevel>
  /** `inline` : même ligne que le titre (pas de libellé « i18n », pas de marge haute). */
  variant?: 'default' | 'inline'
}) {
  if (!levels) {
    return (
      <span
        className={`inline-block text-[10px] text-slate-400 ${variant === 'inline' ? '' : 'mt-1'}`}
      >
        …
      </span>
    )
  }
  return (
    <div
      className={
        variant === 'inline'
          ? 'inline-flex flex-wrap items-center gap-1'
          : 'mt-1.5 flex flex-wrap items-center gap-1'
      }
    >
      {variant === 'default' ? (
        <span className="mr-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-400">
          i18n
        </span>
      ) : null}
      {supportedLocales.map((loc) => {
        const lv = levels[loc]
        const style =
          lv === 'complete'
            ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
            : lv === 'partial'
              ? 'border-amber-200 bg-amber-50 text-amber-900'
              : lv === 'missing'
                ? 'border-red-200 bg-red-50 text-red-900'
                : 'border-slate-200 bg-slate-100 text-slate-600'
        const mark =
          lv === 'complete' ? '✓' : lv === 'partial' ? '⚠' : lv === 'missing' ? '✗' : '—'
        return (
          <span
            key={loc}
            title={`${loc.toUpperCase()} : ${localeCompletenessLabel(lv)}`}
            className={`inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold ${style}`}
          >
            {loc.toUpperCase()}
            <span className="ml-0.5 opacity-90" aria-hidden>
              {mark}
            </span>
          </span>
        )
      })}
    </div>
  )
}
