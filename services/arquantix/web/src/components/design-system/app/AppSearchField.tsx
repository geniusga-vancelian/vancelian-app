'use client'

import { useId, useState } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

export type AppSearchFieldProps = {
  label?: string
  value: string
  onChange: (value: string) => void
  className?: string
  /** Bouton effacer quand la valeur est non vide (preview/63). */
  clearable?: boolean
  disabled?: boolean
}

/** Champ recherche — preview/63-search-result-list · shell `.fld` flottant. */
export function AppSearchField({
  label = 'Search',
  value,
  onChange,
  className,
  clearable = true,
  disabled = false,
}: AppSearchFieldProps) {
  const id = useId()
  const [focused, setFocused] = useState(false)
  const filled = value.length > 0

  return (
    <div
      className={cn(
        'fld fld--icon-left w-full',
        focused && 'fld--focus',
        filled && 'fld--filled',
        disabled && 'fld--disabled',
        className,
      )}
    >
      <KalaiIcon name="search" size={20} className="fld__ic shrink-0" aria-hidden />
      <label htmlFor={id} className="fld__lbl-float">
        {label}
      </label>
      <input
        id={id}
        type="search"
        className="fld__inp"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        autoComplete="off"
        enterKeyHint="search"
      />
      {clearable && filled && !disabled ? (
        <button
          type="button"
          className="inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-v-fg-20 text-white"
          onClick={() => onChange('')}
          aria-label="Clear search"
        >
          <KalaiIcon name="remove" size={12} className="text-white" />
        </button>
      ) : null}
    </div>
  )
}
