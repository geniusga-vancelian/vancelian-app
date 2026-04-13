import { SectionHelpSearch } from './SectionHelpSearch'
import { SectionHelpBreadcrumbs } from './SectionHelpBreadcrumbs'

interface SectionHelpHeroProps {
  kicker?: string
  title?: string
  subtitle?: string
  placeholderSearch?: string
  helperText?: string
  backgroundStyle?: 'purple' | 'dark' | 'light'
  locale: string
  collectionSlug?: string
  collectionTitle?: string
  categorySlug?: string
  categoryTitle?: string
  showBreadcrumbs?: boolean
  breadcrumbsRootLabel?: string
  breadcrumbsSeparator?: string
}

export async function SectionHelpHero({
  kicker,
  title,
  subtitle,
  placeholderSearch,
  helperText,
  backgroundStyle = 'purple',
  locale,
  collectionSlug,
  collectionTitle,
  categorySlug,
  categoryTitle,
  showBreadcrumbs = false,
  breadcrumbsRootLabel,
  breadcrumbsSeparator,
}: SectionHelpHeroProps) {
  const bgClasses = {
    purple: 'bg-gradient-to-b from-indigo-600 to-indigo-700',
    dark: 'bg-gray-900',
    light: 'bg-gray-50',
  }

  const textClasses = {
    purple: 'text-white',
    dark: 'text-white',
    light: 'text-gray-900',
  }

  return (
    <>
      <div className={`${bgClasses[backgroundStyle]} border-b border-gray-200`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
          <div className="text-center max-w-3xl mx-auto">
            {kicker && (
              <p className={`text-sm font-semibold uppercase tracking-wider mb-4 ${textClasses[backgroundStyle]} opacity-90`}>
                {kicker}
              </p>
            )}
            {title && (
              <h1 className={`text-4xl md:text-5xl font-bold mb-12 ${textClasses[backgroundStyle]}`}>
                {title}
              </h1>
            )}
            
            {/* Search Bar */}
            {(placeholderSearch !== undefined || helperText !== undefined) && (
              <div className="max-w-2xl mx-auto">
                <SectionHelpSearch
                  locale={locale}
                  collectionSlug={collectionSlug}
                  categorySlug={categorySlug}
                  placeholder={placeholderSearch || 'Rechercher un article…'}
                  hint={helperText}
                  hintTextColor="white"
                />
              </div>
            )}
          </div>
        </div>
      </div>
      
      {/* Breadcrumbs - Outside header, below for better readability */}
      {showBreadcrumbs && (
        <div className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <SectionHelpBreadcrumbs
              rootLabel={breadcrumbsRootLabel}
              separator={breadcrumbsSeparator}
              locale={locale}
              collectionSlug={collectionSlug}
              collectionTitle={collectionTitle}
              categorySlug={categorySlug}
              categoryTitle={categoryTitle}
            />
          </div>
        </div>
      )}
    </>
  )
}

