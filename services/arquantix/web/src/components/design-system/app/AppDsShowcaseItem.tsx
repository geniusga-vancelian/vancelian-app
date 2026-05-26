import type { AppDsShowcaseItem as Item } from './appDsShowcaseManifest'

type Props = {
  item: Item
}

export function AppDsShowcaseItem({ item }: Props) {
  const src = `/app-ds/preview/${item.file}`
  const openHref = item.openHref ? `/app-ds/${item.openHref}` : src

  return (
    <article className="app-ds-item">
      <header className="app-ds-item__head">
        <h3 className="app-ds-item__title">{item.title}</h3>
        <a className="app-ds-item__open" href={openHref} target="_blank" rel="noopener noreferrer">
          Open ↗
        </a>
      </header>
      <iframe
        className="app-ds-item__frame"
        src={src}
        height={item.height}
        loading="lazy"
        title={item.title}
      />
    </article>
  )
}
