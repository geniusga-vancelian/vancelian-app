/**
 * Diagramme vertical de synthèse cognitive d'un tour conversationnel —
 * Cognitive Bot v4 (Lots 1-7 V1.1) — vue admin "comment le bot a réfléchi".
 *
 * Lecture top-down :
 *   1. INPUT          — la question du user (turn user).
 *   2. CONTEXTE       — summary, recent_turns, signal de message laconique.
 *   3. ANALYSE COG.   — emotional_intent / matched / stage / trust / knowledge
 *                       + intent_classification (primary_tag, family, tags).
 *   4. OBJECTIF       — primary_goal / next_best_action / stop_pushing.
 *   5. ROUTER         — decision_kind / agent ciblé / confidence.
 *   6. CHAÎNE         — séquence d'agents (router → primary → consults).
 *
 * Source de vérité : `assistance_agent_decisions.arguments_json` du
 * `tool_name="router_classify"` (cf. `service._persist_router_decision`).
 *
 * IMPORTANT — Matching `message_id` :
 *   Côté API, `_persist_router_decision` est appelé AVANT que le message
 *   assistant ne soit créé (le router décide qui répond). En conséquence,
 *   le `message_id` persisté est celui du **message USER** qui a déclenché
 *   le tour (cf. `service.py` ligne 1183 : `message_id=user_msg.id`).
 *   Le matching côté UI préfère `userMsg.id` ; des fallbacks (assistant id,
 *   fenêtre temporelle, ordinal, orphelins…) couvrent les divergences FK.
 *
 * Best-effort : une section sans donnée (ex. ancien tour pré-Lot 5)
 * est silencieusement masquée — on n'affiche jamais "inconnu" pour ne
 * pas polluer la lecture admin.
 *
 * Comportement quand le turn sélectionné est USER : on suit le turn
 * ASSISTANT immédiatement suivant (c'est lui qui porte la décision
 * router et le snapshot cognitif). Le turn user reste sélectionné
 * dans la timeline (pas de side-effect sur `selectedTurn`).
 */
'use client'

import { Badge } from '@/components/ui/badge'
import {
  ArrowDown,
  Brain,
  GitBranch,
  Layers,
  MessageSquare,
  Network,
  Target,
} from 'lucide-react'
import { agentColor, type AgentDecision } from './AssistanceToolCallDetailDrawer'

// ─────────────────────────── Types ──────────────────────────────

export interface CognitiveDiagramMessage {
  id: string
  turn_index: number
  role: 'user' | 'assistant' | string
  content: string
  agent_used: string | null
  message_payload: Record<string, unknown> | null
  /** ISO admin — utilisé pour le fallback temporel `findRouterDecision`. */
  created_at?: string | null
}

export interface CognitiveDiagramContext {
  conversation_summary: string | null
  summarized_until_turn: number | null
  total_messages: number
}

interface Props {
  selectedTurn: number | null
  messages: CognitiveDiagramMessage[]
  decisions: AgentDecision[]
  context?: CognitiveDiagramContext
}

// ─────────────────────────── Helpers ────────────────────────────

/** Heuristique « message court / laconique » qui peut bénéficier de
 * l'injection du previous_bot_context (cf. conversation_continuity.py
 * `should_embed_previous_bot_turn`). On ne reproduit pas la logique
 * complète côté UI — on signale juste un proxy visuel. */
const LACONIC_THRESHOLD = 30

/**
 * Résout quel turn ASSISTANT correspond au turn sélectionné dans la
 * timeline. Si l'utilisateur a cliqué sur un turn user, on prend le
 * 1ᵉʳ assistant après. Si c'est déjà un assistant, on le garde.
 */
function resolveAssistantTurn(
  selectedTurn: number | null,
  messages: CognitiveDiagramMessage[],
): CognitiveDiagramMessage | null {
  if (selectedTurn === null) return null
  const sorted = [...messages].sort((a, b) => a.turn_index - b.turn_index)
  const idx = sorted.findIndex((m) => m.turn_index === selectedTurn)
  if (idx < 0) return null
  const selected = sorted[idx]
  if (selected.role === 'assistant') return selected
  for (let i = idx + 1; i < sorted.length; i++) {
    if (sorted[i].role === 'assistant') return sorted[i]
  }
  return null
}

