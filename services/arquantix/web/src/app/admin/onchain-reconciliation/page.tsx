'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { ArrowRight, Download, Filter, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { toastError } from '@/lib/admin/toast'
import {
  autoFixRiskBadgeClass,
  buildDiscrepanciesListUrl,
  buildExportCsvUrl,
  severityBadgeClass,
  statusBadgeClass,
} from '@/lib/admin/onchainReconciliationApi'

interface AutoFixRisk {
  level: string
  label: string
  detail: string
}

interface DiscrepancyRow {
  id: string
  person_id: string
  wallet_address?: string | null
  layer: string
  asset?: string | null
  discrepancy_type: string
  db_amount?: string | null
  onchain_amount?: string | null
  delta?: string | null
  severity: string
  status: string
  created_at?: string | null
  likely_source_summary?: string | null
  likely_sources?: string[]
  auto_fix_risk?: AutoFixRisk
}

const ALL = '__all__'

export default function OnchainReconciliationPage() {
  const router = useRouter()
  const searchParams = useSearchParams()

  const [items, setItems] = useState<DiscrepancyRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const [status, setStatus] = useState(searchParams.get('status') || 'open')
  const [layer, setLayer] = useState(searchParams.get('layer') || ALL)
  const [severity, setSeverity] = useState(searchParams.get('severity') || ALL)
  const [discrepancyType, setDiscrepancyType] = useState(
    searchParams.get('discrepancy_type') || '',
  )
  const [personId, setPersonId] = useState(searchParams.get('person_id') || '')
  const [walletAddress, setWalletAddress] = useState(
    searchParams.get('wallet_address') || '',
  )

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const url = buildDiscrepanciesListUrl({
        status: status === ALL ? undefined : status,
        layer: layer === ALL ? undefined : layer,
        severity: severity === ALL ? undefined : severity,
        discrepancy_type: discrepancyType || undefined,
        person_id: personId || undefined,
        wallet_address: walletAddress || undefined,
        limit: '100',
      })
      const res = await fetch(url, { cache: 'no-store', credentials: 'include' })
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || data.error || 'Échec chargement')
      }
      setItems(data.items || [])
      setTotal(data.total ?? 0)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Erreur inconnue'
      toastError(message)
      setItems([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [status, layer, severity, discrepancyType, personId, walletAddress, router])

  useEffect(() => {
    fetch('/api/admin/me')
      .then((r) => r.json())
      .then((data) => {
        if (!data.user) router.push('/admin/login')
        else load()
      })
      .catch(() => router.push('/admin/login'))
  }, [load, router])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Réconciliation on-chain
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Pilotage des écarts — apply contrôlé avec preuve on-chain (Phase 5B/5C).
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/admin/onchain-reconciliation/health">Santé intents</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/admin/onchain-reconciliation/jobs">Jobs</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <Link href="/admin/onchain-reconciliation/intents">Intents</Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a
              href={buildExportCsvUrl({
                export_type: 'audit',
                status: status === ALL ? undefined : status,
                layer: layer === ALL ? undefined : layer,
                severity: severity === ALL ? undefined : severity,
                discrepancy_type: discrepancyType || undefined,
                person_id: personId || undefined,
                wallet_address: walletAddress || undefined,
              })}
              download
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV audit
            </a>
          </Button>
          <Button variant="outline" size="sm" onClick={() => load()} disabled={loading}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Actualiser
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Filter className="h-4 w-4" />
            Filtres
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3 lg:grid-cols-6">
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger>
              <SelectValue placeholder="Statut" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="open">open</SelectItem>
              <SelectItem value="acknowledged">acknowledged</SelectItem>
              <SelectItem value="resolved">resolved</SelectItem>
              <SelectItem value="ignored">ignored</SelectItem>
              <SelectItem value={ALL}>Tous</SelectItem>
            </SelectContent>
          </Select>
          <Select value={layer} onValueChange={setLayer}>
            <SelectTrigger>
              <SelectValue placeholder="Layer" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Tous</SelectItem>
              <SelectItem value="privy">privy</SelectItem>
              <SelectItem value="lifi">lifi</SelectItem>
              <SelectItem value="lombard">lombard</SelectItem>
              <SelectItem value="morpho">morpho</SelectItem>
              <SelectItem value="bundle">bundle</SelectItem>
            </SelectContent>
          </Select>
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger>
              <SelectValue placeholder="Sévérité" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>Toutes</SelectItem>
              <SelectItem value="P0">P0</SelectItem>
              <SelectItem value="P1">P1</SelectItem>
              <SelectItem value="P2">P2</SelectItem>
            </SelectContent>
          </Select>
          <Input
            placeholder="discrepancy_type"
            value={discrepancyType}
            onChange={(e) => setDiscrepancyType(e.target.value)}
          />
          <Input
            placeholder="person_id (UUID)"
            value={personId}
            onChange={(e) => setPersonId(e.target.value)}
          />
          <Input
            placeholder="wallet 0x…"
            value={walletAddress}
            onChange={(e) => setWalletAddress(e.target.value)}
          />
          <Button className="md:col-span-3 lg:col-span-6" onClick={() => load()} disabled={loading}>
            Appliquer les filtres
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Écarts ({total})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground">Chargement…</p>
          ) : items.length === 0 ? (
            <p className="text-sm text-muted-foreground">Aucun écart pour ces filtres.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Layer</TableHead>
                  <TableHead>Asset</TableHead>
                  <TableHead>DB</TableHead>
                  <TableHead>On-chain</TableHead>
                  <TableHead>Delta</TableHead>
                  <TableHead>Provenance</TableHead>
                  <TableHead>Risk if auto-fixed</TableHead>
                  <TableHead>Sévérité</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Créé</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((row) => (
                  <TableRow key={row.id}>
                    <TableCell className="font-mono text-xs max-w-[140px] truncate">
                      {row.discrepancy_type}
                    </TableCell>
                    <TableCell>{row.layer}</TableCell>
                    <TableCell>{row.asset || '—'}</TableCell>
                    <TableCell>{row.db_amount ?? '—'}</TableCell>
                    <TableCell>{row.onchain_amount ?? '—'}</TableCell>
                    <TableCell>{row.delta ?? '—'}</TableCell>
                    <TableCell className="text-xs max-w-[200px] text-muted-foreground">
                      {row.likely_source_summary || '—'}
                    </TableCell>
                    <TableCell>
                      {row.auto_fix_risk ? (
                        <Badge
                          variant="outline"
                          className={autoFixRiskBadgeClass(row.auto_fix_risk.level)}
                          title={row.auto_fix_risk.detail}
                        >
                          {row.auto_fix_risk.label}
                        </Badge>
                      ) : (
                        '—'
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={severityBadgeClass(row.severity)}>
                        {row.severity}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className={statusBadgeClass(row.status)}>
                        {row.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {row.created_at
                        ? new Date(row.created_at).toLocaleString('fr-FR')
                        : '—'}
                    </TableCell>
                    <TableCell>
                      <Link href={`/admin/onchain-reconciliation/${row.id}`}>
                        <Button variant="ghost" size="sm">
                          Détail
                          <ArrowRight className="h-3 w-3 ml-1" />
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
