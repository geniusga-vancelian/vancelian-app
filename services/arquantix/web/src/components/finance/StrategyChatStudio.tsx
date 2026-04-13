'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Loader2, Send } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface UIState {
  type: 'quick_replies' | 'free_text' | 'slider' | 'allocation_picker' | 'single_choice_strict'
  quick_replies?: string[]
  allow_free_text?: boolean
  slider?: {
    min: number
    max: number
    step: number
  }
  allocation_picker?: {
    min: number
    max: number
    step: number
    max_total?: number
    cards?: Array<{ id: string; title: string; description?: string }>
  }
}

interface ProgressState {
  phase: number
  total_phases: number
}

interface StartResponse {
  session_id: string
  messages: Message[]
  ui: UIState
  progress: ProgressState
  state: Record<string, any>
}

interface StepResponse {
  session_id: string
  messages: Message[]
  ui: UIState
  progress: ProgressState
  state: Record<string, any>
}

interface StateResponse {
  session_id: string
  phase: number
  state: Record<string, any>
}

const SESSION_KEY = 'finance_strategy_chat_session'
const MESSAGES_KEY = 'finance_strategy_chat_messages'

export function StrategyChatStudio() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [ui, setUi] = useState<UIState>({ type: 'free_text' })
  const [progress, setProgress] = useState<ProgressState>({ phase: 0, total_phases: 7 })
  const [stateData, setStateData] = useState<Record<string, any>>({})
  const [error, setError] = useState<string | null>(null)
  const [sliderValue, setSliderValue] = useState(50)
  const [allocationValue, setAllocationValue] = useState(60)
  const [selectedCardId, setSelectedCardId] = useState<string | null>(null)
  const [allocations, setAllocations] = useState<Record<string, number>>({})
  const [showDebug, setShowDebug] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const textEnabled = true

  const profile = stateData?.profile ?? {}
  const confidenceMap = profile?.confidence ?? {}
  const getConfidence = (key: string) => {
    const val = confidenceMap?.[key]
    return typeof val === 'number' ? val : null
  }
  const formatCurrency = (value: any, currency?: string) => {
    if (typeof value === 'number' && Number.isFinite(value)) {
      const unit = currency || '€'
      return `${new Intl.NumberFormat('fr-FR').format(value)} ${unit}`
    }
    if (typeof value === 'string' && value.trim().length > 0) {
      return value
    }
    return '—'
  }
  const formatConfidence = (value: any) => {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return ` (confiance: ${value.toFixed(2)})`
    }
    return ''
  }

  const progressValue = useMemo(() => {
    if (!progress.total_phases || progress.total_phases <= 0) return 0
    return Math.round((progress.phase / progress.total_phases) * 100)
  }, [progress])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const storedSession = sessionStorage.getItem(SESSION_KEY)
    const storedMessages = sessionStorage.getItem(MESSAGES_KEY)

    if (storedSession) {
      setSessionId(storedSession)
      if (storedMessages) {
        try {
          setMessages(JSON.parse(storedMessages))
        } catch {}
      }
      loadState(storedSession)
    } else {
      startSession()
    }
  }, [])

  useEffect(() => {
    sessionStorage.setItem(MESSAGES_KEY, JSON.stringify(messages))
  }, [messages])

  const startSession = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch('/api/finance/strategy-chat/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ locale: 'fr' }),
      })
      const data: StartResponse = await response.json()
      if (!response.ok) {
        throw new Error((data as any)?.error || 'Erreur au démarrage')
      }
      setSessionId(data.session_id)
      sessionStorage.setItem(SESSION_KEY, data.session_id)
      setMessages(data.messages || [])
      setUi(data.ui)
      setProgress(data.progress)
      setStateData(data.state || {})
      setAllocations({})
      setSelectedCardId(null)
    } catch (err: any) {
      setError(err.message || 'Erreur au démarrage du chat')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = async () => {
    if (loading) return
    if (!confirm('Recommencer la conversation ?')) return
    sessionStorage.removeItem(SESSION_KEY)
    sessionStorage.removeItem(MESSAGES_KEY)
    setSessionId(null)
    setMessages([])
    setStateData({})
    setUi({ type: 'quick_replies' })
    setProgress({ phase: 0, total_phases: 7 })
    setError(null)
    await startSession()
  }

  const loadState = async (sid: string) => {
    try {
      const response = await fetch(`/api/finance/strategy-chat/state?session_id=${encodeURIComponent(sid)}`)
      const data: StateResponse = await response.json()
      if (!response.ok) {
        if (response.status === 404) {
          sessionStorage.removeItem(SESSION_KEY)
          sessionStorage.removeItem(MESSAGES_KEY)
          setSessionId(null)
          setMessages([])
          setStateData({})
          await startSession()
          return
        }
        if (response.status === 401) {
          throw new Error((data as any)?.error || 'Unauthorized')
        }
        throw new Error((data as any)?.error || 'Erreur state')
      }
      setProgress({ phase: data.phase, total_phases: 7 })
      setStateData(data.state || {})
    } catch (err: any) {
      setError(err.message || 'Erreur lors du chargement de l’état')
    }
  }

  const appendAssistantMessages = (assistantMessages: Message[]) => {
    if (!assistantMessages || assistantMessages.length === 0) return
    setMessages((prev) => {
      const last = prev[prev.length - 1]
      const firstNew = assistantMessages[0]
      if (last?.role === 'assistant' && firstNew?.role === 'assistant' && last.content === firstNew.content) {
        return [...prev, ...assistantMessages.slice(1)]
      }
      return [...prev, ...assistantMessages]
    })
  }

  const formatUserMessage = (type: string, value: any): string => {
    if (type === 'allocation') {
      const percent = value?.percent ?? allocationValue
      const label = value?.project_id ? `Projet ${value.project_id}` : 'Projet'
      return `${label} — Allocation ${percent}%`
    }
    if (type === 'number') {
      return `Valeur sélectionnée: ${value}`
    }
    return String(value ?? '')
  }

  const sendUserInput = async (type: 'single_choice' | 'free_text' | 'number' | 'allocation', value: any) => {
    if (!sessionId) return
    if (loading) return
    const display = formatUserMessage(type, value)
    if (!display.trim()) return

    setLoading(true)
    setError(null)
    if (type === 'free_text') {
      setInput('')
    }
    setMessages((prev) => [...prev, { role: 'user', content: display }, { role: 'assistant', content: '__typing__' }])

    try {
      const response = await fetch('/api/finance/strategy-chat/step', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          user_input: { type, value },
        }),
      })
      const data: StepResponse = await response.json()
      if (!response.ok) {
        if (response.status === 404) {
          sessionStorage.removeItem(SESSION_KEY)
          sessionStorage.removeItem(MESSAGES_KEY)
          setSessionId(null)
          setMessages([])
          setStateData({})
          await startSession()
          return
        }
        throw new Error((data as any)?.error || 'Erreur étape')
      }
      setMessages((prev) => prev.filter((m) => m.content !== '__typing__'))
      appendAssistantMessages(data.messages || [])
      setUi(data.ui)
      setProgress(data.progress)
      setStateData(data.state || {})
    } catch (err: any) {
      setMessages((prev) => prev.filter((m) => m.content !== '__typing__'))
      setError(err.message || 'Erreur lors de l’envoi')
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const renderInput = () => (
    <div className="flex gap-2">
      <Input
        ref={inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ta réponse…"
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            sendUserInput('free_text', input.trim())
          }
        }}
        disabled={loading}
      />
      <Button
        onClick={() => sendUserInput('free_text', input.trim())}
        disabled={loading || !input.trim()}
      >
        <Send className="w-4 h-4" />
      </Button>
    </div>
  )

  const renderUi = () => {
    if (ui.type === 'quick_replies') {
      const options = ui.quick_replies || []
      return (
        <div className="space-y-3">
          {options.length > 0 && (
            <div className="text-xs uppercase tracking-wide text-gray-500">Suggestions</div>
          )}
          <div className="flex flex-wrap gap-2">
            {options.map((opt) => (
              <Button
                key={opt}
                variant="outline"
                size="sm"
                onClick={() => sendUserInput('single_choice', opt)}
                disabled={loading}
              >
                {opt}
              </Button>
            ))}
          </div>
          {renderInput()}
        </div>
      )
    }

    if (ui.type === 'slider') {
      const min = ui.slider?.min ?? 0
      const max = ui.slider?.max ?? 100
      const step = ui.slider?.step ?? 10
      const sliderLabel =
        sliderValue <= 30
          ? 'Plutôt prudent'
          : sliderValue <= 60
            ? 'Équilibré'
            : 'À l’aise avec les variations'
      return (
        <Card>
          <CardHeader>
            <CardTitle>Ton niveau de confort face aux variations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <input
              type="range"
              min={min}
              max={max}
              step={step}
              value={sliderValue}
              onChange={(e) => setSliderValue(Number(e.target.value))}
              className="w-full"
            />
            <div className="text-sm text-gray-600 flex items-center gap-2">
              <span>Valeur: {sliderValue}</span>
              <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700 text-xs">
                {sliderLabel}
              </span>
            </div>
            <Button variant="outline" onClick={() => sendUserInput('number', sliderValue)}>
              Valider mon niveau de confort
            </Button>
          </CardContent>
        </Card>
      )
    }

    if (ui.type === 'allocation_picker') {
      const cards = ui.allocation_picker?.cards || []
      const min = ui.allocation_picker?.min ?? 0
      const max = ui.allocation_picker?.max ?? 100
      const step = ui.allocation_picker?.step ?? 5
      const maxTotal = ui.allocation_picker?.max_total ?? 100
      const totalAllocated = Object.values(allocations).reduce((acc, v) => acc + v, 0)
      const canApply = selectedCardId && totalAllocated - (allocations[selectedCardId] || 0) + allocationValue <= maxTotal
      return (
        <Card>
          <CardHeader>
            <CardTitle>Allocation Core / Satellite</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {cards.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {cards.map((c) => (
                  <div
                    key={c.id}
                    className={`border rounded-lg p-3 cursor-pointer ${
                      selectedCardId === c.id ? 'border-indigo-500 bg-indigo-50' : 'border-gray-200'
                    }`}
                    onClick={() => setSelectedCardId(c.id)}
                  >
                    <div className="font-medium text-sm">{c.title}</div>
                    {c.description && <div className="text-xs text-gray-600">{c.description}</div>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-gray-500">Aucun projet proposé.</div>
            )}

            <div>
              <input
                type="range"
                min={min}
                max={max}
                step={step}
                value={allocationValue}
                onChange={(e) => setAllocationValue(Number(e.target.value))}
                className="w-full"
              />
              <div className="text-sm text-gray-600">
                Total alloué: {totalAllocated}% / max {maxTotal}%
              </div>
            </div>

            <Button
              variant="outline"
              disabled={!selectedCardId || !canApply}
              onClick={() => {
                if (!selectedCardId) return
                const nextAllocations = {
                  ...allocations,
                  [selectedCardId]: allocationValue,
                }
                setAllocations(nextAllocations)
                sendUserInput('allocation', {
                  project_id: selectedCardId,
                  percent: allocationValue,
                })
              }}
            >
              Appliquer
            </Button>
            {!canApply && (
              <div className="text-xs text-red-600">
                L’allocation dépasse le maximum autorisé.
              </div>
            )}
          </CardContent>
        </Card>
      )
    }

    return (
      renderInput()
    )
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
      <div className="xl:col-span-8 space-y-6">
        <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Project Strategy Chat Builder</CardTitle>
            <Button variant="outline" size="sm" onClick={handleClear} disabled={loading}>
              Recommencer
            </Button>
          </div>
        </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
              <span>Progression</span>
              <span>{progressValue}%</span>
            </div>
            <Progress value={progressValue} />
          </CardContent>
        </Card>

        {progress.phase >= 7 && (
          <Alert>
            <AlertTitle>✅ 100% complété</AlertTitle>
            <AlertDescription>Le parcours est terminé. Tu peux consulter le récapitulatif.</AlertDescription>
          </Alert>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertTitle>Erreur</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Ce que tu as déjà validé</CardTitle>
          </CardHeader>
          <CardContent>
            <details className="rounded-md border border-gray-200 p-3">
              <summary className="cursor-pointer text-sm font-medium text-gray-700">
                Voir le récapitulatif
              </summary>
              <div className="mt-3 space-y-2 text-sm text-gray-700">
                <div>
                  <strong>Projet :</strong> {String(profile.project_summary ?? '—')}
                  <span className="text-xs text-gray-500">
                    {formatConfidence(getConfidence('project_summary'))}
                  </span>
                </div>
                <div>
                  <strong>Type :</strong> {String(profile.goal?.type ?? '—')}
                  <span className="text-xs text-gray-500">
                    {formatConfidence(getConfidence('goal.type'))}
                  </span>
                </div>
                <div>
                  <strong>Objectif total :</strong>{' '}
                  {formatCurrency(profile.goal?.target_amount, profile.contribution_currency)}
                  <span className="text-xs text-gray-500">
                    {formatConfidence(getConfidence('goal.target_amount'))}
                  </span>
                </div>
                <div>
                  <strong>Horizon :</strong> {String(profile.timeline?.horizon_months ?? '—')} mois
                  <span className="text-xs text-gray-500">
                    {formatConfidence(getConfidence('timeline.horizon_months'))}
                  </span>
                </div>
                <div>
                  <strong>Mensuel :</strong>{' '}
                  {formatCurrency(profile.capacity?.monthly_contribution, profile.contribution_currency)}
                  <span className="text-xs text-gray-500">
                    {formatConfidence(getConfidence('capacity.monthly_contribution'))}
                  </span>
                </div>
                <div>
                  <strong>Risque :</strong> {String(profile.risk?.tolerance_score ?? '—')}
                  <span className="text-xs text-gray-500">
                    {formatConfidence(getConfidence('risk.tolerance_score'))}
                  </span>
                </div>
                <div>
                  <strong>Connaissance :</strong> {String(profile.knowledge_level ?? '—')}
                  <span className="text-xs text-gray-500">
                    {formatConfidence(getConfidence('knowledge_level'))}
                  </span>
                </div>
              </div>
            </details>
          </CardContent>
        </Card>

        {/* Messages */}
        <Card className="min-h-[380px]">
          <CardContent className="py-4 space-y-3 max-h-[480px] overflow-y-auto">
            {messages.map((m, idx) => (
              <div
                key={`${m.role}-${idx}`}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`px-3 py-2 rounded-lg text-sm max-w-[80%] ${
                    m.role === 'user'
                      ? 'bg-indigo-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                {m.role === 'assistant' && m.content === '__typing__' ? (
                  <span className="inline-flex gap-1 items-center">
                    <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce [animation-delay:-0.2s]" />
                    <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce [animation-delay:-0.1s]" />
                    <span className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" />
                  </span>
                ) : m.role === 'assistant' ? (
                  <div className="prose prose-sm max-w-none space-y-2 prose-headings:font-semibold prose-headings:text-base prose-strong:text-gray-900 prose-li:my-1">
                    <ReactMarkdown
                      skipHtml
                      components={{
                        p: ({ children }) => <p className="whitespace-pre-line">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
                        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                        h1: ({ children }) => <h1 className="text-base font-semibold">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-base font-semibold">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-sm font-semibold">{children}</h3>,
                        strong: ({ children }) => <strong className="font-semibold text-gray-900">{children}</strong>,
                      }}
                    >
                      {m.content}
                    </ReactMarkdown>
                  </div>
                ) : (
                  m.content
                )}
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </CardContent>
        </Card>

        {renderUi()}
      </div>

      <div className="xl:col-span-4 space-y-6">
        <Card>
          <CardHeader className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <CardTitle>🧠 Strategy state (live)</CardTitle>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowDebug((prev) => !prev)}
                >
                  {showDebug ? 'Masquer' : 'Afficher'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    try {
                      await navigator.clipboard.writeText(JSON.stringify(stateData, null, 2))
                    } catch {}
                  }}
                >
                  Copier
                </Button>
              </div>
            </div>
            <div className="text-xs text-gray-600">
              <span className="mr-3">
                Goal: {profile.goal?.type || '—'}
              </span>
              <span className="mr-3">
                Horizon: {profile.timeline?.horizon_months ?? '—'} ({getConfidence('timeline.horizon_months') ?? '—'})
              </span>
              <span>
                Mensuel: {profile.capacity?.monthly_contribution ?? '—'} ({getConfidence('capacity.monthly_contribution') ?? '—'})
              </span>
            </div>
          </CardHeader>
          <CardContent>
            {showDebug ? (
              <pre className="text-xs whitespace-pre-wrap break-words font-mono max-h-[70vh] overflow-auto rounded-md border p-3 bg-gray-50">
                {Object.keys(stateData || {}).length === 0
                  ? 'Aucun état chargé'
                  : JSON.stringify(
                      {
                        profile: stateData.profile,
                        confidence: stateData.profile?.confidence,
                        compliance: stateData.compliance,
                        last_question: stateData.last_question,
                        debug: stateData.debug,
                        debug_last_selector: stateData.debug_last_selector,
                        debug_next_step_id: stateData.debug_next_step_id,
                        debug_next_reason: stateData.debug_next_reason,
                        debug_project_type: stateData.debug_project_type,
                      },
                      null,
                      2
                    )}
              </pre>
            ) : (
              <div className="text-sm text-gray-500">Aucun JSON affiché.</div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