/**
 * Récupère le user message qui a déclenché la réponse assistant
 * `assistantMsg` (= dernier user avant lui dans l'ordre `turn_index`).
 */
function findTriggeringUserMessage(
  assistantMsg: CognitiveDiagramMessage,
  messages: CognitiveDiagramMessage[],
): CognitiveDiagramMessage | null {
  const sorted = [...messages].sort((a, b) => a.turn_index - b.turn_index)
  const idx = sorted.findIndex((m) => m.id === assistantMsg.id)
  for (let i = idx - 1; i >= 0; i--) {
    if (sorted[i].role === 'user') return sorted[i]
  }
  return null
}

/** Parse ISO admin → ms ; null si invalide. */
function parseIsoMs(iso: string | null | undefined): number | null {
  if (!iso) return null
  const n = Date.parse(iso)
  return Number.isNaN(n) ? null : n
}

/** Présence de données utiles dans arguments (cognitive / objective / intent). */
function routerArgumentsLookRich(args: Record<string, unknown> | undefined): boolean {
  if (!args || typeof args !== 'object') return false
  const cog = args.cognitive_state
  if (cog && typeof cog === 'object' && !Array.isArray(cog)) {
    if (Object.keys(cog).length > 0) return true
  }
  const obj = args.objective
  if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
    if (Object.keys(obj).length > 0) return true
  }
  const intent = args.intent_classification
  if (intent && typeof intent === 'object' && !Array.isArray(intent)) {
    if (Object.keys(intent).length > 0) return true
  }
  return false
}

/**
 * Cherche la décision `router_classify` rattachée au tour. Le matching
 * se fait sur `userMsg.id` car la persistance utilise le message user
 * qui a déclenché le tour (le message assistant n'existe pas encore
 * au moment où le router décide).
 *
 * Fallbacks si `message_id` ne matche pas : FK sur l’assistant du même
 * tour, fenêtre temporelle user→assistant, message_id sur user même
 * `turn_index`, appariement ordinal (k-ième user ↔ k-ième router),
 * orphelins legacy, puis derniers recours chronologiques avec préférence
 * pour un payload riche (cognitive / objective / intent).
 */
