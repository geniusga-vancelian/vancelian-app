import React from 'react'
import type { Components } from 'react-markdown'
import ReactMarkdown from 'react-markdown'

import { articleBodyRemarkPlugins } from '@/lib/blog/articleBodyMarkdown'
import { cn } from '@/lib/utils'

/** Markdown bloc article portail (`art-prose__p`). */
export const portalArticleBodyMarkdownComponents: Partial<Components> = {
  p: ({ children }) => <p className="art-prose__p">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-v-fg">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-v-fg underline decoration-v-fg-20 underline-offset-2 transition hover:decoration-v-terracotta"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => <ul className="art-prose__check m-0">{children}</ul>,
  ol: ({ children }) => <ol className="art-prose__ol m-0">{children}</ol>,
  li: ({ children }) => <li className="art-prose__check-item">{children}</li>,
  code: ({ children }) => (
    <code className="rounded bg-v-fg-05 px-1 py-0.5 font-mono text-[0.9em] text-v-fg">{children}</code>
  ),
}

/** Markdown inline (listes, citations, labels) — pas de marges de paragraphe. */
export const portalArticleInlineMarkdownComponents: Partial<Components> = {
  ...portalArticleBodyMarkdownComponents,
  p: ({ children }) => <span className="inline leading-relaxed">{children}</span>,
  ul: ({ children }) => (
    <ul className="art-prose__check m-0 mt-2">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="art-prose__ol m-0 mt-2">{children}</ol>
  ),
  li: ({ children }) => <li className="art-prose__check-item">{children}</li>,
}

type PortalArticleMarkdownProps = {
  text: string
  variant?: 'body' | 'inline'
  className?: string
}

/** Interprète le Markdown CMS / agent IA dans le DS article portail (`art-prose__*`). */
export function PortalArticleMarkdown({
  text,
  variant = 'body',
  className,
}: PortalArticleMarkdownProps) {
  const body = text.trim()
  if (!body) return null
  const components =
    variant === 'inline' ? portalArticleInlineMarkdownComponents : portalArticleBodyMarkdownComponents
  return (
    <div className={cn(className)}>
      <ReactMarkdown remarkPlugins={[...articleBodyRemarkPlugins]} components={components}>
        {body}
      </ReactMarkdown>
    </div>
  )
}
