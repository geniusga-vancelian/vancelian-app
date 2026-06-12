import React from 'react'
import type { Components } from 'react-markdown'
import ReactMarkdown from 'react-markdown'

import { articleBodyRemarkPlugins } from '@/lib/blog/articleBodyMarkdown'
import { cn } from '@/lib/utils'

/** Markdown inline Vault Builder portail (`overview__body`, `step__title`, etc.). */
export const portalVaultInlineMarkdownComponents: Partial<Components> = {
  p: ({ children }) => <span className="inline leading-relaxed">{children}</span>,
  strong: ({ children }) => <strong className="font-semibold text-v-fg">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-v-fg underline decoration-v-fg-20 underline-offset-2"
    >
      {children}
    </a>
  ),
  code: ({ children }) => (
    <code className="ofd-markdown__code-inline">{children}</code>
  ),
}

type Props = {
  text: string
  className?: string
}

/** Interprète le Markdown agent IA dans les champs texte des modules Vault portail. */
export function PortalVaultInlineMarkdown({ text, className }: Props) {
  const body = text.trim()
  if (!body) return null
  return (
    <span className={cn('ofd-markdown ofd-markdown--inline', className)}>
      <ReactMarkdown
        remarkPlugins={[...articleBodyRemarkPlugins]}
        components={portalVaultInlineMarkdownComponents}
      >
        {body}
      </ReactMarkdown>
    </span>
  )
}

/** Corps de réponse FAQ accordéon — blocs courts, styles `faq__body`. */
const portalVaultFaqBodyMarkdownComponents: Partial<Components> = {
  ...portalVaultInlineMarkdownComponents,
  p: ({ children }) => <p className="m-0 [&+p]:mt-3">{children}</p>,
  ul: ({ children }) => <ul className="m-0 mt-3 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="m-0 mt-3 list-decimal space-y-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
}

export function PortalVaultFaqBodyMarkdown({ text, className }: Props) {
  const body = text.trim()
  if (!body) return null
  return (
    <div className={cn('faq__body ofd-markdown', className)}>
      <ReactMarkdown
        remarkPlugins={[...articleBodyRemarkPlugins]}
        components={portalVaultFaqBodyMarkdownComponents}
      >
        {body}
      </ReactMarkdown>
    </div>
  )
}
