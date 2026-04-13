'use client'

import { useState } from 'react'
import { Copy, Check } from 'lucide-react'

interface HtmlViewerProps {
  html: string
  title?: string
}

export function HtmlViewer({ html, title = 'HTML Code' }: HtmlViewerProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(html)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-lg border border-gray-200">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200">
        <h3 className="text-sm font-medium text-gray-700">{title}</h3>
        <button
          onClick={handleCopy}
          className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-4 h-4" />
              <span>Copied!</span>
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="flex-1 overflow-auto">
        <pre className="p-4 text-xs font-mono text-gray-800 whitespace-pre-wrap break-words">
          {html}
        </pre>
      </div>
    </div>
  )
}









