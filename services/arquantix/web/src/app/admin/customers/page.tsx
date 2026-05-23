'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { toastError } from '@/lib/admin/toast'
import { ChevronLeft, ChevronRight, RefreshCw, Search } from 'lucide-react'

interface ProgressBlock {
  stage: string
  label: string
  completion_ratio: number
}

interface ListItem {
  person_id: string
  mobile: string | null
  email: string | null
  first_name: string | null
  last_name: string | null
  country_of_residence: string | null
  registration_progress: ProgressBlock
  created_at: string
  updated_at: string
  pe_client_id: string | null
  has_privy_wallet?: boolean
  privy_wallet_count?: number
}

interface ListResponse {
  items: ListItem[]
  total: number
  page: number
  page_size: number
}

function stageBadgeClass(stage: string): string {
  if (stage === 'active_client') return 'bg-emerald-700 hover:bg-emerald-700 text-white border-transparent'
  if (stage === 'pe_client_linked') return 'bg-indigo-700 hover:bg-indigo-700 text-white border-transparent'
  if (stage === 'kyc_completed' || stage === 'kyc_approved')
    return 'bg-blue-700 hover:bg-blue-700 text-white border-transparent'
  if (stage.includes('kyc')) return 'bg-amber-600 hover:bg-amber-600 text-white border-transparent'
  if (stage === 'registration_in_progress') return 'bg-cyan-700 hover:bg-cyan-700 text-white border-transparent'
  if (stage === 'account_secured') return 'bg-slate-700 hover:bg-slate-700 text-white border-transparent'
  return 'bg-slate-600 hover:bg-slate-600 text-white border-transparent'
}

export default function AdminCustomersPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<ListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize] = useState(25)
  const [q, setQ] = useState('')
  const [qDebounced, setQDebounced] = useState('')
  const [sort, setSort] = useState('-updated_at')
  const [country, setCountry] = useState('')

  useEffect(() => {
    const t = setTimeout(() => setQDebounced(q.trim()), 350)
    return () => clearTimeout(t)
  }, [q])

  const fetchList = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('page', String(page))
      params.set('page_size', String(pageSize))
      if (qDebounced) params.set('q', qDebounced)
      params.set('sort', sort)
      if (country.trim()) params.set('country', country.trim().toUpperCase())

      const res = await fetch(`/api/admin/customers?${params.toString()}`)
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        throw new Error('Échec du chargement')
      }
      const data: ListResponse = await res.json()
      setItems(data.items ?? [])
      setTotal(data.total ?? 0)
    } catch {
      toastError('Impossible de charger les clients')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, qDebounced, sort, country, router])

  useEffect(() => {
    fetchList()
  }, [fetchList])

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const formatDt = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('fr-FR', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    } catch {
      return iso
    }
  }

  return (
    <div className="max-w-[1400px]">
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">Clients</h1>
          <p className="mt-1 text-sm text-slate-600 max-w-xl">
            Personnes ayant démarré l’inscription (téléphone saisi, session d’inscription ou OTP SMS).
            Vue support & conformité — Customer 360.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchList()} className="gap-2 shrink-0">
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </Button>
      </div>

      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="border-b border-slate-100 bg-slate-50/80 pb-4">
          <CardTitle className="text-base font-medium text-slate-800">Recherche & filtres</CardTitle>
          <div className="flex flex-col gap-3 pt-2 sm:flex-row sm:flex-wrap sm:items-center">
            <div className="relative flex-1 min-w-[200px] max-w-md">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Rechercher (email, téléphone, nom, contenu profil…)"
                value={q}
                onChange={(e) => {
                  setQ(e.target.value)
                  setPage(1)
                }}
                className="pl-9 bg-white border-slate-200"
              />
            </div>
            <Input
              placeholder="Pays (code, ex. FR)"
              value={country}
              onChange={(e) => {
                setCountry(e.target.value)
                setPage(1)
              }}
              className="w-full sm:w-36 bg-white border-slate-200"
            />
            <select
              value={sort}
              onChange={(e) => {
                setSort(e.target.value)
                setPage(1)
              }}
              className="h-10 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-800"
            >
              <option value="-updated_at">Tri : mise à jour ↓</option>
              <option value="updated_at">Tri : mise à jour ↑</option>
              <option value="-created_at">Tri : création ↓</option>
              <option value="created_at">Tri : création ↑</option>
            </select>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading && items.length === 0 ? (
            <div className="flex justify-center py-20 text-slate-500">
              <RefreshCw className="h-6 w-6 animate-spin" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/50 hover:bg-slate-50/50">
                    <TableHead className="font-semibold text-slate-700">ID personne</TableHead>
                    <TableHead className="font-semibold text-slate-700">Mobile</TableHead>
                    <TableHead className="font-semibold text-slate-700">E-mail</TableHead>
                    <TableHead className="font-semibold text-slate-700">Prénom</TableHead>
                    <TableHead className="font-semibold text-slate-700">Nom</TableHead>
                    <TableHead className="font-semibold text-slate-700">Pays</TableHead>
                    <TableHead className="font-semibold text-slate-700">Progression</TableHead>
                    <TableHead className="font-semibold text-slate-700">Wallet Privy</TableHead>
                    <TableHead className="font-semibold text-slate-700">Créé</TableHead>
                    <TableHead className="font-semibold text-slate-700">Maj</TableHead>
                    <TableHead className="w-[100px] text-right font-semibold text-slate-700">Action</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((row) => (
                    <TableRow key={row.person_id} className="border-slate-100 hover:bg-slate-50/80">
                      <TableCell className="font-mono text-xs text-slate-600 max-w-[120px] truncate" title={row.person_id}>
                        {row.person_id.slice(0, 8)}…
                      </TableCell>
                      <TableCell className="text-sm text-slate-800">{row.mobile ?? '—'}</TableCell>
                      <TableCell className="text-sm text-slate-800 max-w-[180px] truncate" title={row.email ?? ''}>
                        {row.email ?? '—'}
                      </TableCell>
                      <TableCell className="text-sm">{row.first_name ?? '—'}</TableCell>
                      <TableCell className="text-sm">{row.last_name ?? '—'}</TableCell>
                      <TableCell className="text-sm">{row.country_of_residence ?? '—'}</TableCell>
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <Badge className={`w-fit text-xs font-medium ${stageBadgeClass(row.registration_progress.stage)}`}>
                            {row.registration_progress.label}
                          </Badge>
                          <span className="text-[11px] text-slate-500">
                            {Math.round(row.registration_progress.completion_ratio * 100)}% complétude
                          </span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {row.has_privy_wallet ? (
                          <Badge className="bg-violet-700 hover:bg-violet-700 text-white border-transparent text-xs">
                            {row.privy_wallet_count ?? 1} wallet{(row.privy_wallet_count ?? 1) > 1 ? 's' : ''}
                          </Badge>
                        ) : (
                          <span className="text-xs text-slate-400">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-slate-600 whitespace-nowrap">{formatDt(row.created_at)}</TableCell>
                      <TableCell className="text-xs text-slate-600 whitespace-nowrap">{formatDt(row.updated_at)}</TableCell>
                      <TableCell className="text-right">
                        <Button variant="outline" size="sm" asChild className="border-indigo-200 text-indigo-800 hover:bg-indigo-50">
                          <Link href={`/admin/customers/${row.person_id}`}>Fiche</Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          <div className="flex flex-col gap-3 border-t border-slate-100 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-slate-600">
              {total} client{total > 1 ? 's' : ''} — page {page} / {totalPages}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages || loading}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
