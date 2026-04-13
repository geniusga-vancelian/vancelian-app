'use client'

import { useMemo, useState } from 'react'
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import type { DebugPayload } from '@/types/chatbot_debug'
import type { TurnResponse } from '@/lib/chat_api'

type DebugPanelProps = {
  debug: DebugPayload | null
  lastResponse: TurnResponse | null
}

export default function DebugPanel({ debug, lastResponse }: DebugPanelProps) {
  const [copied, setCopied] = useState(false)
  const effectiveSummary = debug?.conversation_summary ?? lastResponse?.conversation_summary
  const effectiveFacts = debug?.conversation_facts ?? lastResponse?.conversation_facts
  const effectiveProfile = (debug?.profile ?? lastResponse?.profile ?? {}) as Record<string, unknown>
  const steps = debug?.steps ?? []
  const stepEmoji = (status: 'success' | 'in_progress' | null) => {
    if (status === 'success') return '✅'
    if (status === 'in_progress') return '⏳'
    return '○'
  }

  const normalizeValue = (value: unknown) => {
    if (value === undefined || value === null) return null
    if (typeof value === 'string' && value.trim() === '') return null
    if (Array.isArray(value)) return value.length ? JSON.stringify(value) : null
    if (typeof value === 'object') return Object.keys(value as object).length ? JSON.stringify(value) : null
    return String(value)
  }

  const getPath = (obj: Record<string, unknown>, path: string) => {
    return path.split('.').reduce<unknown>((acc, key) => {
      if (acc && typeof acc === 'object' && key in (acc as Record<string, unknown>)) {
        return (acc as Record<string, unknown>)[key]
      }
      return undefined
    }, obj)
  }

  const factsFields = [
    'goal.type',
    'goal.description',
    'goal.narrative',
    'goal.target_amount',
    'goal.target_date',
    'goal.priority',
    'horizon_months',
    'horizon_bucket',
    'target_amount',
    'initial_amount',
    'monthly_contribution',
    'contribution_frequency',
    'income_monthly',
    'income_bucket',
    'expenses_monthly',
    'emergency_fund',
    'knowledge_level',
    'experience_assets',
    'risk_tolerance_score',
    'max_drawdown_accept',
    'loss_capacity',
    'liquidity_needs.value',
    'liquidity_needs.confidence',
    'constraints',
    'preferences',
    'regulatory_flags.pep',
    'regulatory_flags.sanctions',
    'regulatory_flags.jurisdiction',
    'completeness_score',
    'missing_fields',
    'confidence',
    'asked_questions',
  ]

  const profileFacts = factsFields
    .map((field) => {
      const value = normalizeValue(getPath(effectiveProfile, field))
      return value === null ? null : `${field}: ${value}`
    })
    .filter((item): item is string => Boolean(item))

  const completenessPct = useMemo(() => {
    if (!debug || debug.completeness_score == null) return null
    return Math.round(debug.completeness_score * 100)
  }, [debug?.completeness_score])

  const scoreTone =
    completenessPct == null ? 'text-slate-300' : completenessPct >= 70 ? 'text-emerald-300' : completenessPct >= 40 ? 'text-amber-300' : 'text-rose-300'

  const handleCopy = async () => {
    try {
      const payload = debug ?? lastResponse
      if (!payload) return
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
      setCopied(true)
      setTimeout(() => setCopied(false), 1200)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="h-full rounded-lg border border-slate-800 bg-slate-950 text-slate-100 shadow-sm flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
        <div>
          <p className="text-sm font-semibold text-slate-100">Debug JSON</p>
          <p className="text-xs text-slate-400">Live</p>
        </div>
        <Button variant="secondary" size="sm" onClick={handleCopy}>
          {copied ? 'Copié' : 'Copy JSON'}
        </Button>
      </div>
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {!debug && !lastResponse ? (
          <div className="text-sm text-slate-400">
            En attente d&apos;une réponse backend pour afficher le JSON.
          </div>
        ) : (
        <div className="space-y-4">
          <div>
            <div className="text-xs uppercase text-slate-400 mb-2">Étapes</div>
            {steps.length ? (
              <ul className="space-y-1 text-sm text-slate-200">
                {steps.map((step) => (
                  <li key={step.id}>
                    {stepEmoji(step.status)} {step.label}
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-sm text-slate-400">En attente des étapes debug.</div>
            )}
          </div>
          <Accordion type="multiple" className="w-full space-y-2">
          <AccordionItem value="last-response">
            <AccordionTrigger>Last Response (raw)</AccordionTrigger>
            <AccordionContent>
              <pre className="text-xs font-mono bg-slate-900/70 border border-slate-800 p-3 rounded-lg overflow-auto max-h-96 text-slate-100">
                {JSON.stringify(lastResponse, null, 2)}
              </pre>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="summary">
            <AccordionTrigger>Conversation Summary</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm">
                <div>
                  <div className="text-xs uppercase text-slate-400">Summary</div>
                  <p className="mt-1 text-slate-100">{effectiveSummary || 'N/A'}</p>
                </div>
                <div>
                  <div className="text-xs uppercase text-slate-400">Facts</div>
                  {profileFacts.length > 0 ? (
                    <ul className="mt-1 space-y-1 text-slate-200">
                      {profileFacts.map((fact, index) => (
                        <li key={index}>• {fact}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-1 text-slate-400">Aucun</p>
                  )}
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="decision">
            <AccordionTrigger>Decision</AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3 text-sm font-mono">
                <div>
                  <span className="text-slate-400">state:</span>{' '}
                  <span className="text-slate-100">{debug?.state || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400">next_question_id:</span>{' '}
                  <span className="text-amber-300">{debug?.next_question_id || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400">action:</span>{' '}
                  <span className="text-slate-100">{debug?.action || 'N/A'}</span>
                </div>
                <div>
                  <span className="text-slate-400">reason:</span>{' '}
                  <span className="text-slate-100">{debug?.reason || 'N/A'}</span>
                </div>
                <div className="pt-2">
                  <div className="flex items-center justify-between text-xs text-slate-400">
                    <span>completeness_score</span>
                    <span className={scoreTone}>{completenessPct == null ? 'N/A' : `${completenessPct}%`}</span>
                  </div>
                  <Progress value={completenessPct ?? 0} className="mt-2 h-2" />
                </div>
              </div>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="missing">
            <AccordionTrigger>Missing Fields</AccordionTrigger>
            <AccordionContent>
              {debug?.missing_fields?.length ? (
                <ul className="text-sm text-rose-200 space-y-1">
                  {debug.missing_fields.map((field, index) => (
                    <li key={index}>• {field}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-emerald-300">Aucun champ manquant</p>
              )}
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="asked">
            <AccordionTrigger>Asked Questions</AccordionTrigger>
            <AccordionContent>
              {debug?.asked_questions?.length ? (
                <ul className="text-sm text-slate-200 space-y-1">
                  {debug.asked_questions.map((question, index) => (
                    <li key={index}>• {question}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">Aucune question</p>
              )}
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="profile">
            <AccordionTrigger>Profile</AccordionTrigger>
            <AccordionContent>
              <pre className="text-xs font-mono bg-slate-900/70 border border-slate-800 p-3 rounded-lg overflow-auto max-h-96 text-slate-100">
                {JSON.stringify(debug?.profile ?? {}, null, 2)}
              </pre>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="profile-diff">
            <AccordionTrigger>Profile Diff</AccordionTrigger>
            <AccordionContent>
              <pre className="text-xs font-mono bg-slate-900/70 border border-slate-800 p-3 rounded-lg overflow-auto max-h-96 text-slate-100">
                {JSON.stringify(debug?.profile_diff ?? {}, null, 2)}
              </pre>
            </AccordionContent>
          </AccordionItem>

          <AccordionItem value="disclaimers">
            <AccordionTrigger>Disclaimers</AccordionTrigger>
            <AccordionContent>
              {debug?.disclaimers_shown?.length ? (
                <ul className="text-sm text-slate-200 space-y-1">
                  {debug.disclaimers_shown.map((item, index) => (
                    <li key={index}>• {item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-slate-400">Aucun disclaimer</p>
              )}
            </AccordionContent>
          </AccordionItem>
        </Accordion>
        </div>
        )}
      </div>
    </div>
  )
}
