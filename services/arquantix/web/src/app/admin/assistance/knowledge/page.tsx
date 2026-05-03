'use client'

/**
 * Admin — Knowledge des agents (table `product_knowledge`).
 *
 * Source de vérité : API Python (SQLAlchemy). Cette page passe par les routes
 * proxy `/api/admin/assistance/knowledge/...`. Toute mutation invalide
 * automatiquement le cache du builder côté Python (cf.
 * `_safe_invalidate_catalog_cache` dans `admin_knowledge_router.py`).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  AlertCircle,
  Eye,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'

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

// ─── Types ──────────────────────────────────────────────────────────────────

type Knowledge = {
  slug: string
  topic: string
  title: string
  body: string
  metadata: Record<string, unknown>
  is_active: boolean
  created_at: string | null
  updated_at: string | null
}

type ListResponse = {
  items: Knowledge[]
  total: number
  skip: number
  limit: number
}

type SummaryRow = { topic: string; active: number; inactive: number }

type SummaryResponse = {
  by_topic: SummaryRow[]
  allowed_topics: string[]
}

type PreviewResponse = {
  block: string | null
  chars: number
  lines: number
  is_empty: boolean
}

type FormState = {
  slug: string
  topic: string
  title: string
  body: string
  metadataText: string
  is_active: boolean
}

// Le slug est readonly en édition (PK), donc on en sépare la clé en mode "create".
function emptyForm(defaultTopic: string): FormState {
  return {
    slug: '',
    topic: defaultTopic,
    title: '',
    body: '',
    metadataText: '{}',
    is_active: true,
  }
}

const TOPIC_LABELS: Record<string, string> = {
  transaction_kind: 'Type de transaction',
  definition: 'Fiche produit',
  delay: 'Délai standard',
  faq: 'FAQ',
}

const PAGE_SIZE = 50

// ─── Page ───────────────────────────────────────────────────────────────────

export default function AssistanceKnowledgeAdminPage() {
  const router = useRouter()

  // Liste & filtres
  const [items, setItems] = useState<Knowledge[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [topicFilter, setTopicFilter] = useState<string>('all')
  const [activeFilter, setActiveFilter] = useState<string>('all')
  const [searchInput, setSearchInput] = useState<string>('')
  const [searchApplied, setSearchApplied] = useState<string>('')
  const [loading, setLoading] = useState(true)

  // Summary (compteurs par topic)
  const [summary, setSummary] = useState<SummaryResponse | null>(null)

  // Édition / création
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [drawerMode, setDrawerMode] = useState<'create' | 'edit'>('create')
  const [form, setForm] = useState<FormState>(emptyForm('transaction_kind'))
  const [saving, setSaving] = useState(false)

  // Suppression
  const [deleteSlug, setDeleteSlug] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Aperçu bloc agents
  const [previewOpen, setPreviewOpen] = useState(false)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [preview, setPreview] = useState<PreviewResponse | null>(null)

  const allowedTopics = useMemo(
    () => summary?.allowed_topics ?? Object.keys(TOPIC_LABELS),
    [summary],
  )

  // ─── Fetchers ──────────────────────────────────────────────────────────

  const fetchSummary = useCallback(async () => {
    const res = await fetch('/api/admin/assistance/knowledge/summary')
    if (res.status === 401) {
      router.push('/admin/login')
      return
    }
    if (!res.ok) {
      toastError('Impossible de charger les compteurs')
      return
    }
    setSummary((await res.json()) as SummaryResponse)
  }, [router])

  const fetchList = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams()
    params.set('skip', String(skip))
    params.set('limit', String(PAGE_SIZE))
    if (topicFilter !== 'all') params.set('topic', topicFilter)
    if (activeFilter !== 'all') params.set('is_active', activeFilter)
    if (searchApplied) params.set('search', searchApplied)
    try {
      const res = await fetch(`/api/admin/assistance/knowledge?${params}`)
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        toastError('Impossible de charger la liste')
        return
      }
      const data = (await res.json()) as ListResponse
      setItems(data.items)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }, [skip, topicFilter, activeFilter, searchApplied, router])

  useEffect(() => {
    fetchSummary()
  }, [fetchSummary])

  useEffect(() => {
    fetchList()
  }, [fetchList])

  // ─── Édition / création ────────────────────────────────────────────────

  const openCreate = () => {
    setDrawerMode('create')
    setForm(emptyForm(topicFilter !== 'all' ? topicFilter : 'transaction_kind'))
    setDrawerOpen(true)
  }

  const openEdit = (item: Knowledge) => {
    setDrawerMode('edit')
    setForm({
      slug: item.slug,
      topic: item.topic,
      title: item.title,
      body: item.body,
      metadataText: JSON.stringify(item.metadata ?? {}, null, 2),
      is_active: item.is_active,
    })
    setDrawerOpen(true)
  }

  const closeDrawer = () => {
    if (saving) return
    setDrawerOpen(false)
  }

  const handleSubmit = async () => {
    let metadata: Record<string, unknown> = {}
    try {
      const parsed = form.metadataText.trim() ? JSON.parse(form.metadataText) : {}
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
        throw new Error('not an object')
      }
      metadata = parsed as Record<string, unknown>
    } catch {
      toastError('Le champ metadata doit être un JSON object valide')
      return
    }

    setSaving(true)
    try {
      let res: Response
      if (drawerMode === 'create') {
        res = await fetch('/api/admin/assistance/knowledge', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            slug: form.slug.trim(),
            topic: form.topic,
            title: form.title.trim(),
            body: form.body,
            metadata,
            is_active: form.is_active,
          }),
        })
      } else {
        res = await fetch(
          `/api/admin/assistance/knowledge/${encodeURIComponent(form.slug)}`,
          {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              topic: form.topic,
              title: form.title.trim(),
              body: form.body,
              metadata,
              is_active: form.is_active,
            }),
          },
        )
      }

      if (res.status === 201 || res.ok) {
        toastSuccess(
          drawerMode === 'create'
            ? `Fiche « ${form.slug} » créée`
            : `Fiche « ${form.slug} » mise à jour`,
        )
        setDrawerOpen(false)
        await Promise.all([fetchList(), fetchSummary()])
        return
      }

      const errBody = await res.json().catch(() => ({}))
      toastError(
        (errBody.detail as string) ||
          (errBody.error as string) ||
          `Échec ${drawerMode === 'create' ? 'création' : 'mise à jour'} (${res.status})`,
      )
    } catch {
      toastError('Erreur réseau')
    } finally {
      setSaving(false)
    }
  }

  // ─── Suppression ───────────────────────────────────────────────────────

  const confirmDelete = async () => {
    if (!deleteSlug) return
    setDeleting(true)
    try {
      const res = await fetch(
        `/api/admin/assistance/knowledge/${encodeURIComponent(deleteSlug)}`,
        { method: 'DELETE' },
      )
      if (res.status === 204) {
        toastSuccess(`Fiche « ${deleteSlug} » supprimée`)
        setDeleteSlug(null)
        await Promise.all([fetchList(), fetchSummary()])
        return
      }
      const errBody = await res.json().catch(() => ({}))
      toastError(
        (errBody.detail as string) ||
          (errBody.error as string) ||
          `Échec suppression (${res.status})`,
      )
    } finally {
      setDeleting(false)
    }
  }

  // ─── Aperçu bloc ──────────────────────────────────────────────────────

  const fetchPreview = useCallback(async (refresh: boolean) => {
    setPreviewLoading(true)
    try {
      const res = await fetch(
        `/api/admin/assistance/knowledge/preview-block${refresh ? '?refresh=true' : ''}`,
      )
      if (!res.ok) {
        toastError('Aperçu impossible')
        return
      }
      setPreview((await res.json()) as PreviewResponse)
    } finally {
      setPreviewLoading(false)
    }
  }, [])

  const openPreview = async () => {
    setPreviewOpen(true)
    await fetchPreview(true)
  }

  // ─── UI ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Knowledge des agents</h1>
          <p className="text-sm text-muted-foreground">
            Fiches éditoriales lues par les agents LLM (table{' '}
            <code className="rounded bg-muted px-1 py-0.5 text-xs">
              product_knowledge
            </code>
            ). Chaque modification invalide automatiquement le cache du
            builder ; les agents voient la nouvelle version au tour suivant.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={openPreview}>
            <Eye className="mr-2 h-4 w-4" /> Aperçu agents
          </Button>
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" /> Nouvelle fiche
          </Button>
        </div>
      </header>

      {/* Compteurs par topic */}
      {summary && (
        <section className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-4">
          {summary.allowed_topics.map((topic) => {
            const row = summary.by_topic.find((r) => r.topic === topic)
            const active = row?.active ?? 0
            const inactive = row?.inactive ?? 0
            return (
              <Card key={topic}>
                <CardHeader className="pb-2">
                  <CardDescription className="text-xs uppercase tracking-wide">
                    {TOPIC_LABELS[topic] ?? topic}
                  </CardDescription>
                  <CardTitle className="font-mono text-xs text-muted-foreground">
                    {topic}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex items-baseline gap-2">
                    <span className="text-2xl font-semibold">{active}</span>
                    <span className="text-xs text-muted-foreground">
                      actif{active > 1 ? 's' : ''}
                    </span>
                    {inactive > 0 && (
                      <Badge variant="secondary">{inactive} inactif</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </section>
      )}

      {/* Filtres */}
      <section className="flex flex-wrap items-end gap-3 border-b pb-4">
        <div className="space-y-1">
          <Label className="text-xs">Topic</Label>
          <Select
            value={topicFilter}
            onValueChange={(v) => {
              setSkip(0)
              setTopicFilter(v)
            }}
          >
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous topics</SelectItem>
              {allowedTopics.map((t) => (
                <SelectItem key={t} value={t}>
                  {TOPIC_LABELS[t] ?? t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">État</Label>
          <Select
            value={activeFilter}
            onValueChange={(v) => {
              setSkip(0)
              setActiveFilter(v)
            }}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tous</SelectItem>
              <SelectItem value="true">Actifs</SelectItem>
              <SelectItem value="false">Inactifs</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex-1 space-y-1">
          <Label className="text-xs">Recherche (slug / titre / corps)</Label>
          <div className="flex gap-2">
            <Input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  setSkip(0)
                  setSearchApplied(searchInput)
                }
              }}
              placeholder="ex. crypto, vault, deposit_sepa…"
            />
            <Button
              variant="outline"
              onClick={() => {
                setSkip(0)
                setSearchApplied(searchInput)
              }}
            >
              Rechercher
            </Button>
            {searchApplied && (
              <Button
                variant="ghost"
                onClick={() => {
                  setSearchInput('')
                  setSearchApplied('')
                  setSkip(0)
                }}
              >
                Effacer
              </Button>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          onClick={() => {
            fetchList()
            fetchSummary()
          }}
        >
          <RefreshCw className="mr-2 h-4 w-4" /> Recharger
        </Button>
      </section>

      {/* Liste */}
      <section>
        <div className="rounded border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-56">Slug</TableHead>
                <TableHead className="w-40">Topic</TableHead>
                <TableHead>Titre</TableHead>
                <TableHead className="w-24">État</TableHead>
                <TableHead className="w-28 text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    <Loader2 className="mx-auto h-5 w-5 animate-spin" />
                  </TableCell>
                </TableRow>
              ) : items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={5} className="text-center text-muted-foreground">
                    Aucune fiche pour ces filtres.
                  </TableCell>
                </TableRow>
              ) : (
                items.map((it) => (
                  <TableRow key={it.slug}>
                    <TableCell className="font-mono text-xs">{it.slug}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{TOPIC_LABELS[it.topic] ?? it.topic}</Badge>
                    </TableCell>
                    <TableCell className="max-w-sm truncate">{it.title}</TableCell>
                    <TableCell>
                      {it.is_active ? (
                        <Badge>Actif</Badge>
                      ) : (
                        <Badge variant="secondary">Inactif</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEdit(it)}
                        aria-label="Éditer"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => setDeleteSlug(it.slug)}
                        aria-label="Supprimer"
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>

        {/* Pagination simple */}
        {total > PAGE_SIZE && (
          <div className="mt-3 flex items-center justify-between text-sm text-muted-foreground">
            <span>
              {skip + 1}–{Math.min(skip + PAGE_SIZE, total)} sur {total}
            </span>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={skip === 0}
                onClick={() => setSkip(Math.max(0, skip - PAGE_SIZE))}
              >
                Précédent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={skip + PAGE_SIZE >= total}
                onClick={() => setSkip(skip + PAGE_SIZE)}
              >
                Suivant
              </Button>
            </div>
          </div>
        )}
      </section>

      {/* Drawer édition / création */}
      <Sheet open={drawerOpen} onOpenChange={(o) => !saving && setDrawerOpen(o)}>
        <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle>
              {drawerMode === 'create' ? 'Nouvelle fiche' : `Éditer ${form.slug}`}
            </SheetTitle>
            <SheetDescription>
              Les agents LLM lisent ces fiches via{' '}
              <code className="rounded bg-muted px-1 text-xs">
                read_product_knowledge(slug)
              </code>{' '}
              et via le bloc-catalogue dynamique.
            </SheetDescription>
          </SheetHeader>

          <div className="mt-6 space-y-4 px-4">
            <div className="space-y-1">
              <Label>
                Slug <span className="text-destructive">*</span>
              </Label>
              <Input
                value={form.slug}
                onChange={(e) =>
                  setForm({ ...form, slug: e.target.value.toLowerCase() })
                }
                placeholder="ex. kind_subscribe_my_new_product"
                disabled={drawerMode === 'edit'}
                className="font-mono"
              />
              <p className="text-xs text-muted-foreground">
                Lowercase ASCII, chiffres, <code>_</code> <code>-</code>{' '}
                <code>.</code>. Non modifiable après création.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-1">
                <Label>
                  Topic <span className="text-destructive">*</span>
                </Label>
                <Select
                  value={form.topic}
                  onValueChange={(v) => setForm({ ...form, topic: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {allowedTopics.map((t) => (
                      <SelectItem key={t} value={t}>
                        {TOPIC_LABELS[t] ?? t}{' '}
                        <span className="ml-2 text-xs text-muted-foreground">
                          {t}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end gap-2">
                <Label className="flex items-center gap-2">
                  <Switch
                    checked={form.is_active}
                    onCheckedChange={(v) =>
                      setForm({ ...form, is_active: Boolean(v) })
                    }
                  />
                  {form.is_active ? 'Actif (visible des agents)' : 'Inactif'}
                </Label>
              </div>
            </div>

            <div className="space-y-1">
              <Label>
                Titre <span className="text-destructive">*</span>
              </Label>
              <Input
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="Ex. Souscription d'un coffre Vancelian"
                maxLength={200}
              />
            </div>

            <div className="space-y-1">
              <Label>
                Corps (Markdown) <span className="text-destructive">*</span>
              </Label>
              <Textarea
                value={form.body}
                onChange={(e) => setForm({ ...form, body: e.target.value })}
                rows={10}
                className="font-mono text-sm"
                placeholder="Contenu factuel court (200-500 mots). Markdown supporté."
              />
              <p className="text-xs text-muted-foreground">
                Style Vancelian : phrases courtes, **gras** sur les concepts,
                liste à puces pour les caractéristiques. Pas de promesse de
                rendement précise.
              </p>
            </div>

            <div className="space-y-1">
              <Label>Metadata (JSON)</Label>
              <Textarea
                value={form.metadataText}
                onChange={(e) =>
                  setForm({ ...form, metadataText: e.target.value })
                }
                rows={8}
                className="font-mono text-xs"
                placeholder='{"code": "...", "label_fr": "...", ...}'
              />
              <p className="text-xs text-muted-foreground">
                Pour <code>transaction_kind</code> : <code>code</code>,{' '}
                <code>label_fr</code>, <code>direction</code>{' '}
                (in/out/trade/invest), <code>linked_knowledge_slug</code>,{' '}
                <code>display_order</code>. Voir une fiche existante pour le
                gabarit.
              </p>
            </div>
          </div>

          <SheetFooter className="mt-6 gap-2 px-4">
            <Button variant="outline" onClick={closeDrawer} disabled={saving}>
              Annuler
            </Button>
            <Button onClick={handleSubmit} disabled={saving}>
              {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {drawerMode === 'create' ? 'Créer' : 'Enregistrer'}
            </Button>
          </SheetFooter>
        </SheetContent>
      </Sheet>

      {/* Suppression */}
      <AlertDialog
        open={Boolean(deleteSlug)}
        onOpenChange={(o) => !deleting && !o && setDeleteSlug(null)}
      >
        <AlertDialogContent>
          <AlertDialogTitle>
            Supprimer la fiche « {deleteSlug} » ?
          </AlertDialogTitle>
          <AlertDialogDescription>
            Cette action est irréversible. Pour cacher temporairement une
            fiche aux agents, préfère la passer en{' '}
            <strong>Inactif</strong> dans le formulaire d&apos;édition.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting}>Annuler</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Supprimer
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Aperçu bloc */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Bloc tel que les agents le verront</DialogTitle>
            <DialogDescription>
              Rendu Markdown courant injecté dans le system prompt des agents{' '}
              <code className="text-xs">router</code>,{' '}
              <code className="text-xs">advisor</code>,{' '}
              <code className="text-xs">product</code>,{' '}
              <code className="text-xs">market</code>,{' '}
              <code className="text-xs">compliance.*</code>.
            </DialogDescription>
          </DialogHeader>

          {previewLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" /> Génération…
            </div>
          ) : preview?.is_empty ? (
            <div className="flex items-center gap-2 rounded border border-amber-200 bg-amber-50 p-3 text-amber-900">
              <AlertCircle className="h-4 w-4" />
              Aucun contenu : aucune fiche active dans les topics{' '}
              <code>transaction_kind</code> ou <code>definition</code>.
            </div>
          ) : (
            <>
              <div className="text-xs text-muted-foreground">
                {preview?.chars} caractères · {preview?.lines} lignes · ~{' '}
                {preview ? Math.round(preview.chars / 4) : 0} tokens
              </div>
              <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded bg-muted p-4 text-xs">
                {preview?.block ?? ''}
              </pre>
            </>
          )}

          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => fetchPreview(true)}
              disabled={previewLoading}
            >
              <RefreshCw className="mr-2 h-4 w-4" /> Rafraîchir
            </Button>
            <Button onClick={() => setPreviewOpen(false)}>Fermer</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
