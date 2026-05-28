'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import {
  APPLY_DEPOSIT_WARNING,
  APPLY_DISABLED_NO_RAW_MESSAGE,
  autoFixRiskBadgeClass,
  correctionActionUrl,
  correctionStatusBadgeClass,
  discrepancyActionUrl,
  discrepancyDetailUrl,
  severityBadgeClass,
  statusBadgeClass,
} from '@/lib/admin/onchainReconciliationApi'

interface AutoFixRisk {
  level: string
  label: string
  detail: string
}

interface OnchainProof {
  chain_id?: number
  tx_hash?: string | null
  log_index?: number | null
  block_number?: number | null
  explorer_tx_url?: string | null
  explorer_label?: string | null
  candidate_events?: Array<Record<string, unknown>>
  inferred_from_latest_raw_event?: boolean
}

interface DiscrepancyDetail {
  discrepancy: Record<string, unknown>
  likely_sources?: string[]
  auto_fix_risk?: AutoFixRisk
  onchain_proof?: OnchainProof
  raw_onchain_event?: Record<string, unknown> | null
  corrections: Array<Record<string, unknown>>
  transaction_intent?: Record<string, unknown> | null
}

interface PreviewResult {
  action: string
  risk_level: string
  requires_second_approval: boolean
  allowed_to_apply: boolean
  before_json: Record<string, unknown>
  after_json: Record<string, unknown>
  correction_id?: string
}

const APPLY_ACTION = 'create_missing_deposit_from_raw_event'

