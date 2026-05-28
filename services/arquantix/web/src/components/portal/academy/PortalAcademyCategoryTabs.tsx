'use client'

import { cn } from '@/lib/utils'

export type PortalAcademyTab = {
  id: string
  label: string
}

type Props = {
  tabs: PortalAcademyTab[]
  activeTab: string
  onTabChange: (tabId: string) => void
}

/** Onglets catégories — handoff `.acd-tabs`. */
export function PortalAcademyCategoryTabs({ tabs, activeTab, onTabChange }: Props) {
  if (tabs.length <= 1) return null

  return (
    <div className="acd-tabs" role="tablist" aria-label="Catégories d'articles">
      {tabs.map((tab) => {
        const active = activeTab === tab.id
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={active}
            className={cn('acd-tabs__tab', active && 'is-active')}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}
