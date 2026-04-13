/**
 * Format dates for article display (locale-aware)
 */

const LOCALE_LABELS: Record<string, { published: string; updated: string; minRead: string }> = {
  fr: {
    published: 'Publié le',
    updated: 'Mis à jour le',
    minRead: 'min de lecture',
  },
  en: {
    published: 'Published',
    updated: 'Updated',
    minRead: 'min read',
  },
  it: {
    published: 'Pubblicato il',
    updated: 'Aggiornato il',
    minRead: 'min di lettura',
  },
}

export function getDateLabels(locale: string) {
  return LOCALE_LABELS[locale] || LOCALE_LABELS['fr']
}

export function formatArticleDate(date: Date, locale: string = 'fr'): string {
  const dateFormatter = new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })

  const timeFormatter = new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
  })

  return `${dateFormatter.format(date)} à ${timeFormatter.format(date)}`
}

export function formatArticleDateShort(date: Date, locale: string = 'fr'): string {
  const formatter = new Intl.DateTimeFormat(locale, {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  })

  return formatter.format(date)
}

