'use client'

import type { Components } from 'react-markdown'
import ReactMarkdown from 'react-markdown'

import { articleBodyRemarkPlugins } from '@/lib/blog/articleBodyMarkdown'
import { cn } from '@/lib/utils'

export type PortalVaultMarkdownVariant = 'overview' | 'narrative' | 'advisor'

const VARIANT_CLASS: Record<PortalVaultMarkdownVariant, string> = {
  overview: 'overview__body ofd-markdown',
  narrative: 'ofd-narrative__prose ofd-markdown',
  advisor: 'ai-tip__text ofd-markdown',
}

/** Composants Markdown alignés sur le DS portail (`ofd-markdown` dans offer-detail-layout-patterns.css). */
const portalVaultMarkdownComponents: Partial<Components> = {
  p: ({ children }) => <p>{children}</p>,
  strong: ({ children }) => <strong>{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
  ul: ({ children }) => <ul>{children}</ul>,
  ol: ({ children }) => <ol>{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  h3: ({ children }) => <h3 className="ofd-markdown__h3">{children}</h3>,
  h4: ({ children }) => <h4 className="ofd-markdown__h4">{children}</h4>,
  blockquote: ({ children }) => <blockquote>{children}</blockquote>,
  hr: () => <hr />,
  code: ({ className, children, ...props }) => {
    const isFenced = Boolean(className?.includes('language-'))
    if (isFenced) {
      return (
        <code className={cn(className, 'ofd-markdown__code-block')} {...props}>
          {children}
        </code>
      )
    }
    return (
      <code className="ofd-markdown__code-inline" {...props}>
        {children}
      </code>
    )
  },
  pre: ({ children }) => <pre className="ofd-markdown__pre">{children}</pre>,
}

type Props = {
  markdown: string
  variant?: PortalVaultMarkdownVariant
  className?: string
}

/** Interprète le Markdown Vault Builder / article selon le DS webapp (`overview__body`, `ofd-narrative__prose`, etc.). */
export function PortalVaultMarkdownContent({
  markdown,
  variant = 'overview',
  className,
}: Props) {
  const body = markdown.trim()
  if (!body) return null

  return (
    <div className={cn(VARIANT_CLASS[variant], className)}>
      <ReactMarkdown
        remarkPlugins={[...articleBodyRemarkPlugins]}
        components={portalVaultMarkdownComponents}
      >
        {body}
      </ReactMarkdown>
    </div>
  )
}
