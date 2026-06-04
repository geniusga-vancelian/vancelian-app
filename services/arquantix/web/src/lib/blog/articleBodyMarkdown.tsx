import React from 'react'
import type { Components } from 'react-markdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'
import { cn } from '@/lib/utils'

/** Plugins : GFM (tableaux, etc.) + sauts de ligne simples → `<br>`. */
export const articleBodyRemarkPlugins = [remarkGfm, remarkBreaks] as const

export const articleBodyMarkdownComponents: Partial<Components> = {
  p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
  strong: ({ children }) => <strong className="font-semibold text-[#1a1d24]">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  a: ({ href, children }) => (
    <a
      href={href}
      className="text-[#1a1d24] underline decoration-[#c5c9d4] underline-offset-2 transition hover:decoration-black"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => <ul className="my-4 list-outside list-disc space-y-2 pl-6 text-[#2a2d35]">{children}</ul>,
  ol: ({ children }) => <ol className="my-4 list-outside list-decimal space-y-2 pl-6 text-[#2a2d35]">{children}</ol>,
  li: ({ children }) => <li className="pl-1 leading-relaxed [&_ul]:mt-2 [&_ol]:mt-2">{children}</li>,
  h3: ({ children }) => (
    <h3 className="mb-2 mt-8 scroll-mt-28 text-[1.25rem] font-semibold leading-snug text-black first:mt-0">
      {children}
    </h3>
  ),
  h4: ({ children }) => (
    <h4 className="mb-2 mt-6 scroll-mt-28 text-lg font-semibold text-black first:mt-0">{children}</h4>
  ),
  h5: ({ children }) => <h5 className="mb-1 mt-4 text-base font-semibold text-[#1a1d24]">{children}</h5>,
  h6: ({ children }) => <h6 className="mb-1 mt-3 text-sm font-semibold text-[#2a2d35]">{children}</h6>,
  code: ({ className, children, ...props }) => {
    const isFenced = Boolean(className?.includes('language-'))
    if (isFenced) {
      return (
        <code className={cn(className, 'block font-mono text-sm leading-relaxed text-[#1a1d24]')} {...props}>
          {children}
        </code>
      )
    }
    return (
      <code className="rounded bg-[#f0f1f4] px-1.5 py-0.5 font-mono text-[0.9em] text-[#1a1d24]" {...props}>
        {children}
      </code>
    )
  },
  pre: ({ children }) => (
    <pre className="my-4 overflow-x-auto rounded-lg border border-[#e5e8f0] bg-[#f7f8fb] p-4 text-sm leading-relaxed text-[#1a1d24]">
      {children}
    </pre>
  ),
  blockquote: ({ children }) => (
    <blockquote className="my-4 border-l-4 border-[#dfe3ee] pl-4 text-[#3d4149] [&_p]:mb-0">{children}</blockquote>
  ),
  hr: () => <hr className="my-8 border-0 border-t border-[#e5e8f0]" />,
  table: ({ children }) => (
    <div className="my-6 overflow-x-auto">
      <table className="w-full min-w-[280px] border-collapse border border-[#e5e8f0] text-left text-sm">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-[#f7f8fb]">{children}</thead>,
  th: ({ children }) => <th className="border border-[#e5e8f0] px-3 py-2 font-semibold text-[#1a1d24]">{children}</th>,
  td: ({ children }) => <td className="border border-[#e5e8f0] px-3 py-2 align-top text-[#2a2d35]">{children}</td>,
  tr: ({ children }) => <tr className="even:bg-[#fafbfc]">{children}</tr>,
  del: ({ children }) => <del className="text-[#8b90a0] line-through">{children}</del>,
}

/** Variante compacte (citation, item de liste à puces) — pas de marges de paragraphe article. */
export const articleBodyInlineMarkdownComponents: Partial<Components> = {
  ...articleBodyMarkdownComponents,
  p: ({ children }) => <span className="block leading-relaxed [&+span]:mt-2">{children}</span>,
  ul: ({ children }) => (
    <ul className="mt-2 list-outside list-disc space-y-1 pl-5 font-normal text-[#2a2d35]">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mt-2 list-outside list-decimal space-y-1 pl-5 font-normal text-[#2a2d35]">{children}</ol>
  ),
  li: ({ children }) => <li className="pl-1 leading-relaxed font-normal [&_ul]:mt-1 [&_ol]:mt-1">{children}</li>,
}

type ArticleBodyMarkdownProps = {
  text: string
  variant?: 'body' | 'inline'
  className?: string
}

export function ArticleBodyMarkdown({ text, variant = 'body', className }: ArticleBodyMarkdownProps) {
  const body = text.trim()
  if (!body) return null
  const components =
    variant === 'inline' ? articleBodyInlineMarkdownComponents : articleBodyMarkdownComponents
  return (
    <div className={className}>
      <ReactMarkdown remarkPlugins={[...articleBodyRemarkPlugins]} components={components}>
        {body}
      </ReactMarkdown>
    </div>
  )
}
