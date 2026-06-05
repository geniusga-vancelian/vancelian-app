import { cn } from '@/lib/utils'
import { ArticleBodyMarkdown } from '@/lib/blog/articleBodyMarkdown'
import { figmaDsParagraphLargeBoldClassName } from '@/components/design-system/extracted/tokens/typography'

type Props = {
  items: string[]
  className?: string
}

/** Icône coche (vert vif) — Figma module List. */
function ListCheckIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      strokeWidth={2.25}
      stroke="currentColor"
      className="h-[1.125rem] w-[1.125rem] shrink-0"
      aria-hidden
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  )
}

/**
 * Liste à puces article (blog / help) : coche verte à gauche, libellé au format **Paragraph Large Bold** (DS).
 */
export function ArticleBodyBulletListBlock({ items, className }: Props) {
  const clean = (items || []).map((s) => String(s ?? '').trim()).filter(Boolean)
  if (clean.length === 0) {
    return null
  }
  return (
    <ul className={cn('my-8 list-none space-y-4 p-0', className)}>
      {clean.map((item, i) => (
        <li key={i} className="flex gap-3">
          <span
            className="mt-[0.3em] inline-flex shrink-0 text-[#22c55e]"
            aria-hidden
          >
            <ListCheckIcon />
          </span>
          <div
            className={cn(
              figmaDsParagraphLargeBoldClassName,
              'min-w-0 flex-1 text-black [&_strong]:font-semibold',
            )}
          >
            <ArticleBodyMarkdown text={item} variant="inline" />
          </div>
        </li>
      ))}
    </ul>
  )
}
