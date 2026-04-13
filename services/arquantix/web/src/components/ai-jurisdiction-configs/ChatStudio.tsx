'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, RotateCcw } from 'lucide-react'
import { composeJurisdictionConfig } from './api'
import { toastError, toastInfo } from '@/lib/admin/toast'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatStudioProps {
  jurisdiction: string
  purpose: 'KYC' | 'AML_RISK'
  onConfigGenerated: (spec: any, assistantText: string) => void
}

export function ChatStudio({ jurisdiction, purpose, onConfigGenerated }: ChatStudioProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [previousSpec, setPreviousSpec] = useState<any>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const formatQuestions = (questions: any[]): string => {
    if (!questions || questions.length === 0) {
      return ''
    }

    let formatted = '\n\n❓ Missing Field Slugs (must resolve):\n'
    questions.forEach((q: any) => {
      if (q && typeof q === 'object') {
        const term = q.term || q.field || 'Unknown field'
        const suggestions = q.suggestions || []
        
        formatted += `\n• "${term}"\n`
        if (suggestions.length > 0) {
          formatted += `  Suggestions: ${suggestions.join(', ')}\n`
        } else {
          formatted += `  No suggestions found. Consider adding this field to the catalog.\n`
        }
      } else {
        // Fallback: render as JSON if structure is unexpected
        formatted += `\n• ${JSON.stringify(q, null, 2)}\n`
      }
    })
    return formatted
  }

  const formatValueSuggestions = (valueSuggestions: any[]): string => {
    if (!valueSuggestions || valueSuggestions.length === 0) {
      return ''
    }

    let formatted = '\n\n💡 Suggested Values (optional):\n'
    valueSuggestions.forEach((vs: any) => {
      if (vs && typeof vs === 'object') {
        const fieldSlug = vs.field_slug || vs.field || 'Unknown field'
        const suggestedValues = vs.suggested_values || vs.values || []
        
        formatted += `\n• "${fieldSlug}"\n`
        if (suggestedValues.length > 0) {
          formatted += `  Suggested values: ${suggestedValues.join(', ')}\n`
        }
      } else {
        // Fallback: render as JSON if structure is unexpected
        formatted += `\n• ${JSON.stringify(vs, null, 2)}\n`
      }
    })
    return formatted
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) {
      if (!input.trim()) {
        toastError('Please enter a message')
      }
      return
    }

    if (!jurisdiction || jurisdiction.trim() === '') {
      toastError('Please select a jurisdiction first')
      return
    }

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      const response = await composeJurisdictionConfig({
        jurisdiction: jurisdiction.trim(),
        purpose,
        prompt: userMessage,
        previous_spec: previousSpec || undefined,
        messages: messages.map((m) => ({ role: m.role, content: m.content })),
      })

      let assistantMessage = response.assistant_text

      // Append warnings if any
      if (response.warnings && response.warnings.length > 0) {
        assistantMessage +=
          '\n\n⚠️ Warnings:\n' + response.warnings.map((w: string) => `• ${w}`).join('\n')
        toastInfo(response.warnings[0])
      }

      // Append blocking questions (missing slugs) if any
      if (response.questions && response.questions.length > 0) {
        assistantMessage += formatQuestions(response.questions)
      }

      // Append non-blocking value suggestions if any
      if (response.value_suggestions && response.value_suggestions.length > 0) {
        assistantMessage += formatValueSuggestions(response.value_suggestions)
      }

      setMessages((prev) => [...prev, { role: 'assistant', content: assistantMessage }])
      setPreviousSpec(response.spec)

      onConfigGenerated(response.spec, response.assistant_text)
    } catch (error) {
      console.error('Compose error:', error)

      let errorMessage = 'Failed to generate config'
      if (error instanceof Error) {
        errorMessage = error.message
      } else if (typeof error === 'string') {
        errorMessage = error
      } else if (error && typeof error === 'object') {
        errorMessage = (error as any).message || (error as any).error || JSON.stringify(error)
      }

      toastError(errorMessage)

      const isBackendError =
        errorMessage.toLowerCase().includes('backend') ||
        errorMessage.toLowerCase().includes('unavailable')
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: isBackendError
            ? `❌ Error: ${errorMessage}\n\nPlease ensure the FastAPI backend is running and accessible.`
            : `❌ Error: ${errorMessage}\n\nPlease try again or check the console for details.`,
        },
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleReset = () => {
    setPreviousSpec(null)
    setMessages([])
  }

  return (
    <div className="h-full flex flex-col bg-white rounded-lg border border-gray-200">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="text-sm">Start a conversation to create a {purpose} config</p>
            <p className="text-xs mt-2">
              Try: "Create a {purpose === 'KYC' ? 'basic onboarding flow' : 'risk scoring ruleset'}"
            </p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${
                msg.role === 'user'
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex gap-1">
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: '0ms' }}
                />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: '150ms' }}
                />
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: '300ms' }}
                />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Describe the ${purpose} configuration you want to create...`}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent resize-none"
              disabled={isLoading || !jurisdiction}
            />
          </div>
          <button
            onClick={handleReset}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 disabled:opacity-50 transition-colors"
            title="Reset conversation"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || !jurisdiction}
            className="flex items-center justify-center w-10 h-10 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
