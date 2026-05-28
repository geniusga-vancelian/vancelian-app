'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, ExternalLink, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { toastError } from '@/lib/admin/toast'
import { ONCHAIN_RECONCILIATION_BFF_BASE } from '@/lib/admin/onchainReconciliationApi'

type ProductHealth = {
  product_type: string
  total: number
  by_status: Record<string, number>
  stale: number
  without_raw_onchain_event: number
  submitted_too_old: number
  confirmed_without_ledger: number
  success_rate: number | null
  partial_rate: number | null
}

type StalePreview = {
  intent_id: string
  person_id: string
  product_type: string
  status: string
  age_minutes: number
  ttl_minutes: number
  severity: string
  discrepancy_type: string
}

type HealthPayload = {
  generated_at: string
  global: {
    total_intents: number
    stale_intents: number
    ttl_policy_minutes: Record<string, number>
  }
  by_product: ProductHealth[]
  stale_preview: StalePreview[]
  top_anomalies: Array<{ discrepancy_type: string; count: number }>
}

function pct(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—'
  return `${(value * 100).toFixed(1)} %`
}

function intentsFilterUrl(productType: string, status?: string): string {
  const qs = new URLSearchParams({ product_type: productType })
  if (status) qs.set('status', status)
  return `/admin/onchain-reconciliation/intents?${qs.toString()}`
}

export default function TransactionIntentHealthPage() {
  const [data, setData] = useState<HealthPayload | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${ONCHAIN_RECONCILIATION_BFF_BASE}/health`, {
        cache: 'no-store',
      })
      if (!res.ok) {
        const text = await res.text()
        throw new Error(text || `HTTP ${res.status}`)
      }
      setData((await res.json()) as HealthPayload)
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erreur chargement santé')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <Link href="/admin/onchain-reconciliation">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Réconciliation
          </Button>
        </Link>
        <h1 className="text-2xl font-semibold">Santé transaction intents</h1>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Actualiser
        </Button>
        <Link href="/admin/onchain-reconciliation/intents">
          <Button variant="outline" size="sm">
            Liste intents
            <ExternalLink className="h-3 w-3 ml-2" />
          </Button>
        </Link>
      </div>

      {data && (
        <>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Intents totaux
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{data.global.total_intents}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Généré {new Date(data.generated_at).toLocaleString('fr-FR')}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Stale (TTL dépassé)
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold text-amber-700">
                  {data.global.stale_intents}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Politique TTL (minutes)
                </CardTitle>
              </CardHeader>
              <CardContent className="text-xs space-y-1 font-mono">
                {Object.entries(data.global.ttl_policy_minutes).map(([k, v]) => (
                  <div key={k}>
                    {k}: {v} min
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            {data.by_product.map((row) => (
              <Card key={row.product_type}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-base font-mono">{row.product_type}</CardTitle>
                  <Link href={intentsFilterUrl(row.product_type)}>
                    <Button variant="ghost" size="sm" className="text-xs">
                      Voir intents
                    </Button>
                  </Link>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Total</span>
                    <span className="font-medium">{row.total}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Stale</span>
                    <Badge variant="outline" className="text-amber-800">
                      {row.stale}
                    </Badge>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Taux succès</span>
                    <span>{pct(row.success_rate)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Taux partial</span>
                    <span>{pct(row.partial_rate)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Sans raw event</span>
                    <span>{row.without_raw_onchain_event}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Submitted trop ancien</span>
                    <span>{row.submitted_too_old}</span>
                  </div>
                  {row.confirmed_without_ledger > 0 && (
                    <div className="flex justify-between text-amber-900">
                      <span>Confirmed sans ledger</span>
                      <span>{row.confirmed_without_ledger}</span>
                    </div>
                  )}
                  <div className="flex flex-wrap gap-1 pt-1">
                    {Object.entries(row.by_status).map(([st, n]) => (
                      <Link key={st} href={intentsFilterUrl(row.product_type, st)}>
                        <Badge variant="secondary" className="text-xs cursor-pointer">
                          {st}: {n}
                        </Badge>
                      </Link>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Top anomalies (layer=intent)</CardTitle>
              </CardHeader>
              <CardContent>
                {data.top_anomalies.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucune anomaly ouverte.</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead className="text-right">Count</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.top_anomalies.map((row) => (
                        <TableRow key={row.discrepancy_type}>
                          <TableCell className="font-mono text-xs">
                            {row.discrepancy_type}
                          </TableCell>
                          <TableCell className="text-right">{row.count}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Stale intents (aperçu)</CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                {data.stale_preview.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Aucun intent stale.</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Produit</TableHead>
                        <TableHead>Statut</TableHead>
                        <TableHead>Âge</TableHead>
                        <TableHead>Sev.</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {data.stale_preview.map((row) => (
                        <TableRow key={row.intent_id}>
                          <TableCell className="font-mono text-xs">
                            {row.product_type}
                          </TableCell>
                          <TableCell>{row.status}</TableCell>
                          <TableCell>
                            {Math.round(row.age_minutes)} min / {row.ttl_minutes}
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{row.severity}</Badge>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
