'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
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

interface IntentRow {
  id: string
  person_id: string | null
  wallet_address?: string | null
  product_type: string
  operation_type: string
  status: string
  tx_hash?: string | null
  linked_table?: string | null
  linked_id?: string | null
  linked_reference_id?: string | null
  created_at?: string | null
}

export default function TransactionIntentsPage() {
  const router = useRouter()
  const [items, setItems] = useState<IntentRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [personId, setPersonId] = useState('')
  const [productType, setProductType] = useState('')
  const [status, setStatus] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const qs = new URLSearchParams()
      if (personId) qs.set('person_id', personId)
      if (productType) qs.set('product_type', productType)
      if (status) qs.set('status', status)
      qs.set('limit', '100')
      const res = await fetch(
        `${ONCHAIN_RECONCILIATION_BFF_BASE}/intents?${qs.toString()}`,
        { cache: 'no-store', credentials: 'include' },
      )
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Erreur')
      setItems(data.items || [])
      setTotal(data.total ?? 0)
    } catch (err: unknown) {
      toastError(err instanceof Error ? err.message : 'Erreur')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [personId, productType, status, router])

  useEffect(() => {
    load()
  }, [load])

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/admin/onchain-reconciliation">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Réconciliation
          </Button>
        </Link>
        <h1 className="text-2xl font-semibold">Transaction intents</h1>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Actualiser
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Filtres</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Input
            placeholder="person_id"
            value={personId}
            onChange={(e) => setPersonId(e.target.value)}
            className="max-w-xs font-mono text-xs"
          />
          <Input
            placeholder="product_type (lifi_swap, morpho_earn, lombard_borrow, bundle_invest…)"
            value={productType}
            onChange={(e) => setProductType(e.target.value)}
            className="max-w-xs"
          />
          <Input
            placeholder="status"
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="max-w-[160px]"
          />
        </CardContent>
      </Card>

      <p className="text-sm text-muted-foreground">{total} intent(s)</p>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Produit</TableHead>
            <TableHead>Op</TableHead>
            <TableHead>Statut</TableHead>
            <TableHead>tx_hash</TableHead>
            <TableHead>Lié à</TableHead>
            <TableHead>Créé</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((row) => (
            <TableRow key={row.id}>
              <TableCell>
                <code className="text-xs">{row.product_type}</code>
              </TableCell>
              <TableCell>{row.operation_type}</TableCell>
              <TableCell>
                <Badge variant="outline">{row.status}</Badge>
              </TableCell>
              <TableCell className="font-mono text-xs max-w-[120px] truncate">
                {row.tx_hash || '—'}
              </TableCell>
              <TableCell className="text-xs">
                {row.linked_table || '—'}
                {row.linked_reference_id ? (
                  <span className="block font-mono truncate max-w-[100px]">
                    {row.linked_reference_id}
                  </span>
                ) : row.linked_id ? (
                  <span className="block font-mono truncate max-w-[100px]">
                    {row.linked_id}
                  </span>
                ) : null}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {row.created_at
                  ? new Date(row.created_at).toLocaleString('fr-FR')
                  : '—'}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
