/**
 * API functions for AI Email Builder
 */
import { ComposeEmailRequest, ComposeEmailResponse, TranscribeAudioResponse, EmailTemplate } from './types'

export async function composeEmail(request: ComposeEmailRequest): Promise<ComposeEmailResponse> {
  // Use UGG endpoint if template is arquantix_ugg_v1
  const isUGGTemplate = request.templateId === 'arquantix_ugg_v1'
  const endpoint = isUGGTemplate ? '/api/ai/email/compose-ugg' : '/api/ai/email/compose'
  
  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    let errorData: any
    try {
      errorData = await response.json()
    } catch {
      // If response is not JSON, create error object from status
      throw new Error(`Request failed with status ${response.status}`)
    }
    
    // Log detailed error in dev mode
    if (process.env.NODE_ENV === 'development') {
      console.error('[AI Email API] Compose error:', {
        status: response.status,
        code: errorData.code,
        error: errorData.error,
        details: errorData.details,
        url: errorData.url,
        fullError: errorData,
      })
    }
    
    // Extract error message
    const errorMessage = 
      errorData.error || 
      errorData.detail || 
      errorData.details || 
      errorData.message ||
      `Request failed with status ${response.status}`
    
    // Check if it's a backend unavailable error
    if (errorData.code === 'BACKEND_UNAVAILABLE' || errorData.code === 'BACKEND_ERROR') {
      throw new Error(errorMessage)
    }
    
    throw new Error(errorMessage)
  }

  const result = await response.json()
  
  // Show warnings in console (but don't block)
  if (result.warnings && result.warnings.length > 0) {
    if (process.env.NODE_ENV === 'development') {
      console.warn('[AI Email API] Warnings:', result.warnings)
    }
    // Only show first warning to user via toast (handled by ChatStudio)
    // Backend unavailable warnings should be shown prominently
    const backendWarning = result.warnings.find((w: string) => 
      w.includes('Backend unavailable') || w.includes('fallback')
    )
    if (backendWarning && process.env.NODE_ENV === 'development') {
      console.error('[AI Email API] Backend fallback warning:', backendWarning)
    }
  }
  
  return result
}

export async function listEmailTemplates(): Promise<EmailTemplate[]> {
  const response = await fetch('/api/ai/email/templates', {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to fetch templates' }))
    throw new Error(error.error || 'Failed to fetch templates')
  }

  return response.json()
}

export async function transcribeAudio(file: File): Promise<TranscribeAudioResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch('/api/ai/voice/transcribe', {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to transcribe audio' }))
    throw new Error(error.error || 'Failed to transcribe audio')
  }

  return response.json()
}

