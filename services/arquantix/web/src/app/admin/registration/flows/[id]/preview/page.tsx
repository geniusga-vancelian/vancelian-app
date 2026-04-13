'use client'

import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'next/navigation'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

const COUNTRIES = [
  {code:'AF',name:'Afghanistan'},{code:'AL',name:'Albania'},{code:'DZ',name:'Algeria'},{code:'AD',name:'Andorra'},
  {code:'AO',name:'Angola'},{code:'AG',name:'Antigua and Barbuda'},{code:'AR',name:'Argentina'},{code:'AM',name:'Armenia'},
  {code:'AU',name:'Australia'},{code:'AT',name:'Austria'},{code:'AZ',name:'Azerbaijan'},{code:'BS',name:'Bahamas'},
  {code:'BH',name:'Bahrain'},{code:'BD',name:'Bangladesh'},{code:'BB',name:'Barbados'},{code:'BY',name:'Belarus'},
  {code:'BE',name:'Belgium'},{code:'BZ',name:'Belize'},{code:'BJ',name:'Benin'},{code:'BT',name:'Bhutan'},
  {code:'BO',name:'Bolivia'},{code:'BA',name:'Bosnia and Herzegovina'},{code:'BW',name:'Botswana'},{code:'BR',name:'Brazil'},
  {code:'BN',name:'Brunei'},{code:'BG',name:'Bulgaria'},{code:'BF',name:'Burkina Faso'},{code:'BI',name:'Burundi'},
  {code:'CV',name:'Cabo Verde'},{code:'KH',name:'Cambodia'},{code:'CM',name:'Cameroon'},{code:'CA',name:'Canada'},
  {code:'CF',name:'Central African Republic'},{code:'TD',name:'Chad'},{code:'CL',name:'Chile'},{code:'CN',name:'China'},
  {code:'CO',name:'Colombia'},{code:'KM',name:'Comoros'},{code:'CG',name:'Congo'},{code:'CD',name:'Congo (DRC)'},
  {code:'CR',name:'Costa Rica'},{code:'CI',name:"Côte d'Ivoire"},{code:'HR',name:'Croatia'},{code:'CU',name:'Cuba'},
  {code:'CY',name:'Cyprus'},{code:'CZ',name:'Czech Republic'},{code:'DK',name:'Denmark'},{code:'DJ',name:'Djibouti'},
  {code:'DM',name:'Dominica'},{code:'DO',name:'Dominican Republic'},{code:'EC',name:'Ecuador'},{code:'EG',name:'Egypt'},
  {code:'SV',name:'El Salvador'},{code:'GQ',name:'Equatorial Guinea'},{code:'ER',name:'Eritrea'},{code:'EE',name:'Estonia'},
  {code:'SZ',name:'Eswatini'},{code:'ET',name:'Ethiopia'},{code:'FJ',name:'Fiji'},{code:'FI',name:'Finland'},
  {code:'FR',name:'France'},{code:'GA',name:'Gabon'},{code:'GM',name:'Gambia'},{code:'GE',name:'Georgia'},
  {code:'DE',name:'Germany'},{code:'GH',name:'Ghana'},{code:'GR',name:'Greece'},{code:'GD',name:'Grenada'},
  {code:'GT',name:'Guatemala'},{code:'GN',name:'Guinea'},{code:'GW',name:'Guinea-Bissau'},{code:'GY',name:'Guyana'},
  {code:'HT',name:'Haiti'},{code:'HN',name:'Honduras'},{code:'HU',name:'Hungary'},{code:'IS',name:'Iceland'},
  {code:'IN',name:'India'},{code:'ID',name:'Indonesia'},{code:'IR',name:'Iran'},{code:'IQ',name:'Iraq'},
  {code:'IE',name:'Ireland'},{code:'IL',name:'Israel'},{code:'IT',name:'Italy'},{code:'JM',name:'Jamaica'},
  {code:'JP',name:'Japan'},{code:'JO',name:'Jordan'},{code:'KZ',name:'Kazakhstan'},{code:'KE',name:'Kenya'},
  {code:'KI',name:'Kiribati'},{code:'KP',name:'Korea (North)'},{code:'KR',name:'Korea (South)'},{code:'KW',name:'Kuwait'},
  {code:'KG',name:'Kyrgyzstan'},{code:'LA',name:'Laos'},{code:'LV',name:'Latvia'},{code:'LB',name:'Lebanon'},
  {code:'LS',name:'Lesotho'},{code:'LR',name:'Liberia'},{code:'LY',name:'Libya'},{code:'LI',name:'Liechtenstein'},
  {code:'LT',name:'Lithuania'},{code:'LU',name:'Luxembourg'},{code:'MG',name:'Madagascar'},{code:'MW',name:'Malawi'},
  {code:'MY',name:'Malaysia'},{code:'MV',name:'Maldives'},{code:'ML',name:'Mali'},{code:'MT',name:'Malta'},
  {code:'MH',name:'Marshall Islands'},{code:'MR',name:'Mauritania'},{code:'MU',name:'Mauritius'},{code:'MX',name:'Mexico'},
  {code:'FM',name:'Micronesia'},{code:'MD',name:'Moldova'},{code:'MC',name:'Monaco'},{code:'MN',name:'Mongolia'},
  {code:'ME',name:'Montenegro'},{code:'MA',name:'Morocco'},{code:'MZ',name:'Mozambique'},{code:'MM',name:'Myanmar'},
  {code:'NA',name:'Namibia'},{code:'NR',name:'Nauru'},{code:'NP',name:'Nepal'},{code:'NL',name:'Netherlands'},
  {code:'NZ',name:'New Zealand'},{code:'NI',name:'Nicaragua'},{code:'NE',name:'Niger'},{code:'NG',name:'Nigeria'},
  {code:'MK',name:'North Macedonia'},{code:'NO',name:'Norway'},{code:'OM',name:'Oman'},{code:'PK',name:'Pakistan'},
  {code:'PW',name:'Palau'},{code:'PS',name:'Palestine'},{code:'PA',name:'Panama'},{code:'PG',name:'Papua New Guinea'},
  {code:'PY',name:'Paraguay'},{code:'PE',name:'Peru'},{code:'PH',name:'Philippines'},{code:'PL',name:'Poland'},
  {code:'PT',name:'Portugal'},{code:'QA',name:'Qatar'},{code:'RO',name:'Romania'},{code:'RU',name:'Russia'},
  {code:'RW',name:'Rwanda'},{code:'KN',name:'Saint Kitts and Nevis'},{code:'LC',name:'Saint Lucia'},
  {code:'VC',name:'Saint Vincent and the Grenadines'},{code:'WS',name:'Samoa'},{code:'SM',name:'San Marino'},
  {code:'ST',name:'São Tomé and Príncipe'},{code:'SA',name:'Saudi Arabia'},{code:'SN',name:'Senegal'},
  {code:'RS',name:'Serbia'},{code:'SC',name:'Seychelles'},{code:'SL',name:'Sierra Leone'},{code:'SG',name:'Singapore'},
  {code:'SK',name:'Slovakia'},{code:'SI',name:'Slovenia'},{code:'SB',name:'Solomon Islands'},{code:'SO',name:'Somalia'},
  {code:'ZA',name:'South Africa'},{code:'SS',name:'South Sudan'},{code:'ES',name:'Spain'},{code:'LK',name:'Sri Lanka'},
  {code:'SD',name:'Sudan'},{code:'SR',name:'Suriname'},{code:'SE',name:'Sweden'},{code:'CH',name:'Switzerland'},
  {code:'SY',name:'Syria'},{code:'TW',name:'Taiwan'},{code:'TJ',name:'Tajikistan'},{code:'TZ',name:'Tanzania'},
  {code:'TH',name:'Thailand'},{code:'TL',name:'Timor-Leste'},{code:'TG',name:'Togo'},{code:'TO',name:'Tonga'},
  {code:'TT',name:'Trinidad and Tobago'},{code:'TN',name:'Tunisia'},{code:'TR',name:'Turkey'},{code:'TM',name:'Turkmenistan'},
  {code:'TV',name:'Tuvalu'},{code:'UG',name:'Uganda'},{code:'UA',name:'Ukraine'},{code:'AE',name:'United Arab Emirates'},
  {code:'GB',name:'United Kingdom'},{code:'US',name:'United States'},{code:'UY',name:'Uruguay'},{code:'UZ',name:'Uzbekistan'},
  {code:'VU',name:'Vanuatu'},{code:'VA',name:'Vatican City'},{code:'VE',name:'Venezuela'},{code:'VN',name:'Vietnam'},
  {code:'YE',name:'Yemen'},{code:'ZM',name:'Zambia'},{code:'ZW',name:'Zimbabwe'},
]

