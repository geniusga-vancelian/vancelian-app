'use client'

import { useEffect, useState, useCallback, useMemo, type ReactNode } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import {
  AlertDialog, AlertDialogContent, AlertDialogHeader, AlertDialogTitle,
  AlertDialogDescription, AlertDialogFooter, AlertDialogCancel, AlertDialogAction,
} from '@/components/ui/alert-dialog'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://127.0.0.1:8000'

const FIELD_BOUND_TYPES = [
  'text_input', 'phone_input', 'select', 'country_picker',
  'date_picker', 'checkbox', 'multi_select',
  'address_autocomplete',
  'address_step',
] as const

const CONTENT_TYPES = [
  'section_title', 'rich_text', 'info_box', 'legal_content',
  'divider', 'spacer', 'bullet_list', 'link_text',
] as const

const LANGS = ['en', 'fr'] as const

type I18nFillLevel = 'complete' | 'partial' | 'missing'

function langFillLevel(i18n: Record<string, string> | null | undefined): I18nFillLevel {
  const vals = LANGS.map(l => (i18n?.[l] || '').trim())
  const n = vals.filter(Boolean).length
  if (n === LANGS.length) return 'complete'
  if (n === 0) return 'missing'
  return 'partial'
}

function I18nBadge({
  level,
  tooltip,
}: {
  level: I18nFillLevel
  tooltip?: string
}) {
  const cls =
    level === 'complete'
      ? 'bg-green-100 text-green-800 border-green-200'
      : level === 'partial'
        ? 'bg-amber-100 text-amber-900 border-amber-200'
        : 'bg-red-50 text-red-700 border-red-200'
  const label = level === 'complete' ? 'i18n ✓' : level === 'partial' ? 'i18n ~' : 'i18n !'
  return (
    <span title={tooltip || label}>
      <Badge variant="outline" className={`text-[9px] px-1 py-0 ${cls}`}>
        {label}
      </Badge>
    </span>
  )
}

function autoKey(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 8)}`
}

interface Flow {
  id: string; name: string; version: number; status: string; entrypoint_type: string
  jurisdiction?: { code: string; name?: string; entity_name?: string | null }
}

interface JurisdictionPolicySummary {
  residence_country_count: number
  phone_country_count: number
  nationality_country_count: number
  default_residence_iso2: string | null
  default_phone_iso2: string | null
  inherit_phone_countries_from_residence: boolean
  has_policy_rows: boolean
}
interface Step {
  id: string; flow_id: string; step_key: string; title: string
  description: string | null; position: number; is_optional: boolean; is_blocking: boolean
  title_i18n: Record<string, string> | null; description_i18n: Record<string, string> | null
  visibility_rule_json?: Record<string, unknown> | null
  completion_rule_json?: Record<string, unknown> | null
}
interface Screen {
  id: string; step_id: string; screen_key: string; title: string
  subtitle: string | null; position: number; layout_type: string
  title_i18n: Record<string, string> | null; subtitle_i18n: Record<string, string> | null
  button_label: string | null; button_label_i18n: Record<string, string> | null
  config?: Record<string, unknown> | null
  screen_type?: string
  interaction_type?: string | null
  interaction_config_json?: Record<string, unknown> | null
  interaction_template_key?: string | null
  interaction_template_display_name?: string | null
}

interface InteractionTemplate {
  template_key: string
  display_name: string
  description: string
  interaction_type: string
  default_title: string
  default_subtitle: string
  default_button_label: string
  default_interaction_config: Record<string, string>
  required_config_fields: string[]
  selectable: boolean
}

interface PermissionPromptTemplate {
  template_key: string
  display_name: string
  description: string
  permission_kind: string
  default_title: string
  default_subtitle: string
  default_button_label: string
  default_config: Record<string, string>
}
interface Component {
  id: string; screen_id: string; component_type: string; component_key: string
  position: number; props: Record<string, unknown>; binding_slug: string | null
  field_definition_id?: string | null
  visibility_rule_json?: Record<string, unknown> | null
  validation_rule_json?: Record<string, unknown> | null
}

function stepI18nSummary(step: Step): { level: I18nFillLevel; tip: string } {
  const t = langFillLevel(step.title_i18n)
  const hasDesc = !!(step.description?.trim() || Object.keys(step.description_i18n || {}).some(k => (step.description_i18n?.[k] || '').trim()))
  const d = hasDesc ? langFillLevel(step.description_i18n) : ('complete' as const)
  const order: I18nFillLevel[] = ['missing', 'partial', 'complete']
  const worst = (a: I18nFillLevel, b: I18nFillLevel) => (order.indexOf(a) < order.indexOf(b) ? a : b)
  const level = worst(t, d)
  const parts: string[] = []
  if (t !== 'complete') parts.push(`title_i18n: ${t}`)
  if (hasDesc && d !== 'complete') parts.push(`description_i18n: ${d}`)
  return { level, tip: parts.length ? parts.join('; ') : 'Step i18n OK (en/fr)' }
}

function screenI18nSummary(screen: Screen): { level: I18nFillLevel; tip: string } {
  const t = langFillLevel(screen.title_i18n)
  const hasSub = !!(screen.subtitle?.trim() || Object.keys(screen.subtitle_i18n || {}).some(k => (screen.subtitle_i18n?.[k] || '').trim()))
  const s = hasSub ? langFillLevel(screen.subtitle_i18n) : ('complete' as const)
  const order: I18nFillLevel[] = ['missing', 'partial', 'complete']
  const worst = (a: I18nFillLevel, b: I18nFillLevel) => (order.indexOf(a) < order.indexOf(b) ? a : b)
  const level = worst(t, s)
  const parts: string[] = []
  if (t !== 'complete') parts.push(`title_i18n: ${t}`)
  if (hasSub && s !== 'complete') parts.push(`subtitle_i18n: ${s}`)
  return { level, tip: parts.length ? parts.join('; ') : 'Screen i18n OK (en/fr)' }
}

function componentI18nSummary(comp: Component): { level: I18nFillLevel; tip: string } {
  const isInput = (FIELD_BOUND_TYPES as readonly string[]).includes(comp.component_type)
  const p = comp.props || {}
  if (isInput) {
    const raw = p.label
    let li: Record<string, string> = {}
    if (raw && typeof raw === 'object' && !Array.isArray(raw)) li = raw as Record<string, string>
    else if (typeof raw === 'string' && raw.trim()) {
      li = (p.label_i18n as Record<string, string>) || {}
    }
    const level = langFillLevel(Object.keys(li).length ? li : (p.label_i18n as Record<string, string>) || {})
    const ph =
      typeof p.placeholder === 'string'
        ? p.placeholder
        : p.placeholder && typeof p.placeholder === 'object'
          ? 'set'
          : ''
    const pl = p.placeholder_i18n as Record<string, string> | undefined
    const phLevel = ph ? langFillLevel(pl) : ('complete' as const)
    const order: I18nFillLevel[] = ['missing', 'partial', 'complete']
    const worst = (a: I18nFillLevel, b: I18nFillLevel) => (order.indexOf(a) < order.indexOf(b) ? a : b)
    return {
      level: worst(level, phLevel),
      tip: `label i18n: ${level}; placeholder i18n: ${ph ? phLevel : 'n/a'}`,
    }
  }
  const labelLv = langFillLevel((p.label_i18n as Record<string, string>) || {})
  const content = (p.content as string) || (p.text as string) || ''
  const ci = (p.content_i18n as Record<string, string>) || (p.text_i18n as Record<string, string>)
  const contentLv = content.trim() ? langFillLevel(ci) : ('complete' as const)
  const order: I18nFillLevel[] = ['missing', 'partial', 'complete']
  const worst = (a: I18nFillLevel, b: I18nFillLevel) => (order.indexOf(a) < order.indexOf(b) ? a : b)
  return { level: worst(labelLv, contentLv), tip: 'content block i18n' }
}

interface HealthIssue {
  level: string; category: string; message: string
  step_id?: string; screen_id?: string; component_id?: string
}

interface FieldCatalogItem {
  id: string; slug: string; slug_snake: string; label: string
  field_type: string; category: string | null
  component_type_default: string | null; required_default: boolean | null
  options: unknown[] | null
}

type StepForm = {
  title: string; description: string
  is_blocking: boolean; is_optional: boolean
  title_i18n: Record<string, string>; description_i18n: Record<string, string>
  visibility_rule_json: Record<string, unknown> | null
  completion_rule_json: Record<string, unknown> | null
}

/** Champs affichés sur l’écran Home address (mobile) — pas le pays, collecté en amont. */
const ADDRESS_STEP_HOME_FIELD_KEYS = [
  'address_line_1',
  'address_line_2',
  'postal_code',
  'city',
] as const
type AddressStepHomeFieldKey = (typeof ADDRESS_STEP_HOME_FIELD_KEYS)[number]

const BUILDER_PRESET_COUNTRY_RESIDENCE = 'country_of_residence' as const

type CompForm = {
  component_type: string; binding_slug: string
  label: string; required: boolean; placeholder: string; options: string
  description: string; link_label: string; link_url: string
  label_i18n: Record<string, string>; placeholder_i18n: Record<string, string>
  description_i18n: Record<string, string>; link_label_i18n: Record<string, string>
  visibility_rule_json: Record<string, unknown> | null
  validation_rule_json: Record<string, unknown> | null
  /** address_step composite (i18n + champs) */
  address_step_title_i18n: Record<string, string>
  address_step_subtitle_i18n: Record<string, string>
  address_step_search_label_i18n: Record<string, string>
  address_step_manual_label_i18n: Record<string, string>
  address_step_field_labels_i18n: Record<AddressStepHomeFieldKey, Record<string, string>>
  address_step_field_placeholders_i18n: Record<AddressStepHomeFieldKey, Record<string, string>>
  address_step_search_enabled: boolean
  address_step_search_min_chars: string
  address_step_search_debounce_ms: string
  address_step_line2_optional: boolean
}

const emptyStep = (): StepForm => ({
  title: '', description: '', is_blocking: true, is_optional: false,
  title_i18n: {}, description_i18n: {},
  visibility_rule_json: null, completion_rule_json: null,
})
const emptyComp = (): CompForm => ({
  component_type: 'text_input', binding_slug: '',
  label: '', required: false, placeholder: '', options: '[]',
  description: '', link_label: '', link_url: '',
  label_i18n: {}, placeholder_i18n: {}, description_i18n: {}, link_label_i18n: {},
  visibility_rule_json: null,
  validation_rule_json: null,
  address_step_title_i18n: {},
  address_step_subtitle_i18n: {},
  address_step_search_label_i18n: {},
  address_step_manual_label_i18n: {},
  address_step_field_labels_i18n: {
    address_line_1: {},
    address_line_2: {},
    postal_code: {},
    city: {},
  },
  address_step_field_placeholders_i18n: {
    address_line_1: {},
    address_line_2: {},
    postal_code: {},
    city: {},
  },
  address_step_search_enabled: true,
  address_step_search_min_chars: '2',
  address_step_search_debounce_ms: '300',
  address_step_line2_optional: true,
})

const RULE_OPERATORS = [
  { value: 'equals', label: 'equals' },
  { value: 'not_equals', label: 'not equals' },
  { value: 'in', label: 'in (list)' },
  { value: 'not_in', label: 'not in (list)' },
  { value: 'exists', label: 'exists' },
  { value: 'not_exists', label: 'does not exist' },
] as const

function RuleEditor({ label, value, onChange }: {
  label: string
  value: Record<string, unknown> | null | undefined
  onChange: (v: Record<string, unknown> | null) => void
}) {
  const [mode, setMode] = useState<'simple' | 'json'>(
    value && (value.operator === 'all_of' || value.operator === 'any_of') ? 'json' : 'simple'
  )
  const [jsonText, setJsonText] = useState(value ? JSON.stringify(value, null, 2) : '')
  const [jsonError, setJsonError] = useState('')

  const rule = value || {}
  const field = (rule.field as string) || ''
  const operator = (rule.operator as string) || 'equals'
  const ruleValue = rule.value ?? rule.values ?? ''

  const cls = 'w-full px-2 py-1 border border-gray-300 rounded text-xs focus:ring-1 focus:ring-blue-500'

  const summary = useMemo(() => {
    if (!value || Object.keys(value).length === 0) return null
    const op = (value.operator as string) || 'equals'
    const f = (value.field as string) || '?'
    if (op === 'all_of' || op === 'any_of') {
      const sub = (value.rules as unknown[]) || []
      return `${op}(${sub.length} rules)`
    }
    if (op === 'exists' || op === 'not_exists') return `${f} ${op}`
    if (op === 'in' || op === 'not_in') {
      const v = value.values ?? value.value
      const disp = Array.isArray(v) ? `[${v.join(', ')}]` : JSON.stringify(v)
      return `${f} ${op} ${disp}`
    }
    const v = value.value ?? value.values
    return `${f} ${op} ${JSON.stringify(v)}`
  }, [value])

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-gray-600">{label}</span>
        <div className="flex gap-1">
          <button className={`px-1.5 py-0.5 text-[10px] rounded ${mode === 'simple' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
            onClick={() => setMode('simple')}>Simple</button>
          <button className={`px-1.5 py-0.5 text-[10px] rounded ${mode === 'json' ? 'bg-blue-600 text-white' : 'bg-gray-100'}`}
            onClick={() => { setMode('json'); setJsonText(value ? JSON.stringify(value, null, 2) : ''); setJsonError('') }}>JSON</button>
          {value && Object.keys(value).length > 0 && (
            <button className="px-1.5 py-0.5 text-[10px] rounded bg-red-50 text-red-600"
              onClick={() => onChange(null)}>Clear</button>
          )}
        </div>
      </div>
      {summary && <p className="text-[10px] text-indigo-600 italic">→ {summary}</p>}
      {mode === 'simple' ? (
        <div className="flex gap-1">
          <input className={cls + ' flex-1'} placeholder="field" value={field}
            onChange={e => onChange({ ...rule, field: e.target.value })} />
          <select className={cls + ' w-28'} value={operator}
            onChange={e => onChange({ ...rule, operator: e.target.value })}>
            {RULE_OPERATORS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          {!['exists', 'not_exists'].includes(operator) && (
            <input className={cls + ' flex-1'} placeholder="value"
              value={typeof ruleValue === 'string' ? ruleValue : JSON.stringify(ruleValue)}
              onChange={e => {
                let v: unknown = e.target.value
                try { v = JSON.parse(e.target.value) } catch { /* keep string */ }
                const key = ['in', 'not_in'].includes(operator) ? 'values' : 'value'
                const next = { ...rule, [key]: v }
                delete next[key === 'values' ? 'value' : 'values']
                onChange(next as Record<string, unknown>)
              }} />
          )}
        </div>
      ) : (
        <div>
          <textarea className={cls + ' h-20 font-mono'} value={jsonText}
            onChange={e => {
              setJsonText(e.target.value)
              if (!e.target.value.trim()) { onChange(null); setJsonError(''); return }
              try {
                const parsed = JSON.parse(e.target.value)
                onChange(parsed)
                setJsonError('')
              } catch { setJsonError('Invalid JSON') }
            }} />
          {jsonError && <p className="text-[10px] text-red-500">{jsonError}</p>}
        </div>
      )}
    </div>
  )
}

