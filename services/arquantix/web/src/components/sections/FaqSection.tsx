'use client'

import React from 'react'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import ReactMarkdown from 'react-markdown'

export interface FaqSectionProps {
  title?: string
  subtitle?: string
  items?: Array<{
    id: string
    question: string
    answerMarkdown: string
  }>
  ui?: {
    expandAllLabel?: string
    collapseAllLabel?: string
  }
}

export function FaqSection({
  title = 'FAQ',
  subtitle = 'Frequently Asked Questions',
  items = [],
  ui,
}: FaqSectionProps) {
  // Show section even if no items (admin can add items)
  const hasItems = items && items.length > 0

  return (
    <section className="w-full py-16 md:py-20 bg-white">
      <div className="max-w-[900px] mx-auto px-4 sm:px-6 lg:px-8">
        {/* Centered Header */}
        <div className="text-center mb-10">
          {subtitle && (
            <p className="text-sm uppercase tracking-wider text-gray-500 mb-3">
              {subtitle}
            </p>
          )}
          {title && (
            <h2 className="text-[2.75rem] md:text-[2.75rem] font-bold text-gray-900 leading-tight tracking-tight">
              {title}
            </h2>
          )}
        </div>

        {/* Accordion List */}
        {hasItems ? (
          <Accordion type="single" collapsible className="w-full space-y-4">
            {items.map((item) => (
            <AccordionItem
              key={item.id}
              value={item.id}
              className="border border-gray-200 rounded-lg bg-neutral-100 overflow-hidden"
            >
              <AccordionTrigger className="px-6 py-4 hover:no-underline bg-neutral-100">
                <span className="text-left font-semibold text-gray-900 pr-4">
                  {item.question}
                </span>
              </AccordionTrigger>
              <AccordionContent className="px-6 pb-4 bg-white">
                <div className="text-gray-700 leading-relaxed">
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                      strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                      em: ({ children }) => <em className="italic">{children}</em>,
                      ul: ({ children }) => <ul className="list-disc list-inside mb-4 space-y-2">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-inside mb-4 space-y-2">{children}</ol>,
                      li: ({ children }) => <li className="ml-4">{children}</li>,
                      a: ({ href, children }) => (
                        <a
                          href={href}
                          className="text-indigo-600 hover:text-indigo-800 underline"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          {children}
                        </a>
                      ),
                      h1: ({ children }) => <h1 className="text-2xl font-bold mb-3 mt-4">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-xl font-bold mb-2 mt-3">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-lg font-semibold mb-2 mt-2">{children}</h3>,
                    }}
                  >
                    {item.answerMarkdown || ''}
                  </ReactMarkdown>
                </div>
              </AccordionContent>
            </AccordionItem>
            ))}
          </Accordion>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <p>No FAQ items yet. Add questions in the admin panel.</p>
          </div>
        )}
      </div>
    </section>
  )
}

