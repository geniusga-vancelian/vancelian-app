/**
 * Tags affichés au-dessus des bulles assistant : agent cible · intention · objectif.
 * Source : ligne ``router_classify`` rattachée au **message utilisateur précédant**
 * la réponse assistant (persist ``message_id`` = user_msg).
 */

import type { AgentDecision } from '@/components/admin/AssistanceToolCallDetailDrawer'

export interface MessageReadLike {
  id: string
  turn_index: number
  role: string
}

const AGENT_LABEL_FR: Record<string, string> = {
  action: 'Action',
  product: 'Produit',
  market: 'Marché',
  advisor: 'Conseiller',
  compliance: 'Compliance',
  trust: 'Trust',
  default: 'Général',
}

/** Alias courants hors catalogue explicite. */
const INTENT_LABEL_FR: Record<string, string> = {
  info: 'Info',
  information: 'Info',
  fear: 'Peur',
  curiosity: 'Curiosité',
  transaction: 'Transactionnel',
  opportunity: 'Opportunité',
  neutral: 'Neutre',
  anger: 'Colère',
  compliance: 'Conformité',
}

const GOAL_LABEL_FR: Record<string, string> = {
  reassure: 'Réassurance',
  de_escalate: 'Désescalade',
  unblock: 'Débloquer',
  inform: 'Informer',
  educate: 'Éduquer',
  convert: 'Investissement',
}

export type AssistantRoutingTags = {
  agentLabel: string | null
  clientIntentLabel: string | null
  objectiveLabel: string | null
}

function normKey(s: string): string {
  return s.trim().toLowerCase()
}

function prettifySlug(s: string): string {
  const k = normKey(s)
  if (!k) return s
  if (INTENT_LABEL_FR[k]) return INTENT_LABEL_FR[k]
  if (GOAL_LABEL_FR[k]) return GOAL_LABEL_FR[k]
  return s.replace(/_/g, ' ')
}

export function labelRoutedAgent(agentId: unknown): string | null {
  if (typeof agentId !== 'string' || !agentId.trim()) return null
  const id = agentId.trim()
  return AGENT_LABEL_FR[id] ?? id.charAt(0).toUpperCase() + id.slice(1)
}

export function findPrecedingUserMessage(
  messages: MessageReadLike[],
  assistantTurnIndex: number,
): MessageReadLike | null {
  const sorted = [...messages].sort((a, b) => a.turn_index - b.turn_index)
  const idx = sorted.findIndex(
    (m) => m.turn_index === assistantTurnIndex && m.role === 'assistant',
  )
  if (idx < 0) return null
  for (let i = idx - 1; i >= 0; i--) {
    if (sorted[i].role === 'user') return sorted[i]
  }
  return null
}

export function getRouterClassifyForUserTurn(
  userTurnIndex: number,
  decisionsByTurn: Map<number, AgentDecision[]>,
): AgentDecision | null {
  const list = decisionsByTurn.get(userTurnIndex) ?? []
  return list.find((d) => d.tool_name === 'router_classify') ?? null
}

export function extractAssistantRoutingTags(
  assistantTurnIndex: number,
  messages: MessageReadLike[],
  decisionsByTurn: Map<number, AgentDecision[]>,
): AssistantRoutingTags {
  const userBefore = findPrecedingUserMessage(messages, assistantTurnIndex)
  if (!userBefore) {
    return { agentLabel: null, clientIntentLabel: null, objectiveLabel: null }
  }
  const router = getRouterClassifyForUserTurn(
    userBefore.turn_index,
    decisionsByTurn,
  )
  if (!router) {
    return { agentLabel: null, clientIntentLabel: null, objectiveLabel: null }
  }
  const args = router.arguments ?? {}

  const agentLabel = labelRoutedAgent(args.agent_id)

  const intentBlock = args.intent_classification
  let clientIntentLabel: string | null = null
  if (intentBlock && typeof intentBlock === 'object' && !Array.isArray(intentBlock)) {
    const ic = intentBlock as Record<string, unknown>
    const primary =
      typeof ic.primary_tag === 'string' && ic.primary_tag.trim()
        ? ic.primary_tag.trim()
        : null
    const family =
      typeof ic.family === 'string' && ic.family.trim() ? ic.family.trim() : null
    if (primary) clientIntentLabel = prettifySlug(primary)
    else if (family) clientIntentLabel = prettifySlug(family)
  }
  const cog = args.cognitive_state
  if (
    !clientIntentLabel &&
    cog &&
    typeof cog === 'object' &&
    !Array.isArray(cog)
  ) {
    const em = (cog as Record<string, unknown>).emotional_intent
    if (typeof em === 'string' && em.trim()) {
      clientIntentLabel = prettifySlug(em.trim())
    }
  }

  const obj = args.objective
  let objectiveLabel: string | null = null
  if (obj && typeof obj === 'object' && !Array.isArray(obj)) {
    const pg = (obj as Record<string, unknown>).primary_goal
    if (typeof pg === 'string' && pg.trim()) {
      objectiveLabel =
        GOAL_LABEL_FR[normKey(pg.trim())] ?? prettifySlug(pg.trim())
    }
  }

  return {
    agentLabel,
    clientIntentLabel,
    objectiveLabel,
  }
}
