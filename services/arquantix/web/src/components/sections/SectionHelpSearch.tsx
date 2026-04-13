'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { Search, X, Loader2 } from 'lucide-react'
import Link from 'next/link'
import { formatArticleDateShort } from '@/lib/blog/formatDates'

interface SectionHelpSearchProps {
  placeholder?: string
  hint?: string
  clearLabel?: string
  noResultsTitle?: string
  noResultsSubtitle?: string
  locale: string
  searchQuery?: string
  onSearch?: (query: string) => void
  collectionSlug?: string
  categorySlug?: string
  hintTextColor?: 'white' | 'gray'
}

interface SearchResult {
  id: string
  slug: string
  question: string
  snippet: string
  collection: { slug: string; title: string }
  category: { slug: string; title: string }
  updatedAt: string
}

export function SectionHelpSearch({
  placeholder = 'Rechercher un article…',
  hint,
  clearLabel = 'Effacer',
  noResultsTitle = 'Aucun résultat',
  noResultsSubtitle = 'Essayez un autre mot-clé.',
  locale,
  searchQuery: initialQuery = '',
  onSearch,
  collectionSlug,
  categorySlug,
  hintTextColor = 'gray',
}: SectionHelpSearchProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname() ?? ''
  const [query, setQuery] = useState(initialQuery || searchParams?.get('q') || '')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showResults, setShowResults] = useState(false)

  // Sync with URL query param
  useEffect(() => {
    const urlQuery = searchParams?.get('q') || ''
    if (urlQuery !== query) {
      setQuery(urlQuery)
      if (urlQuery.length >= 2) {
        performSearch(urlQuery)
      } else {
        setResults([])
        setShowResults(false)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams])

  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim() || searchQuery.trim().length < 2) {
      setResults([])
      setShowResults(false)
      return
    }

    setLoading(true)
    setError(null)

      if (process.env.NODE_ENV !== 'production') {
        console.debug('[SectionHelpSearch] Performing search:', {
          query: searchQuery.trim(),
          locale,
          collectionSlug,
          categorySlug,
        })
      }

    try {
      const params = new URLSearchParams()
      params.set('q', searchQuery.trim())
      params.set('locale', locale)
      if (collectionSlug) {
        params.set('collection', collectionSlug)
      }
      if (categorySlug) {
        params.set('category', categorySlug)
      }

      const apiUrl = `/api/help/search?${params.toString()}`
      
      if (process.env.NODE_ENV !== 'production') {
        console.debug('[SectionHelpSearch] Fetching:', apiUrl)
      }

      const response = await fetch(apiUrl)
      
      if (!response.ok) {
        const errorText = await response.text()
        if (process.env.NODE_ENV !== 'production') {
          console.error('[SectionHelpSearch] API error:', response.status, errorText)
        }
        throw new Error(`Search failed: ${response.status} ${errorText}`)
      }

      const data = await response.json()
      
      if (process.env.NODE_ENV !== 'production') {
        console.debug('[SectionHelpSearch] Search completed:', {
          resultsCount: data.results?.length || 0,
          query: data.query,
          hasError: !!data.error,
        })
      }

      setResults(data.results || [])
      setShowResults(true)
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error'
      console.error('[SectionHelpSearch] Search error:', err)
      if (process.env.NODE_ENV !== 'production') {
        console.error('[SectionHelpSearch] Error details:', {
          message: errorMessage,
          stack: err instanceof Error ? err.stack : undefined,
        })
      }
      setError('Erreur lors de la recherche. Veuillez réessayer.')
      setResults([])
      setShowResults(false)
    } finally {
      setLoading(false)
    }
  }, [locale, collectionSlug, categorySlug])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmedQuery = query.trim()
    
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[SectionHelpSearch] Form submitted:', trimmedQuery)
    }

    if (trimmedQuery.length < 2) {
      return
    }

    // Update URL - this will trigger the URL sync effect which will perform the search
    const params = new URLSearchParams(searchParams?.toString() ?? '')
    if (trimmedQuery) {
      params.set('q', trimmedQuery)
    } else {
      params.delete('q')
    }
    router.push(`${pathname}?${params.toString()}`)

    // Note: Search will be performed by URL sync effect, avoid double search
    // But we perform it here anyway if URL doesn't change immediately
    const newUrl = `${pathname}?${params.toString()}`
    if (newUrl !== `${pathname}?${searchParams?.toString() ?? ''}`) {
      performSearch(trimmedQuery)
    }

    if (onSearch) {
      onSearch(trimmedQuery)
    }
  }

  const handleClear = () => {
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[SectionHelpSearch] Clearing search')
    }

    setQuery('')
    setResults([])
    setShowResults(false)
    setError(null)

    // Update URL
    const params = new URLSearchParams(searchParams?.toString() ?? '')
    params.delete('q')
    router.push(`${pathname}?${params.toString()}`)

    if (onSearch) {
      onSearch('')
    }
  }

  // Debounce effect for input changes (only if not from URL sync)
  useEffect(() => {
    const urlQuery = searchParams?.get('q') || ''
    // Skip debounce if query matches URL (means it came from URL sync, not user typing)
    if (query === urlQuery) {
      return
    }

    if (query.trim().length >= 2) {
      const timeoutId = setTimeout(() => {
        // Only search if query still doesn't match URL (avoid double search)
        if (query !== (searchParams?.get('q') || '')) {
          performSearch(query)
        }
      }, 300)
      return () => clearTimeout(timeoutId)
    } else {
      setResults([])
      setShowResults(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newQuery = e.target.value
    setQuery(newQuery)
    
    if (process.env.NODE_ENV !== 'production') {
      console.debug('[SectionHelpSearch] Input changed:', newQuery)
    }
  }

  const getArticleUrl = (result: SearchResult) => {
    return `/help/${result.collection.slug}/${result.category.slug}/${result.slug}`
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-8 mb-8">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={handleInputChange}
            placeholder={placeholder}
            className="w-full pl-12 pr-12 py-4 text-lg border border-gray-300 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          />
          {loading && (
            <Loader2 className="absolute right-12 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400 animate-spin" />
          )}
          {query && !loading && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              aria-label={clearLabel}
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
        {hint && (
          <p className={`mt-2 text-sm ${hintTextColor === 'white' ? 'text-white opacity-90' : 'text-gray-500'}`}>{hint}</p>
        )}
      </form>

      {/* Search Results */}
      {showResults && (
        <div className="mt-4 bg-white rounded-xl shadow-lg border border-gray-200 max-h-96 overflow-y-auto">
          {error && (
            <div className="p-4 text-sm text-red-600">
              {error}
            </div>
          )}
          {!error && results.length === 0 && !loading && (
            <div className="p-6 text-center">
              <p className="text-lg font-semibold text-gray-900 mb-2">{noResultsTitle}</p>
              <p className="text-gray-500">{noResultsSubtitle}</p>
            </div>
          )}
          {!error && results.length > 0 && (
            <div className="divide-y divide-gray-200">
              {results.map((result) => (
                <Link
                  key={result.id}
                  href={getArticleUrl(result)}
                  className="block p-4 hover:bg-gray-50 transition-colors"
                  onClick={() => setShowResults(false)}
                >
                  <h3 className="text-base font-semibold text-gray-900 mb-1">
                    {result.question}
                  </h3>
                  {result.snippet && (
                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                      {result.snippet}
                    </p>
                  )}
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>{result.collection.title}</span>
                    <span>›</span>
                    <span>{result.category.title}</span>
                    {result.updatedAt && (
                      <>
                        <span>•</span>
                        <span>Mis à jour {formatArticleDateShort(new Date(result.updatedAt), locale)}</span>
                      </>
                    )}
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