interface FlowStep {
  id: string
  step_key: string
  title: string
  description: string | null
  position: number
  is_optional: boolean
  is_blocking: boolean
  screens: FlowScreen[]
}

interface FlowScreen {
  id: string
  screen_key: string
  title: string
  subtitle: string | null
  layout_type: string
  components: FlowComponent[]
}

interface FlowComponent {
  id: string
  component_type: string
  component_key: string
  position: number
  props: Record<string, unknown>
  binding_slug: string | null
  validation: Record<string, unknown> | null
}

interface SessionState {
  session_id: string
  status: string
  flow_version: number
  progress_percent: number
  is_last_screen: boolean
  current_step: {
    id: string
    step_key: string
    title: string
    description: string | null
    is_blocking: boolean
    status: string
  } | null
  current_step_status: string | null
  screen: FlowScreen | null
  collected_data: Record<string, unknown>
  step_states: Array<{
    step_id: string
    status: string
    started_at: string | null
    completed_at: string | null
  }>
}

interface PreviewData {
  flow: {
    id: string
    name: string
    version: number
    status: string
    jurisdiction: { code: string; name: string }
    steps: FlowStep[]
  }
  statistics: {
    total_steps: number
    total_screens: number
    total_components: number
    blocking_steps: number
  }
}

function ComponentPreview({ comp, value, onChange }: {
  comp: FlowComponent
  value: unknown
  onChange: (slug: string, val: unknown) => void
}) {
  const slug = comp.binding_slug || ''
  const props = comp.props || {}
  const label = (props.label as string) || comp.component_key
  const required = props.required as boolean
  const placeholder = (props.placeholder as string) || ''

  switch (comp.component_type) {
    case 'text_input':
      return (
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          <input
            type={(props.keyboard_type as string) === 'email' ? 'email' : 'text'}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder={placeholder}
            value={(value as string) || ''}
            onChange={e => onChange(slug, e.target.value)}
          />
        </div>
      )

    case 'phone_input':
      return (
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          <input
            type="tel"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            placeholder="+33 6 12 34 56 78"
            value={(value as string) || ''}
            onChange={e => onChange(slug, e.target.value)}
          />
        </div>
      )

    case 'country_picker':
      return (
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
            value={(value as string) || ''}
            onChange={e => onChange(slug, e.target.value)}
          >
            <option value="">Select...</option>
            {COUNTRIES.map(c => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </select>
        </div>
      )

    case 'date_picker':
      return (
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          <input
            type="date"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            value={(value as string) || ''}
            onChange={e => onChange(slug, e.target.value)}
          />
        </div>
      )

    case 'checkbox':
      return (
        <div className="flex items-start gap-3 py-1">
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            checked={!!value}
            onChange={e => onChange(slug, e.target.checked)}
          />
          <label className="text-sm text-gray-700">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
        </div>
      )

    case 'select':
      return (
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          <select
            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white focus:ring-2 focus:ring-blue-500"
            value={(value as string) || ''}
            onChange={e => onChange(slug, e.target.value)}
          >
            <option value="">Select...</option>
            {(props.options as Array<{ value: string; label: string }> || []).map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
      )

    case 'legal_content':
      return (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <p className="text-sm text-amber-800">
            {(props.text as string) || (props.content as string) || 'Legal content placeholder'}
          </p>
        </div>
      )

    case 'section_title':
      return (
        <h3 className="text-base font-semibold text-gray-900 pt-2">
          {label}
        </h3>
      )

    case 'multi_select': {
      const msOptions = (props.options as Array<{ value: string; label: string }>) || []
      const selected = Array.isArray(value) ? (value as string[]) : []
      return (
        <div className="space-y-1.5">
          <label className="text-sm font-medium text-gray-700">
            {label} {required && <span className="text-red-500">*</span>}
          </label>
          <div className="space-y-1">
            {msOptions.map(opt => (
              <label key={opt.value} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={selected.includes(opt.value)}
                  onChange={e => {
                    const next = e.target.checked
                      ? [...selected, opt.value]
                      : selected.filter(v => v !== opt.value)
                    onChange(slug, next)
                  }}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>
      )
    }

    case 'info_box':
      return (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex gap-3">
          <span className="text-blue-500 text-lg">ℹ</span>
          <p className="text-sm text-blue-800">
            {(props.text as string) || (props.content as string) || 'Info content'}
          </p>
        </div>
      )

    case 'rich_text':
      return (
        <div className="prose prose-sm max-w-none">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">
            {(props.text as string) || (props.content as string) || ''}
          </p>
        </div>
      )

    case 'divider':
      return <hr className="border-gray-200 my-2" />

    case 'spacer':
      return <div style={{ height: `${(props.height as number) || 16}px` }} />

    case 'bullet_list': {
      const items = (props.items as string[]) || []
      return (
        <div className="space-y-1">
          {label && <p className="text-sm font-medium text-gray-700">{label}</p>}
          <ul className="list-disc list-inside space-y-0.5">
            {items.map((item, i) => (
              <li key={i} className="text-sm text-gray-700">{item}</li>
            ))}
          </ul>
        </div>
      )
    }

    default:
      return (
        <div className="p-3 bg-gray-100 rounded-lg border border-dashed border-gray-300">
          <p className="text-xs text-gray-500">
            Unknown: <code>{comp.component_type}</code> — {comp.component_key}
          </p>
        </div>
      )
  }
}

const STEP_STATUS_COLORS: Record<string, string> = {
  not_started: 'bg-gray-100 text-gray-600',
  in_progress: 'bg-blue-100 text-blue-700',
  completed: 'bg-green-100 text-green-700',
  skipped: 'bg-yellow-100 text-yellow-700',
  blocked: 'bg-red-100 text-red-700',
}

export default function FlowPreviewPage() {
  const params = useParams()
  const flowId = (params?.id as string | undefined) ?? ''

  const [preview, setPreview] = useState<PreviewData | null>(null)
  const [session, setSession] = useState<SessionState | null>(null)
  const [formData, setFormData] = useState<Record<string, unknown>>({})
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    fetch(`${BACKEND}/api/admin/registration/flows/${flowId}/preview`)
      .then(r => r.json())
      .then(data => { setPreview(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [flowId])

  const startSession = useCallback(async () => {
    if (!preview) return
    setSubmitting(true)
    setError(null)
    try {
      const jurisdiction = preview.flow.jurisdiction.code
      const res = await fetch(`${BACKEND}/api/registration/sessions/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ jurisdiction }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Failed to start session')
      }
      const data = await res.json()
      setSession(data)
      setFormData(data.collected_data || {})
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }, [preview])

  const submitScreen = useCallback(async () => {
    if (!session) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${BACKEND}/api/registration/sessions/${session.session_id}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ answers: formData }),
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Submit failed')
      }
      const data = await res.json()
      setSession(data)
      setFormData({ ...data.collected_data, ...formData })
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }, [session, formData])

  const navigate = useCallback(async (direction: 'next' | 'prev') => {
    if (!session) return
    setSubmitting(true)
    setError(null)
    try {
      if (direction === 'next' && Object.keys(formData).length > 0) {
        const submitRes = await fetch(`${BACKEND}/api/registration/sessions/${session.session_id}/submit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ answers: formData }),
        })
        if (!submitRes.ok) {
          const err = await submitRes.json()
          throw new Error(err.detail || 'Submit failed')
        }
        const data = await submitRes.json()
        setSession(data)
        setFormData(prev => ({ ...prev, ...data.collected_data }))
        return
      }
      const res = await fetch(`${BACKEND}/api/registration/sessions/${session.session_id}/${direction}`, {
        method: 'POST',
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || `${direction} failed`)
      }
      const data = await res.json()
      setSession(data)
      setFormData(prev => ({ ...prev, ...data.collected_data }))
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }, [session, formData])

  const completeSession = useCallback(async () => {
    if (!session) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${BACKEND}/api/registration/sessions/${session.session_id}/complete`, {
        method: 'POST',
      })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Complete failed')
      }
      const data = await res.json()
      setSession(prev => prev ? { ...prev, status: 'completed' } : null)
      alert(`Session completed!\nPerson ID: ${data.person_id}\nProjected fields: ${data.projection?.projected_fields}`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }, [session])

  const handleFieldChange = useCallback((slug: string, value: unknown) => {
    setFormData(prev => ({ ...prev, [slug]: value }))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      </div>
    )
  }

  if (!preview) {
    return <div className="text-red-600 p-4">Flow not found</div>
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-gray-900">{preview.flow.name}</h1>
          <Badge variant="outline">{preview.flow.jurisdiction.code}</Badge>
          <Badge className={preview.flow.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}>
            {preview.flow.status}
          </Badge>
        </div>
        <p className="text-sm text-gray-500">
          v{preview.flow.version} — {preview.statistics.total_steps} steps, {preview.statistics.total_screens} screens, {preview.statistics.total_components} components
          {preview.statistics.blocking_steps > 0 && ` (${preview.statistics.blocking_steps} blocking)`}
        </p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-12 gap-6">
        {/* LEFT PANEL: Steps */}
        <div className="col-span-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Steps</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {preview.flow.steps.map(step => {
                const isActive = session?.current_step?.step_key === step.step_key
                const stepState = session?.step_states?.find(s => s.step_id === step.id)

                return (
                  <div
                    key={step.id}
                    className={`p-3 rounded-lg border transition-colors ${
                      isActive
                        ? 'border-blue-400 bg-blue-50'
                        : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium text-gray-900">{step.title}</span>
                      <div className="flex gap-1">
                        {step.is_blocking
                          ? <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-red-300 text-red-600">blocking</Badge>
                          : <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-green-300 text-green-600">optional</Badge>
                        }
                      </div>
                    </div>
                    <div className="text-xs text-gray-500">{step.step_key}</div>
                    {stepState && (
                      <Badge className={`mt-1 text-[10px] ${STEP_STATUS_COLORS[stepState.status] || 'bg-gray-100 text-gray-600'}`}>
                        {stepState.status}
                      </Badge>
                    )}
                    <div className="text-xs text-gray-400 mt-1">
                      {step.screens.length} screen{step.screens.length > 1 ? 's' : ''} —
                      {step.screens.reduce((a, s) => a + s.components.length, 0)} components
                    </div>
                  </div>
                )
              })}

              {!session && (
                <Button onClick={startSession} disabled={submitting} className="w-full mt-3" size="sm">
                  {submitting ? 'Starting...' : 'Start Session'}
                </Button>
              )}

              {session && session.status !== 'completed' && (
                <div className="pt-2 border-t space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-500">Progress</span>
                    <span className="text-xs font-medium">{session.progress_percent}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-1.5">
                    <div
                      className="bg-blue-600 h-1.5 rounded-full transition-all"
                      style={{ width: `${session.progress_percent}%` }}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* RIGHT PANEL: Screen Preview */}
        <div className="col-span-5">
          {!session ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-gray-500 text-sm">Click "Start Session" to begin the flow preview</p>
              </CardContent>
            </Card>
          ) : session.status === 'completed' ? (
            <Card>
              <CardContent className="py-12 text-center">
                <div className="text-4xl mb-3">&#10003;</div>
                <p className="font-medium text-green-700">Session Completed</p>
                <Button onClick={startSession} variant="outline" size="sm" className="mt-4">
                  Start New Session
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg">
                      {session.screen?.title || 'Screen'}
                    </CardTitle>
                    {session.screen?.subtitle && (
                      <p className="text-sm text-gray-500 mt-0.5">{session.screen.subtitle}</p>
                    )}
                  </div>
                  {session.current_step && (
                    <Badge variant="outline" className="text-xs">
                      {session.current_step.step_key}
                    </Badge>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {session.screen?.components.map(comp => (
                  <ComponentPreview
                    key={comp.id}
                    comp={comp}
                    value={formData[comp.binding_slug || '']}
                    onChange={handleFieldChange}
                  />
                ))}

                <div className="flex gap-2 pt-4 border-t">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('prev')}
                    disabled={submitting}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => navigate('next')}
                    disabled={submitting || session.is_last_screen}
                  >
                    Next
                  </Button>
                  <Button
                    size="sm"
                    onClick={submitScreen}
                    disabled={submitting}
                    className="flex-1"
                  >
                    {submitting ? 'Submitting...' : session.is_last_screen ? 'Submit (Last)' : 'Submit & Next'}
                  </Button>
                  {session.is_last_screen && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={completeSession}
                      disabled={submitting}
                      className="bg-green-50 text-green-700 border-green-300 hover:bg-green-100"
                    >
                      Complete
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* DEBUG PANEL */}
        <div className="col-span-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Debug Panel</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 text-xs">
              {session ? (
                <>
                  <div>
                    <span className="font-medium text-gray-700">session_id</span>
                    <pre className="mt-1 p-2 bg-gray-50 rounded text-[11px] break-all">{session.session_id}</pre>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <span className="font-medium text-gray-700">status</span>
                      <pre className="mt-1 p-1.5 bg-gray-50 rounded">{session.status}</pre>
                    </div>
                    <div>
                      <span className="font-medium text-gray-700">flow_version</span>
                      <pre className="mt-1 p-1.5 bg-gray-50 rounded">{session.flow_version}</pre>
                    </div>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">current_step</span>
                    <pre className="mt-1 p-2 bg-gray-50 rounded overflow-auto max-h-24">
                      {JSON.stringify(session.current_step, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">step_states</span>
                    <pre className="mt-1 p-2 bg-gray-50 rounded overflow-auto max-h-32">
                      {JSON.stringify(session.step_states, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">collected_data</span>
                    <pre className="mt-1 p-2 bg-gray-50 rounded overflow-auto max-h-40">
                      {JSON.stringify(session.collected_data, null, 2)}
                    </pre>
                  </div>
                  <div>
                    <span className="font-medium text-gray-700">local form_data</span>
                    <pre className="mt-1 p-2 bg-blue-50 rounded overflow-auto max-h-40">
                      {JSON.stringify(formData, null, 2)}
                    </pre>
                  </div>
                </>
              ) : (
                <p className="text-gray-400">No active session</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