function I18nField({ label, value, onChange, multiline = false }: {
  label: string
  value: Record<string, string>
  onChange: (v: Record<string, string>) => void
  multiline?: boolean
}) {
  const cls = 'w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
  return (
    <div className="space-y-1">
      <span className="text-xs font-medium text-gray-600">{label} (i18n)</span>
      <div className="flex gap-1">
        {LANGS.map(lang => (
          <div key={lang} className="flex-1">
            <span className="text-[10px] text-gray-400 uppercase">{lang}</span>
            {multiline ? (
              <textarea className={cls + ' h-16'} placeholder={`${label} (${lang})`}
                value={value[lang] || ''} onChange={e => onChange({ ...value, [lang]: e.target.value })} />
            ) : (
              <input className={cls} placeholder={`${label} (${lang})`}
                value={value[lang] || ''} onChange={e => onChange({ ...value, [lang]: e.target.value })} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function cleanI18n(obj: Record<string, string>): Record<string, string> | null {
  const filtered = Object.fromEntries(Object.entries(obj).filter(([, v]) => v.trim() !== ''))
  return Object.keys(filtered).length > 0 ? filtered : null
}

/** Lit un objet i18n depuis la config écran (API JSON). */
function asStringRecord(v: unknown): Record<string, string> {
  if (!v || typeof v !== 'object' || Array.isArray(v)) return {}
  const out: Record<string, string> = {}
  for (const [k, val] of Object.entries(v)) {
    if (typeof val === 'string') out[k] = val
  }
  return out
}

const ADDRESS_STEP_I18N_DEFAULTS: Pick<
  CompForm,
  | 'address_step_title_i18n'
  | 'address_step_subtitle_i18n'
  | 'address_step_search_label_i18n'
  | 'address_step_manual_label_i18n'
  | 'address_step_field_labels_i18n'
  | 'address_step_field_placeholders_i18n'
> = {
  address_step_title_i18n: { en: 'Home address', fr: 'Adresse du domicile' },
  address_step_subtitle_i18n: {
    en: 'Please enter your home address exactly as it appears on your identity document.',
    fr: 'Indiquez votre adresse telle qu’elle figure sur votre pièce d’identité.',
  },
  address_step_search_label_i18n: { en: 'Search address', fr: 'Rechercher une adresse' },
  address_step_manual_label_i18n: { en: 'My address is not here', fr: 'Mon adresse ne figure pas ici' },
  address_step_field_labels_i18n: {
    address_line_1: { en: 'Street name, building', fr: 'Rue, numéro, bâtiment' },
    address_line_2: { en: 'Floor, unit number', fr: 'Étage, appartement' },
    postal_code: { en: 'Postal code', fr: 'Code postal' },
    city: { en: 'Town / City', fr: 'Ville' },
  },
  address_step_field_placeholders_i18n: {
    address_line_1: { en: 'e.g. 10 Downing Street', fr: 'ex. 10 rue de Rivoli' },
    address_line_2: { en: 'e.g. Apt 4B', fr: 'ex. Appartement 4B' },
    postal_code: { en: 'e.g. 75001', fr: 'ex. 75001' },
    city: { en: 'e.g. Paris', fr: 'ex. Paris' },
  },
}

function mergeFlatI18nFromProps(
  p: Record<string, unknown>,
  i18nKey: string,
  legacyKey: string,
): Record<string, string> {
  const ti = asStringRecord(p[i18nKey])
  if (Object.keys(ti).length > 0) return ti
  const leg = p[legacyKey]
  if (typeof leg === 'string' && leg.trim())
    return { en: leg.trim(), fr: leg.trim() }
  return {}
}

function readAddressStepFieldMap(raw: unknown): Record<AddressStepHomeFieldKey, Record<string, string>> {
  const base: Record<AddressStepHomeFieldKey, Record<string, string>> = {
    address_line_1: {},
    address_line_2: {},
    postal_code: {},
    city: {},
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return base
  const o = raw as Record<string, unknown>
  for (const fk of ADDRESS_STEP_HOME_FIELD_KEYS) {
    const entry = o[fk]
    if (typeof entry === 'string' && entry.trim()) {
      const t = entry.trim()
      base[fk] = { en: t, fr: t }
    } else if (entry && typeof entry === 'object' && !Array.isArray(entry)) {
      base[fk] = asStringRecord(entry)
    }
  }
  return base
}

function cleanFieldLabelsMap(
  m: Record<AddressStepHomeFieldKey, Record<string, string>>,
): Record<string, Record<string, string>> | null {
  const out: Record<string, Record<string, string>> = {}
  for (const fk of ADDRESS_STEP_HOME_FIELD_KEYS) {
    const c = cleanI18n(m[fk] || {})
    if (c) out[fk] = c
  }
  return Object.keys(out).length > 0 ? out : null
}

function legacyStringFromI18n(i18n: Record<string, string>): string | undefined {
  const c = cleanI18n(i18n)
  if (!c) return undefined
  const v = (c.en || c.fr || Object.values(c)[0])?.trim()
  return v || undefined
}

/** Props `props_json` pour `address_step` — même logique que l’enregistrement manuel du composant. */
function buildAddressStepPropsJson(compForm: CompForm): Record<string, unknown> {
  const minC = parseInt(compForm.address_step_search_min_chars || '2', 10)
  const deb = parseInt(compForm.address_step_search_debounce_ms || '300', 10)
  const propsJson: Record<string, unknown> = {}
  const ti = cleanI18n(compForm.address_step_title_i18n)
  if (ti) propsJson.title_i18n = ti
  const lt = legacyStringFromI18n(compForm.address_step_title_i18n)
  if (lt) propsJson.title = lt
  const si = cleanI18n(compForm.address_step_subtitle_i18n)
  if (si) propsJson.subtitle_i18n = si
  const ls = legacyStringFromI18n(compForm.address_step_subtitle_i18n)
  if (ls) propsJson.subtitle = ls
  const sli = cleanI18n(compForm.address_step_search_label_i18n)
  if (sli) propsJson.search_label_i18n = sli
  const lsq = legacyStringFromI18n(compForm.address_step_search_label_i18n)
  if (lsq) propsJson.search_label = lsq
  const mei = cleanI18n(compForm.address_step_manual_label_i18n)
  if (mei) propsJson.manual_entry_label_i18n = mei
  const lme = legacyStringFromI18n(compForm.address_step_manual_label_i18n)
  if (lme) propsJson.manual_entry_label = lme
  const fl = cleanFieldLabelsMap(compForm.address_step_field_labels_i18n)
  if (fl) propsJson.field_labels_i18n = fl
  const fp = cleanFieldLabelsMap(compForm.address_step_field_placeholders_i18n)
  if (fp) propsJson.field_placeholders_i18n = fp
  propsJson.search_enabled = compForm.address_step_search_enabled
  propsJson.search_min_chars = Number.isFinite(minC) ? Math.min(20, Math.max(1, minC)) : 2
  propsJson.search_debounce_ms = Number.isFinite(deb) ? Math.min(5000, Math.max(50, deb)) : 300
  propsJson.address_line_2_optional = compForm.address_step_line2_optional
  propsJson.binding_slugs = {
    postal_code: 'postal_code',
    address_line_1: 'address_line_1',
    address_line_2: 'address_line_2',
    city: 'city',
    country_of_residence: 'country_of_residence',
  }
  propsJson.store_place_id = true
  propsJson.metadata_slug = 'address_metadata'
  return propsJson
}

function fieldCatalogItemForAddressLine1(catalog: FieldCatalogItem[]): FieldCatalogItem | undefined {
  return catalog.find(
    x =>
      x.slug_snake.replace(/-/g, '_') === 'address_line_1' ||
      x.slug.replace(/-/g, '_') === 'address_line_1',
  )
}

function fieldCatalogItemForCountryResidence(catalog: FieldCatalogItem[]): FieldCatalogItem | undefined {
  return catalog.find(
    x =>
      x.slug_snake.replace(/-/g, '_') === 'country_of_residence' ||
      x.slug.replace(/-/g, '_') === 'country_of_residence',
  )
}

/** Écran formulaire créé via le bouton + Address (admin uniquement). */
function screenIsAddressPreset(screen: Screen): boolean {
  const st = (screen.screen_type || 'form').trim()
  if (st !== 'form') return false
  const cfg = screen.config
  if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) return false
  return (cfg as { builder_preset?: string }).builder_preset === 'address_step'
}

/** Écran « pays de résidence » (+ Country). */
function screenIsCountryResidencePreset(screen: Screen): boolean {
  const st = (screen.screen_type || 'form').trim()
  if (st !== 'form') return false
  const cfg = screen.config
  if (!cfg || typeof cfg !== 'object' || Array.isArray(cfg)) return false
  return (cfg as { builder_preset?: string }).builder_preset === BUILDER_PRESET_COUNTRY_RESIDENCE
}

/**
 * Titre de l’écran dans la liste / en-tête éditeur (distinct du titre affiché dans le widget mobile).
 */
const ADDRESS_STEP_SCREEN_LIST_TITLE_I18N: Record<string, string> = {
  en: 'Home address',
  fr: 'Adresse du domicile',
}

const COUNTRY_RESIDENCE_SCREEN_LIST_TITLE_I18N: Record<string, string> = {
  en: 'Country of residence',
  fr: 'Pays de résidence',
}

/** Construit un [CompForm] pour l’aperçu à partir d’un composant `address_step` persisté. */
function addressStepPreviewFormFromComponent(comp: Component): CompForm | null {
  if (comp.component_type !== 'address_step') return null
  const p = comp.props || {}
  const labelVal = p.label
  return {
    ...emptyComp(),
    component_type: 'address_step',
    binding_slug: comp.binding_slug || '',
    label: typeof labelVal === 'string' ? labelVal : '',
    required: !!p.required,
    placeholder: '',
    options: '[]',
    description: '',
    link_label: '',
    link_url: '',
    label_i18n: {},
    placeholder_i18n: {},
    description_i18n: {},
    link_label_i18n: {},
    visibility_rule_json: comp.visibility_rule_json || null,
    validation_rule_json: comp.validation_rule_json || null,
    address_step_title_i18n: mergeFlatI18nFromProps(p as Record<string, unknown>, 'title_i18n', 'title'),
    address_step_subtitle_i18n: mergeFlatI18nFromProps(p as Record<string, unknown>, 'subtitle_i18n', 'subtitle'),
    address_step_search_label_i18n: mergeFlatI18nFromProps(
      p as Record<string, unknown>,
      'search_label_i18n',
      'search_label',
    ),
    address_step_manual_label_i18n: mergeFlatI18nFromProps(
      p as Record<string, unknown>,
      'manual_entry_label_i18n',
      'manual_entry_label',
    ),
    address_step_field_labels_i18n: readAddressStepFieldMap(p.field_labels_i18n),
    address_step_field_placeholders_i18n: readAddressStepFieldMap(p.field_placeholders_i18n),
    address_step_search_enabled: p.search_enabled !== false,
    address_step_search_min_chars:
      typeof p.search_min_chars === 'number' ? String(p.search_min_chars) : '2',
    address_step_search_debounce_ms:
      typeof p.search_debounce_ms === 'number' ? String(p.search_debounce_ms) : '300',
    address_step_line2_optional: p.address_line_2_optional !== false,
  }
}

// ─── address_step admin preview (static mobile mock) ─────────────────────

function pickPreviewI18n(m: Record<string, string> | undefined, langs: string[]): string {
  if (!m) return ''
  for (const L of langs) {
    const v = m[L]?.trim()
    if (v) return v
  }
  const f = Object.values(m).find(x => typeof x === 'string' && x.trim())
  return (f as string)?.trim() || ''
}

const ADDRESS_STEP_PREVIEW_FALLBACKS: Record<AddressStepHomeFieldKey | 'search' | 'manual', string> = {
  search: 'Search address',
  manual: 'My address is not here',
  address_line_1: 'Street, building',
  address_line_2: 'Floor, unit',
  postal_code: 'Postal code',
  city: 'City',
}

function formatPreviewFieldLabel(base: string, required: boolean): string {
  const t = base.replace(/\s*\*$/u, '').trim()
  if (!required) return t
  return t.endsWith('*') ? t : `${t} *`
}

type AddressStepPreviewField = {
  key: AddressStepHomeFieldKey
  label: string
  placeholder: string
  required: boolean
}

function buildAddressStepPreviewModel(
  form: CompForm,
  langs: string[],
): {
  title: string
  subtitle: string
  searchLabel: string
  manualLabel: string
  searchEnabled: boolean
  line2Optional: boolean
  fields: AddressStepPreviewField[]
} {
  const title = pickPreviewI18n(form.address_step_title_i18n, langs)
  const subtitle = pickPreviewI18n(form.address_step_subtitle_i18n, langs)
  const searchLabel =
    pickPreviewI18n(form.address_step_search_label_i18n, langs) ||
    ADDRESS_STEP_PREVIEW_FALLBACKS.search
  const manualLabel =
    pickPreviewI18n(form.address_step_manual_label_i18n, langs) ||
    ADDRESS_STEP_PREVIEW_FALLBACKS.manual
  const line2Opt = form.address_step_line2_optional !== false
  const searchEnabled = form.address_step_search_enabled !== false

  const labelFor = (fk: AddressStepHomeFieldKey, fallback: string, required: boolean) => {
    const custom = pickPreviewI18n(form.address_step_field_labels_i18n[fk], langs)
    return formatPreviewFieldLabel(custom || fallback, required)
  }
  const phFor = (fk: AddressStepHomeFieldKey) =>
    pickPreviewI18n(form.address_step_field_placeholders_i18n[fk], langs)

  const line2Fallback = line2Opt
    ? `${ADDRESS_STEP_PREVIEW_FALLBACKS.address_line_2} (optional)`
    : ADDRESS_STEP_PREVIEW_FALLBACKS.address_line_2

  const fields: AddressStepPreviewField[] = [
    {
      key: 'address_line_1',
      label: labelFor('address_line_1', ADDRESS_STEP_PREVIEW_FALLBACKS.address_line_1, true),
      placeholder: phFor('address_line_1'),
      required: true,
    },
    {
      key: 'address_line_2',
      label: labelFor('address_line_2', line2Fallback, !line2Opt),
      placeholder: phFor('address_line_2'),
      required: !line2Opt,
    },
    {
      key: 'postal_code',
      label: labelFor('postal_code', ADDRESS_STEP_PREVIEW_FALLBACKS.postal_code, true),
      placeholder: phFor('postal_code'),
      required: true,
    },
    {
      key: 'city',
      label: labelFor('city', ADDRESS_STEP_PREVIEW_FALLBACKS.city, true),
      placeholder: phFor('city'),
      required: true,
    },
  ]

  return {
    title,
    subtitle,
    searchLabel,
    manualLabel,
    searchEnabled,
    line2Optional: line2Opt,
    fields,
  }
}

function AddressStepPreviewPanel({ form }: { form: CompForm }) {
  const [navLang, setNavLang] = useState('en')
  useEffect(() => {
    setNavLang(typeof navigator !== 'undefined' ? navigator.language : 'en')
  }, [])

  const localeChain = useMemo(() => {
    const b = navLang.split('-')[0].toLowerCase()
    return [...new Set([b, 'en', 'fr'])]
  }, [navLang])

  const model = useMemo(
    () => buildAddressStepPreviewModel(form, localeChain),
    [form, localeChain],
  )

  const mockFieldShell = (trailing?: ReactNode) => (
    <div className="flex min-h-[56px] items-center justify-between rounded-2xl border-[1.5px] border-white bg-white px-4 py-2 shadow-sm">
      <span className="text-[17px] font-semibold text-slate-200">—</span>
      {trailing}
    </div>
  )

  return (
    <div className="mt-4 border-t border-indigo-200 pt-4">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-indigo-900">
        Aperçu mobile (statique)
      </p>
      <p className="mt-1 text-[10px] leading-snug text-indigo-800/85">
        Pas d’appel réseau. Résolution i18n :{' '}
        <span className="font-mono">{localeChain.join(' → ')}</span>
        <span className="text-slate-500"> (navigateur : {navLang})</span>
      </p>
      <div className="mx-auto mt-3 max-w-[min(100%,360px)] rounded-[28px] border border-slate-200/90 bg-[#F2F2F7] p-4 shadow-inner">
        {model.title ? (
          <h3 className="text-[22px] font-bold leading-tight tracking-tight text-slate-900">
            {model.title}
          </h3>
        ) : null}
        {model.subtitle ? (
          <p className="mt-2 text-[15px] font-normal leading-snug text-slate-500">{model.subtitle}</p>
        ) : null}
        {(model.title || model.subtitle) && <div className="h-5" />}

        <p className="mb-2 rounded-lg bg-slate-100/90 px-2 py-1.5 text-[10px] leading-snug text-slate-600">
          Pays de résidence : écran précédent (non affiché ici). La recherche utilise ce pays.
        </p>

        {model.searchEnabled ? (
          <>
            <p className="mb-2 text-[13px] font-semibold text-slate-800">{model.searchLabel}</p>
            <div className="flex items-center gap-2.5 rounded-[14px] border border-slate-300/50 bg-white/90 px-3.5 py-3 shadow-sm">
              <svg
                className="h-[18px] w-[18px] shrink-0 text-slate-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden
              >
                <circle cx="11" cy="11" r="7" />
                <path d="M20 20l-4-4" strokeLinecap="round" />
              </svg>
              <span className="text-[15px] text-slate-400">{model.searchLabel}</span>
            </div>
            <button
              type="button"
              tabIndex={-1}
              className="mt-2 w-full cursor-default py-2 text-left text-[14px] font-semibold text-indigo-600"
            >
              {model.manualLabel}
            </button>
            <div className="h-4" />
          </>
        ) : null}

        {model.fields.map(f => (
          <div key={f.key} className="mb-3">
            <span className="mb-1.5 block px-1 text-[11px] font-semibold text-[#8E8E93]">
              {f.label}
            </span>
            {mockFieldShell()}
            {f.placeholder.trim() ? (
              <p className="mt-1 pl-1 text-[13px] text-[#808080]">{f.placeholder}</p>
            ) : null}
          </div>
        ))}

        <p className="mt-2 text-center text-[10px] text-slate-400">
          Continue (bouton fixe du flux — non inclus ici)
        </p>
      </div>
    </div>
  )
}

export default function FlowEditorPage() {
  const params = useParams()
  const flowId = (params?.id as string | undefined) ?? ''

  const [flow, setFlow] = useState<Flow | null>(null)
  const [steps, setSteps] = useState<Step[]>([])
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null)
  const [screens, setScreens] = useState<Screen[]>([])
  const [selectedScreenId, setSelectedScreenId] = useState<string | null>(null)
  const [components, setComponents] = useState<Component[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [stepForm, setStepForm] = useState<StepForm>(emptyStep())
  const [editingStepId, setEditingStepId] = useState<string | null>(null)
  const [showStepForm, setShowStepForm] = useState(false)

  // Screen structure state (right panel)
  const [headerTitle, setHeaderTitle] = useState('')
  const [headerTitleI18n, setHeaderTitleI18n] = useState<Record<string, string>>({})
  const [headerSubtitle, setHeaderSubtitle] = useState('')
  const [headerSubtitleI18n, setHeaderSubtitleI18n] = useState<Record<string, string>>({})
  const [buttonLabel, setButtonLabel] = useState('')
  const [buttonLabelI18n, setButtonLabelI18n] = useState<Record<string, string>>({})

  const [screenType, setScreenType] = useState<'form' | 'interaction' | 'permission_prompt'>('form')
  const [interactionType, setInteractionType] = useState('phone_verification_sms')
  const [icSourceSlug, setIcSourceSlug] = useState('phone_number')
  const [icVerifiedFlagSlug, setIcVerifiedFlagSlug] = useState('phone_verified')
  const [icPurpose, setIcPurpose] = useState('verify_phone')
  const [interactionBizTemplate, setInteractionBizTemplate] = useState<string>('custom')
  const [interactionTemplates, setInteractionTemplates] = useState<InteractionTemplate[]>([])
  const [permissionPromptTemplates, setPermissionPromptTemplates] = useState<PermissionPromptTemplate[]>([])
  const [permissionBizTemplate, setPermissionBizTemplate] = useState<string>('custom')
  const [permissionKind, setPermissionKind] = useState('face_id')
  const [permissionDecisionSlug, setPermissionDecisionSlug] = useState('face_id_enabled')
  const [permissionSecondaryLabel, setPermissionSecondaryLabel] = useState('Not Now')
  /** Écrans « form » : modale de confirmation du numéro sur l’app mobile (config.phone_confirm_modal_*). */
  const [phoneConfirmModalEnabled, setPhoneConfirmModalEnabled] = useState(true)
  const [phoneModalTitleI18n, setPhoneModalTitleI18n] = useState<Record<string, string>>({})
  const [phoneModalDescriptionI18n, setPhoneModalDescriptionI18n] = useState<Record<string, string>>({})
  const [phoneModalConfirmI18n, setPhoneModalConfirmI18n] = useState<Record<string, string>>({})
  const [phoneModalBackI18n, setPhoneModalBackI18n] = useState<Record<string, string>>({})

  const [compForm, setCompForm] = useState<CompForm>(emptyComp())
  const [editingCompId, setEditingCompId] = useState<string | null>(null)
  const [showCompForm, setShowCompForm] = useState(false)

  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean; title: string; description: string; confirmLabel: string; onConfirm: () => void
  }>({ open: false, title: '', description: '', confirmLabel: 'Delete', onConfirm: () => {} })

  const askConfirm = useCallback((
    title: string,
    description: string,
    onConfirm: () => void,
    confirmLabel = 'Delete',
  ) => {
    setConfirmDialog({ open: true, title, description, confirmLabel, onConfirm })
  }, [])

  const [publishOpen, setPublishOpen] = useState(false)
  const [publishByName, setPublishByName] = useState('')
  const [publishSuccess, setPublishSuccess] = useState<string | null>(null)

  // ─── Field Catalog (state only — callbacks defined after api) ─
  const [fieldCatalog, setFieldCatalog] = useState<FieldCatalogItem[]>([])
  const [compMode, setCompMode] = useState<'content' | 'client_field'>('client_field')

  // ─── Health & Publish (state only — callbacks defined after api) ─
  const [health, setHealth] = useState<{
    can_publish: boolean; errors: HealthIssue[]; warnings: HealthIssue[]
    error_count: number; warning_count: number
  } | null>(null)
  const [showHealth, setShowHealth] = useState(false)
  const [publishing, setPublishing] = useState(false)
  const [jurisdictionPolicy, setJurisdictionPolicy] = useState<JurisdictionPolicySummary | null>(null)

  const inputCls = 'w-full px-2.5 py-1.5 border border-gray-300 rounded text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500'

  const api = useCallback(async (url: string, opts?: RequestInit) => {
    const res = await fetch(`${BACKEND}${url}`, {
      headers: { 'Content-Type': 'application/json' }, ...opts,
    })
    if (opts?.method === 'DELETE' && res.status === 204) return null
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }))
      let msg = 'Request failed'
      if (typeof err.detail === 'string') msg = err.detail
      else if (Array.isArray(err.detail))
        msg = err.detail.map((e: { loc?: string[]; msg?: string }) =>
          `${(e.loc || []).slice(-1).join('.')}: ${e.msg || 'invalid'}`
        ).join(' | ')
      throw new Error(msg)
    }
    return res.json()
  }, [])

  // ─── Data loading ─────────────────────────────────────────────

  const loadFlow = useCallback(async () => {
    try {
      const [f, s] = await Promise.all([
        api(`/api/admin/registration/flows/${flowId}`),
        api(`/api/admin/registration/flows/${flowId}/steps`),
      ])
      setFlow(f); setSteps(s); setLoading(false)
    } catch (e) { setError((e as Error).message); setLoading(false) }
  }, [flowId, api])

  useEffect(() => { loadFlow() }, [loadFlow])

  useEffect(() => {
    const c = flow?.jurisdiction?.code
    if (!c) {
      setJurisdictionPolicy(null)
      return
    }
    fetch(`${BACKEND}/api/admin/jurisdiction-policies/${encodeURIComponent(c)}`)
      .then(r => (r.ok ? r.json() : null))
      .then((d: { summary?: JurisdictionPolicySummary } | null) => {
        setJurisdictionPolicy(d?.summary ?? null)
      })
      .catch(() => setJurisdictionPolicy(null))
  }, [flow?.jurisdiction?.code])

  // ─── Health & Publish callbacks ─────────────────────────────
  const loadHealth = useCallback(async () => {
    try {
      const h = await api(`/api/admin/registration/flows/${flowId}/health`)
      setHealth(h)
    } catch { /* ignore */ }
  }, [flowId, api])

  const runPublish = useCallback(async () => {
    const name = publishByName.trim()
    if (!name) return
    setPublishing(true)
    setPublishSuccess(null)
    try {
      const result = await api(`/api/admin/registration/flows/${flowId}/publish`, {
        method: 'POST', body: JSON.stringify({ published_by: name }),
      })
      setFlow(result)
      setPublishOpen(false)
      setPublishByName('')
      setPublishSuccess(`Published as v${result.version} by ${name}.`)
      await loadHealth()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setPublishing(false)
    }
  }, [flowId, api, loadHealth, publishByName])

  const archiveFlow = useCallback(async () => {
    askConfirm(
      'Archive flow',
      'This will set the flow to archived and it will no longer be the active version for new sessions. Continue?',
      async () => {
        try {
          const result = await api(`/api/admin/registration/flows/${flowId}/archive`, { method: 'POST' })
          setFlow(result)
          setPublishSuccess('Flow archived.')
        } catch (e) {
          setError((e as Error).message)
        }
      },
      'Archive',
    )
  }, [flowId, api, askConfirm])

  useEffect(() => {
    fetch(`${BACKEND}/api/admin/registration/field-definitions/catalog`)
      .then(r => r.json())
      .then(setFieldCatalog)
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch(`${BACKEND}/api/admin/registration/interaction-templates`)
      .then(r => r.json())
      .then((rows: InteractionTemplate[]) => {
        if (Array.isArray(rows)) setInteractionTemplates(rows)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetch(`${BACKEND}/api/admin/registration/permission-prompt-templates`)
      .then(r => r.json())
      .then((rows: PermissionPromptTemplate[]) => {
        if (Array.isArray(rows)) setPermissionPromptTemplates(rows)
      })
      .catch(() => {})
  }, [])

  useEffect(() => { loadHealth() }, [loadHealth])

  const applyFieldDef = useCallback((fd: FieldCatalogItem) => {
    setCompForm(f => ({
      ...f,
      binding_slug: fd.slug_snake,
      component_type: fd.component_type_default || f.component_type,
      label: fd.label,
      required: fd.required_default ?? false,
      options: fd.options ? JSON.stringify(fd.options, null, 2) : f.options,
      _field_definition_id: fd.id,
    } as CompForm & { _field_definition_id?: string }))
  }, [])

  const loadScreens = useCallback(async (stepId: string) => {
    try { setScreens(await api(`/api/admin/registration/steps/${stepId}/screens`)) }
    catch (e) { setError((e as Error).message) }
  }, [api])

  const loadComponents = useCallback(async (screenId: string) => {
    try { setComponents(await api(`/api/admin/registration/screens/${screenId}/components`)) }
    catch (e) { setError((e as Error).message) }
  }, [api])

  const populateScreenStructure = useCallback((screen: Screen) => {
    setHeaderTitle(screen.title || '')
    setHeaderTitleI18n(screen.title_i18n || {})
    setHeaderSubtitle(screen.subtitle || '')
    setHeaderSubtitleI18n(screen.subtitle_i18n || {})
    setButtonLabel(screen.button_label || '')
    setButtonLabelI18n(screen.button_label_i18n || {})
    const rawSt = (screen.screen_type || 'form').trim()
    if (rawSt === 'permission_prompt') {
      setScreenType('permission_prompt')
      setInteractionBizTemplate('custom')
      const pcfg =
        screen.config && typeof screen.config === 'object' && !Array.isArray(screen.config)
          ? (screen.config as Record<string, unknown>)
          : {}
      const pk = String(pcfg.permission_kind || 'face_id')
      setPermissionKind(pk)
      setPermissionDecisionSlug(String(pcfg.decision_slug || ''))
      setPermissionSecondaryLabel(String(pcfg.secondary_button_label || 'Not Now'))
      const tpl = permissionPromptTemplates.find(x => x.permission_kind === pk)
      setPermissionBizTemplate(tpl?.template_key || 'custom')
    } else if (rawSt === 'interaction') {
      setScreenType('interaction')
      setPermissionBizTemplate('custom')
      setInteractionType(screen.interaction_type || 'phone_verification_sms')
      const icj = screen.interaction_config_json
      if (icj && typeof icj === 'object') {
        setIcSourceSlug(String(icj.source_field_slug || 'phone_number'))
        setIcVerifiedFlagSlug(String(icj.verified_flag_slug || 'phone_verified'))
        setIcPurpose(String(icj.purpose || 'verify_phone'))
      } else {
        setIcSourceSlug('phone_number')
        setIcVerifiedFlagSlug('phone_verified')
        setIcPurpose('verify_phone')
      }
      if (screen.interaction_template_key) {
        setInteractionBizTemplate(screen.interaction_template_key)
      } else {
        setInteractionBizTemplate('custom')
      }
    } else {
      setScreenType('form')
      setPermissionBizTemplate('custom')
      setInteractionBizTemplate('custom')
      setInteractionType(screen.interaction_type || 'phone_verification_sms')
      const icj = screen.interaction_config_json
      if (icj && typeof icj === 'object') {
        setIcSourceSlug(String(icj.source_field_slug || 'phone_number'))
        setIcVerifiedFlagSlug(String(icj.verified_flag_slug || 'phone_verified'))
        setIcPurpose(String(icj.purpose || 'verify_phone'))
      } else {
        setIcSourceSlug('phone_number')
        setIcVerifiedFlagSlug('phone_verified')
        setIcPurpose('verify_phone')
      }
    }
    const cfg = screen.config
    if (cfg && typeof cfg === 'object' && !Array.isArray(cfg) && typeof cfg.phone_confirm_modal_enabled === 'boolean') {
      setPhoneConfirmModalEnabled(cfg.phone_confirm_modal_enabled)
    } else {
      setPhoneConfirmModalEnabled(true)
    }
    if (cfg && typeof cfg === 'object' && !Array.isArray(cfg)) {
      setPhoneModalTitleI18n(asStringRecord(cfg.phone_confirm_modal_title_i18n))
      setPhoneModalDescriptionI18n(asStringRecord(cfg.phone_confirm_modal_description_i18n))
      setPhoneModalConfirmI18n(asStringRecord(cfg.phone_confirm_modal_confirm_label_i18n))
      setPhoneModalBackI18n(asStringRecord(cfg.phone_confirm_modal_back_label_i18n))
    } else {
      setPhoneModalTitleI18n({})
      setPhoneModalDescriptionI18n({})
      setPhoneModalConfirmI18n({})
      setPhoneModalBackI18n({})
    }
  }, [permissionPromptTemplates])

  const selectStep = useCallback((stepId: string) => {
    setSelectedStepId(stepId)
    setSelectedScreenId(null)
    setComponents([])
    loadScreens(stepId)
  }, [loadScreens])

  const selectScreen = useCallback((screenId: string) => {
    setSelectedScreenId(screenId)
    setShowCompForm(false); setEditingCompId(null)
    const screen = screens.find(s => s.id === screenId)
    if (screen) populateScreenStructure(screen)
    loadComponents(screenId)
  }, [screens, populateScreenStructure, loadComponents])

  // ─── Steps CRUD ───────────────────────────────────────────────

  const saveStep = useCallback(async () => {
    setError(null)
    const rulePayload = {
      visibility_rule_json: stepForm.visibility_rule_json && Object.keys(stepForm.visibility_rule_json).length > 0
        ? stepForm.visibility_rule_json : null,
      completion_rule_json: stepForm.completion_rule_json && Object.keys(stepForm.completion_rule_json).length > 0
        ? stepForm.completion_rule_json : null,
    }
    try {
      if (editingStepId) {
        await api(`/api/admin/registration/steps/${editingStepId}`, {
          method: 'PATCH',
          body: JSON.stringify({
            title: stepForm.title, description: stepForm.description || null,
            is_blocking: stepForm.is_blocking, is_optional: stepForm.is_optional,
            title_i18n: cleanI18n(stepForm.title_i18n), description_i18n: cleanI18n(stepForm.description_i18n),
            ...rulePayload,
          }),
        })
      } else {
        await api(`/api/admin/registration/flows/${flowId}/steps`, {
          method: 'POST',
          body: JSON.stringify({
            step_key: autoKey('step'), title: stepForm.title,
            description: stepForm.description || null, position: steps.length,
            is_blocking: stepForm.is_blocking, is_optional: stepForm.is_optional,
            title_i18n: cleanI18n(stepForm.title_i18n), description_i18n: cleanI18n(stepForm.description_i18n),
            ...rulePayload,
          }),
        })
      }
      setShowStepForm(false); setEditingStepId(null); setStepForm(emptyStep())
      setSteps(await api(`/api/admin/registration/flows/${flowId}/steps`))
      loadHealth()
    } catch (e) { setError((e as Error).message) }
  }, [editingStepId, stepForm, flowId, steps.length, api, loadHealth])

  const deleteStep = useCallback((id: string) => {
    askConfirm('Delete step', 'This will permanently delete the step and all its screens and components. Continue?', async () => {
      try {
        await api(`/api/admin/registration/steps/${id}`, { method: 'DELETE' })
        if (selectedStepId === id) { setSelectedStepId(null); setScreens([]); setSelectedScreenId(null); setComponents([]) }
        setSteps(await api(`/api/admin/registration/flows/${flowId}/steps`))
      } catch (e) { setError((e as Error).message) }
    })
  }, [flowId, selectedStepId, api, askConfirm])

  const reorderStep = useCallback(async (idx: number, dir: -1 | 1) => {
    const arr = [...steps]; const swap = idx + dir
    if (swap < 0 || swap >= arr.length) return
    ;[arr[idx], arr[swap]] = [arr[swap], arr[idx]]
    setSteps(arr)
    try {
      await api(`/api/admin/registration/flows/${flowId}/steps/reorder`, {
        method: 'POST', body: JSON.stringify({ items: arr.map((s, i) => ({ id: s.id, position: i })) }),
      })
    } catch (e) { setError((e as Error).message) }
  }, [steps, flowId, api])

  const startEditStep = useCallback((step: Step) => {
    setEditingStepId(step.id)
    setStepForm({
      title: step.title, description: step.description || '',
      is_blocking: step.is_blocking, is_optional: step.is_optional,
      title_i18n: step.title_i18n || {}, description_i18n: step.description_i18n || {},
      visibility_rule_json: step.visibility_rule_json || null,
      completion_rule_json: step.completion_rule_json || null,
    })
    setShowStepForm(true)
  }, [])

  // ─── Screens CRUD ─────────────────────────────────────────────

  const createScreen = useCallback(async (title: string) => {
    if (!selectedStepId || !title.trim()) return
    setError(null)
    try {
      await api(`/api/admin/registration/steps/${selectedStepId}/screens`, {
        method: 'POST',
        body: JSON.stringify({
          screen_key: autoKey('screen'), title: title.trim(),
          position: screens.length, layout_type: 'form',
          button_label: 'Continue',
        }),
      })
      loadScreens(selectedStepId)
    } catch (e) { setError((e as Error).message) }
  }, [selectedStepId, screens.length, api, loadScreens])

  const createScreenFromTemplate = useCallback(async (templateKey: string) => {
    if (!selectedStepId) return
    const t = interactionTemplates.find(x => x.template_key === templateKey)
    if (!t?.selectable) {
      setError('This template is not available yet.')
      return
    }
    setError(null)
    try {
      await api(`/api/admin/registration/steps/${selectedStepId}/screens`, {
        method: 'POST',
        body: JSON.stringify({
          screen_key: autoKey('screen'),
          title: t.default_title,
          subtitle: t.default_subtitle,
          position: screens.length,
          layout_type: 'form',
          button_label: t.default_button_label || 'Continue',
          screen_type: 'interaction',
          interaction_type: t.interaction_type,
          interaction_config_json: { ...t.default_interaction_config },
        }),
      })
      await loadScreens(selectedStepId)
    } catch (e) { setError((e as Error).message) }
  }, [selectedStepId, screens.length, interactionTemplates, api, loadScreens])

  const createScreenFromPermissionTemplate = useCallback(async (templateKey: string) => {
    if (!selectedStepId) return
    const t = permissionPromptTemplates.find(x => x.template_key === templateKey)
    if (!t) {
      setError('Modèle permission introuvable.')
      return
    }
    setError(null)
    try {
      await api(`/api/admin/registration/steps/${selectedStepId}/screens`, {
        method: 'POST',
        body: JSON.stringify({
          screen_key: autoKey('screen'),
          title: t.default_title,
          subtitle: t.default_subtitle,
          position: screens.length,
          layout_type: 'form',
          button_label: t.default_button_label || 'Continue',
          screen_type: 'permission_prompt',
          interaction_type: null,
          interaction_config_json: null,
          config_json: { ...t.default_config },
        }),
      })
      await loadScreens(selectedStepId)
    } catch (e) { setError((e as Error).message) }
  }, [selectedStepId, screens.length, permissionPromptTemplates, api, loadScreens])

  /** Crée l’écran + composant (appelé après garde-fous / confirmation). */
  const runCreateScreenWithAddressStep = useCallback(async () => {
    if (!selectedStepId) return
    const fd = fieldCatalogItemForAddressLine1(fieldCatalog)
    if (!fd?.id) {
      setError(
        'Catalogue champs : aucune définition « address_line_1 ». Créez-la dans Field definitions avant d’utiliser + Address.',
      )
      return
    }
    setError(null)
    let createdScreenId: string | null = null
    try {
      const listTitleI18n =
        cleanI18n(ADDRESS_STEP_SCREEN_LIST_TITLE_I18N) ?? ADDRESS_STEP_SCREEN_LIST_TITLE_I18N
      const listTitlePlain =
        legacyStringFromI18n(ADDRESS_STEP_SCREEN_LIST_TITLE_I18N) || 'Home address'

      const ti = ADDRESS_STEP_I18N_DEFAULTS.address_step_title_i18n
      const st = ADDRESS_STEP_I18N_DEFAULTS.address_step_subtitle_i18n
      const subtitlePlain = legacyStringFromI18n(st) || ''
      const subtitleI18n = cleanI18n(st)

      const newScreen = (await api(`/api/admin/registration/steps/${selectedStepId}/screens`, {
        method: 'POST',
        body: JSON.stringify({
          screen_key: autoKey('screen'),
          title: listTitlePlain,
          title_i18n: listTitleI18n,
          subtitle: subtitlePlain || null,
          ...(subtitleI18n ? { subtitle_i18n: subtitleI18n } : {}),
          position: screens.length,
          layout_type: 'form',
          button_label: 'Continue',
          screen_type: 'form',
          config_json: { builder_preset: 'address_step' },
        }),
      })) as Screen
      createdScreenId = newScreen.id

      const preset: CompForm = {
        ...emptyComp(),
        component_type: 'address_step',
        binding_slug: 'address_line_1',
        label: fd.label || 'Address',
        required: fd.required_default ?? true,
        ...ADDRESS_STEP_I18N_DEFAULTS,
        address_step_search_enabled: true,
        address_step_search_min_chars: '2',
        address_step_search_debounce_ms: '300',
        address_step_line2_optional: true,
      }
      const stepProps = buildAddressStepPropsJson(preset)
      const props_json = { ...stepProps, label: preset.label }

      await api(`/api/admin/registration/screens/${newScreen.id}/components`, {
        method: 'POST',
        body: JSON.stringify({
          component_type: 'address_step',
          component_key: autoKey('address_step'),
          position: 0,
          props_json,
          binding_slug: 'address_line_1',
          field_definition_id: fd.id,
        }),
      })

      const list = (await api(
        `/api/admin/registration/steps/${selectedStepId}/screens`,
      )) as Screen[]
      setScreens(list)
      const hydrated = list.find(s => s.id === newScreen.id) || newScreen
      setSelectedScreenId(hydrated.id)
      setShowCompForm(false)
      setEditingCompId(null)
      populateScreenStructure(hydrated)
      await loadComponents(hydrated.id)
      loadHealth()
    } catch (e) {
      const msg = (e as Error).message
      if (createdScreenId) {
        try {
          await api(`/api/admin/registration/screens/${createdScreenId}`, { method: 'DELETE' })
        } catch {
          /* rollback best-effort */
        }
        setError(
          `Échec de la création du composant address_step : ${msg}. L’écran vide a été supprimé pour éviter un écran bloqué.`,
        )
        if (selectedStepId) {
          try {
            const list = (await api(
              `/api/admin/registration/steps/${selectedStepId}/screens`,
            )) as Screen[]
            setScreens(list)
          } catch {
            /* ignore */
          }
        }
      } else {
        setError(msg)
      }
    }
  }, [
    selectedStepId,
    screens.length,
    fieldCatalog,
    api,
    populateScreenStructure,
    loadComponents,
    loadHealth,
  ])

  /** Quick action + Address : évite les doublons involontaires (confirmation si déjà présent). */
  const requestCreateScreenWithAddressStep = useCallback(() => {
    if (!selectedStepId) return
    const fd = fieldCatalogItemForAddressLine1(fieldCatalog)
    if (!fd?.id) {
      setError(
        'Catalogue champs : aucune définition « address_line_1 ». Créez-la dans Field definitions avant d’utiliser + Address.',
      )
      return
    }
    const dup = screens.some(screenIsAddressPreset)
    if (dup) {
      askConfirm(
        'Écran Address déjà présent',
        'Cette étape contient déjà un écran marqué Address (+ Address). En ajouter un second peut dupliquer la saisie d’adresse dans le parcours. Voulez-vous continuer ?',
        () => {
          void runCreateScreenWithAddressStep()
        },
        'Créer quand même',
      )
      return
    }
    void runCreateScreenWithAddressStep()
  }, [selectedStepId, screens, fieldCatalog, askConfirm, runCreateScreenWithAddressStep])

  const runCreateScreenWithCountryResidence = useCallback(async () => {
    if (!selectedStepId) return
    const fd = fieldCatalogItemForCountryResidence(fieldCatalog)
    if (!fd?.id) {
      setError(
        'Catalogue champs : aucune définition « country_of_residence ». Créez-la dans Field definitions avant d’utiliser + Country.',
      )
      return
    }
    setError(null)
    let createdScreenId: string | null = null
    try {
      const listTitleI18n =
        cleanI18n(COUNTRY_RESIDENCE_SCREEN_LIST_TITLE_I18N) ?? COUNTRY_RESIDENCE_SCREEN_LIST_TITLE_I18N
      const listTitlePlain =
        legacyStringFromI18n(COUNTRY_RESIDENCE_SCREEN_LIST_TITLE_I18N) || 'Country of residence'

      const newScreen = (await api(`/api/admin/registration/steps/${selectedStepId}/screens`, {
        method: 'POST',
        body: JSON.stringify({
          screen_key: autoKey('screen'),
          title: listTitlePlain,
          title_i18n: listTitleI18n,
          subtitle: null,
          position: screens.length,
          layout_type: 'form',
          button_label: 'Continue',
          screen_type: 'form',
          config_json: { builder_preset: BUILDER_PRESET_COUNTRY_RESIDENCE },
        }),
      })) as Screen
      createdScreenId = newScreen.id

      const props_json = {
        required: true,
        label: {
          en: 'Country of residence',
          fr: 'Pays de résidence',
        },
      }

      await api(`/api/admin/registration/screens/${newScreen.id}/components`, {
        method: 'POST',
        body: JSON.stringify({
          component_type: 'country_picker',
          component_key: autoKey('country_residence'),
          position: 0,
          props_json,
          binding_slug: 'country_of_residence',
          field_definition_id: fd.id,
        }),
      })

      const list = (await api(
        `/api/admin/registration/steps/${selectedStepId}/screens`,
      )) as Screen[]
      setScreens(list)
      const hydrated = list.find(s => s.id === newScreen.id) || newScreen
      setSelectedScreenId(hydrated.id)
      setShowCompForm(false)
      setEditingCompId(null)
      populateScreenStructure(hydrated)
      await loadComponents(hydrated.id)
      loadHealth()
    } catch (e) {
      const msg = (e as Error).message
      if (createdScreenId) {
        try {
          await api(`/api/admin/registration/screens/${createdScreenId}`, { method: 'DELETE' })
        } catch {
          /* rollback */
        }
        setError(
          `Échec de la création du composant pays : ${msg}. L’écran vide a été supprimé.`,
        )
        if (selectedStepId) {
          try {
            const list = (await api(
              `/api/admin/registration/steps/${selectedStepId}/screens`,
            )) as Screen[]
            setScreens(list)
          } catch {
            /* ignore */
          }
        }
      } else {
        setError(msg)
      }
    }
  }, [
    selectedStepId,
    screens.length,
    fieldCatalog,
    api,
    populateScreenStructure,
    loadComponents,
    loadHealth,
  ])

  const requestCreateScreenWithCountryResidence = useCallback(() => {
    if (!selectedStepId) return
    const fd = fieldCatalogItemForCountryResidence(fieldCatalog)
    if (!fd?.id) {
      setError(
        'Catalogue champs : aucune définition « country_of_residence ». Créez-la dans Field definitions avant d’utiliser + Country.',
      )
      return
    }
    const dup = screens.some(screenIsCountryResidencePreset)
    if (dup) {
      askConfirm(
        'Écran pays déjà présent',
        'Cette étape contient déjà un écran « Pays de résidence ». En ajouter un second peut dupliquer la saisie. Continuer ?',
        () => {
          void runCreateScreenWithCountryResidence()
        },
        'Créer quand même',
      )
      return
    }
    void runCreateScreenWithCountryResidence()
  }, [selectedStepId, screens, fieldCatalog, askConfirm, runCreateScreenWithCountryResidence])

  const applyInteractionBizTemplate = useCallback((key: string) => {
    setInteractionBizTemplate(key)
    if (key === 'custom') return
    const t = interactionTemplates.find(x => x.template_key === key)
    if (!t) return
    setScreenType('interaction')
    setInteractionType(t.interaction_type)
    setHeaderTitle(t.default_title)
    setHeaderSubtitle(t.default_subtitle)
    setButtonLabel(t.default_button_label || 'Continue')
    const cfg = t.default_interaction_config
    setIcSourceSlug(String(cfg.source_field_slug || ''))
    setIcVerifiedFlagSlug(String(cfg.verified_flag_slug || ''))
    setIcPurpose(String(cfg.purpose || ''))
  }, [interactionTemplates])

  const applyPermissionBizTemplate = useCallback((key: string) => {
    setPermissionBizTemplate(key)
    if (key === 'custom') return
    const t = permissionPromptTemplates.find(x => x.template_key === key)
    if (!t) return
    setHeaderTitle(t.default_title)
    setHeaderSubtitle(t.default_subtitle)
    setButtonLabel(t.default_button_label || 'Continue')
    const dc = t.default_config
    setPermissionKind(String(dc.permission_kind || ''))
    setPermissionDecisionSlug(String(dc.decision_slug || ''))
    setPermissionSecondaryLabel(String(dc.secondary_button_label || 'Not Now'))
  }, [permissionPromptTemplates])

  const deleteScreen = useCallback((id: string) => {
    if (!selectedStepId) return
    askConfirm('Delete screen', 'This will permanently delete the screen and all its components. Continue?', async () => {
      try {
        await api(`/api/admin/registration/screens/${id}`, { method: 'DELETE' })
        if (selectedScreenId === id) { setSelectedScreenId(null); setComponents([]) }
        loadScreens(selectedStepId)
      } catch (e) { setError((e as Error).message) }
    })
  }, [selectedStepId, selectedScreenId, api, loadScreens, askConfirm])

  const reorderScreen = useCallback(async (idx: number, dir: -1 | 1) => {
    if (!selectedStepId) return
    const arr = [...screens]; const swap = idx + dir
    if (swap < 0 || swap >= arr.length) return
    ;[arr[idx], arr[swap]] = [arr[swap], arr[idx]]
    setScreens(arr)
    try {
      await api(`/api/admin/registration/steps/${selectedStepId}/screens/reorder`, {
        method: 'POST', body: JSON.stringify({ items: arr.map((s, i) => ({ id: s.id, position: i })) }),
      })
    } catch (e) { setError((e as Error).message) }
  }, [screens, selectedStepId, api])

  // ─── Screen structure save (header + button) ──────────────────

  const saveScreenStructure = useCallback(async () => {
    if (!selectedScreenId) return
    setError(null)
    try {
      const interactionPayload =
        screenType === 'interaction' && interactionType === 'phone_verification_sms'
          ? {
              source_field_slug: icSourceSlug.trim(),
              verified_flag_slug: icVerifiedFlagSlug.trim(),
              purpose: icPurpose.trim() || 'verify_phone',
            }
          : null
      const screenRow = screens.find(s => s.id === selectedScreenId)
      const prevCfg =
        screenRow?.config && typeof screenRow.config === 'object' && !Array.isArray(screenRow.config)
          ? { ...(screenRow.config as Record<string, unknown>) }
          : {}
      const payload: Record<string, unknown> = {
        title: headerTitle, subtitle: headerSubtitle || null,
        title_i18n: cleanI18n(headerTitleI18n), subtitle_i18n: cleanI18n(headerSubtitleI18n),
        button_label: buttonLabel || 'Continue',
        button_label_i18n: cleanI18n(buttonLabelI18n),
        screen_type: screenType,
        interaction_type: screenType === 'interaction' ? interactionType : null,
        interaction_config_json: screenType === 'interaction' ? interactionPayload : null,
      }
      if (screenType === 'form') {
        const nextCfg: Record<string, unknown> = {
          ...prevCfg,
          phone_confirm_modal_enabled: phoneConfirmModalEnabled,
        }
        const setOrDel = (key: string, cleaned: Record<string, string> | null) => {
          if (cleaned) nextCfg[key] = cleaned
          else delete nextCfg[key]
        }
        setOrDel('phone_confirm_modal_title_i18n', cleanI18n(phoneModalTitleI18n))
        setOrDel('phone_confirm_modal_description_i18n', cleanI18n(phoneModalDescriptionI18n))
        setOrDel('phone_confirm_modal_confirm_label_i18n', cleanI18n(phoneModalConfirmI18n))
        setOrDel('phone_confirm_modal_back_label_i18n', cleanI18n(phoneModalBackI18n))
        payload.config_json = nextCfg
      } else if (screenType === 'permission_prompt') {
        payload.config_json = {
          permission_kind: permissionKind,
          decision_slug: permissionDecisionSlug.trim(),
          secondary_button_label: permissionSecondaryLabel.trim() || 'Not Now',
        }
      }
      await api(`/api/admin/registration/screens/${selectedScreenId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload),
      })
      if (selectedStepId) {
        const updated = await api(`/api/admin/registration/steps/${selectedStepId}/screens`)
        setScreens(updated)
      }
    } catch (e) { setError((e as Error).message) }
  }, [
    selectedScreenId, selectedStepId, screens, headerTitle, headerSubtitle, headerTitleI18n, headerSubtitleI18n,
    buttonLabel, buttonLabelI18n, screenType, interactionType, icSourceSlug, icVerifiedFlagSlug, icPurpose,
    phoneConfirmModalEnabled, phoneModalTitleI18n, phoneModalDescriptionI18n, phoneModalConfirmI18n,
    phoneModalBackI18n,
    permissionKind, permissionDecisionSlug, permissionSecondaryLabel,
    api,
  ])

  // ─── Components CRUD (input fields only) ──────────────────────

  const saveComponent = useCallback(async () => {
    if (!selectedScreenId) return
    setError(null)
    const isContentType = (CONTENT_TYPES as readonly string[]).includes(compForm.component_type)

    if (!isContentType && !editingCompId) {
      const fdPick = (compForm as CompForm & { _field_definition_id?: string })._field_definition_id
      if (!fdPick) {
        setError('Select a field from the Field Catalog before creating a client field (required for governance).')
        return
      }
    }

    const propsJson: Record<string, unknown> = {
      label: compForm.label,
    }
    if (!isContentType) propsJson.required = compForm.required
    if (compForm.placeholder) propsJson.placeholder = compForm.placeholder
    const li = cleanI18n(compForm.label_i18n)
    if (li) propsJson.label = li
    const pi = cleanI18n(compForm.placeholder_i18n)
    if (pi) propsJson.placeholder = pi

    if (['select', 'multi_select'].includes(compForm.component_type)) {
      try { propsJson.options = JSON.parse(compForm.options) } catch { propsJson.options = [] }
    }

    if (compForm.component_type === 'link_text') {
      if (compForm.link_label) propsJson.link_label = compForm.link_label
      const lli = cleanI18n(compForm.link_label_i18n)
      if (lli) propsJson.link_label = lli
      if (compForm.link_url) propsJson.link_url = compForm.link_url
    }

    if (compForm.component_type === 'checkbox') {
      if (compForm.description) propsJson.description = compForm.description
      const di = cleanI18n(compForm.description_i18n)
      if (di) propsJson.description = di
    }

    if (compForm.component_type === 'address_autocomplete') {
      propsJson.binding_slugs = {
        street: 'address_line_1',
        postal: 'postal_code',
        city: 'city',
        country: 'country_of_residence',
      }
      propsJson.enable_manual_override = true
      propsJson.store_place_id = true
      propsJson.metadata_slug = 'address_metadata'
      propsJson.search_label = 'Search address'
    }

    if (compForm.component_type === 'address_step') {
      Object.assign(propsJson, buildAddressStepPropsJson(compForm))
    }

    if (['rich_text', 'legal_content', 'info_box'].includes(compForm.component_type)) {
      if (compForm.description) propsJson.content = compForm.description
      const di = cleanI18n(compForm.description_i18n)
      if (di) propsJson.content = di
    }

    const fdId = isContentType ? null : ((compForm as CompForm & { _field_definition_id?: string })._field_definition_id || null)
    const bindingSlug = isContentType ? null : (compForm.binding_slug || null)

    const vis =
      compForm.visibility_rule_json && Object.keys(compForm.visibility_rule_json).length > 0
        ? compForm.visibility_rule_json
        : null
    const val =
      compForm.validation_rule_json && Object.keys(compForm.validation_rule_json).length > 0
        ? compForm.validation_rule_json
        : null

    try {
      if (editingCompId) {
        await api(`/api/admin/registration/components/${editingCompId}`, {
          method: 'PATCH',
          body: JSON.stringify({
            component_type: compForm.component_type, props_json: propsJson,
            binding_slug: bindingSlug,
            field_definition_id: fdId,
            visibility_rule_json: vis,
            validation_rule_json: val,
          }),
        })
      } else {
        await api(`/api/admin/registration/screens/${selectedScreenId}/components`, {
          method: 'POST',
          body: JSON.stringify({
            component_type: compForm.component_type,
            component_key: autoKey(compForm.component_type),
            position: components.length, props_json: propsJson,
            binding_slug: bindingSlug,
            field_definition_id: fdId,
            visibility_rule_json: vis,
            validation_rule_json: val,
          }),
        })
      }
      setShowCompForm(false); setEditingCompId(null); setCompForm(emptyComp()); setCompMode('client_field')
      loadComponents(selectedScreenId)
      loadHealth()
    } catch (e) { setError((e as Error).message) }
  }, [editingCompId, compForm, selectedScreenId, components.length, api, loadComponents, loadHealth])

  const deleteComponent = useCallback((id: string) => {
    if (!selectedScreenId) return
    askConfirm('Delete field', 'This will permanently delete this field. Continue?', async () => {
      try {
        await api(`/api/admin/registration/components/${id}`, { method: 'DELETE' })
        loadComponents(selectedScreenId)
      } catch (e) { setError((e as Error).message) }
    })
  }, [selectedScreenId, api, loadComponents, askConfirm])

  const reorderComponent = useCallback(async (idx: number, dir: -1 | 1) => {
    if (!selectedScreenId) return
    const arr = [...components]; const swap = idx + dir
    if (swap < 0 || swap >= arr.length) return
    ;[arr[idx], arr[swap]] = [arr[swap], arr[idx]]
    setComponents(arr)
    try {
      await api(`/api/admin/registration/screens/${selectedScreenId}/components/reorder`, {
        method: 'POST', body: JSON.stringify({ items: arr.map((c, i) => ({ id: c.id, position: i })) }),
      })
    } catch (e) { setError((e as Error).message) }
  }, [components, selectedScreenId, api])

  const startEditComp = useCallback((comp: Component) => {
    setEditingCompId(comp.id)
    const isContent = (CONTENT_TYPES as readonly string[]).includes(comp.component_type)
    setCompMode(isContent ? 'content' : 'client_field')
    const p = comp.props || {}
    const labelVal = p.label
    const placeholderVal = p.placeholder
    const descVal = p.description || p.content
    const linkLabelVal = p.link_label
    const isAddrStep = comp.component_type === 'address_step'
    setCompForm({
      component_type: comp.component_type,
      binding_slug: comp.binding_slug || '',
      label: typeof labelVal === 'string' ? labelVal : '',
      required: !!p.required,
      placeholder: typeof placeholderVal === 'string' ? placeholderVal : '',
      options: JSON.stringify(p.options || [], null, 2),
      description: typeof descVal === 'string' ? descVal : '',
      link_label: typeof linkLabelVal === 'string' ? linkLabelVal : '',
      link_url: (p.link_url as string) || '',
      label_i18n: typeof labelVal === 'object' && labelVal ? (labelVal as Record<string, string>) : {},
      placeholder_i18n: typeof placeholderVal === 'object' && placeholderVal ? (placeholderVal as Record<string, string>) : {},
      description_i18n: typeof descVal === 'object' && descVal ? (descVal as Record<string, string>) : {},
      link_label_i18n: typeof linkLabelVal === 'object' && linkLabelVal ? (linkLabelVal as Record<string, string>) : {},
      visibility_rule_json: comp.visibility_rule_json || null,
      validation_rule_json: comp.validation_rule_json || null,
      address_step_title_i18n: isAddrStep
        ? mergeFlatI18nFromProps(p as Record<string, unknown>, 'title_i18n', 'title')
        : {},
      address_step_subtitle_i18n: isAddrStep
        ? mergeFlatI18nFromProps(p as Record<string, unknown>, 'subtitle_i18n', 'subtitle')
        : {},
      address_step_search_label_i18n: isAddrStep
        ? mergeFlatI18nFromProps(p as Record<string, unknown>, 'search_label_i18n', 'search_label')
        : {},
      address_step_manual_label_i18n: isAddrStep
        ? mergeFlatI18nFromProps(
            p as Record<string, unknown>,
            'manual_entry_label_i18n',
            'manual_entry_label',
          )
        : {},
      address_step_field_labels_i18n: isAddrStep
        ? readAddressStepFieldMap(p.field_labels_i18n)
        : {
            address_line_1: {},
            address_line_2: {},
            postal_code: {},
            city: {},
          },
      address_step_field_placeholders_i18n: isAddrStep
        ? readAddressStepFieldMap(p.field_placeholders_i18n)
        : {
            address_line_1: {},
            address_line_2: {},
            postal_code: {},
            city: {},
          },
      address_step_search_enabled: isAddrStep ? p.search_enabled !== false : true,
      address_step_search_min_chars: isAddrStep && typeof p.search_min_chars === 'number' ? String(p.search_min_chars) : '2',
      address_step_search_debounce_ms: isAddrStep && typeof p.search_debounce_ms === 'number' ? String(p.search_debounce_ms) : '300',
      address_step_line2_optional: isAddrStep ? p.address_line_2_optional !== false : true,
      ...(comp.field_definition_id ? { _field_definition_id: comp.field_definition_id } : {}),
    } as CompForm & { _field_definition_id?: string })
    setShowCompForm(true)
  }, [])

  const selectedScreen = screens.find(s => s.id === selectedScreenId)

  const addressStepHeaderPreviewForm = useMemo(() => {
    if (!selectedScreenId || !selectedScreen || !screenIsAddressPreset(selectedScreen)) return null
    if (components.length !== 1) return null
    return addressStepPreviewFormFromComponent(components[0])
  }, [selectedScreenId, selectedScreen, components])

  // ─── Render ───────────────────────────────────────────────────
  // (Hooks above must stay before any conditional return.)

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
    </div>
  )

  if (!flow) return <div className="text-red-600 p-4">Flow not found</div>

  return (
    <div>
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="text-2xl font-bold text-gray-900">{flow.name}</h1>
            <Badge variant="outline">v{flow.version}</Badge>
            <Badge className={
              flow.status === 'active' ? 'bg-green-100 text-green-700'
              : flow.status === 'draft' ? 'bg-yellow-100 text-yellow-700'
              : 'bg-gray-100 text-gray-600'
            }>{flow.status}</Badge>
          </div>
          <p className="text-sm text-gray-500">{flow.entrypoint_type} — {steps.length} steps</p>
        </div>
        <div className="flex gap-2 items-center">
          <Button variant="outline" size="sm" onClick={() => { loadHealth(); setShowHealth(h => !h) }}>
            {health ? `Health (${health.error_count}E / ${health.warning_count}W)` : 'Check Health'}
          </Button>
          {flow.status === 'draft' && (
            <Button size="sm" className="bg-green-600 hover:bg-green-700 text-white"
              disabled={publishing || (health !== null && !health.can_publish)}
              onClick={() => { setPublishOpen(true); setPublishByName(''); setPublishSuccess(null) }}>
              {publishing ? 'Publishing…' : 'Publish…'}
            </Button>
          )}
          {flow.status === 'active' && (
            <Button size="sm" variant="outline" className="text-orange-600 border-orange-300 hover:bg-orange-50"
              onClick={archiveFlow}>Archive</Button>
          )}
          <Link href={`/admin/registration/flows/${flowId}/preview`}>
            <Button variant="outline" size="sm">Preview</Button>
          </Link>
          <Link href="/admin/registration">
            <Button variant="outline" size="sm">Back to list</Button>
          </Link>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 underline">dismiss</button>
        </div>
      )}
      {publishSuccess && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-800 flex justify-between items-center">
          <span>{publishSuccess}</span>
          <button type="button" className="text-emerald-700 underline text-xs" onClick={() => setPublishSuccess(null)}>dismiss</button>
        </div>
      )}

      {flow.jurisdiction && (
        <Card className="mb-4 border-indigo-100 bg-indigo-50/40">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold text-indigo-950">Jurisdiction policy in use</CardTitle>
            <p className="text-xs text-indigo-900/80 font-normal">
              Le flow ne contient pas la policy : il référence la juridiction{' '}
              <span className="font-mono font-medium">{flow.jurisdiction.code}</span>.
              Édition détaillée sur la page dédiée.
            </p>
          </CardHeader>
          <CardContent className="text-sm space-y-2">
            {jurisdictionPolicy ? (
              <>
                <div className="flex flex-wrap gap-x-6 gap-y-1 text-gray-800">
                  <span>Residence countries: <strong className="font-mono">{jurisdictionPolicy.residence_country_count}</strong></span>
                  <span>Phone countries: <strong className="font-mono">{jurisdictionPolicy.phone_country_count}</strong></span>
                  <span>Nationality countries: <strong className="font-mono">{jurisdictionPolicy.nationality_country_count ?? 0}</strong></span>
                  <span>Default residence: <strong className="font-mono">{jurisdictionPolicy.default_residence_iso2 ?? '—'}</strong></span>
                  <span>Default phone: <strong className="font-mono">{jurisdictionPolicy.default_phone_iso2 ?? '—'}</strong></span>
                </div>
                {jurisdictionPolicy.inherit_phone_countries_from_residence && (
                  <Badge variant="outline" className="text-[10px] border-indigo-200 text-indigo-900">Phone inherits from residence</Badge>
                )}
                <Link href={`/admin/jurisdiction-policies/${encodeURIComponent(flow.jurisdiction.code)}`}>
                  <Button size="sm" variant="secondary" className="mt-2">Edit jurisdiction policy</Button>
                </Link>
              </>
            ) : (
              <p className="text-xs text-gray-600">Chargement de la policy… ou aucune donnée (vérifiez l’API).</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* Health Panel */}
      {showHealth && health && (
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-semibold">
                Publish Readiness
                {health.can_publish
                  ? <Badge className="ml-2 bg-green-100 text-green-700">Ready</Badge>
                  : <Badge className="ml-2 bg-red-100 text-red-700">Not Ready</Badge>
                }
              </CardTitle>
              <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => setShowHealth(false)}>Close</Button>
            </div>
          </CardHeader>
          <CardContent>
            {health.errors.length > 0 && (
              <div className="mb-3">
                <span className="text-xs font-semibold text-red-600 block mb-1">Blocking errors ({health.error_count})</span>
                {Object.entries(
                  health.errors.reduce<Record<string, HealthIssue[]>>((acc, e) => {
                    acc[e.category] = acc[e.category] || []
                    acc[e.category].push(e)
                    return acc
                  }, {}),
                ).map(([cat, items]) => (
                  <div key={cat} className="mb-2">
                    <span className="text-[10px] font-bold text-red-800 uppercase tracking-wide">{cat}</span>
                    <ul className="space-y-1 mt-0.5">
                      {items.map((e, i) => (
                        <li key={i} className="text-xs text-red-800 bg-red-50 border border-red-100 rounded px-2 py-1">
                          {e.message}
                          {(e.step_id || e.screen_id || e.component_id) && (
                            <span className="block text-[10px] text-red-600 font-mono mt-0.5">
                              {e.step_id && `step ${e.step_id.slice(0, 8)}…`}
                              {e.screen_id && ` · screen ${e.screen_id.slice(0, 8)}…`}
                              {e.component_id && ` · comp ${e.component_id.slice(0, 8)}…`}
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
            {health.warnings.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-amber-700 block mb-1">Warnings ({health.warning_count})</span>
                {Object.entries(
                  health.warnings.reduce<Record<string, HealthIssue[]>>((acc, w) => {
                    acc[w.category] = acc[w.category] || []
                    acc[w.category].push(w)
                    return acc
                  }, {}),
                ).map(([cat, items]) => (
                  <div key={cat} className="mb-2">
                    <span className="text-[10px] font-bold text-amber-900 uppercase tracking-wide">{cat}</span>
                    <ul className="space-y-1 max-h-32 overflow-y-auto mt-0.5">
                      {items.map((w, i) => (
                        <li key={i} className="text-xs text-amber-900 bg-amber-50 border border-amber-100 rounded px-2 py-1">
                          {w.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            )}
            {health.errors.length === 0 && health.warnings.length === 0 && (
              <p className="text-sm text-green-600">All checks passed. Flow is ready to publish.</p>
            )}
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-12 gap-4">
        {/* ─── Steps Panel ─── */}
        <div className="col-span-3">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">Steps</CardTitle>
                <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => {
                  setEditingStepId(null); setStepForm(emptyStep()); setShowStepForm(true)
                }}>+ Add Step</Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {showStepForm && (
                <div className="p-3 border border-blue-200 rounded-lg bg-blue-50 space-y-2">
                  <input className={inputCls} placeholder="Title" value={stepForm.title}
                    onChange={e => setStepForm(f => ({ ...f, title: e.target.value }))} />
                  <I18nField label="Title" value={stepForm.title_i18n}
                    onChange={v => setStepForm(f => ({ ...f, title_i18n: v }))} />
                  <input className={inputCls} placeholder="Description (optional)" value={stepForm.description}
                    onChange={e => setStepForm(f => ({ ...f, description: e.target.value }))} />
                  <I18nField label="Description" value={stepForm.description_i18n}
                    onChange={v => setStepForm(f => ({ ...f, description_i18n: v }))} />
                  <div className="flex items-center gap-4 text-xs">
                    <label className="flex items-center gap-1">
                      <input type="checkbox" checked={stepForm.is_blocking}
                        onChange={e => setStepForm(f => ({ ...f, is_blocking: e.target.checked }))} /> Blocking
                    </label>
                    <label className="flex items-center gap-1">
                      <input type="checkbox" checked={stepForm.is_optional}
                        onChange={e => setStepForm(f => ({ ...f, is_optional: e.target.checked }))} /> Optional
                    </label>
                  </div>
                  <RuleEditor label="Visibility Rule"
                    value={stepForm.visibility_rule_json}
                    onChange={v => setStepForm(f => ({ ...f, visibility_rule_json: v }))} />
                  <RuleEditor label="Completion Rule"
                    value={stepForm.completion_rule_json}
                    onChange={v => setStepForm(f => ({ ...f, completion_rule_json: v }))} />
                  <div className="flex gap-2">
                    <Button size="sm" className="h-7 text-xs flex-1" onClick={saveStep}>
                      {editingStepId ? 'Update' : 'Create'}
                    </Button>
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => {
                      setShowStepForm(false); setEditingStepId(null)
                    }}>Cancel</Button>
                  </div>
                </div>
              )}

              {steps.map((step, idx) => (
                <div key={step.id} onClick={() => selectStep(step.id)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedStepId === step.id ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'
                  }`}>
                  <div className="flex items-center justify-between mb-1 gap-1">
                    <span className="text-sm font-medium text-gray-900 truncate">{step.title}</span>
                    <div className="flex items-center gap-1 shrink-0">
                      {(() => {
                        const s = stepI18nSummary(step)
                        return <I18nBadge level={s.level} tooltip={s.tip} />
                      })()}
                      <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${
                        step.is_blocking ? 'border-red-300 text-red-600' : 'border-green-300 text-green-600'
                      }`}>{step.is_blocking ? 'blocking' : 'optional'}</Badge>
                    </div>
                  </div>
                  <div className="flex gap-1 mt-2" onClick={e => e.stopPropagation()}>
                    <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-gray-100 disabled:opacity-30"
                      disabled={idx === 0} onClick={() => reorderStep(idx, -1)}>▲</button>
                    <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-gray-100 disabled:opacity-30"
                      disabled={idx === steps.length - 1} onClick={() => reorderStep(idx, 1)}>▼</button>
                    <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-blue-50 text-blue-600"
                      onClick={() => startEditStep(step)}>Edit</button>
                    <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-red-50 text-red-600"
                      onClick={() => deleteStep(step.id)}>Del</button>
                  </div>
                </div>
              ))}

              {steps.length === 0 && !showStepForm && (
                <p className="text-xs text-gray-400 text-center py-4">No steps yet</p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ─── Screens Panel ─── */}
        <div className="col-span-3">
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">
                  Screens {selectedStepId ? `(${screens.length})` : ''}
                </CardTitle>
                {selectedStepId && (
                  <div className="flex flex-wrap gap-1 justify-end">
                    <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => {
                      const title = prompt('Screen title (form):')
                      if (title) createScreen(title)
                    }} title="Classic form screen with components">+ Form screen</Button>
                    <Button size="sm" className="h-7 text-xs bg-violet-600 hover:bg-violet-700 text-white"
                      onClick={() => createScreenFromTemplate('confirmation_code_sms')}
                      title="Add SMS OTP verification (preset)">+ Code SMS</Button>
                    <Button size="sm" className="h-7 text-xs bg-sky-600 hover:bg-sky-700 text-white"
                      onClick={() => createScreenFromPermissionTemplate('push_notifications_activation')}
                      title="Écran demande notifications push (app mobile)">+ Notifications</Button>
                    <Button size="sm" className="h-7 text-xs bg-slate-700 hover:bg-slate-800 text-white"
                      onClick={() => createScreenFromPermissionTemplate('face_id_activation')}
                      title="Écran activation Face ID / biométrie (app mobile)">+ Face ID</Button>
                    <Button size="sm" className="h-7 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                      onClick={() => requestCreateScreenWithAddressStep()}
                      title="Home address — recherche + lignes d’adresse (pays collecté sur l’écran + Country en amont)">+ Address</Button>
                    <Button size="sm" className="h-7 text-xs bg-teal-600 hover:bg-teal-700 text-white"
                      onClick={() => requestCreateScreenWithCountryResidence()}
                      title="Country of residence — un seul country_picker (à placer avant Home address)">+ Country</Button>
                  </div>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {!selectedStepId ? (
                <p className="text-xs text-gray-400 text-center py-8">Select a step</p>
              ) : (
                <>
                  {screens.map((screen, idx) => (
                    <div key={screen.id} onClick={() => selectScreen(screen.id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                        selectedScreenId === screen.id ? 'border-blue-400 bg-blue-50' : 'border-gray-200 bg-white hover:bg-gray-50'
                      }`}>
                      <div className="flex items-center justify-between gap-1 flex-wrap">
                        <div className="min-w-0 flex-1 max-w-[min(220px,58vw)]">
                          <span className="text-sm font-medium text-gray-900 truncate block" title={screen.title}>
                            {screen.title}
                          </span>
                          {screenIsAddressPreset(screen) ? (
                            <span
                              className="text-[10px] text-emerald-800/85 truncate block mt-0.5"
                              title="Home address — sans pays à l’écran"
                            >
                              address_step · home address
                            </span>
                          ) : null}
                          {screenIsCountryResidencePreset(screen) ? (
                            <span
                              className="text-[10px] text-teal-800/85 truncate block mt-0.5"
                              title="Pays de résidence — placer avant l’écran adresse"
                            >
                              country_picker · résidence
                            </span>
                          ) : null}
                        </div>
                        <div className="flex items-center gap-1 shrink-0 flex-wrap justify-end">
                          {screen.screen_type === 'interaction' && (
                            <>
                              <Badge variant="outline" className="text-[9px] px-1 py-0 border-violet-300 text-violet-700">
                                interaction
                              </Badge>
                              {screen.interaction_template_display_name ? (
                                <span className="text-[10px] text-violet-800 font-medium truncate max-w-[100px]" title={screen.interaction_template_display_name}>
                                  {screen.interaction_template_display_name}
                                </span>
                              ) : null}
                            </>
                          )}
                          {screen.screen_type === 'permission_prompt' && (
                            <Badge variant="outline" className="text-[9px] px-1 py-0 border-sky-300 text-sky-800">
                              permission
                            </Badge>
                          )}
                          {screenIsAddressPreset(screen) && (
                              <Badge
                                variant="outline"
                                className="text-[9px] px-1.5 py-0 font-semibold border-emerald-400 bg-emerald-50 text-emerald-900 shadow-sm"
                                title="Home address"
                              >
                                Home addr.
                              </Badge>
                            )}
                          {screenIsCountryResidencePreset(screen) && (
                              <Badge
                                variant="outline"
                                className="text-[9px] px-1.5 py-0 font-semibold border-teal-400 bg-teal-50 text-teal-900 shadow-sm"
                                title="Country of residence"
                              >
                                Country
                              </Badge>
                            )}
                          {(() => {
                            const s = screenI18nSummary(screen)
                            return <I18nBadge level={s.level} tooltip={s.tip} />
                          })()}
                        </div>
                      </div>
                      {screen.screen_type === 'interaction' && screen.interaction_type && (
                        <p className="text-[10px] text-gray-400 mt-0.5 font-mono truncate" title={screen.interaction_type}>
                          {screen.interaction_type}
                        </p>
                      )}
                      {screen.screen_type === 'permission_prompt' && screen.config && typeof screen.config === 'object' && !Array.isArray(screen.config) && (
                        <p className="text-[10px] text-sky-800/90 mt-0.5 font-mono truncate" title={String((screen.config as { permission_kind?: string }).permission_kind)}>
                          {(screen.config as { permission_kind?: string }).permission_kind || 'permission_prompt'}
                        </p>
                      )}
                      <div className="flex gap-1 mt-2" onClick={e => e.stopPropagation()}>
                        <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-gray-100 disabled:opacity-30"
                          disabled={idx === 0} onClick={() => reorderScreen(idx, -1)}>▲</button>
                        <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-gray-100 disabled:opacity-30"
                          disabled={idx === screens.length - 1} onClick={() => reorderScreen(idx, 1)}>▼</button>
                        <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-red-50 text-red-600"
                          onClick={() => deleteScreen(screen.id)}>Del</button>
                      </div>
                    </div>
                  ))}
                  {screens.length === 0 && (
                    <p className="text-xs text-gray-400 text-center py-4">No screens in this step</p>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </div>

        {/* ─── Screen Structure Panel (3 sections) ─── */}
        <div className="col-span-6">
          {!selectedScreen ? (
            <Card>
              <CardContent className="py-12">
                <p className="text-sm text-gray-400 text-center">Select a screen to edit its structure</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {/* Section 1: Header */}
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center text-blue-600 text-xs font-bold">1</div>
                    <CardTitle className="text-sm font-semibold">Page Header</CardTitle>
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-blue-300 text-blue-600">required</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <label className="text-xs font-medium text-gray-700 mb-1 block">Title *</label>
                    <input className={inputCls} placeholder="Page title (e.g. Your Information)" value={headerTitle}
                      onChange={e => setHeaderTitle(e.target.value)} />
                    <I18nField label="Title" value={headerTitleI18n} onChange={setHeaderTitleI18n} />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-700 mb-1 block">Description</label>
                    <textarea className={inputCls + ' h-16'} placeholder="Optional description shown below the title"
                      value={headerSubtitle} onChange={e => setHeaderSubtitle(e.target.value)} />
                    <I18nField label="Description" value={headerSubtitleI18n} onChange={setHeaderSubtitleI18n} multiline />
                  </div>
                  {screenType === 'form' && addressStepHeaderPreviewForm ? (
                    <div className="rounded-lg border border-emerald-200/90 bg-gradient-to-b from-emerald-50/90 to-white p-3 shadow-sm">
                      <p className="text-[11px] font-semibold text-emerald-900">
                        Aperçu du widget <span className="font-mono text-[10px]">address_step</span>
                      </p>
                      <p className="text-[10px] text-emerald-800/80 mt-0.5 mb-2">
                        Statique — reflète le composant enregistré (un seul composant sur cet écran).
                      </p>
                      <AddressStepPreviewPanel form={addressStepHeaderPreviewForm} />
                    </div>
                  ) : null}
                  <div className="pt-2 border-t border-gray-100 space-y-2">
                    <label className="text-xs font-medium text-gray-700 mb-1 block">Screen type</label>
                    <select
                      className={inputCls}
                      value={screenType}
                      onChange={e => {
                        const v = e.target.value as 'form' | 'interaction' | 'permission_prompt'
                        setScreenType(v)
                        if (v === 'form') {
                          setInteractionBizTemplate('custom')
                          setPermissionBizTemplate('custom')
                        }
                        if (v === 'interaction') {
                          setPermissionBizTemplate('custom')
                        }
                        if (v === 'permission_prompt') {
                          setInteractionBizTemplate('custom')
                          const first = permissionPromptTemplates[0]
                          if (first) {
                            setPermissionBizTemplate(first.template_key)
                            setHeaderTitle(first.default_title)
                            setHeaderSubtitle(first.default_subtitle)
                            setButtonLabel(first.default_button_label || 'Continue')
                            const dc = first.default_config
                            setPermissionKind(String(dc.permission_kind || ''))
                            setPermissionDecisionSlug(String(dc.decision_slug || ''))
                            setPermissionSecondaryLabel(String(dc.secondary_button_label || 'Not Now'))
                          } else {
                            setPermissionKind('face_id')
                            setPermissionDecisionSlug('face_id_enabled')
                            setPermissionSecondaryLabel('Not Now')
                            setPermissionBizTemplate('custom')
                          }
                        }
                      }}
                    >
                      <option value="form">Form screen</option>
                      <option value="interaction">Interaction screen</option>
                      <option value="permission_prompt">Permission (Face ID / notifications)</option>
                    </select>
                    {screenType === 'interaction' && (
                      <div className="space-y-2 p-2 rounded-lg bg-violet-50 border border-violet-200">
                        <label className="text-xs font-semibold text-violet-900 block">Interaction template</label>
                        <p className="text-[10px] text-violet-800/90">Pick a business preset or Custom to edit technical fields yourself.</p>
                        <select
                          className={inputCls}
                          value={interactionBizTemplate}
                          onChange={e => applyInteractionBizTemplate(e.target.value)}
                        >
                          <option value="custom">Custom (advanced)</option>
                          {interactionTemplates.map(t => (
                            <option
                              key={t.template_key}
                              value={t.template_key}
                              disabled={!t.selectable}
                            >
                              {t.display_name}{!t.selectable ? ' — soon' : ''}
                            </option>
                          ))}
                        </select>
                        <div>
                          <span className="text-[10px] text-violet-800 block mb-0.5">interaction_type (runtime)</span>
                          <select
                            className={inputCls}
                            value={interactionType}
                            onChange={e => {
                              setInteractionType(e.target.value)
                              setInteractionBizTemplate('custom')
                            }}
                          >
                            <option value="phone_verification_sms">phone_verification_sms</option>
                          </select>
                        </div>
                        {interactionType === 'phone_verification_sms' && (
                          <>
                            <div>
                              <span className="text-[10px] text-violet-800 block mb-0.5">source_field_slug</span>
                              <input className={inputCls + ' font-mono text-xs'} value={icSourceSlug}
                                onChange={e => setIcSourceSlug(e.target.value)} placeholder="phone_number" />
                            </div>
                            <div>
                              <span className="text-[10px] text-violet-800 block mb-0.5">verified_flag_slug</span>
                              <input className={inputCls + ' font-mono text-xs'} value={icVerifiedFlagSlug}
                                onChange={e => setIcVerifiedFlagSlug(e.target.value)} placeholder="phone_verified" />
                            </div>
                            <div>
                              <span className="text-[10px] text-violet-800 block mb-0.5">purpose (2FA)</span>
                              <input className={inputCls + ' font-mono text-xs'} value={icPurpose}
                                onChange={e => setIcPurpose(e.target.value)} placeholder="verify_phone" />
                            </div>
                          </>
                        )}
                      </div>
                    )}
                    {screenType === 'permission_prompt' && (
                      <div className="space-y-2 p-2 rounded-lg bg-sky-50 border border-sky-200">
                        <label className="text-xs font-semibold text-sky-950 block">Modèles permission (app mobile)</label>
                        <p className="text-[10px] text-sky-900/90">
                          L’utilisateur envoie une valeur booléenne sur <span className="font-mono">decision_slug</span> au tap sur le bouton principal (oui) ou secondaire (non).
                        </p>
                        <select
                          className={inputCls}
                          value={permissionBizTemplate}
                          onChange={e => {
                            setPermissionBizTemplate(e.target.value)
                            applyPermissionBizTemplate(e.target.value)
                          }}
                        >
                          <option value="custom">Custom (champs ci-dessous)</option>
                          {permissionPromptTemplates.map(t => (
                            <option key={t.template_key} value={t.template_key}>
                              {t.display_name}
                            </option>
                          ))}
                        </select>
                        <div>
                          <span className="text-[10px] text-sky-900 block mb-0.5">permission_kind</span>
                          <select
                            className={inputCls + ' font-mono text-xs'}
                            value={permissionKind}
                            onChange={e => {
                              setPermissionKind(e.target.value)
                              setPermissionBizTemplate('custom')
                            }}
                          >
                            <option value="face_id">face_id</option>
                            <option value="push_notifications">push_notifications</option>
                          </select>
                        </div>
                        <div>
                          <span className="text-[10px] text-sky-900 block mb-0.5">decision_slug (booléen persisté)</span>
                          <input
                            className={inputCls + ' font-mono text-xs'}
                            value={permissionDecisionSlug}
                            onChange={e => {
                              setPermissionDecisionSlug(e.target.value)
                              setPermissionBizTemplate('custom')
                            }}
                            placeholder="face_id_enabled"
                          />
                        </div>
                        <div>
                          <span className="text-[10px] text-sky-900 block mb-0.5">secondary_button_label</span>
                          <input
                            className={inputCls}
                            value={permissionSecondaryLabel}
                            onChange={e => {
                              setPermissionSecondaryLabel(e.target.value)
                              setPermissionBizTemplate('custom')
                            }}
                            placeholder="Not Now"
                          />
                        </div>
                      </div>
                    )}
                    {screenType === 'form' && (
                      <div className="pt-3 mt-1 border-t border-gray-100 space-y-3">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-medium text-gray-800">Modale de confirmation du numéro (app mobile)</p>
                            <p className="text-[10px] text-gray-500 mt-1 leading-snug">
                              Activée : l’utilisateur voit une modale avant l’envoi du SMS. Désactivée : Continue envoie directement à l’étape suivante. Enregistrez la structure d’écran pour appliquer les textes.
                            </p>
                          </div>
                          <div className="flex flex-col items-end gap-1 shrink-0 pt-0.5">
                            <Switch
                              checked={phoneConfirmModalEnabled}
                              onCheckedChange={setPhoneConfirmModalEnabled}
                              aria-label="Modale de confirmation du numéro"
                            />
                            <span className="text-[10px] text-gray-500 font-medium">
                              {phoneConfirmModalEnabled ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                        </div>
                        {phoneConfirmModalEnabled && (
                          <div className="rounded-lg border border-slate-200 bg-slate-50/80 p-3 space-y-3">
                            <p className="text-[10px] font-semibold text-slate-700 uppercase tracking-wide">Textes de la modale (i18n)</p>
                            <p className="text-[10px] text-slate-500">
                              Laisser un champ vide pour une langue : l’app utilisera l’autre langue, puis les textes par défaut (anglais type Revolut).
                            </p>
                            <I18nField label="Titre (barre de la modale)" value={phoneModalTitleI18n} onChange={setPhoneModalTitleI18n} />
                            <I18nField
                              label="Sous-texte (sous le numéro)"
                              value={phoneModalDescriptionI18n}
                              onChange={setPhoneModalDescriptionI18n}
                              multiline
                            />
                            <I18nField label="Bouton principal (confirmer)" value={phoneModalConfirmI18n} onChange={setPhoneModalConfirmI18n} />
                            <I18nField label="Bouton secondaire (retour)" value={phoneModalBackI18n} onChange={setPhoneModalBackI18n} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>

              {/* Section 2: Components */}
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-6 h-6 rounded bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-bold">2</div>
                      <CardTitle className="text-sm font-semibold">Components ({components.length})</CardTitle>
                    </div>
                    {!showCompForm && (
                      <div className="flex gap-1">
                        <Button size="sm" variant="outline" className="h-7 text-xs border-emerald-300 text-emerald-700 hover:bg-emerald-50" onClick={() => {
                          setEditingCompId(null); setCompForm(emptyComp()); setCompMode('client_field'); setShowCompForm(true)
                        }}>+ Client Field</Button>
                        <Button size="sm" variant="outline" className="h-7 text-xs border-gray-300 text-gray-600 hover:bg-gray-50" onClick={() => {
                          setEditingCompId(null); setCompForm({ ...emptyComp(), component_type: 'section_title', binding_slug: '' }); setCompMode('content'); setShowCompForm(true)
                        }}>+ Content Block</Button>
                      </div>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  {(screenType === 'interaction' || screenType === 'permission_prompt') && (
                    <p className={`text-xs rounded p-2 border ${
                      screenType === 'interaction'
                        ? 'text-violet-800 bg-violet-50 border-violet-200'
                        : 'text-sky-900 bg-sky-50 border-sky-200'
                    }`}>
                      {screenType === 'interaction'
                        ? 'Interaction screens usually have no form components. You can still add content blocks if needed.'
                        : 'Les écrans permission (Face ID / notifications) n’ont pas de champs formulaire : tout passe par les deux boutons et decision_slug.'}
                    </p>
                  )}
                  {showCompForm && (
                    <div className={`p-3 border rounded-lg space-y-2 ${compMode === 'client_field' ? 'border-emerald-200 bg-emerald-50' : 'border-gray-200 bg-gray-50'}`}>
                      {/* Mode indicator */}
                      {!editingCompId && (
                        <div className="flex items-center gap-2 mb-1">
                          <Badge className={compMode === 'client_field' ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-200 text-gray-700'}>
                            {compMode === 'client_field' ? 'Client Field' : 'Content Block'}
                          </Badge>
                          <button className="text-[10px] text-blue-600 underline" onClick={() => {
                            if (compMode === 'client_field') {
                              setCompMode('content'); setCompForm(f => ({ ...f, component_type: 'section_title', binding_slug: '', _field_definition_id: undefined } as CompForm))
                            } else {
                              setCompMode('client_field'); setCompForm(f => ({ ...f, component_type: 'text_input' } as CompForm))
                            }
                          }}>Switch to {compMode === 'client_field' ? 'Content Block' : 'Client Field'}</button>
                        </div>
                      )}

                      {/* ─── Client Field mode: field catalog first ─── */}
                      {compMode === 'client_field' && (
                        <>
                          {!editingCompId && (
                            <div className="rounded-lg border-2 border-emerald-400 bg-emerald-50/80 p-2">
                              <label className="text-xs font-semibold text-emerald-900 mb-1 block">1. From Field Catalog (recommended)</label>
                              <p className="text-[10px] text-emerald-800 mb-1">Always start here for inputs — bindings and definitions stay compliant.</p>
                              <select className={inputCls}
                                onChange={e => {
                                  const fd = fieldCatalog.find(f => f.id === e.target.value)
                                  if (fd) applyFieldDef(fd)
                                }}
                                defaultValue="">
                                <option value="" disabled>Select from Field Catalog…</option>
                                {fieldCatalog.map(fd => (
                                  <option key={fd.id} value={fd.id}>
                                    {fd.label} ({fd.slug}) — {fd.field_type}
                                    {fd.category ? ` [${fd.category}]` : ''}
                                  </option>
                                ))}
                              </select>
                            </div>
                          )}
                          {compMode === 'client_field' && !editingCompId && !(compForm as CompForm & { _field_definition_id?: string })._field_definition_id && (
                            <div className="text-xs text-amber-950 bg-amber-100 border border-amber-400 rounded p-2">
                              <strong>Catalog required for new client fields.</strong> Select a row above before saving — custom-only inputs are blocked by the API.
                            </div>
                          )}
                          <div>
                            <label className="text-xs font-medium text-gray-600 mb-1 block">Widget type</label>
                            <select className={inputCls} value={compForm.component_type}
                              onChange={e => {
                                const v = e.target.value
                                setCompForm(f => {
                                  if (v === 'address_step' && f.component_type !== 'address_step') {
                                    return {
                                      ...f,
                                      component_type: v,
                                      ...ADDRESS_STEP_I18N_DEFAULTS,
                                      address_step_search_enabled: true,
                                      address_step_search_min_chars: '2',
                                      address_step_search_debounce_ms: '300',
                                      address_step_line2_optional: true,
                                    }
                                  }
                                  return { ...f, component_type: v }
                                })
                              }}>
                              {FIELD_BOUND_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="text-xs font-medium text-gray-600 mb-1 block">binding_slug</label>
                            <input className={inputCls + ' bg-gray-100 font-mono text-xs'} placeholder="auto-filled from field catalog" value={compForm.binding_slug}
                              onChange={e => setCompForm(f => ({ ...f, binding_slug: e.target.value }))} readOnly={!editingCompId} />
                          </div>
                          <input className={inputCls} placeholder="Label" value={compForm.label}
                            onChange={e => setCompForm(f => ({ ...f, label: e.target.value }))} />
                          <I18nField label="Label" value={compForm.label_i18n}
                            onChange={v => setCompForm(f => ({ ...f, label_i18n: v }))} />
                          <input className={inputCls} placeholder="Placeholder (optional)" value={compForm.placeholder}
                            onChange={e => setCompForm(f => ({ ...f, placeholder: e.target.value }))} />
                          <I18nField label="Placeholder" value={compForm.placeholder_i18n}
                            onChange={v => setCompForm(f => ({ ...f, placeholder_i18n: v }))} />
                          <label className="flex items-center gap-2 text-xs">
                            <input type="checkbox" checked={compForm.required}
                              onChange={e => setCompForm(f => ({ ...f, required: e.target.checked }))} /> Required
                          </label>
                          {['select', 'multi_select'].includes(compForm.component_type) && (
                            <textarea className={inputCls + ' h-20 font-mono'} placeholder='[{"value":"x","label":"X"}]'
                              value={compForm.options}
                              onChange={e => setCompForm(f => ({ ...f, options: e.target.value }))} />
                          )}
                          {compForm.component_type === 'checkbox' && (
                            <div className="space-y-2 p-2.5 border border-emerald-300 rounded-lg bg-white">
                              <span className="text-xs font-semibold text-emerald-700">Description &amp; Links (markdown)</span>
                              <textarea className={inputCls + ' h-20'}
                                placeholder={'Use [link text](url) for links.\nEx: [Terms](https://example.com/terms)'}
                                value={compForm.description}
                                onChange={e => setCompForm(f => ({ ...f, description: e.target.value }))} />
                              <I18nField label="Description" value={compForm.description_i18n}
                                onChange={v => setCompForm(f => ({ ...f, description_i18n: v }))} multiline />
                            </div>
                          )}
                          {compForm.component_type === 'address_step' && (
                            <div className="space-y-2 p-2.5 border border-indigo-200 rounded-lg bg-indigo-50/50">
                              <span className="text-xs font-semibold text-indigo-900">Address step (search-first)</span>
                              <p className="text-[10px] text-indigo-800/90 leading-snug">
                                Catalogue sur <span className="font-mono">address_line_1</span>. Textes : <span className="font-mono">title_i18n</span>, <span className="font-mono">subtitle_i18n</span>, etc. Des clés legacy (<span className="font-mono">title</span>, …) sont aussi écrites au save pour compatibilité.
                              </p>
                              <I18nField label="Titre (dans le widget)" value={compForm.address_step_title_i18n}
                                onChange={v => setCompForm(f => ({ ...f, address_step_title_i18n: v }))} />
                              <I18nField label="Sous-titre" value={compForm.address_step_subtitle_i18n}
                                onChange={v => setCompForm(f => ({ ...f, address_step_subtitle_i18n: v }))} multiline />
                              <label className="flex items-center gap-2 text-xs">
                                <input type="checkbox" checked={compForm.address_step_search_enabled}
                                  onChange={e => setCompForm(f => ({ ...f, address_step_search_enabled: e.target.checked }))} />
                                Search enabled
                              </label>
                              <I18nField label="Libellé barre de recherche" value={compForm.address_step_search_label_i18n}
                                onChange={v => setCompForm(f => ({ ...f, address_step_search_label_i18n: v }))} />
                              <I18nField label="Lien saisie manuelle" value={compForm.address_step_manual_label_i18n}
                                onChange={v => setCompForm(f => ({ ...f, address_step_manual_label_i18n: v }))} />
                              <div className="flex gap-2">
                                <div className="flex-1">
                                  <span className="text-[10px] text-gray-600 block mb-0.5">search_min_chars</span>
                                  <input className={inputCls + ' font-mono text-xs'} type="number" min={1} max={20}
                                    value={compForm.address_step_search_min_chars}
                                    onChange={e => setCompForm(f => ({ ...f, address_step_search_min_chars: e.target.value }))} />
                                </div>
                                <div className="flex-1">
                                  <span className="text-[10px] text-gray-600 block mb-0.5">search_debounce_ms</span>
                                  <input className={inputCls + ' font-mono text-xs'} type="number" min={50} max={5000}
                                    value={compForm.address_step_search_debounce_ms}
                                    onChange={e => setCompForm(f => ({ ...f, address_step_search_debounce_ms: e.target.value }))} />
                                </div>
                              </div>
                              <label className="flex items-center gap-2 text-xs">
                                <input type="checkbox" checked={compForm.address_step_line2_optional}
                                  onChange={e => setCompForm(f => ({ ...f, address_step_line2_optional: e.target.checked }))} />
                                address_line_2 optional (floor / unit)
                              </label>
                              <p className="rounded-md border border-emerald-200 bg-emerald-50/90 px-2 py-1.5 text-[10px] leading-snug text-emerald-900">
                                <strong>Parcours :</strong> placez un écran « + Country » (<span className="font-mono">country_of_residence</span>){' '}
                                <em>avant</em> cet écran. L’app n’affiche plus le pays sur Home address ; la recherche utilise la valeur déjà en session.
                              </p>
                              {selectedScreenId &&
                                components.some(
                                  c =>
                                    c.component_type === 'country_picker' &&
                                    c.binding_slug === 'country_of_residence',
                                ) && (
                                  <p className="rounded-md border border-amber-300 bg-amber-50 px-2 py-1.5 text-[10px] leading-snug text-amber-950">
                                    <strong>Attention :</strong> cet écran inclut encore un <span className="font-mono">country_picker</span> sur le même écran que l’adresse. Retirez-le pour éviter de redemander le pays (flux attendu : pays sur l’écran précédent uniquement).
                                  </p>
                                )}
                              <p className="text-[10px] font-semibold text-indigo-900 pt-1">Labels des champs ligne d’adresse (i18n) — pas le pays</p>
                              {ADDRESS_STEP_HOME_FIELD_KEYS.map(fk => (
                                <div key={`lbl-${fk}`} className="rounded border border-indigo-100 bg-white/80 p-2">
                                  <span className="text-[10px] font-mono text-gray-500 block mb-1">{fk}</span>
                                  <I18nField
                                    label="Label"
                                    value={compForm.address_step_field_labels_i18n[fk]}
                                    onChange={v => setCompForm(f => ({
                                      ...f,
                                      address_step_field_labels_i18n: {
                                        ...f.address_step_field_labels_i18n,
                                        [fk]: v,
                                      },
                                    }))}
                                  />
                                </div>
                              ))}
                              <p className="text-[10px] font-semibold text-indigo-900 pt-1">Placeholders / aide (i18n)</p>
                              {ADDRESS_STEP_HOME_FIELD_KEYS.map(fk => (
                                <div key={`ph-${fk}`} className="rounded border border-indigo-100 bg-white/80 p-2">
                                  <span className="text-[10px] font-mono text-gray-500 block mb-1">{fk}</span>
                                  <I18nField
                                    label="Placeholder / exemple"
                                    value={compForm.address_step_field_placeholders_i18n[fk]}
                                    onChange={v => setCompForm(f => ({
                                      ...f,
                                      address_step_field_placeholders_i18n: {
                                        ...f.address_step_field_placeholders_i18n,
                                        [fk]: v,
                                      },
                                    }))}
                                    multiline
                                  />
                                </div>
                              ))}
                              <AddressStepPreviewPanel form={compForm} />
                            </div>
                          )}
                          <RuleEditor
                            label="Visibility Rule (component)"
                            value={compForm.visibility_rule_json}
                            onChange={v => setCompForm(f => ({ ...f, visibility_rule_json: v }))}
                          />
                          <RuleEditor
                            label="Validation Rule"
                            value={compForm.validation_rule_json}
                            onChange={v => setCompForm(f => ({ ...f, validation_rule_json: v }))}
                          />
                        </>
                      )}

                      {/* ─── Content Block mode ─── */}
                      {compMode === 'content' && (
                        <>
                          <div>
                            <label className="text-xs font-medium text-gray-600 mb-1 block">Content type</label>
                            <select className={inputCls} value={compForm.component_type}
                              onChange={e => setCompForm(f => ({ ...f, component_type: e.target.value }))}>
                              {CONTENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                          </div>
                          <input className={inputCls} placeholder="Label / text content" value={compForm.label}
                            onChange={e => setCompForm(f => ({ ...f, label: e.target.value }))} />
                          <I18nField label="Label" value={compForm.label_i18n}
                            onChange={v => setCompForm(f => ({ ...f, label_i18n: v }))} />
                          {compForm.component_type === 'link_text' && (
                            <div className="space-y-2 p-2.5 border border-gray-300 rounded-lg bg-white">
                              <span className="text-xs font-semibold text-gray-700">Link settings</span>
                              <input className={inputCls} placeholder="Link label (e.g. Log in)"
                                value={compForm.link_label}
                                onChange={e => setCompForm(f => ({ ...f, link_label: e.target.value }))} />
                              <I18nField label="Link label" value={compForm.link_label_i18n}
                                onChange={v => setCompForm(f => ({ ...f, link_label_i18n: v }))} />
                              <input className={inputCls} placeholder="Link URL (e.g. https://...)"
                                value={compForm.link_url}
                                onChange={e => setCompForm(f => ({ ...f, link_url: e.target.value }))} />
                            </div>
                          )}
                          {['rich_text', 'legal_content', 'info_box'].includes(compForm.component_type) && (
                            <div>
                              <label className="text-xs font-medium text-gray-600 mb-1 block">Content (markdown)</label>
                              <textarea className={inputCls + ' h-20'}
                                placeholder="Rich text content…"
                                value={compForm.description}
                                onChange={e => setCompForm(f => ({ ...f, description: e.target.value }))} />
                              <I18nField label="Content" value={compForm.description_i18n}
                                onChange={v => setCompForm(f => ({ ...f, description_i18n: v }))} multiline />
                            </div>
                          )}
                          <RuleEditor
                            label="Visibility Rule (component)"
                            value={compForm.visibility_rule_json}
                            onChange={v => setCompForm(f => ({ ...f, visibility_rule_json: v }))}
                          />
                        </>
                      )}

                      <div className="flex gap-2">
                        <Button size="sm" className="h-7 text-xs flex-1" onClick={saveComponent}>
                          {editingCompId ? 'Update' : 'Create'}
                        </Button>
                        <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => {
                          setShowCompForm(false); setEditingCompId(null)
                        }}>Cancel</Button>
                      </div>
                    </div>
                  )}

                  {components.map((comp, idx) => {
                    const isFieldBound = (FIELD_BOUND_TYPES as readonly string[]).includes(comp.component_type)
                    return (
                      <div key={comp.id} className="p-3 rounded-lg border border-gray-200 bg-white">
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <Badge className={`text-[10px] ${isFieldBound ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                              {comp.component_type}
                            </Badge>
                            <Badge variant="outline" className={`text-[9px] px-1 py-0 ${isFieldBound ? 'border-emerald-300 text-emerald-600' : 'border-gray-300 text-gray-500'}`}>
                              {isFieldBound ? 'Client Field' : 'Content'}
                            </Badge>
                            {(() => {
                              const s = componentI18nSummary(comp)
                              return <I18nBadge level={s.level} tooltip={s.tip} />
                            })()}
                          </div>
                          {comp.binding_slug && (
                            <span className="text-[10px] text-gray-500 font-mono">{comp.binding_slug}</span>
                          )}
                        </div>
                        <div className="text-sm text-gray-900">
                          {typeof comp.props?.label === 'string'
                            ? comp.props.label
                            : typeof comp.props?.label === 'object' && comp.props.label
                              ? (comp.props.label as Record<string, string>).en || comp.component_type
                              : comp.component_type}
                        </div>
                        <div className="flex gap-1 mt-2">
                          <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-gray-100 disabled:opacity-30"
                            disabled={idx === 0} onClick={() => reorderComponent(idx, -1)}>▲</button>
                          <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-gray-100 disabled:opacity-30"
                            disabled={idx === components.length - 1} onClick={() => reorderComponent(idx, 1)}>▼</button>
                          <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-blue-50 text-blue-600"
                            onClick={() => startEditComp(comp)}>Edit</button>
                          <button className="px-1.5 py-0.5 text-xs border rounded hover:bg-red-50 text-red-600"
                            onClick={() => deleteComponent(comp.id)}>Del</button>
                        </div>
                      </div>
                    )
                  })}

                  {components.length === 0 && !showCompForm && (
                    <p className="text-xs text-gray-400 text-center py-4">No components yet</p>
                  )}
                </CardContent>
              </Card>

              {/* Section 3: Action Button */}
              <Card>
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded bg-green-100 flex items-center justify-center text-green-600 text-xs font-bold">3</div>
                    <CardTitle className="text-sm font-semibold">Action Button</CardTitle>
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-green-300 text-green-600">required</Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <label className="text-xs font-medium text-gray-700 mb-1 block">Button Label *</label>
                    <input className={inputCls} placeholder="e.g. Continue, Submit, Next"
                      value={buttonLabel} onChange={e => setButtonLabel(e.target.value)} />
                    <I18nField label="Button Label" value={buttonLabelI18n} onChange={setButtonLabelI18n} />
                  </div>
                </CardContent>
              </Card>

              {/* Save all structure */}
              <Button className="w-full" onClick={saveScreenStructure}>
                Save Screen Structure
              </Button>
            </div>
          )}
        </div>
      </div>

      <AlertDialog open={confirmDialog.open} onOpenChange={open => { if (!open) setConfirmDialog(d => ({ ...d, open: false })) }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{confirmDialog.title}</AlertDialogTitle>
            <AlertDialogDescription>{confirmDialog.description}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={() => { confirmDialog.onConfirm(); setConfirmDialog(d => ({ ...d, open: false })) }}
            >
              {confirmDialog.confirmLabel}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={publishOpen} onOpenChange={open => { setPublishOpen(open); if (!open) setPublishByName('') }}>
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <AlertDialogTitle>Publish flow</AlertDialogTitle>
            <AlertDialogDescription>
              The publish guard must pass (see Health). Enter who is publishing for the audit trail.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="py-2">
            <label className="text-xs font-medium text-gray-600 block mb-1">Published by</label>
            <input
              className={inputCls}
              placeholder="Name or email"
              value={publishByName}
              onChange={e => setPublishByName(e.target.value)}
              autoFocus
            />
          </div>
          <AlertDialogFooter className="gap-2 sm:gap-0">
            <AlertDialogCancel type="button">Cancel</AlertDialogCancel>
            <Button
              type="button"
              className="bg-green-600 hover:bg-green-700 text-white"
              disabled={!publishByName.trim() || publishing || (health !== null && !health.can_publish)}
              onClick={() => runPublish()}
            >
              {publishing ? 'Publishing…' : 'Publish now'}
            </Button>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
