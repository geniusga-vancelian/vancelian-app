'use client'

/**
 * Admin — catalogue des tools agent ``action`` + whitelist CTA
 * (`action_cta_catalog`). Données : GET proxy FastAPI.
 */
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { Loader2, MousePointerClick, RefreshCw } from 'lucide-react'

import { AssistanceAdminHubNav } from '@/components/admin/AssistanceAdminHubNav'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { toastError } from '@/lib/admin/toast'

type CtaRow = {
  kind: string
  default_label: string
  deep_link_template: string
  available_phase_2b: boolean
  requires_param: string | null
}

type ToolRow = {
  tool_name: string
  title: string
  tool_description_llm: string
  autonomy_level: string
  client_flow_steps: string[]
  related_cta_kinds: string[]
}

type Payload = {
  doc_revision: string
  source_files_note: string[]
  action_agent_tools: ToolRow[]
  cta_whitelist: CtaRow[]
}

export default function AgentActionOptionsPage() {
  const [data, setData] = useState<Payload | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/assistance/agent-action-options')
      const json = await res.json().catch(() => null)
      if (!res.ok) {
        toastError(
          typeof json?.error === 'string' ? json.error : 'Impossible de charger le catalogue',
        )
        setData(null)
        return
      }
      setData(json as Payload)
    } catch {
      toastError('Réponse invalide ou réseau indisponible')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <MousePointerClick className="h-7 w-7 text-indigo-600" aria-hidden />
            <h1 className="text-2xl font-semibold tracking-tight text-slate-900">
              Options agent action
            </h1>
          </div>
          <p className="max-w-3xl text-sm text-slate-600">
            Parcours côté app pour les actions poussées par l&apos;assistant&nbsp;: tools
            registrés sous l&apos;agent <code className="rounded bg-slate-100 px-1">action</code> et liens{' '}
            <code className="rounded bg-slate-100 px-1">vancelian://</code>{' '}
            whitelistés. Les étapes décrites sont à maintenir côté API Python jusqu&apos;à une
            future persistance CMS.
          </p>
          <nav className="text-xs">
            <Link href="/admin/assistance" className="text-indigo-600 hover:underline">
              ← Assistance admin
            </Link>
          </nav>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={loading}
          onClick={() => void load()}
          className="gap-2"
        >
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          ) : (
            <RefreshCw className="h-4 w-4" aria-hidden />
          )}
          Actualiser
        </Button>
      </div>

      <AssistanceAdminHubNav />

      {loading && !data ? (
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
          Chargement…
        </div>
      ) : null}

      {data ? (
        <Alert className="border-slate-200 bg-white">
          <AlertTitle className="text-slate-800">Révision doc · {data.doc_revision}</AlertTitle>
          <AlertDescription className="text-slate-600">
            Fichiers source listés côté API&nbsp;:
            <ul className="mt-2 list-inside list-disc text-xs">
              {data.source_files_note.map((p) => (
                <li key={p}>
                  <code className="rounded bg-slate-50 px-1">{p}</code>
                </li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      ) : null}

      {data ? (
        <div className="grid gap-6 lg:grid-cols-1">
          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle>Tools agent action</CardTitle>
              <CardDescription>
                Description LLM telle qu&apos;exposée au modèle + étapes côté client pour mener
                l&apos;action dans l&apos;app.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {data.action_agent_tools.map((t) => (
                <div
                  key={t.tool_name}
                  className="rounded-lg border border-slate-100 bg-slate-50/50 p-4"
                >
                  <div className="flex flex-wrap items-baseline gap-2">
                    <h3 className="font-medium text-slate-900">{t.title}</h3>
                    <code className="rounded bg-white px-1.5 py-0.5 text-xs text-indigo-800 ring-1 ring-indigo-100">
                      {t.tool_name}
                    </code>
                    <Badge variant="secondary" className="text-[10px] font-normal">
                      {t.autonomy_level}
                    </Badge>
                  </div>
                  {t.tool_description_llm ? (
                    <p className="mt-2 text-sm text-slate-600 whitespace-pre-wrap">
                      {t.tool_description_llm}
                    </p>
                  ) : null}
                  <p className="mt-3 text-xs font-medium uppercase tracking-wide text-slate-500">
                    Flow client
                  </p>
                  <ol className="mt-1 list-decimal space-y-1 pl-5 text-sm text-slate-700">
                    {t.client_flow_steps.map((step, i) => (
                      <li key={i}>{step}</li>
                    ))}
                  </ol>
                  {t.related_cta_kinds.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      <span className="text-xs text-slate-500">CTA liées&nbsp;:</span>
                      {t.related_cta_kinds.map((k) => (
                        <Badge key={k} variant="outline" className="font-mono text-[10px]">
                          {k}
                        </Badge>
                      ))}
                    </div>
                  ) : null}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card className="border-slate-200">
            <CardHeader>
              <CardTitle>Whitelist des kinds CTA</CardTitle>
              <CardDescription>
                Schémas <code className="rounded bg-slate-100 px-1">vancelian://</code> — alignés
                Flutter resolver + <code className="rounded bg-slate-100 px-1">build_action</code>.
              </CardDescription>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Kind</TableHead>
                    <TableHead>Label défaut</TableHead>
                    <TableHead>Template deep-link</TableHead>
                    <TableHead className="whitespace-nowrap">Phase 2b</TableHead>
                    <TableHead>Param requis</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.cta_whitelist.map((r) => (
                    <TableRow key={r.kind}>
                      <TableCell className="font-mono text-xs">{r.kind}</TableCell>
                      <TableCell className="max-w-[200px] text-sm">{r.default_label}</TableCell>
                      <TableCell className="max-w-md font-mono text-xs break-all">
                        {r.deep_link_template}
                      </TableCell>
                      <TableCell>
                        {r.available_phase_2b ? (
                          <Badge className="bg-emerald-600 hover:bg-emerald-600">oui</Badge>
                        ) : (
                          <Badge variant="secondary">non</Badge>
                        )}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {r.requires_param ?? '—'}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  )
}