function findRouterDecision(
  userMsg: CognitiveDiagramMessage | null,
  assistantMsg: CognitiveDiagramMessage | null,
  decisions: AgentDecision[],
  allMessages: CognitiveDiagramMessage[],
): AgentDecision | null {
  if (!userMsg) return null
  const routerDecisions = decisions.filter(
    (d) => d.tool_name === 'router_classify',
  )
  if (routerDecisions.length === 0) return null

  const sortedMsgs = [...allMessages].sort(
    (a, b) => a.turn_index - b.turn_index,
  )

  const exact = routerDecisions.find((d) => d.message_id === userMsg.id)
  if (exact) return exact

  if (assistantMsg) {
    const byAssistantId = routerDecisions.find(
      (d) => d.message_id === assistantMsg.id,
    )
    if (byAssistantId) return byAssistantId
  }

  const tUser = parseIsoMs(userMsg.created_at)
  const tAsst = assistantMsg ? parseIsoMs(assistantMsg.created_at) : null

  if (tUser !== null && tAsst !== null && tAsst >= tUser) {
    const inWindow = routerDecisions.filter((d) => {
      const td = parseIsoMs(d.created_at)
      if (td === null) return false
      return td >= tUser && td <= tAsst
    })
    if (inWindow.length > 0) {
      inWindow.sort(
        (a, b) =>
          (parseIsoMs(a.created_at) ?? 0) - (parseIsoMs(b.created_at) ?? 0),
      )
      const preferred = inWindow.find((d) => routerArgumentsLookRich(d.arguments))
      return preferred ?? inWindow[0]!
    }
  }

  const linkedSameTurnUser = routerDecisions.find((d) => {
    if (!d.message_id || d.message_id === userMsg.id) return false
    const linked = sortedMsgs.find((m) => m.id === d.message_id)
    return linked?.role === 'user' && linked.turn_index === userMsg.turn_index
  })
  if (linkedSameTurnUser) return linkedSameTurnUser

  const userMessages = sortedMsgs.filter((m) => m.role === 'user')
  const userOrdinal = userMessages.findIndex((m) => m.id === userMsg.id)
  if (userOrdinal >= 0) {
    const routersChrono = [...routerDecisions].sort(
      (a, b) =>
        (parseIsoMs(a.created_at) ?? 0) - (parseIsoMs(b.created_at) ?? 0),
    )
    if (userOrdinal < routersChrono.length) {
      return routersChrono[userOrdinal]!
    }
  }

  const orphans = routerDecisions.filter((d) => !d.message_id)
  if (orphans.length > 0) {
    orphans.sort(
      (a, b) =>
        a.iteration - b.iteration ||
        (parseIsoMs(a.created_at) ?? 0) - (parseIsoMs(b.created_at) ?? 0),
    )
    const rich = [...orphans].reverse().find((d) => routerArgumentsLookRich(d.arguments))
    return rich ?? orphans.at(-1) ?? null
  }

  if (tUser !== null) {
    const afterUser = [...routerDecisions]
      .filter((d) => {
        const td = parseIsoMs(d.created_at)
        return td !== null && td >= tUser
      })
      .sort(
        (a, b) =>
          (parseIsoMs(a.created_at) ?? 0) - (parseIsoMs(b.created_at) ?? 0),
      )
    const useful = afterUser.find((d) => routerArgumentsLookRich(d.arguments))
    if (useful) return useful
    if (afterUser.length > 0) return afterUser[0]!
  }

  const allChrono = [...routerDecisions].sort(
    (a, b) =>
      (parseIsoMs(a.created_at) ?? 0) - (parseIsoMs(b.created_at) ?? 0),
  )
  const richLast = [...allChrono].reverse().find((d) => routerArgumentsLookRich(d.arguments))
  return richLast ?? allChrono.at(-1) ?? null
}

/**
 * Lit `message_payload.metadata.agent_chain` (Phase 2c orchestration).
 */
function extractAgentChain(
  assistantMsg: CognitiveDiagramMessage | null,
): string[] {
  if (!assistantMsg?.message_payload) return []
  const meta = (assistantMsg.message_payload as { metadata?: unknown })
    ?.metadata
  if (!meta || typeof meta !== 'object') return []
  const chain = (meta as { agent_chain?: unknown }).agent_chain
  if (!Array.isArray(chain)) return []
  return chain.filter((x): x is string => typeof x === 'string')
}

/**
 * Lit `message_payload.metadata.consultations` (Phase 2c
 * `consult_specialist`).
 */
function extractConsultations(
  assistantMsg: CognitiveDiagramMessage | null,
): Array<{ target: string; purpose?: string }> {
  if (!assistantMsg?.message_payload) return []
  const meta = (assistantMsg.message_payload as { metadata?: unknown })
    ?.metadata
  if (!meta || typeof meta !== 'object') return []
  const list = (meta as { consultations?: unknown }).consultations
  if (!Array.isArray(list)) return []
  return list
    .filter((c): c is Record<string, unknown> => typeof c === 'object' && c !== null)
    .map((c) => ({
      target: typeof c.target === 'string' ? c.target : 'unknown',
      purpose: typeof c.purpose === 'string' ? c.purpose : undefined,
    }))
}

// Couleurs sémantiques pour les états cognitifs (cohérent avec la
// page admin `cognitive-funnel` Lot 6).
function emotionalIntentColor(value: string): string {
  switch (value) {
    case 'FEAR_RISK':
    case 'ANGER':
    case 'COMPLIANCE_BLOCKED':
      return 'bg-red-50 text-red-700 border-red-200'
    case 'CURIOSITY':
    case 'OPPORTUNITY':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'TRANSACTION':
      return 'bg-cyan-50 text-cyan-700 border-cyan-200'
    case 'NEUTRAL':
    default:
      return 'bg-slate-50 text-slate-700 border-slate-200'
  }
}

