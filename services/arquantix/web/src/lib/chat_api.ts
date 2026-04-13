/**
 * Bot IA épargne — API client: createSession, sendTurn, getProfile
 * Calls /api/chatbot/* (Next.js routes that proxy to FastAPI)
 */

import type { DebugPayload } from '@/types/chatbot_debug'

export interface TurnResponse {
  reply: string
  profile_diff?: Record<string, unknown>
  state: string
  disclaimers_shown: string[]
  proposal_preview?: { allocation?: unknown[]; rationale?: string; disclaimers?: string[] }
  completeness_score?: number
  conversation_summary?: string
  conversation_facts?: string[]
  profile?: Record<string, unknown>
  next_question_id?: string
  goal_phase?: 'goal_free' | 'goal_clarify' | 'goal_force_pick' | null
  goal_locked?: boolean
  goal_confidence?: number
  goal_attempts?: number
  debug?: DebugPayload
}

export interface ProfileResponse {
  profile: Record<string, unknown>
  completeness_score: number
  missing_fields: string[]
}

export async function createSession(): Promise<{ session_id: string }> {
  const res = await fetch('/api/chatbot/session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}

export async function sendTurn(sessionId: string, message: string): Promise<TurnResponse> {
  const res = await fetch('/api/chatbot/conversation/turn', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}

export async function getProfile(sessionId: string): Promise<ProfileResponse> {
  const res = await fetch(`/api/chatbot/profile?session_id=${encodeURIComponent(sessionId)}`)
  if (!res.ok) throw new Error(await res.text().catch(() => res.statusText))
  return res.json()
}
