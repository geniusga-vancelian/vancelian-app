'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { ArrowLeft, Send, Sparkles, RotateCcw, Code2, Copy } from 'lucide-react'

interface TemplateMeta {
  id: string
  description: string
  subjectExamples: { fr: string; en: string }
  fixture: Record<string, unknown> | null
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  /** Variables JSON produites par l'assistant (pour ce message uniquement). */
  vars?: Record<string, unknown>
  warnings?: string[]
}

interface ApiSuccess {
  ok: true
  templateId: string
  locale: 'fr' | 'en'
  vars: Record<string, unknown>
  subject: string
  html: string
  warnings: string[]
  model: string
  usage?: { inputTokens?: number; outputTokens?: number }
}

interface ApiError {
  ok: false
  error: string
  code: string
  details?: unknown
}

const TEMPLATE_OPTIONS = [
  { id: 'newsletter-quarterly', label: 'Newsletter trimestrielle' },
  { id: 'otp-login', label: 'OTP / Code de connexion' },
  { id: 'transaction-confirmation', label: 'Confirmation de transaction' },
  { id: 'welcome', label: 'Welcome / Onboarding' },
] as const

const LOCALES = ['fr', 'en'] as const

export default function EmailAiBuilderPage() {
  const search = useSearchParams()
  const initialTemplate = (search?.get('template') ?? 'newsletter-quarterly') as string
  const [templates, setTemplates] = useState<TemplateMeta[]>([])
  const [templateId, setTemplateId] = useState<string>(initialTemplate)
  const [locale, setLocale] = useState<'fr' | 'en'>('fr')
  const [prompt, setPrompt] = useState<string>('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [pending, setPending] = useState(false)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [previewSubject, setPreviewSubject] = useState<string>('')
  const [model, setModel] = useState<string>('')
  const [usage, setUsage] = useState<ApiSuccess['usage']>(undefined)
  const [errorBox, setErrorBox] = useState<string | null>(null)
  const [showVars, setShowVars] = useState(false)
  const [currentVars, setCurrentVars] = useState<Record<string, unknown> | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)

  /* Charge les templates pour récupérer fixtures + descriptions */
  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch('/api/admin/email/templates', { cache: 'no-store' })
        if (!res.ok) return
        const json = (await res.json()) as { items: TemplateMeta[] }
        setTemplates(json.items)
      } catch {
        /* silencieux */
      }
    })()
  }, [])

  /* Si on change de template, on reset le chat (nouveau contexte) */
  const onTemplateChange = (id: string) => {
    setTemplateId(id)
    setMessages([])
    setPreviewHtml(null)
    setPreviewSubject('')
    setCurrentVars(null)
    setErrorBox(null)
  }

  const tplMeta = useMemo(
    () => templates.find((t) => t.id === templateId),
    [templates, templateId],
  )

  const onReset = () => {
    setMessages([])
    setPreviewHtml(null)
    setPreviewSubject('')
    setCurrentVars(null)
    setErrorBox(null)
  }

  const onSubmit = async () => {
    if (!prompt.trim() || pending) return
    setErrorBox(null)
    const userMsg: ChatMessage = { role: 'user', content: prompt.trim() }
    setMessages((prev) => [...prev, userMsg])
    setPending(true)
    const submittedPrompt = prompt.trim()
    setPrompt('')

    try {
      const res = await fetch('/api/admin/email/ai-builder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          templateId,
          locale,
          prompt: submittedPrompt,
          previousVars: currentVars ?? undefined,
        }),
      })
      const json = (await res.json()) as ApiSuccess | ApiError
      if (!('ok' in json) || !json.ok) {
        const errMsg =
          ('error' in json && json.error) ||
          'Erreur inconnue lors de la génération.'
        setErrorBox(`${errMsg}${'code' in json && json.code ? ` (${json.code})` : ''}`)
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: `❌ Échec : ${errMsg}`,
          },
        ])
        return
      }
      setPreviewHtml(json.html)
      setPreviewSubject(json.subject)
      setCurrentVars(json.vars)
      setModel(json.model)
      setUsage(json.usage)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `✓ Email mis à jour. Subject: « ${json.subject} »${
            json.warnings.length ? ` — ${json.warnings.length} warning(s)` : ''
          }`,
          vars: json.vars,
          warnings: json.warnings,
        },
      ])
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err)
      setErrorBox(msg)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `❌ Erreur réseau : ${msg}` },
      ])
    } finally {
      setPending(false)
      inputRef.current?.focus()
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault()
      void onSubmit()
    }
  }

  return (
    <div className="space-y-4 max-w-[1500px]">
      <div className="flex items-center gap-3">
        <Link
          href="/admin/email"
          className="text-gray-500 hover:text-gray-900 inline-flex items-center gap-1 text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Hub
        </Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-2xl font-bold text-gray-900 inline-flex items-center gap-2">
          <Sparkles className="w-5 h-5 text-blue-500" /> AI Builder
        </h1>
      </div>

      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-3 bg-white border border-gray-200 rounded-lg p-3">
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Template
        </label>
        <select
          value={templateId}
          onChange={(e) => onTemplateChange(e.target.value)}
          className="text-sm border border-gray-300 rounded-md px-2 py-1 focus:ring-2 focus:ring-gray-900/10"
        >
          {TEMPLATE_OPTIONS.map((t) => (
            <option key={t.id} value={t.id}>
              {t.label}
            </option>
          ))}
        </select>

        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide ml-2">
          Locale
        </label>
        <div className="flex gap-1">
          {LOCALES.map((l) => (
            <button
              key={l}
              onClick={() => setLocale(l)}
              className={`px-2 py-0.5 text-xs rounded-full font-medium transition-colors ${
                locale === l
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-3 text-xs text-gray-500">
          {model && <span>Model: <code className="font-mono">{model}</code></span>}
          {usage?.inputTokens !== undefined && (
            <span>
              tokens: {usage.inputTokens} in / {usage.outputTokens ?? 0} out
            </span>
          )}
          <button
            onClick={onReset}
            disabled={pending || messages.length === 0}
            className="inline-flex items-center gap-1 px-2 py-1 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RotateCcw className="w-3 h-3" /> Reset
          </button>
        </div>
      </div>

      {tplMeta?.description && (
        <div className="text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-md px-3 py-2">
          <span className="font-mono text-xs text-gray-500">{tplMeta.id}</span> —{' '}
          {tplMeta.description}
        </div>
      )}

      <div
        className="grid gap-4"
        style={{ gridTemplateColumns: 'minmax(360px, 0.42fr) minmax(420px, 0.58fr)' }}
      >
        {/* Chat */}
        <div className="bg-white border border-gray-200 rounded-xl flex flex-col h-[calc(100vh-260px)] min-h-[480px]">
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {messages.length === 0 && (
              <div className="text-sm text-gray-500 space-y-2">
                <p>Décris l’email que tu veux générer en utilisant le template{' '}
                  <strong>{templateId}</strong> en <strong>{locale.toUpperCase()}</strong>.</p>
                <p className="text-xs">Exemples :</p>
                <ul className="text-xs list-disc pl-4 space-y-1 text-gray-600">
                  {EXAMPLES[templateId as keyof typeof EXAMPLES]?.map((ex, i) => (
                    <li key={i}>
                      <button
                        onClick={() => setPrompt(ex)}
                        className="text-left hover:underline text-gray-700"
                      >
                        {ex}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className={`text-sm rounded-lg px-3 py-2 ${
                  m.role === 'user'
                    ? 'bg-gray-900 text-white ml-8'
                    : 'bg-gray-50 text-gray-900 mr-8 border border-gray-200'
                }`}
              >
                {m.content}
                {m.warnings && m.warnings.length > 0 && (
                  <ul className="mt-1 text-[11px] text-amber-700 list-disc pl-4">
                    {m.warnings.map((w, j) => (
                      <li key={j}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
            {pending && (
              <div className="text-sm text-gray-500 italic">
                Génération en cours…
              </div>
            )}
            {errorBox && (
              <div className="text-xs bg-red-50 text-red-800 border border-red-200 rounded-md p-2 font-mono whitespace-pre-wrap">
                {errorBox}
              </div>
            )}
          </div>
          <div className="border-t border-gray-200 p-3">
            <textarea
              ref={inputRef}
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={
                currentVars
                  ? 'Modifier l’email (ex: "raccourcis l’intro et change le CTA en \'Open client space\'")'
                  : 'Décris l’email à générer…'
              }
              rows={3}
              disabled={pending}
              className="w-full resize-none text-sm border border-gray-300 rounded-md px-3 py-2 focus:ring-2 focus:ring-gray-900/10 focus:border-gray-400 disabled:opacity-60"
            />
            <div className="flex items-center justify-between mt-2">
              <span className="text-[11px] text-gray-400">⌘/Ctrl + Enter pour envoyer</span>
              <button
                onClick={() => void onSubmit()}
                disabled={!prompt.trim() || pending}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-gray-900 text-white text-sm rounded-md hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Send className="w-3.5 h-3.5" />
                {pending ? 'Envoi…' : currentVars ? 'Itérer' : 'Générer'}
              </button>
            </div>
          </div>
        </div>

        {/* Preview */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden flex flex-col h-[calc(100vh-260px)] min-h-[480px]">
          <div className="px-4 py-2 border-b border-gray-100 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs text-gray-500 uppercase tracking-wide">Preview</div>
              <div className="text-sm font-medium text-gray-900 truncate">
                {previewSubject || '— en attente de génération —'}
              </div>
            </div>
            <div className="flex gap-1">
              <button
                onClick={() => setShowVars((v) => !v)}
                disabled={!currentVars}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700 disabled:opacity-40"
              >
                <Code2 className="w-3 h-3" /> {showVars ? 'Masquer JSON' : 'Voir JSON'}
              </button>
              <CopyHtmlButton html={previewHtml} />
            </div>
          </div>

          <div className="flex-1 overflow-hidden bg-gray-50">
            {previewHtml ? (
              <iframe
                title="ai-preview"
                srcDoc={previewHtml}
                className="w-full h-full bg-white"
              />
            ) : (
              <div className="h-full flex items-center justify-center text-sm text-gray-400">
                Aucune génération encore. Lance un prompt à gauche.
              </div>
            )}
          </div>

          {showVars && currentVars && (
            <div className="border-t border-gray-200 p-3 max-h-72 overflow-auto bg-gray-900">
              <pre className="text-gray-100 text-[11px] leading-relaxed font-mono">
                {JSON.stringify(currentVars, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function CopyHtmlButton({ html }: { html: string | null }) {
  const [copied, setCopied] = useState(false)
  const onCopy = async () => {
    if (!html) return
    try {
      await navigator.clipboard.writeText(html)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* refusé */
    }
  }
  return (
    <button
      onClick={onCopy}
      disabled={!html}
      className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700 disabled:opacity-40"
    >
      <Copy className="w-3 h-3" /> {copied ? 'Copié ✓' : 'Copier HTML'}
    </button>
  )
}

const EXAMPLES = {
  'newsletter-quarterly': [
    'Génère la newsletter Q3 2026 sur le lancement de notre nouveau vault « Asia Real Estate », avec un CTA vers /vaults/asia-real-estate.',
    'Crée une lettre courte sur le sujet « Custody on-chain et MiCA », ton institutionnel, 2 highlights produits.',
  ],
  'otp-login': [
    'Code OTP pour Sarah Chen, 6 chiffres, expiration 10 minutes, depuis Geneva (IP 92.184.111.12), MacBook Pro Safari.',
    'Code OTP de connexion court (sans device info) pour un client mobile, expiration 5 minutes.',
  ],
  'transaction-confirmation': [
    'Confirmation d’une souscription au vault Gold Backed Yield, USD 50,000, fees USD 250, ref ARQ-2026-05-000310, settled le 30 mai 2026.',
    'Confirmation d’un retrait (REDEMPTION) de EUR 12,000 du vault Real Estate, ref ARQ-2026-05-000312, statut « En cours d’exécution ».',
  ],
  welcome: [
    'Email de bienvenue pour Marc Dubois qui vient de finaliser son KYC, avec un focus sur Vault Builder.',
    'Welcome onboarding pour un client institutionnel (entreprise), ton plus formel, lien vers une démo dédiée.',
  ],
} as const
