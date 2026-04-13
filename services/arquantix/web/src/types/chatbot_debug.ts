export type ProfileSnapshot = Record<string, unknown>

export type DecisionSnapshot = {
  state?: string
  next_question_id?: string
  action?: string
  reason?: string
  completeness_score?: number
}

export type DebugPayload = {
  state: string
  next_question_id?: string
  action?: string
  reason?: string
  completeness_score?: number
  missing_fields: string[]
  asked_questions: string[]
  disclaimers_shown: string[]
  profile_diff: Record<string, unknown>
  profile: ProfileSnapshot
  conversation_summary?: string
  conversation_facts?: string[]
  steps?: { id: string; label: string; status: 'success' | 'in_progress' | null }[]
  goal_phase?: 'goal_free' | 'goal_clarify' | 'goal_force_pick' | null
  goal_locked?: boolean
  goal_confidence?: number
  goal_attempts?: number
  turn_index?: number
  goal_next_question_id?: string | null
}
