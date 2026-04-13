import type { ReactNode } from 'react'
import { Navigation } from '@/components/sections/Navigation'
import { ReadingProgress } from '@/components/blog/ReadingProgress'
import type { MenuItem } from '@/lib/menu/getPrimaryMenu'

/**
 * Coquille commune aux pages « lecture » type article blog :
 * barre de progression, nav claire, conteneur blanc avec offset sous le header fixe.
 */
export function ArticleReadingLayout({
  menuItems,
  themeColor = 'light',
  showReadingProgress = true,
  children,
}: {
  menuItems: MenuItem[]
  themeColor?: 'dark' | 'light'
  showReadingProgress?: boolean
  children: ReactNode
}) {
  return (
    <>
      {showReadingProgress ? <ReadingProgress /> : null}
      <Navigation menuItems={menuItems} themeColor={themeColor} />
      <article className="min-h-screen bg-white pt-20 md:pt-24">{children}</article>
    </>
  )
}