function stageColor(value: string): string {
  switch (value) {
    case 'discovery':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'clarification':
      return 'bg-indigo-50 text-indigo-700 border-indigo-200'
    case 'recommendation':
      return 'bg-violet-50 text-violet-700 border-violet-200'
    case 'conversion':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    default:
      return 'bg-slate-50 text-slate-700 border-slate-200'
  }
}

function decisionKindColor(kind: string): string {
  switch (kind) {
    case 'route_to':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'ask_clarification':
      return 'bg-amber-50 text-amber-700 border-amber-200'
    case 'redirect_off_topic':
      return 'bg-red-50 text-red-700 border-red-200'
    default:
      return 'bg-slate-50 text-slate-700 border-slate-200'
  }
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text
  return `${text.slice(0, max).trim()}…`
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(0)}%`
}

// ─────────────────────────── Sub-components ─────────────────────

function StepConnector() {
  return (
    <div className="flex justify-center my-1">
      <ArrowDown className="h-3.5 w-3.5 text-slate-300" />
    </div>
  )
}

function StepCard({
  icon,
  title,
  children,
  tone = 'neutral',
}: {
  icon: React.ReactNode
  title: string
  children: React.ReactNode
  tone?:
    | 'neutral'
    | 'cognitive'
    | 'objective'
    | 'router'
    | 'chain'
    | 'input'
    | 'context'
}) {
  const toneClass = (() => {
    switch (tone) {
      case 'input':
        return 'border-slate-200'
      case 'context':
        return 'border-amber-200 bg-amber-50/30'
      case 'cognitive':
        return 'border-indigo-200 bg-indigo-50/30'
      case 'objective':
        return 'border-violet-200 bg-violet-50/30'
      case 'router':
        return 'border-emerald-200 bg-emerald-50/30'
      case 'chain':
        return 'border-cyan-200 bg-cyan-50/30'
      default:
        return 'border-slate-200'
    }
  })()
  return (
    <div className={`rounded-md border p-2.5 ${toneClass}`}>
      <div className="flex items-center gap-1.5 mb-1.5 text-[10px] uppercase font-semibold tracking-wide text-slate-600">
        {icon}
        <span>{title}</span>
      </div>
      <div className="text-xs text-slate-800 space-y-1">{children}</div>
    </div>
  )
}

function KvLine({
  k,
  v,
  badgeClass,
}: {
  k: string
  v: React.ReactNode
  badgeClass?: string
}) {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      <span className="text-[10px] uppercase tracking-wide text-slate-500 font-medium min-w-[68px]">
        {k}
      </span>
      {badgeClass ? (
        <Badge
          variant="outline"
          className={`text-[10px] py-0 px-1.5 font-normal ${badgeClass}`}
        >
          {v}
        </Badge>
      ) : (
        <span className="text-xs text-slate-700 font-mono">{v}</span>
      )}
    </div>
  )
}

// ─────────────────────────── Main component ─────────────────────

export function CognitiveTurnDiagram({
  selectedTurn,
  messages,
  decisions,
  context,
}: Props) {
  if (selectedTurn === null) {
    return (
      <p className="text-xs text-slate-400 p-2">
        Sélectionne un turn (user ou assistant) pour voir la synthèse cognitive.
      </p>
    )
  }

  const assistantMsg = resolveAssistantTurn(selectedTurn, messages)
  if (!assistantMsg) {
    return (
      <p className="text-xs text-slate-400 p-2">
        Pas de tour assistant correspondant à ce turn (réponse pas
        encore générée ou conversation interrompue).
      </p>
    )
  }
  const userMsg = findTriggeringUserMessage(assistantMsg, messages)
  const routerDecision = findRouterDecision(
    userMsg,
    assistantMsg,
    decisions,
    messages,
  )

  // Extraction du payload router (best-effort).
  const args = (routerDecision?.arguments ?? {}) as Record<string, unknown>
  const cognitive = (args.cognitive_state ?? null) as Record<
    string,
    unknown
  > | null
  const objective = (args.objective ?? null) as Record<
    string,
    unknown
  > | null
  const intentClassification = (args.intent_classification ?? null) as Record<
    string,
    unknown
  > | null
  // Cognitive Bot v4 — Lot 7 V1.2 (2026-05-05) : snapshot historique du
  // bloc CLIENT DISCOVERY tel qu'envoyé au LLM ce tour. Voir
  // `service._persist_router_decision`.
  const clientDiscoveryBlock =
    typeof args.client_discovery_block === 'string'
      ? args.client_discovery_block
      : null
  const decisionKind =
    typeof args.decision_kind === 'string' ? args.decision_kind : null
  const targetAgentFromRouter =
    typeof args.agent_id === 'string' ? args.agent_id : null
  const confidence =
    typeof args.confidence === 'number' ? args.confidence : null
  const reasoning = routerDecision?.reasoning_summary ?? null

  // Agent chain & consultations depuis le message assistant.
  const agentChain = extractAgentChain(assistantMsg)
  const consultations = extractConsultations(assistantMsg)
  const finalAgent = assistantMsg.agent_used

  // Best-effort : on rend uniquement les sections qui ont des données.
  const hasInput = Boolean(userMsg)
  const hasCognitive =
    cognitive !== null &&
    Object.keys(cognitive).some(
      (k) => cognitive[k] !== null && cognitive[k] !== undefined,
    )
  const hasIntent =
    intentClassification !== null &&
    Object.keys(intentClassification).some(
      (k) =>
        intentClassification[k] !== null &&
        intentClassification[k] !== undefined,
    )
  const hasObjective =
    objective !== null &&
    Object.keys(objective).some(
      (k) => objective[k] !== null && objective[k] !== undefined,
    )
  const hasRouter = Boolean(routerDecision)
  const hasChain =
    agentChain.length > 0 || consultations.length > 0 || Boolean(finalAgent)

  const userTurnIdx = userMsg?.turn_index ?? null
  const isLaconic =
    userMsg !== null && (userMsg.content?.trim().length ?? 0) <= LACONIC_THRESHOLD
  const recentTurnsCount =
    userTurnIdx !== null ? Math.max(0, Math.min(6, userTurnIdx)) : 0
  const summaryActive =
    context?.conversation_summary !== null &&
    context?.conversation_summary !== undefined &&
    context.conversation_summary.trim().length > 0
  const summaryCovers =
    summaryActive &&
    context?.summarized_until_turn !== null &&
    context?.summarized_until_turn !== undefined &&
    userTurnIdx !== null &&
    context.summarized_until_turn >= userTurnIdx
  const hasContext =
    summaryActive ||
    isLaconic ||
    recentTurnsCount > 0 ||
    Boolean(clientDiscoveryBlock)

  // Ordonnancement : étape user originale visible en haut, étapes
  // suivantes liées à la réponse assistant.
  const sections: React.ReactNode[] = []

  if (hasInput && userMsg) {
    sections.push(
      <StepCard
        key="input"
        icon={<MessageSquare className="h-3 w-3 text-slate-500" />}
        title={`Input · turn ${userMsg.turn_index}`}
        tone="input"
      >
        <p className="text-xs text-slate-700 whitespace-pre-wrap break-words">
          {truncate(userMsg.content, 240) || '(message vide)'}
        </p>
      </StepCard>,
    )
  }

  if (hasContext) {
    sections.push(
      <StepCard
        key="context"
        icon={<Layers className="h-3 w-3 text-amber-600" />}
        title="Contexte injecté au bot"
        tone="context"
      >
        {recentTurnsCount > 0 && (
          <KvLine
            k="historique"
            v={`${recentTurnsCount} tour${recentTurnsCount > 1 ? 's' : ''} récent${recentTurnsCount > 1 ? 's' : ''}`}
          />
        )}
        {summaryActive ? (
          <KvLine
            k="summary"
            v={
              summaryCovers
                ? `actif · jusqu'à T${context!.summarized_until_turn}`
                : `pré-existant · jusqu'à T${context!.summarized_until_turn ?? '?'}`
            }
            badgeClass={
              summaryCovers
                ? 'bg-amber-50 text-amber-700 border-amber-200'
                : 'bg-slate-50 text-slate-600 border-slate-200'
            }
          />
        ) : (
          <KvLine
            k="summary"
            v="aucun (conv. courte)"
            badgeClass="bg-slate-50 text-slate-500 border-slate-200"
          />
        )}
        {isLaconic && (
          <KvLine
            k="laconique"
            v={`${userMsg!.content.trim().length} car. → contexte précédent ≈ injecté`}
            badgeClass="bg-amber-50 text-amber-700 border-amber-200"
          />
        )}
        {clientDiscoveryBlock && (
          <details className="mt-1 text-[11px] text-slate-700">
            <summary className="cursor-pointer text-amber-700 hover:text-amber-900 font-medium">
              [CLIENT DISCOVERY] tel que vu par le bot
            </summary>
            <pre className="mt-1 text-[10px] bg-amber-50/50 border border-amber-200 rounded p-2 overflow-x-auto whitespace-pre-wrap max-h-48">
              {clientDiscoveryBlock}
            </pre>
          </details>
        )}
      </StepCard>,
    )
  }

  if (hasCognitive && cognitive) {
    const ei = (cognitive.emotional_intent as string | null) ?? null
    const matched =
      (cognitive.matched_emotional_intents as unknown[] | null) ?? null
    const stage = (cognitive.conversation_stage as string | null) ?? null
    const trust = cognitive.trust_level as number | null | undefined
    const knowledge = (cognitive.knowledge_level as string | null) ?? null
    sections.push(
      <StepCard
        key="cognitive"
        icon={<Brain className="h-3 w-3 text-indigo-500" />}
        title="Analyse intention user"
        tone="cognitive"
      >
        {ei && (
          <KvLine k="emotion" v={ei} badgeClass={emotionalIntentColor(ei)} />
        )}
        {Array.isArray(matched) && matched.length > 1 && (
          <KvLine
            k="ambig."
            v={`${matched.length} émotions détectées (${matched.slice(0, 3).join(', ')}${matched.length > 3 ? '…' : ''})`}
            badgeClass="bg-amber-50 text-amber-700 border-amber-200"
          />
        )}
        {Array.isArray(matched) && matched.length === 1 && (
          <KvLine
            k="confiance"
            v="non-ambigu"
            badgeClass="bg-emerald-50 text-emerald-700 border-emerald-200"
          />
        )}
        {stage && <KvLine k="stage" v={stage} badgeClass={stageColor(stage)} />}
        {typeof trust === 'number' && (
          <KvLine k="trust" v={formatPercent(trust)} />
        )}
        {knowledge && <KvLine k="knowledge" v={knowledge} />}
      </StepCard>,
    )
  }

  if (hasIntent && intentClassification) {
    const primaryTag =
      (intentClassification.primary_tag as string | null) ?? null
    const family = (intentClassification.family as string | null) ?? null
    const scopeLevel =
      (intentClassification.scope_level as string | null) ?? null
    const preferredAgent =
      (intentClassification.preferred_agent as string | null) ?? null
    const tags = (intentClassification.tags as unknown[] | null) ?? null
    sections.push(
      <StepCard
        key="intent"
        icon={<Brain className="h-3 w-3 text-indigo-700" />}
        title="Classification keyword (Router v2)"
        tone="cognitive"
      >
        {primaryTag && (
          <KvLine
            k="tag"
            v={primaryTag}
            badgeClass="bg-indigo-50 text-indigo-700 border-indigo-200"
          />
        )}
        {family && <KvLine k="famille" v={family} />}
        {scopeLevel && <KvLine k="scope" v={scopeLevel} />}
        {preferredAgent && (
          <KvLine
            k="suggéré"
            v={preferredAgent}
            badgeClass={agentColor(preferredAgent)}
          />
        )}
        {Array.isArray(tags) && tags.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] uppercase tracking-wide text-slate-500 font-medium min-w-[68px]">
              tags
            </span>
            <div className="flex gap-1 flex-wrap">
              {tags.slice(0, 6).map((t, i) =>
                typeof t === 'string' ? (
                  <Badge
                    key={`${t}-${i}`}
                    variant="outline"
                    className="text-[10px] py-0 px-1.5 font-normal bg-slate-50 text-slate-600 border-slate-200"
                  >
                    {t}
                  </Badge>
                ) : null,
              )}
              {tags.length > 6 && (
                <span className="text-[10px] text-slate-400">
                  +{tags.length - 6}
                </span>
              )}
            </div>
          </div>
        )}
      </StepCard>,
    )
  }

  if (hasObjective && objective) {
    const goal = (objective.primary_goal as string | null) ?? null
    const nba = (objective.next_best_action as string | null) ?? null
    const stop = (objective.stop_pushing as boolean | null) ?? null
    const strategy = (objective.strategy_hint as string | null) ?? null
    sections.push(
      <StepCard
        key="objective"
        icon={<Target className="h-3 w-3 text-violet-500" />}
        title="Objectif · réponse bot"
        tone="objective"
      >
        {goal && <KvLine k="goal" v={goal} />}
        {nba && <KvLine k="action" v={nba} />}
        {stop !== null && (
          <KvLine
            k="stop_push"
            v={stop ? 'true' : 'false'}
            badgeClass={
              stop
                ? 'bg-red-50 text-red-700 border-red-200'
                : 'bg-slate-50 text-slate-600 border-slate-200'
            }
          />
        )}
        {strategy && (
          <p className="text-[11px] text-slate-600 italic mt-1">
            « {truncate(strategy, 140)} »
          </p>
        )}
      </StepCard>,
    )
  }

  if (hasRouter) {
    sections.push(
      <StepCard
        key="router"
        icon={<GitBranch className="h-3 w-3 text-emerald-500" />}
        title="Décision router"
        tone="router"
      >
        {decisionKind && (
          <KvLine
            k="kind"
            v={decisionKind}
            badgeClass={decisionKindColor(decisionKind)}
          />
        )}
        {targetAgentFromRouter && (
          <KvLine
            k="agent"
            v={targetAgentFromRouter}
            badgeClass={agentColor(targetAgentFromRouter)}
          />
        )}
        {confidence !== null && (
          <KvLine k="confidence" v={formatPercent(confidence)} />
        )}
        {reasoning && (
          <p className="text-[11px] text-slate-600 italic mt-1">
            « {truncate(reasoning, 180)} »
          </p>
        )}
      </StepCard>,
    )
  }

  if (hasChain) {
    sections.push(
      <StepCard
        key="chain"
        icon={<Network className="h-3 w-3 text-cyan-500" />}
        title="Chaîne d'agents"
        tone="chain"
      >
        <div className="flex items-center gap-1 flex-wrap">
          {(agentChain.length > 0 ? agentChain : ['router', finalAgent ?? '']).map(
            (a, i) =>
              a ? (
                <span key={`${a}-${i}`} className="flex items-center gap-1">
                  <Badge
                    variant="outline"
                    className={`text-[10px] py-0 px-1.5 font-normal ${agentColor(a)}`}
                  >
                    {a}
                  </Badge>
                  {i < (agentChain.length || 2) - 1 && (
                    <span className="text-slate-400 text-xs">→</span>
                  )}
                </span>
              ) : null,
          )}
        </div>
        {consultations.length > 0 && (
          <div className="mt-1.5 space-y-0.5">
            <p className="text-[10px] uppercase tracking-wide text-slate-500 font-medium">
              consultations
            </p>
            {consultations.map((c, i) => (
              <div
                key={i}
                className="flex items-center gap-1.5 text-[11px] text-slate-700"
              >
                <span className="text-slate-400">↳</span>
                <Badge
                  variant="outline"
                  className={`text-[10px] py-0 px-1.5 font-normal ${agentColor(c.target)}`}
                >
                  {c.target}
                </Badge>
                {c.purpose && (
                  <span className="text-slate-500 italic">{c.purpose}</span>
                )}
              </div>
            ))}
          </div>
        )}
      </StepCard>,
    )
  }

  if (sections.length === 0) {
    return (
      <p className="text-xs text-slate-400 p-2">
        Aucune trace cognitive disponible pour ce turn (tour
        antérieur à Cognitive Bot v4 ou décision router non persistée).
      </p>
    )
  }

  return (
    <div className="space-y-0.5">
      {sections.map((section, i) => (
        <div key={i}>
          {section}
          {i < sections.length - 1 && <StepConnector />}
        </div>
      ))}
    </div>
  )
}
