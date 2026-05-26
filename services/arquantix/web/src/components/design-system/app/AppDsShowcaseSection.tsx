import type { AppDsShowcaseSection as Section } from './appDsShowcaseManifest'
import { AppDsShowcaseItem } from './AppDsShowcaseItem'
import { cn } from '@/lib/utils'

type Props = {
  section: Section
  /** 2 ou 3 colonnes sur desktop (comme le kit). */
  columns?: 1 | 2 | 3
}

export function AppDsShowcaseSection({ section, columns = 1 }: Props) {
  const gridClass =
    columns === 3 ? 'app-ds-grid app-ds-grid--3' : columns === 2 ? 'app-ds-grid app-ds-grid--2' : 'app-ds-grid'

  return (
    <section className="app-ds-sec sec" id={section.id}>
      <header className="sec__head">
        <span className="sec__dot" aria-hidden />
        <span className="sec__num">{section.num}</span>
        <h2 className="sec__title">{section.title}</h2>
        {section.count ? <span className="app-ds-sec__count">{section.count}</span> : null}
      </header>
      <div className={cn(gridClass)}>
        {section.items.map((item) => (
          <AppDsShowcaseItem key={item.file} item={item} />
        ))}
      </div>
    </section>
  )
}
