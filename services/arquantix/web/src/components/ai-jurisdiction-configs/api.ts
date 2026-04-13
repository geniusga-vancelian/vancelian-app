/**
 * API functions for AI Jurisdiction Configs Builder
 */
import {
  ComposeJurisdictionConfigRequest,
  ComposeJurisdictionConfigResponse,
  ValidateJurisdictionConfigRequest,
  ValidateJurisdictionConfigResponse,
} from './types'

export async function composeJurisdictionConfig(
  request: ComposeJurisdictionConfigRequest
): Promise<ComposeJurisdictionConfigResponse> {
  const response = await fetch('/api/ai/jurisdiction-configs/compose', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    let errorData: any
    try {
      errorData = await response.json()
    } catch {
      throw new Error(`Request failed with status ${response.status}`)
    }

    // Handle validation errors with details
    if (response.status === 400 && errorData.validation_errors) {
      const validationDetails = errorData.validation_errors
        .map((err: any) => `${err.field}: ${err.message}`)
        .join(', ')
      throw new Error(`Validation failed: ${validationDetails}`)
    }

    const errorMessage =
      errorData.error ||
      errorData.detail ||
      errorData.details ||
      errorData.message ||
      `Request failed with status ${response.status}`

    throw new Error(errorMessage)
  }

  return response.json()
}

export async function validateJurisdictionConfig(
  request: ValidateJurisdictionConfigRequest
): Promise<ValidateJurisdictionConfigResponse> {
  const response = await fetch('/api/ai/jurisdiction-configs/validate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    let errorData: any
    try {
      errorData = await response.json()
    } catch {
      throw new Error(`Request failed with status ${response.status}`)
    }

    // Handle validation errors with details
    if (response.status === 400 && errorData.validation_errors) {
      const validationDetails = errorData.validation_errors
        .map((err: any) => `${err.field}: ${err.message}`)
        .join(', ')
      throw new Error(`Validation failed: ${validationDetails}`)
    }

    const errorMessage =
      errorData.error ||
      errorData.detail ||
      errorData.details ||
      errorData.message ||
      `Request failed with status ${response.status}`

    throw new Error(errorMessage)
  }

  return response.json()
}
