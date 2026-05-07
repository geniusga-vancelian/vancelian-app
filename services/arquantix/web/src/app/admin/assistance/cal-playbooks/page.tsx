'use client'

/**
 * Admin — Catalogue des playbooks CAL (table ``assistance_action_playbooks``).
 * Proxy FastAPI comme Knowledge.
 */
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { Eye, Loader2, Plus, RefreshCw, Trash2, ListOrdered } from 'lucide-react'

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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type Playbook = {
  id: string
  action_key: string
  label: string
  description: string | null
  transaction_kind: string
  agent_id: string
  definition: Record<string, unknown>
  is_enabled: boolean
  sort_order: number
  created_at: string | null
  updated_at: string | null
}

type ListResponse = {
  items: Playbook[]
  total: number
  skip: number
  limit: number
}

type FormState = {
  action_key: string
  label: string
  description: string
  transaction_kind: string
  agent_id: string
  definitionText: string
  is_enabled: boolean
  sort_order: string
}

const TX_KINDS = ['crypto_buy', 'bundle_invest'] as const

const DEFAULT_DEF = `{
  "target_kinds": ["crypto_buy"],
  "steps": [
    {
      "id": "list_sources",
      "tool": "show_invest_source_accounts",
      "order": 1,
      "instruction_fr": "Instruction pour le LLM…"
    }
  ],
  "required_slots_fr": "",
  "unavailable_message_fr": ""
}`

function emptyForm(): FormState {
  return {
    action_key: '',
    label: '',
    description: '',
    transaction_kind: 'crypto_buy',
    agent_id: 'product',
    definitionText: DEFAULT_DEF,
    is_enabled: true,
    sort_order: '0',
  }
}

