'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { createSession, sendTurn, type TurnResponse } from '@/lib/chat_api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import DebugPanel from '@/components/chat/DebugPanel'
import type { DebugPayload } from '@/types/chatbot_debug'

interface Message {
  role: 'user' | 'assistant'
  content: string
  disclaimers?: string[]
}

type StepStatus = 'null' | 'in_progress' | 'success'
type DebugStep = { id: string; label: string; status: StepStatus }

const SESSION_STORAGE_KEY = 'chatbot_session_id'
const STARTED_STORAGE_KEY = 'chatbot_started'
const OPENING_TEXT =
  'Bonjour 🙂 Parle-moi librement de ton projet d’épargne. Je vais t’aider à le clarifier et à le construire pas à pas.'
const DEFAULT_STEPS: DebugStep[] = [
  { id: 'opening', label: 'Ouverture', status: 'null' },
  { id: 'goal_category', label: 'Catégorie', status: 'null' },
  { id: 'project_details', label: 'Détails projet', status: 'null' },
  { id: 'horizon', label: 'Horizon', status: 'null' },
  { id: 'effort', label: 'Effort', status: 'null' },
  { id: 'liquidity', label: 'Souplesse', status: 'null' },
  { id: 'risk', label: 'Risque', status: 'null' },
  { id: 'wrapup', label: 'Restitution', status: 'null' },
]

