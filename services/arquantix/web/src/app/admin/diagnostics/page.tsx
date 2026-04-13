'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface DiagnosticCheck {
  check: string
  status: 'PASS' | 'FAIL' | 'SKIP'
  details?: string[]
  errors?: string[]
  duration_ms?: number
  [key: string]: any
}

interface DiagnosticReport {
  timestamp: string
  mode: string
  checks: DiagnosticCheck[]
  summary: {
    total: number
    passed: number
    failed: number
    skipped: number
  }
  total_duration_ms: number
  markdown?: string
}

interface AuthProbeResult {
  cookie_names: string[]
  raw_cookie_names?: string[]
  has_cookie_header: boolean
  session_found: boolean
  session_email: string | null
  jwt_generated: boolean
  error?: string
}

export default function DiagnosticsPage() {
  const [report, setReport] = useState<DiagnosticReport | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [mode, setMode] = useState<'quick' | 'full'>('quick')
  const [authProbe, setAuthProbe] = useState<AuthProbeResult | null>(null)
  const [isProbing, setIsProbing] = useState(false)
  const [whoami, setWhoami] = useState<any>(null)
  const [isWhoamiLoading, setIsWhoamiLoading] = useState(false)
  const [jwtDebug, setJwtDebug] = useState<any>(null)
  const [isJwtDebugLoading, setIsJwtDebugLoading] = useState(false)
  const [authTrace, setAuthTrace] = useState<any>(null)
  const [isAuthTraceLoading, setIsAuthTraceLoading] = useState(false)

  const handleRun = async () => {
    setIsRunning(true)
    setReport(null)
    try {
      const response = await fetch('/api/diagnostics/market-backtest/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({ mode }),
      })

      // Read response body ONCE - use text() first, then parse if needed
      const responseText = await response.text()
      let responseData: any = null
      
      try {
        responseData = responseText ? JSON.parse(responseText) : null
      } catch {
        responseData = { error: responseText || 'Failed to parse response' }
      }

      if (!response.ok) {
        // Display detailed error information
        console.error('[Diagnostics] Error response:', responseData)
        const errorDetails = JSON.stringify(responseData, null, 2)
        const errorMsg = responseData.error || responseData.detail || responseData.message || `Failed to run diagnostic (${response.status})`
        toastError(`Diagnostic failed: ${errorMsg}`)
        
        // Set report with error details for display
        setReport({
          timestamp: new Date().toISOString(),
          mode: mode,
          checks: [{
            check: 'Diagnostic Run',
            status: 'FAIL',
            errors: [errorMsg],
            details: [`Status: ${response.status}`, `Details: ${errorDetails}`],
          }],
          summary: {
            total: 1,
            passed: 0,
            failed: 1,
            skipped: 0,
          },
          total_duration_ms: 0,
          error_details: responseData,
        } as any)
        return
      }

      // Success: use parsed data
      setReport(responseData)
      toastSuccess('Diagnostic completed successfully')
    } catch (error: any) {
      console.error('[Diagnostics] Request error:', error)
      toastError(`Failed to run diagnostic: ${error.message}`)
      setReport({
        timestamp: new Date().toISOString(),
        mode: mode,
        checks: [{
          check: 'Diagnostic Run',
          status: 'FAIL',
          errors: [error.message || 'Unknown error'],
        }],
        summary: {
          total: 1,
          passed: 0,
          failed: 1,
          skipped: 0,
        },
        total_duration_ms: 0,
      } as any)
    } finally {
      setIsRunning(false)
    }
  }

  const handleCopyMarkdown = () => {
    if (report?.markdown) {
      navigator.clipboard.writeText(report.markdown)
      toastSuccess('Markdown report copied to clipboard')
    }
  }

  const handleAuthProbe = async () => {
    setIsProbing(true)
    try {
      const response = await fetch('/api/auth/probe', {
        method: 'GET',
        credentials: 'include',
      })

      const data = await response.json()
      setAuthProbe(data)
      
      if (data.session_found && data.jwt_generated) {
        toastSuccess('Auth probe: Session found and JWT generated')
      } else if (data.session_found && !data.jwt_generated) {
        toastError('Auth probe: Session found but JWT generation failed')
      } else if (!data.session_found && data.cookie_names.length > 0) {
        toastError('Auth probe: Cookies present but session not found')
      } else {
        toastError('Auth probe: No cookies or session found')
      }
    } catch (error: any) {
      toastError(`Auth probe failed: ${error.message}`)
      setAuthProbe({
        cookie_names: [],
        has_cookie_header: false,
        session_found: false,
        session_email: null,
        jwt_generated: false,
        error: error.message,
      })
    } finally {
      setIsProbing(false)
    }
  }

  const getAuthProbeHint = (probe: AuthProbeResult | null): string | null => {
    if (!probe) return null
    
    if (probe.cookie_names.length === 0 && !probe.has_cookie_header) {
      return 'No cookies received; login cookie not set/sent'
    }
    
    if (!probe.session_found && probe.cookie_names.length > 0) {
      return 'Session cookie present but cannot be parsed by getSessionFromCookie'
    }
    
    if (probe.session_found && !probe.jwt_generated) {
      return 'JWT generation problem'
    }
    
    if (probe.session_found && probe.jwt_generated) {
      return '✅ Auth working correctly'
    }
    
    return null
  }

  const handleWhoami = async () => {
    setIsWhoamiLoading(true)
    setWhoami(null)
    try {
      const response = await fetch('/api/diagnostics/whoami', {
        method: 'GET',
        credentials: 'include',
      })

      const data = await response.json()
      setWhoami(data)
      
      if (response.ok && data.authenticated) {
        toastSuccess(`Authenticated as: ${data.user?.email}`)
      } else {
        toastError(`Whoami failed: ${data.error || 'Unknown error'}`)
      }
    } catch (error: any) {
      toastError(`Whoami error: ${error.message}`)
      setWhoami({ error: error.message })
    } finally {
      setIsWhoamiLoading(false)
    }
  }

  const handleJwtDebug = async () => {
    setIsJwtDebugLoading(true)
    setJwtDebug(null)
    try {
      const response = await fetch('/api/diagnostics/jwt-debug', {
        method: 'POST',
        credentials: 'include',
      })

      const data = await response.json()
      setJwtDebug(data)
      
      if (data.verify_ok) {
        toastSuccess('JWT verification OK!')
      } else {
        toastError(`JWT verification failed: ${data.verify_error || 'Unknown error'}`)
      }
    } catch (error: any) {
      toastError(`JWT Debug error: ${error.message}`)
      setJwtDebug({ error: error.message })
    } finally {
      setIsJwtDebugLoading(false)
    }
  }

  const handleAuthTrace = async () => {
    setIsAuthTraceLoading(true)
    setAuthTrace(null)
    try {
      const response = await fetch('/api/diagnostics/auth-trace', {
        method: 'POST',
        credentials: 'include',
      })

      const data = await response.json()
      setAuthTrace(data)
      
      if (data.get_current_user_ok) {
        toastSuccess('Auth trace: Authentication successful!')
      } else {
        toastError(`Auth trace: ${data.get_current_user_error || data.step || 'Unknown error'}`)
      }
    } catch (error: any) {
      toastError(`Auth Trace error: ${error.message}`)
      setAuthTrace({ error: error.message })
    } finally {
      setIsAuthTraceLoading(false)
    }
  }

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Diagnostics</h1>

      {/* Auth Probe Section */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Auth Probe</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-2 flex-wrap">
              <Button
                onClick={handleAuthProbe}
                disabled={isProbing}
                variant="outline"
              >
                {isProbing ? 'Probing...' : 'Run Auth Probe'}
              </Button>
              <Button
                onClick={handleJwtDebug}
                disabled={isJwtDebugLoading}
                variant="outline"
              >
                {isJwtDebugLoading ? 'Debugging...' : 'JWT Debug'}
              </Button>
              <Button
                onClick={handleAuthTrace}
                disabled={isAuthTraceLoading}
                variant="outline"
              >
                {isAuthTraceLoading ? 'Tracing...' : 'Auth Trace'}
              </Button>
              <Button
                onClick={handleWhoami}
                disabled={isWhoamiLoading}
                variant="outline"
              >
                {isWhoamiLoading ? 'Checking...' : 'Who am I?'}
              </Button>
            </div>
            
            {authTrace && (
              <div className="space-y-2">
                <h3 className="font-semibold mb-2">Auth Trace Results:</h3>
                <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto">
                  {JSON.stringify(authTrace, null, 2)}
                </pre>
                {authTrace.get_current_user_ok && (
                  <div className="p-3 rounded text-sm bg-green-50 text-green-800 border border-green-200">
                    ✅ Authentication successful! {authTrace.notes || ''}
                  </div>
                )}
                {!authTrace.get_current_user_ok && authTrace.step && (
                  <div className="p-3 rounded text-sm bg-red-50 text-red-800 border border-red-200">
                    ❌ Authentication failed at step: <strong>{authTrace.step}</strong>
                    {authTrace.get_current_user_error && (
                      <div className="mt-1 text-xs">Error: {authTrace.get_current_user_error}</div>
                    )}
                    {authTrace.get_current_user_error_type && (
                      <div className="mt-1 text-xs">Error type: {authTrace.get_current_user_error_type}</div>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {jwtDebug && (
              <div className="space-y-2">
                <h3 className="font-semibold mb-2">JWT Debug Results:</h3>
                <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto">
                  {JSON.stringify(jwtDebug, null, 2)}
                </pre>
                {jwtDebug.verify_ok && (
                  <div className="p-3 rounded text-sm bg-green-50 text-green-800 border border-green-200">
                    ✅ JWT verification successful! Token is valid.
                  </div>
                )}
                {!jwtDebug.verify_ok && jwtDebug.verify_error && (
                  <div className="p-3 rounded text-sm bg-red-50 text-red-800 border border-red-200">
                    ❌ JWT verification failed: {jwtDebug.verify_error}
                    {jwtDebug.verify_error_type && (
                      <div className="mt-1 text-xs">Error type: {jwtDebug.verify_error_type}</div>
                    )}
                  </div>
                )}
              </div>
            )}
            
            {whoami && (
              <div className="space-y-2">
                <h3 className="font-semibold mb-2">Whoami Results:</h3>
                <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto">
                  {JSON.stringify(whoami, null, 2)}
                </pre>
              </div>
            )}
            
            {authProbe && (
              <div className="space-y-2">
                <div>
                  <h3 className="font-semibold mb-2">Probe Results:</h3>
                  <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto">
                    {JSON.stringify(authProbe, null, 2)}
                  </pre>
                </div>
                
                {getAuthProbeHint(authProbe) && (
                  <div className={`p-3 rounded text-sm ${
                    getAuthProbeHint(authProbe)?.includes('✅') 
                      ? 'bg-green-50 text-green-800 border border-green-200'
                      : 'bg-yellow-50 text-yellow-800 border border-yellow-200'
                  }`}>
                    <strong>Hint:</strong> {getAuthProbeHint(authProbe)}
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Run Diagnostic</h2>
        
        <div className="flex items-center space-x-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Mode</label>
            <Select value={mode} onValueChange={(v: 'quick' | 'full') => setMode(v)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="quick">Quick</SelectItem>
                <SelectItem value="full">Full</SelectItem>
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex-1" />
          
          <Button
            onClick={handleRun}
            disabled={isRunning}
          >
            {isRunning ? 'Running...' : 'Run Quick Diagnostic'}
          </Button>
        </div>

        {mode === 'full' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded p-3 text-sm text-yellow-800">
            ⚠️ Full mode will perform a larger backfill. This may take longer and use more API calls.
          </div>
        )}
      </div>

      {report && (
        <div className="space-y-6">
          {/* Error Details (if present) */}
          {(report as any).error_details && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-4 text-red-800">Error Details</h2>
              <pre className="bg-white p-4 rounded text-xs overflow-x-auto max-h-96 overflow-y-auto border border-red-200">
                {JSON.stringify((report as any).error_details, null, 2)}
              </pre>
            </div>
          )}
          
          {/* Summary */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Summary</h2>
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{report.summary.passed}</div>
                <div className="text-sm text-gray-600">Passed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{report.summary.failed}</div>
                <div className="text-sm text-gray-600">Failed</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-600">{report.summary.skipped}</div>
                <div className="text-sm text-gray-600">Skipped</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">{report.summary.total}</div>
                <div className="text-sm text-gray-600">Total</div>
              </div>
            </div>
            <div className="mt-4 text-sm text-gray-500">
              Duration: {report.total_duration_ms} ms | Mode: {report.mode} | Timestamp: {new Date(report.timestamp).toLocaleString()}
            </div>
          </div>

          {/* Checks */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold mb-4">Checks Detail</h2>
            <div className="space-y-4">
              {report.checks.map((check, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">
                      {idx + 1}. {check.check}
                    </h3>
                    <span className={`px-3 py-1 rounded text-sm font-medium ${
                      check.status === 'PASS' ? 'bg-green-100 text-green-800' :
                      check.status === 'FAIL' ? 'bg-red-100 text-red-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {check.status}
                    </span>
                  </div>
                  
                  {check.details && check.details.length > 0 && (
                    <div className="mt-2">
                      <div className="text-sm text-gray-700">
                        {check.details.map((detail, i) => (
                          <div key={i} className="mb-1">{detail}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {check.errors && check.errors.length > 0 && (
                    <div className="mt-2">
                      <div className="text-sm text-red-600">
                        {check.errors.map((error, i) => (
                          <div key={i} className="mb-1">❌ {error}</div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {check.duration_ms !== undefined && (
                    <div className="mt-2 text-xs text-gray-500">
                      Duration: {check.duration_ms} ms
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Markdown Report */}
          {report.markdown && (
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">Markdown Report</h2>
                <Button onClick={handleCopyMarkdown} variant="outline" size="sm">
                  Copy Markdown
                </Button>
              </div>
              <pre className="bg-gray-50 p-4 rounded text-xs overflow-x-auto max-h-96 overflow-y-auto">
                {report.markdown}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