export default function CalPlaybooksAdminPage() {
  const router = useRouter()
  const [items, setItems] = useState<Playbook[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<string>('all')
  const [searchInput, setSearchInput] = useState('')
  const [searchApplied, setSearchApplied] = useState('')

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [mode, setMode] = useState<'create' | 'edit'>('create')
  const [form, setForm] = useState<FormState>(emptyForm)
  const [saving, setSaving] = useState(false)

  const [deleteKey, setDeleteKey] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewMd, setPreviewMd] = useState('')
  const [previewLoading, setPreviewLoading] = useState(false)

  const fetchList = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    params.set('skip', '0')
    params.set('limit', '200')
    if (activeFilter !== 'all') params.set('is_enabled', activeFilter)
    if (searchApplied) params.set('search', searchApplied)
    try {
      const res = await fetch(`/api/admin/assistance/action-playbooks?${params}`)
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        toastError('Impossible de charger les playbooks')
        return
      }
      const data = (await res.json()) as ListResponse
      setItems(data.items)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }, [activeFilter, searchApplied, router])

  useEffect(() => {
    void fetchList()
  }, [fetchList])

  const openCreate = () => {
    setMode('create')
    setForm(emptyForm())
    setDrawerOpen(true)
  }

  const openEdit = (p: Playbook) => {
    setMode('edit')
    setForm({
      action_key: p.action_key,
      label: p.label,
      description: p.description ?? '',
      transaction_kind: p.transaction_kind,
      agent_id: p.agent_id,
      definitionText: JSON.stringify(p.definition ?? {}, null, 2),
      is_enabled: p.is_enabled,
      sort_order: String(p.sort_order),
    })
    setDrawerOpen(true)
  }

  const loadPreview = async () => {
    setPreviewLoading(true)
    try {
      const res = await fetch(
        '/api/admin/assistance/action-playbooks/preview-render?refresh=true',
      )
      if (!res.ok) {
        toastError('Aperçu indisponible')
        return
      }
      const j = (await res.json()) as { markdown: string }
      setPreviewMd(j.markdown ?? '')
      setPreviewOpen(true)
    } finally {
      setPreviewLoading(false)
    }
  }

  const submit = async () => {
    let definition: Record<string, unknown>
    try {
      const parsed = JSON.parse(form.definitionText || '{}')
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('bad')
      }
      definition = parsed as Record<string, unknown>
    } catch {
      toastError('Le JSON « definition » est invalide')
      return
    }

    const sortOrder = parseInt(form.sort_order, 10)
    if (Number.isNaN(sortOrder)) {
      toastError('sort_order doit être un entier')
      return
    }

    setSaving(true)
    try {
      let res: Response
      if (mode === 'create') {
        res = await fetch('/api/admin/assistance/action-playbooks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            action_key: form.action_key.trim(),
            label: form.label.trim(),
            description: form.description.trim() || null,
            transaction_kind: form.transaction_kind,
            agent_id: form.agent_id.trim() || 'product',
            definition,
            is_enabled: form.is_enabled,
            sort_order: sortOrder,
          }),
        })
      } else {
        res = await fetch(
          `/api/admin/assistance/action-playbooks/${encodeURIComponent(form.action_key)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              label: form.label.trim(),
              description: form.description.trim() || null,
              transaction_kind: form.transaction_kind,
              agent_id: form.agent_id.trim() || 'product',
              definition,
              is_enabled: form.is_enabled,
              sort_order: sortOrder,
            }),
          },
        )
      }

      if (res.status === 201 || res.ok) {
        toastSuccess(
          mode === 'create'
            ? `Playbook « ${form.action_key} » créé`
            : `Playbook « ${form.action_key} » mis à jour`,
        )
        setDrawerOpen(false)
        await fetchList()
        return
      }

      const errBody = (await res.json().catch(() => ({}))) as {
        detail?: unknown
        error?: string
      }
      const msg =
        typeof errBody.detail === 'string'
          ? errBody.detail
          : errBody.error || `Erreur ${res.status}`
      toastError(msg)
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deleteKey) return
    setDeleting(true)
    try {
      const res = await fetch(
        `/api/admin/assistance/action-playbooks/${encodeURIComponent(deleteKey)}`,
        { method: 'DELETE' },
      )
      if (res.status === 204) {
        toastSuccess('Playbook supprimé')
        setDeleteKey(null)
        await fetchList()
        return
      }
      toastError('Suppression impossible')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-sm text-muted-foreground">
            <Link href="/admin" className="hover:underline">
              Admin
            </Link>
            {' / '}
            <Link href="/admin/assistance" className="hover:underline">
              Assistance
            </Link>
          </p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">
            Playbooks CAL
          </h1>
          <p className="text-muted-foreground mt-1 max-w-2xl text-sm">
            Définition déclarative des parcours (outils, ordre, consignes FR) injectée
            dans l’agent <strong>product</strong> sous{' '}
            <code className="rounded bg-slate-100 px-1">[ACTION_PLAYBOOKS_CATALOG]</code>.
          </p>
        </div>
        <AssistanceAdminHubNav />
      </div>

      <Alert>
        <ListOrdered className="h-4 w-4" />
        <AlertTitle>Contrôle runtime</AlertTitle>
        <AlertDescription>
          Les changements sont pris en compte sous ~30&nbsp;s (cache) ou immédiatement
          après sauvegarde. Le bouton « Aperçu injection » montre le Markdown vu par le
          modèle.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>Catalogue</CardTitle>
            <CardDescription>
              {total} playbook(s) — clés alignées sur{' '}
              <code>transaction_kind</code> du routeur (
              {TX_KINDS.join(', ')}).
            </CardDescription>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => void loadPreview()}
              disabled={previewLoading}
            >
              {previewLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Eye className="mr-2 h-4 w-4" />
              )}
              Aperçu injection
            </Button>
            <Button variant="outline" size="sm" onClick={() => void fetchList()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Recharger
            </Button>
            <Button size="sm" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Nouveau
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex flex-wrap items-end gap-3 border-t pt-4">
          <div className="space-y-1">
            <Label className="text-xs">État</Label>
            <Select value={activeFilter} onValueChange={(v) => setActiveFilter(v)}>
              <SelectTrigger className="w-36">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Tous</SelectItem>
                <SelectItem value="true">Actifs</SelectItem>
                <SelectItem value="false">Inactifs</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-[200px] flex-1 space-y-1">
            <Label className="text-xs">Recherche (clé / libellé)</Label>
            <div className="flex gap-2">
              <Input
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') setSearchApplied(searchInput)
                }}
                placeholder="crypto_buy…"
              />
              <Button variant="outline" onClick={() => setSearchApplied(searchInput)}>
                OK
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <section className="rounded-lg border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Clé</TableHead>
              <TableHead>Libellé</TableHead>
              <TableHead className="w-36">transaction_kind</TableHead>
              <TableHead className="w-24">Tri</TableHead>
              <TableHead className="w-28">État</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground">
                  Aucun playbook.
                </TableCell>
              </TableRow>
            ) : (
              items.map((p) => (
                <TableRow key={p.id}>
                  <TableCell className="font-mono text-xs">{p.action_key}</TableCell>
                  <TableCell>{p.label}</TableCell>
                  <TableCell>
                    <Badge variant="secondary">{p.transaction_kind}</Badge>
                  </TableCell>
                  <TableCell>{p.sort_order}</TableCell>
                  <TableCell>
                    {p.is_enabled ? (
                      <Badge>Actif</Badge>
                    ) : (
                      <Badge variant="outline">Off</Badge>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(p)}>
                      Éditer
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-destructive"
                      onClick={() => setDeleteKey(p.action_key)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </section>

      <Sheet open={drawerOpen} onOpenChange={(o) => !saving && setDrawerOpen(o)}>
        <SheetContent className="flex w-full max-w-lg flex-col gap-4 overflow-y-auto sm:max-w-xl">
          <SheetHeader>
            <SheetTitle>
              {mode === 'create' ? 'Nouveau playbook' : `Éditer ${form.action_key}`}
            </SheetTitle>
            <SheetDescription>
              JSON <code>definition</code> : étapes, outils, textes FR. Référence{' '}
              <code>steps[].tool</code> ∈ show_invest_source_accounts,
              show_invest_confirmation_draft.
            </SheetDescription>
          </SheetHeader>

          <div className="space-y-3">
            <div className="space-y-1">
              <Label>action_key</Label>
              <Input
                value={form.action_key}
                onChange={(e) => setForm((f) => ({ ...f, action_key: e.target.value }))}
                disabled={mode === 'edit'}
                placeholder="crypto_buy"
              />
            </div>
            <div className="space-y-1">
              <Label>Libellé</Label>
              <Input
                value={form.label}
                onChange={(e) => setForm((f) => ({ ...f, label: e.target.value }))}
              />
            </div>
            <div className="space-y-1">
              <Label>Description</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <Label>transaction_kind</Label>
                <Select
                  value={form.transaction_kind}
                  onValueChange={(v) => setForm((f) => ({ ...f, transaction_kind: v }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TX_KINDS.map((k) => (
                      <SelectItem key={k} value={k}>
                        {k}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label>sort_order</Label>
                <Input
                  value={form.sort_order}
                  onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))}
                />
              </div>
            </div>
            <div className="space-y-1">
              <Label>agent_id</Label>
              <Input
                value={form.agent_id}
                onChange={(e) => setForm((f) => ({ ...f, agent_id: e.target.value }))}
              />
            </div>
            <div className="flex items-center gap-2">
              <Switch
                id="en"
                checked={form.is_enabled}
                onCheckedChange={(v) => setForm((f) => ({ ...f, is_enabled: Boolean(v) }))}
              />
              <Label htmlFor="en">Actif</Label>
            </div>
            <div className="space-y-1">
              <Label>definition (JSON)</Label>
              <Textarea
                className="min-h-[280px] font-mono text-xs"
                value={form.definitionText}
                onChange={(e) =>
                  setForm((f) => ({ ...f, definitionText: e.target.value }))
                }
              />
            </div>
          </div>

          <SheetFooter className="gap-2 sm:justify-end">
            <Button variant="outline" onClick={() => setDrawerOpen(false)} disabled={saving}>
              Annuler
            </Button>
            <Button onClick={() => void submit()} disabled={saving}>
              {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Enregistrer
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Aperçu Markdown injecté (agent product)</DialogTitle>
            <DialogDescription>
              Rendu identique au bloc concaténé après le prompt système.
            </DialogDescription>
          </DialogHeader>
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{previewMd}</ReactMarkdown>
          </div>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteKey)} onOpenChange={(o) => !o && setDeleteKey(null)}>
        <AlertDialogContent>
          <AlertDialogTitle>Supprimer ce playbook ?</AlertDialogTitle>
          <AlertDialogDescription>
            Cette action est irréversible. Clé :{' '}
            <span className="font-mono">{deleteKey}</span>
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={() => void handleDelete()} disabled={deleting}>
              {deleting ? '…' : 'Supprimer'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