export default function ChatPage() {
  // Load session_id from localStorage on mount
  const [sessionId, setSessionId] = useState<string | null>(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem(SESSION_STORAGE_KEY)
    }
    return null
  })
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [completeness, setCompleteness] = useState(0)
  const [disclaimerToConfirm, setDisclaimerToConfirm] = useState<string[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [debugData, setDebugData] = useState<DebugPayload | null>(null)
  const [lastResponse, setLastResponse] = useState<TurnResponse | null>(null)
  const [started, setStarted] = useState(false)
  const [uiSteps, setUiSteps] = useState<DebugStep[]>(DEFAULT_STEPS)
  const [hasBackendSteps, setHasBackendSteps] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  const toDebugSteps = useCallback(
    (steps: DebugStep[]) =>
      steps.map((s) => ({
        ...s,
        status: s.status === 'null' ? null : s.status,
      })),
    [],
  )

  const uiDebugPayload: DebugPayload = {
    state: 'coach',
    next_question_id: undefined,
    action: undefined,
    reason: undefined,
    completeness_score: undefined,
    missing_fields: [],
    asked_questions: [],
    disclaimers_shown: [],
    profile_diff: {},
    profile: {},
    conversation_summary: undefined,
    conversation_facts: [],
    steps: toDebugSteps(uiSteps),
  }

  const buildStepsFromProfile = useCallback((profile: Record<string, unknown>, state: string | undefined) => {
    const goal = (profile.goal as Record<string, unknown> | undefined) || {}
    const goalDetails = Boolean(goal.description || goal.narrative || goal.target_amount)
    const goalConf = typeof profile.goal_confidence === 'number' ? profile.goal_confidence : null
    const projectTypeConf = typeof profile.project_type_confidence === 'number' ? profile.project_type_confidence : null
    const goalLockedLocal = Boolean(profile.goal_locked)
      || (goalConf != null && goalConf >= 0.7)
      || (projectTypeConf != null && projectTypeConf >= 0.7)
      || profile.project_type != null
    const horizonSuccess = profile.horizon_months != null
    const initialOk = profile.initial_amount != null
    const monthlyOk = profile.monthly_contribution != null
    const effortSuccess = initialOk || monthlyOk
    const liquidity = profile.liquidity_needs as Record<string, unknown> | undefined
    const liquidityValue = liquidity?.value
    const liquidityConf = typeof liquidity?.confidence === 'number' ? liquidity?.confidence : null
    const liquiditySuccess = liquidityValue != null && (liquidityConf == null || liquidityConf >= 0.7)
    const riskScore = profile.risk_tolerance_score
    const riskConf = typeof profile.risk_tolerance_score_confidence === 'number'
      ? profile.risk_tolerance_score_confidence
      : null
    const riskSuccess = riskScore != null && (riskConf == null || riskConf >= 0.7)
    const wrapupSuccess = state === 'restitution' || state === 'restitution_done' || state === 'proposal_generated'

    const openingStatus: StepStatus = started ? 'success' : 'null'
    const goalCategoryStatus: StepStatus = started ? (goalLockedLocal ? 'success' : 'in_progress') : 'null'
    const projectDetailsStatus: StepStatus = goalDetails ? 'success' : goalCategoryStatus === 'success' ? 'in_progress' : 'null'
    const horizonStatus: StepStatus = horizonSuccess ? 'success' : goalCategoryStatus === 'success' ? 'in_progress' : 'null'
    const effortStatus: StepStatus = effortSuccess ? 'success' : horizonStatus === 'success' ? 'in_progress' : 'null'
    const liquidityStatus: StepStatus = liquiditySuccess ? 'success' : effortStatus === 'success' ? 'in_progress' : 'null'
    const riskStatus: StepStatus = riskSuccess ? 'success' : liquidityStatus === 'success' ? 'in_progress' : 'null'
    const wrapupStatus: StepStatus = wrapupSuccess ? 'success' : riskStatus === 'success' ? 'in_progress' : 'null'

    return [
      { id: 'opening', label: 'Ouverture', status: openingStatus },
      { id: 'goal_category', label: 'Catégorie', status: goalCategoryStatus },
      { id: 'project_details', label: 'Détails projet', status: projectDetailsStatus },
      { id: 'horizon', label: 'Horizon', status: horizonStatus },
      { id: 'effort', label: 'Effort', status: effortStatus },
      { id: 'liquidity', label: 'Souplesse', status: liquidityStatus },
      { id: 'risk', label: 'Risque', status: riskStatus },
      { id: 'wrapup', label: 'Restitution', status: wrapupStatus },
    ]
  }, [started])

  const buildDebugFallback = useCallback((res: TurnResponse): DebugPayload => {
    return {
      state: res.state,
      next_question_id: undefined,
      action: undefined,
      reason: undefined,
      completeness_score: res.completeness_score,
      missing_fields: [],
      asked_questions: [],
      disclaimers_shown: res.disclaimers_shown || [],
      profile_diff: res.profile_diff || {},
      profile: res.profile || {},
      conversation_summary: res.conversation_summary,
      conversation_facts: res.conversation_facts || [],
    }
  }, [])

  const handleReset = useCallback(async () => {
    if (loading) return
    setLoading(true)
    setError(null)
    setMessages([])
    setLastResponse(null)
    setCompleteness(0)
    setDisclaimerToConfirm(null)
    setDebugData(null)
    setStarted(false)
    setUiSteps(DEFAULT_STEPS)
    setHasBackendSteps(false)
    localStorage.removeItem(STARTED_STORAGE_KEY)
    localStorage.removeItem(SESSION_STORAGE_KEY)
    setSessionId(null)
    try {
      const result = await createSession()
      const session_id = result.session_id
      localStorage.setItem(SESSION_STORAGE_KEY, session_id)
      setSessionId(session_id)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [buildDebugFallback, loading])

  const handleStart = useCallback(async () => {
    if (loading || started) return
    setLoading(true)
    setError(null)
    try {
      let session_id = sessionId
      if (!session_id) {
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
        session_id = storedSessionId
      }
      if (!session_id) {
        const result = await createSession()
        session_id = result.session_id
        localStorage.setItem(SESSION_STORAGE_KEY, session_id)
      }
      setSessionId(session_id)
      setMessages((m) => (m.length ? m : [{ role: 'assistant', content: OPENING_TEXT }]))
      setStarted(true)
      setUiSteps((prev) =>
        prev.map((s) =>
          s.id === 'opening' ? { ...s, status: 'in_progress' } : { ...s, status: 'null' },
        ),
      )
      localStorage.setItem(STARTED_STORAGE_KEY, 'true')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [loading, sessionId, started])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleTurn = useCallback(async (text: string) => {
    if (!started || !sessionId || !text.trim() || loading) return
    const userMsg = text.trim()
    if (!hasBackendSteps) {
      setUiSteps((prev) =>
        prev.map((s) => {
          if (s.id === 'opening') return { ...s, status: 'success' }
          if (s.id === 'goal_category') return { ...s, status: 'in_progress' }
          return s
        }),
      )
    }
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: userMsg }])
    setLoading(true)
    setError(null)
    try {
      const res: TurnResponse = await sendTurn(sessionId, userMsg)
      setHasBackendSteps(Array.isArray(res.debug?.steps))
      setMessages((m) => [...m, { role: 'assistant', content: res.reply, disclaimers: res.disclaimers_shown }])
      setLastResponse(res)
      if (res.completeness_score != null) setCompleteness(Math.round(res.completeness_score * 100))
      if (res.disclaimers_shown?.length) setDisclaimerToConfirm(res.disclaimers_shown)
      setDebugData(res.debug ?? buildDebugFallback(res))
      if (!res.debug?.steps && res.profile) {
        const mergedProfile = {
          ...res.profile,
          goal_locked: res.goal_locked ?? (res.profile as Record<string, unknown>).goal_locked,
          goal_confidence: res.goal_confidence ?? (res.profile as Record<string, unknown>).goal_confidence,
        }
        setUiSteps(buildStepsFromProfile(mergedProfile, res.state))
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [sessionId, loading, buildDebugFallback, started, hasBackendSteps])

  useEffect(() => {
    let cancelled = false
    setError(null)
    const run = async () => {
      try {
        const storedSessionId = localStorage.getItem(SESSION_STORAGE_KEY)
        const storedStarted = localStorage.getItem(STARTED_STORAGE_KEY) === 'true'
        let session_id = storedSessionId
        if (cancelled) return
        setSessionId(session_id)
        if (storedStarted) {
          setStarted(true)
          if (messages.length === 0) {
            setMessages([{ role: 'assistant', content: OPENING_TEXT }])
          }
          setUiSteps((prev) =>
            prev.map((s) =>
              s.id === 'opening' ? { ...s, status: 'in_progress' } : { ...s, status: 'null' },
            ),
          )
        }
      } catch (e: unknown) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Erreur')
          localStorage.removeItem(SESSION_STORAGE_KEY)
          localStorage.removeItem(STARTED_STORAGE_KEY)
        }
      }
    }
    run()
    return () => { cancelled = true }
  }, [])

  const onDisclaimerOk = () => setDisclaimerToConfirm(null)

  const progressPct = Math.min(100, Math.max(0, completeness))
  const timeToWowHint = completeness >= 40 ? 'Vous avez une première idée.' : 'Encore 2–3 réponses pour une première idée.'
  const goalLocked = Boolean(debugData?.goal_locked ?? lastResponse?.goal_locked
    ?? (debugData?.profile as Record<string, unknown> | undefined)?.goal_locked
    ?? (lastResponse?.profile as Record<string, unknown> | undefined)?.goal_locked)
  const goalPhase = debugData?.goal_phase ?? lastResponse?.goal_phase ?? null
  const showGoalChips = started && !goalLocked && (goalPhase === 'goal_clarify' || goalPhase === 'goal_force_pick')
  const isForcePick = goalPhase === 'goal_force_pick'
  const goalPickChips = [
    { label: 'Acheter quelque chose', display: '🏡 Acheter quelque chose' },
    { label: 'Mieux vivre au quotidien', display: '✨ Mieux vivre au quotidien' },
    { label: 'Préparer mon avenir', display: '🛡️ Préparer mon avenir' },
    { label: 'Protéger mes proches', display: '👨‍👩‍👧‍👦 Protéger mes proches' },
    { label: 'Vivre des expériences', display: '🌍 Vivre des expériences' },
    { label: 'Faire fructifier mon argent', display: '📈 Faire fructifier mon argent' },
  ]

  const profileFallbackSteps =
    debugData?.profile ? buildStepsFromProfile(debugData.profile as Record<string, unknown>, debugData.state) : null
  const effectiveDebug: DebugPayload | null = debugData
    ? ({
        ...debugData,
        steps:
          debugData.steps ??
          (!hasBackendSteps ? toDebugSteps((profileFallbackSteps ?? uiSteps) as DebugStep[]) : undefined),
      } as DebugPayload)
    : !hasBackendSteps
      ? uiDebugPayload
      : null

  return (
    <main className="min-h-screen bg-slate-50">
      <div className="container mx-auto px-4 py-6 max-w-6xl">
        <div className="flex flex-col md:flex-row gap-6">
          <div className="w-full md:w-[60%]">
            <div className="flex items-center justify-between mb-2">
              <h1 className="text-2xl font-bold text-slate-900">Projet d&apos;épargne</h1>
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={handleStart} disabled={loading || started}>
                  Start
                </Button>
                <Button variant="outline" size="sm" onClick={handleReset} disabled={loading}>
                  Reset
                </Button>
              </div>
            </div>
            <p className="text-slate-600 text-sm mb-4">{timeToWowHint}</p>

            <Progress value={progressPct} className="h-2 mb-4" />

            <div className="relative flex flex-col">
              <Card className="mb-4">
                <CardHeader className="py-3">
                  <CardTitle className="text-base">Échange</CardTitle>
                </CardHeader>
                <CardContent className="relative space-y-3 min-h-[240px] max-h-[360px] overflow-y-auto">
                  {messages.length === 0 && !loading && !started && (
                    <p className="text-slate-500 text-sm">Clique Start pour commencer.</p>
                  )}
                  {messages.map((m, i) => (
                    <div
                      key={i}
                      className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                          m.role === 'user'
                            ? 'bg-slate-900 text-white'
                            : 'bg-white border border-slate-200 text-slate-800'
                        }`}
                      >
                        {m.content}
                      </div>
                    </div>
                  ))}
                  {loading && (
                    <div className="flex justify-start">
                      <div className="rounded-lg px-3 py-2 text-sm bg-white border border-slate-200 inline-flex gap-1 items-center">
                        <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.2s]" />
                        <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce [animation-delay:-0.1s]" />
                        <span className="w-2 h-2 rounded-full bg-slate-400 animate-bounce" />
                      </div>
                    </div>
                  )}
                  <div ref={bottomRef} />
                </CardContent>
              </Card>

            {disclaimerToConfirm && disclaimerToConfirm.length > 0 && (
              <Card className="mb-4 border-amber-200 bg-amber-50">
                <CardContent className="py-3">
                  <p className="text-amber-900 text-sm mb-2">
                    Ceci est une illustration pédagogique, pas un conseil. Les performances passées ne préjugent pas des futures.
                  </p>
                  <Button size="sm" onClick={onDisclaimerOk} className="bg-amber-700 hover:bg-amber-800">
                    J&apos;ai compris
                  </Button>
                </CardContent>
              </Card>
            )}

            {error && (
              <p className="text-red-600 text-sm mb-4">{error}</p>
            )}

            {isForcePick && (
              <p className="text-slate-600 text-sm mb-3">
                Choisis une catégorie pour continuer.
              </p>
            )}

            {showGoalChips && (
              <div className="flex flex-wrap gap-2 mb-3">
                {goalPickChips.map((chip) => (
                  <Button
                    key={chip.label}
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleTurn(chip.label)}
                    disabled={!sessionId || loading}
                  >
                    {chip.display}
                  </Button>
                ))}
              </div>
            )}

            <div className="relative">
              {isForcePick && (
                <div className="absolute -top-5 left-0 text-xs text-slate-600 bg-slate-100 border border-slate-200 rounded-full px-2 py-0.5">
                  Sélection requise
                </div>
              )}
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  handleTurn(input)
                }}
                className="flex gap-2"
              >
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    !started
                      ? 'Clique Start pour commencer'
                      : isForcePick
                        ? 'Choisis une catégorie ci-dessous'
                        : 'Votre message…'
                  }
                  disabled={!sessionId || loading || isForcePick || !started}
                  className="flex-1"
                />
                <Button type="submit" disabled={!sessionId || loading || !input.trim() || isForcePick || !started}>
                  Envoyer
                </Button>
              </form>
            </div>
            </div>
          </div>

          <div className="hidden md:block md:w-[40%]">
            <div className="h-[calc(100vh-6rem)]">
              <DebugPanel debug={effectiveDebug} lastResponse={lastResponse} />
            </div>
          </div>
        </div>
      </div>
    </main>
  )
}