export default function OnchainReconciliationDetailPage() {
  const params = useParams()
  const router = useRouter()
  const id = String(params.id || '')

  const [detail, setDetail] = useState<DiscrepancyDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [note, setNote] = useState('')
  const [resolveNote, setResolveNote] = useState('')
  const [preview, setPreview] = useState<PreviewResult | null>(null)
  const [activeCorrectionId, setActiveCorrectionId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(discrepancyDetailUrl(id), {
        cache: 'no-store',
        credentials: 'include',
      })
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Introuvable')
      setDetail(data)
      const pending = (data.corrections as Array<Record<string, unknown>>)?.find(
        (c) =>
          c.status === 'requested' ||
          c.status === 'approved' ||
          (c.status === 'preview' && c.metadata_json && (c.metadata_json as Record<string, unknown>).allowed_to_apply),
      )
      setActiveCorrectionId(pending ? String(pending.id) : null)
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setLoading(false)
    }
  }, [id, router])

  useEffect(() => {
    if (id) load()
  }, [id, load])

  const postDiscrepancyAction = async (action: string, body: Record<string, unknown> = {}) => {
    setBusy(true)
    try {
      const res = await fetch(discrepancyActionUrl(id, action), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || data.error || 'Échec')
      toastSuccess(`Action ${action} enregistrée`)
      if (action === 'preview-correction') {
        setPreview(data as PreviewResult)
      } else {
        setPreview(null)
        await load()
      }
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setBusy(false)
    }
  }

  const postCorrectionAction = async (correctionId: string, action: string) => {
    setBusy(true)
    try {
      const res = await fetch(correctionActionUrl(correctionId, action), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || data.error || 'Échec')
      toastSuccess(`Correction ${action}`)
      await load()
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setBusy(false)
    }
  }

  const requestCorrection = async () => {
    const raw = detail?.raw_onchain_event
    if (!raw?.id) {
      toastError(APPLY_DISABLED_NO_RAW_MESSAGE)
      return
    }
    setBusy(true)
    try {
      const res = await fetch(discrepancyActionUrl(id, 'request-correction'), {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: APPLY_ACTION,
          raw_onchain_event_id: raw.id,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Échec')
      toastSuccess('Correction demandée')
      setActiveCorrectionId(String(data.id))
      await load()
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <p className="text-sm text-muted-foreground">Chargement…</p>
  }

  if (!detail?.discrepancy) {
    return (
      <div>
        <Link href="/admin/onchain-reconciliation">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Retour
          </Button>
        </Link>
        <p className="mt-4 text-sm text-muted-foreground">Écart introuvable.</p>
      </div>
    )
  }

  const d = detail.discrepancy
  const hasRawProof = Boolean(detail.raw_onchain_event?.id)
  const activeCorrection = detail.corrections.find((c) => String(c.id) === activeCorrectionId)
  const correctionStatus = activeCorrection ? String(activeCorrection.status || '') : ''
  const canApply =
    hasRawProof &&
    correctionStatus === 'approved' &&
    Boolean(
      activeCorrection?.metadata_json &&
        (activeCorrection.metadata_json as Record<string, unknown>).allowed_to_apply !== false,
    )

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center gap-4 flex-wrap">
        <Link href="/admin/onchain-reconciliation">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Liste
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-semibold">Écart {String(d.discrepancy_type)}</h1>
          <p className="text-xs text-muted-foreground font-mono">{id}</p>
        </div>
        <Badge variant="outline" className={severityBadgeClass(String(d.severity))}>
          {String(d.severity)}
        </Badge>
        <Badge variant="outline" className={statusBadgeClass(String(d.status))}>
          {String(d.status)}
        </Badge>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Résumé</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm md:grid-cols-2">
          <div>
            <span className="text-muted-foreground">Person</span>{' '}
            <Link
              href={`/admin/customers/${d.person_id}`}
              className="font-mono text-xs underline"
            >
              {String(d.person_id)}
            </Link>
          </div>
          <div>
            <span className="text-muted-foreground">Wallet</span>{' '}
            <span className="font-mono text-xs">{String(d.wallet_address || '—')}</span>
          </div>
          <div>
            <span className="text-muted-foreground">Layer</span> {String(d.layer)}
          </div>
          <div>
            <span className="text-muted-foreground">Asset</span> {String(d.asset || '—')}
          </div>
          <div>DB: {String(d.db_amount ?? '—')}</div>
          <div>On-chain: {String(d.onchain_amount ?? '—')}</div>
          <div>Delta: {String(d.delta ?? '—')}</div>
          <div>
            Réf: {String(d.reference_type || '—')} / {String(d.reference_id || '—')}
          </div>
        </CardContent>
      </Card>

      {detail.likely_sources && detail.likely_sources.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Likely source</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc pl-5 text-sm space-y-1 text-muted-foreground">
              {detail.likely_sources.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {detail.auto_fix_risk && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Risk if auto-fixed</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Badge
              variant="outline"
              className={autoFixRiskBadgeClass(detail.auto_fix_risk.level)}
            >
              {detail.auto_fix_risk.label}
            </Badge>
            <p className="text-sm text-muted-foreground">{detail.auto_fix_risk.detail}</p>
          </CardContent>
        </Card>
      )}

      {detail.onchain_proof && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Preuve on-chain / explorer</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>
              <span className="text-muted-foreground">chain_id</span>{' '}
              {String(detail.onchain_proof.chain_id ?? '—')}
            </div>
            <div className="font-mono text-xs break-all">
              tx_hash: {detail.onchain_proof.tx_hash || '—'}
            </div>
            {detail.onchain_proof.explorer_tx_url && (
              <a
                href={detail.onchain_proof.explorer_tx_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex text-primary underline text-sm"
              >
                Ouvrir {detail.onchain_proof.explorer_label || 'explorer'} →
              </a>
            )}
          </CardContent>
        </Card>
      )}

      {detail.transaction_intent && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Transaction intent</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-2 text-sm md:grid-cols-2">
            <div>
              <span className="text-muted-foreground">product</span>{' '}
              {String(detail.transaction_intent.product_type)}
            </div>
            <div>
              <span className="text-muted-foreground">operation</span>{' '}
              {String(detail.transaction_intent.operation_type)}
            </div>
            <div>
              <span className="text-muted-foreground">status</span>{' '}
              <Badge variant="outline">{String(detail.transaction_intent.status)}</Badge>
            </div>
            <div className="font-mono text-xs break-all">
              tx: {String(detail.transaction_intent.tx_hash || '—')}
            </div>
            <div>
              linked: {String(detail.transaction_intent.linked_table || '—')} /{' '}
              <span className="font-mono text-xs">
                {String(
                  detail.transaction_intent.linked_reference_id ||
                    detail.transaction_intent.linked_id ||
                    '—',
                )}
              </span>
            </div>
            <div>
              <Link
                href="/admin/onchain-reconciliation/intents"
                className="text-primary underline text-xs"
              >
                Voir tous les intents →
              </Link>
            </div>
            {String(detail.transaction_intent.product_type) === 'bundle_invest' &&
              Array.isArray(
                (detail.transaction_intent.metadata_json as { legs?: unknown })?.legs,
              ) && (
                <div className="md:col-span-2 overflow-x-auto">
                  <p className="text-muted-foreground text-xs mb-2">Legs bundle</p>
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="text-left text-muted-foreground border-b">
                        <th className="py-1 pr-2">asset</th>
                        <th className="py-1 pr-2">weight</th>
                        <th className="py-1 pr-2">status</th>
                        <th className="py-1 pr-2">swap_id</th>
                        <th className="py-1 pr-2">tx_hash</th>
                        <th className="py-1">leg_id</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        (detail.transaction_intent.metadata_json as { legs: Array<Record<string, unknown>> })
                          .legs
                      ).map((leg, idx) => (
                        <tr key={`${String(leg.leg_id)}-${idx}`} className="border-b border-muted/30">
                          <td className="py-1 pr-2">{String(leg.asset ?? '—')}</td>
                          <td className="py-1 pr-2">{String(leg.target_weight ?? '—')}</td>
                          <td className="py-1 pr-2">
                            <Badge variant="outline">{String(leg.status ?? '—')}</Badge>
                          </td>
                          <td className="py-1 pr-2 font-mono truncate max-w-[100px]">
                            {String(leg.swap_id ?? '—')}
                          </td>
                          <td className="py-1 pr-2 font-mono truncate max-w-[120px]">
                            {String(leg.tx_hash ?? '—')}
                          </td>
                          <td className="py-1 font-mono truncate max-w-[100px]">
                            {String(leg.leg_id ?? '—')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            {String(detail.transaction_intent.product_type) === 'lombard_borrow' &&
              Array.isArray(
                (detail.transaction_intent.metadata_json as { steps?: unknown })?.steps,
              ) && (
                <div className="md:col-span-2 overflow-x-auto">
                  <p className="text-muted-foreground text-xs mb-2">Steps Lombard</p>
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="text-left text-muted-foreground border-b">
                        <th className="py-1 pr-2">step</th>
                        <th className="py-1 pr-2">tx_index</th>
                        <th className="py-1 pr-2">status</th>
                        <th className="py-1 pr-2">tx_hash</th>
                        <th className="py-1">ledger_entry_id</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        (detail.transaction_intent.metadata_json as { steps: Array<Record<string, unknown>> })
                          .steps
                      ).map((step, idx) => (
                        <tr key={`${String(step.step)}-${idx}`} className="border-b border-muted/30">
                          <td className="py-1 pr-2">{String(step.step ?? '—')}</td>
                          <td className="py-1 pr-2">{String(step.tx_index ?? '—')}</td>
                          <td className="py-1 pr-2">
                            <Badge variant="outline">{String(step.status ?? '—')}</Badge>
                          </td>
                          <td className="py-1 pr-2 font-mono truncate max-w-[140px]">
                            {String(step.tx_hash ?? '—')}
                          </td>
                          <td className="py-1 font-mono truncate max-w-[120px]">
                            {String(step.ledger_entry_id ?? '—')}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
          </CardContent>
        </Card>
      )}

      {detail.raw_onchain_event ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Événement raw_onchain_events (preuve)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {detail.raw_onchain_event.consumed_by_correction_id && (
              <p className="text-sm text-amber-800 font-medium">
                Consommé par correction{' '}
                <span className="font-mono text-xs">
                  {String(detail.raw_onchain_event.consumed_by_correction_id)}
                </span>
              </p>
            )}
            <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-48">
              {JSON.stringify(detail.raw_onchain_event, null, 2)}
            </pre>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-amber-200 bg-amber-50/50">
          <CardContent className="pt-6 text-sm text-amber-900">
            Balance-only / manual review — aucun raw_onchain_event vérifié lié à cet écart.
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Workflow correction (Phase 5B)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {hasRawProof && (
            <p className="text-sm text-muted-foreground border-l-4 border-primary pl-3">
              {APPLY_DEPOSIT_WARNING}
            </p>
          )}
          {!hasRawProof && (
            <p className="text-sm font-medium text-amber-800">{APPLY_DISABLED_NO_RAW_MESSAGE}</p>
          )}

          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              disabled={busy || !hasRawProof}
              onClick={() => postDiscrepancyAction('preview-correction', {})}
            >
              Preview correction
            </Button>
            <Button
              variant="default"
              disabled={busy || !hasRawProof}
              onClick={requestCorrection}
            >
              Request correction
            </Button>
            {activeCorrectionId && correctionStatus === 'requested' && (
              <>
                <Button
                  variant="outline"
                  disabled={busy}
                  onClick={() => postCorrectionAction(activeCorrectionId, 'approve')}
                >
                  Approve correction
                </Button>
                <Button
                  variant="ghost"
                  disabled={busy}
                  onClick={() => postCorrectionAction(activeCorrectionId, 'reject')}
                >
                  Reject
                </Button>
              </>
            )}
            <Button
              variant="destructive"
              disabled={busy || !canApply}
              title={!hasRawProof ? APPLY_DISABLED_NO_RAW_MESSAGE : undefined}
              onClick={() =>
                activeCorrectionId && postCorrectionAction(activeCorrectionId, 'apply')
              }
            >
              Apply
            </Button>
          </div>

          {activeCorrection && (
            <div className="text-xs text-muted-foreground">
              Correction active:{' '}
              <Badge
                variant="outline"
                className={correctionStatusBadgeClass(correctionStatus)}
              >
                {correctionStatus}
              </Badge>{' '}
              — {String(activeCorrection.action)}
            </div>
          )}

          <Input
            placeholder="Note optionnelle (ack / ignore)"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <div className="flex flex-wrap gap-2 border-t pt-4">
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => postDiscrepancyAction('acknowledge', { note: note || undefined })}
            >
              Acknowledge
            </Button>
            <Button
              variant="outline"
              disabled={busy}
              onClick={() => postDiscrepancyAction('ignore', { note: note || undefined })}
            >
              Ignore
            </Button>
          </div>
          <div className="space-y-2 border-t pt-4">
            <label className="text-sm font-medium">Resolve manually</label>
            <Textarea
              value={resolveNote}
              onChange={(e) => setResolveNote(e.target.value)}
              placeholder="Note de résolution manuelle (obligatoire)"
              rows={3}
            />
            <Button
              variant="outline"
              disabled={busy || !resolveNote.trim()}
              onClick={() =>
                postDiscrepancyAction('resolve-manually', {
                  note: resolveNote.trim(),
                  resolution_code: 'manual',
                })
              }
            >
              Resolve manually
            </Button>
          </div>
        </CardContent>
      </Card>

      {preview && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Preview correction</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>
              Action: <code>{preview.action}</code> — risque {preview.risk_level}
            </div>
            <div>
              allowed_to_apply:{' '}
              <strong>{preview.allowed_to_apply ? 'true' : 'false'}</strong>
            </div>
            <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-40">
              {JSON.stringify(preview.after_json, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Journal des corrections (audit)</CardTitle>
        </CardHeader>
        <CardContent>
          {detail.corrections.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucune correction enregistrée.</p>
          ) : (
            <div className="space-y-4">
              {detail.corrections.map((c) => (
                <div key={String(c.id)} className="border rounded-lg p-3 space-y-2 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="text-xs">{String(c.action)}</code>
                    <Badge
                      variant="outline"
                      className={correctionStatusBadgeClass(String(c.status || 'preview'))}
                    >
                      {String(c.status || 'preview')}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">{String(c.id)}</span>
                  </div>
                  <div className="grid gap-1 text-xs md:grid-cols-2">
                    <div>
                      <span className="text-muted-foreground">requested_by</span>{' '}
                      {String(c.requested_by || '—')}
                      {c.requested_at ? (
                        <span className="text-muted-foreground">
                          {' '}
                          · {new Date(String(c.requested_at)).toLocaleString('fr-FR')}
                        </span>
                      ) : null}
                    </div>
                    <div>
                      <span className="text-muted-foreground">approved_by</span>{' '}
                      {String(c.approved_by || '—')}
                      {c.approved_at ? (
                        <span className="text-muted-foreground">
                          {' '}
                          · {new Date(String(c.approved_at)).toLocaleString('fr-FR')}
                        </span>
                      ) : null}
                    </div>
                    <div>
                      <span className="text-muted-foreground">applied_by</span>{' '}
                      {String(c.applied_by || '—')}
                      {c.applied_at ? (
                        <span className="text-muted-foreground">
                          {' '}
                          · {new Date(String(c.applied_at)).toLocaleString('fr-FR')}
                        </span>
                      ) : null}
                    </div>
                    <div>
                      <span className="text-muted-foreground">rejected_by</span>{' '}
                      {String(c.rejected_by || '—')}
                      {c.reject_reason ? (
                        <span className="text-muted-foreground"> — {String(c.reject_reason)}</span>
                      ) : null}
                    </div>
                  </div>
                  <details className="text-xs">
                    <summary className="cursor-pointer text-muted-foreground">before_json / after_json</summary>
                    <div className="mt-2 grid gap-2 md:grid-cols-2">
                      <pre className="bg-muted p-2 rounded overflow-auto max-h-32">
                        {JSON.stringify(c.before_json ?? {}, null, 2)}
                      </pre>
                      <pre className="bg-muted p-2 rounded overflow-auto max-h-32">
                        {JSON.stringify(c.after_json ?? {}, null, 2)}
                      </pre>
                    </div>
                  </details>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
