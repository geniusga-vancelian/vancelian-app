/**
 * TypeScript types for AI Jurisdiction Configs Builder
 */

export interface ComposeJurisdictionConfigRequest {
  jurisdiction: string
  purpose: 'KYC' | 'AML_RISK'
  prompt: string
  previous_spec?: any
  messages?: Array<{ role: string; content: string }>
}

export interface ComposeJurisdictionConfigResponse {
  spec: any
  assistant_text: string
  warnings?: string[]
  questions?: string[]
  value_suggestions?: unknown[]
}

export interface ValidateJurisdictionConfigRequest {
  jurisdiction: string
  purpose: 'KYC' | 'AML_RISK'
  spec: any
}

export interface ValidateJurisdictionConfigResponse {
  ok: boolean
  errors: string[]
  normalized_spec?: any
}
