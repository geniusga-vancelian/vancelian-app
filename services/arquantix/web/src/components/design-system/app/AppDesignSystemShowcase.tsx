'use client'

import Image from 'next/image'
import {
  APP_DS_SHOWCASE_SECTIONS,
  APP_DS_SHOWCASE_VERSION,
} from './appDsShowcaseManifest'
import { AppDsShowcaseSection } from './AppDsShowcaseSection'

const TOC_GROUPS: { head: string; sectionIds: string[] }[] = [
  { head: 'Foundations', sectionIds: ['brand', 'colors', 'type', 'spacing'] },
  { head: 'Components', sectionIds: ['simple', 'ui', 'cards', 'misc'] },
]

/** Showcase complet — calqué sur `ui_kits/vancelian-app/index.html` v2.1. */
export function AppDesignSystemShowcase() {
  return (
    <div className="app-ds-page">
      <header className="app-ds-ph">
        <div>
          <Image
            src="/brand/vancelian/logo-black-h.svg"
            alt="Vancelian"
            width={140}
            height={22}
            className="app-ds-ph__logo"
          />
          <h1 className="app-ds-ph__title">App design system</h1>
          <p className="app-ds-ph__sub">
            Mini-Storybook · chaque composant chargé depuis le handoff{' '}
            <code className="font-ui text-v-fg-muted">App Vancelian.zip</code> (
            <code className="font-ui text-v-fg-muted">/app-ds/preview</code>). Aligné pixel
            avec la dernière version du zip.
          </p>
        </div>
        <div className="app-ds-ph__meta">
          <strong>{APP_DS_SHOWCASE_VERSION}</strong>
          Mobile-first · portail web
        </div>
      </header>

      <nav className="app-ds-toc" aria-label="Table des matières">
        {TOC_GROUPS.map((group) => (
          <div key={group.head}>
            <div className="app-ds-toc__head">{group.head}</div>
            {group.sectionIds.map((id) => {
              const sec = APP_DS_SHOWCASE_SECTIONS.find((s) => s.id === id)
              if (!sec) return null
              return (
                <a key={id} href={`#${id}`}>
                  {sec.num} · {sec.title}
                </a>
              )
            })}
          </div>
        ))}
      </nav>

      {APP_DS_SHOWCASE_SECTIONS.map((section) => (
        <AppDsShowcaseSection
          key={section.id}
          section={section}
          columns={
            section.id === 'colors' ? 3 : section.id === 'brand' ? 2 : 1
          }
        />
      ))}

      <footer className="app-ds-footer">
        <div>Vancelian · App design system · v2.1</div>
        <div>Aman · Hermès · Cereal</div>
      </footer>
    </div>
  )
}
