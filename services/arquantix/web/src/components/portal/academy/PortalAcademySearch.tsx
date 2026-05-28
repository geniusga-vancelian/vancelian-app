'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'

type Props = {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

/** Barre de recherche — handoff `.faq-search.acd-search`. */
export function PortalAcademySearch({
  value,
  onChange,
  placeholder = 'Rechercher un article, une catégorie, un auteur…',
}: Props) {
  return (
    <div className="faq-search acd-search">
      <span className="faq-search__ic" aria-hidden>
        <KalaiIcon name="search" size={16} />
      </span>
      <input
        type="search"
        className="faq-search__input"
        placeholder={placeholder}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        aria-label="Rechercher dans l'Académie"
      />
      {value ? (
        <button
          type="button"
          className="faq-search__clear"
          onClick={() => onChange('')}
          aria-label="Effacer la recherche"
        >
          <KalaiIcon name="close" size={16} />
        </button>
      ) : null}
    </div>
  )
}
