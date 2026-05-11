'use client'

/**
 * Éditeur du wiki Markdown produit (assistance / chatbot).
 * Fichiers sous `api/services/assistance/data/wiki/` — cf. `wiki_repo.py`.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  BookMarked,
  ChevronDown,
  ChevronRight,
  FilePlus2,
  Folder,
  Loader2,
  Save,
  Search,
  AlertTriangle,
  ChevronsUp,
  ChevronsDown,
} from 'lucide-react'

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
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { toastError, toastSuccess } from '@/lib/admin/toast'

import {
  WIKI_FAQ_CATEGORIES,
  type WikiTreeNode,
} from '@/lib/admin/assistanceWikiShared'
import { AssistanceAdminHubNav } from '@/components/admin/AssistanceAdminHubNav'

type BrowseResponse = { root: string; nodes: WikiTreeNode[] }
type BrowseError = { error: string; message?: string; root: null; nodes: [] }

/** Tous les chemins de dossiers dans l’arbre (pour « tout déplier »). */
function collectAllDirPaths(nodes: WikiTreeNode[]): string[] {
  const out: string[] = []
  for (const n of nodes) {
    if (n.type === 'dir' && n.children) {
      out.push(n.path)
      out.push(...collectAllDirPaths(n.children))
    }
  }
  return out
}

/** Dossiers parents d’un fichier `foo/bar/baz.md` → `foo`, `foo/bar`. */
function parentFolderPaths(filePath: string): string[] {
  if (!filePath.endsWith('.md')) return []
  const parts = filePath.split('/').filter(Boolean)
  if (parts.length <= 1) return []
  const acc: string[] = []
  for (let i = 0; i < parts.length - 1; i++) {
    acc.push(parts.slice(0, i + 1).join('/'))
  }
  return acc
}

function WikiTreeRow({
  node,
  depth,
  selectedPath,
  onSelect,
  expandedPaths,
  onToggleFolder,
}: {
  node: WikiTreeNode
  depth: number
  selectedPath: string | null
  onSelect: (path: string) => void
  expandedPaths: Set<string>
  onToggleFolder: (folderPath: string) => void
}) {
  const pad = 6 + depth * 14
  if (node.type === 'file') {
    const active = selectedPath === node.path
    return (
      <button
        type="button"
        onClick={() => onSelect(node.path)}
        className={`w-full text-left text-sm py-1 px-2 rounded truncate ${
          active ? 'bg-indigo-100 text-indigo-900 font-medium' : 'hover:bg-gray-100'
        }`}
        style={{ paddingLeft: pad }}
      >
        {node.name}
      </button>
    )
  }

  const open = expandedPaths.has(node.path)
  return (
    <div className="mb-0.5">
      <button
        type="button"
        onClick={() => onToggleFolder(node.path)}
        className="flex w-full items-center gap-1 text-left text-xs font-semibold text-gray-600 py-1 px-2 rounded hover:bg-gray-100 transition-colors"
        style={{ paddingLeft: pad }}
        aria-expanded={open}
      >
        <span className="shrink-0 text-gray-400 w-4 flex justify-center" aria-hidden>
          {open ? (
            <ChevronDown className="w-3.5 h-3.5" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5" />
          )}
        </span>
        <Folder className="w-3.5 h-3.5 shrink-0 text-amber-600/90" />
        <span className="truncate">{node.name}</span>
      </button>
      {open &&
        node.children?.map((ch) => (
          <WikiTreeRow
            key={ch.path}
            node={ch}
            depth={depth + 1}
            selectedPath={selectedPath}
            onSelect={onSelect}
            expandedPaths={expandedPaths}
            onToggleFolder={onToggleFolder}
          />
        ))}
    </div>
  )
}

function filterTree(nodes: WikiTreeNode[], q: string): WikiTreeNode[] {
  if (!q.trim()) return nodes
  const lower = q.toLowerCase().trim()
  const out: WikiTreeNode[] = []
  for (const n of nodes) {
    if (n.type === 'file') {
      if (n.name.toLowerCase().includes(lower) || n.path.toLowerCase().includes(lower)) {
        out.push(n)
      }
    } else if (n.children) {
      const sub = filterTree(n.children, q)
      if (sub.length > 0) {
        out.push({ ...n, children: sub })
      }
    }
  }
  return out
}

function buildFaqTemplate(category: string, slug: string, title: string): string {
  const today = new Date().toISOString().slice(0, 10)
  const safeTitle = title.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
  return `---
title: "${safeTitle}"
slug: ${slug}
category: ${category}
audience: client
status: draft
last_reviewed: ${today}
tags: []
questions:
  - ""
---

# ${title}

## Short answer

## Details

`
}

function buildNonFaqTemplate(_section: 'concepts' | 'entities' | 'policies', slug: string, title: string): string {
  const today = new Date().toISOString().slice(0, 10)
  const safeTitle = title.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
  return `---
title: "${safeTitle}"
slug: ${slug}
audience: client
status: draft
last_reviewed: ${today}
tags: []
---

# ${title}

## Short answer

## Details

`
}

export default function AdminAssistanceWikiPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [authChecked, setAuthChecked] = useState(false)
  const [wikiRoot, setWikiRoot] = useState<string | null>(null)
  const [nodes, setNodes] = useState<WikiTreeNode[]>([])
  const [browseError, setBrowseError] = useState<string | null>(null)
  const [loadingTree, setLoadingTree] = useState(true)
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [savedSnapshot, setSavedSnapshot] = useState('')
  const [loadingFile, setLoadingFile] = useState(false)
  const [saving, setSaving] = useState(false)
  const [filter, setFilter] = useState('')

  /** Dossiers ouverts dans l’accordéon (clic / tout déplier / auto pour le fichier actif). */
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(() => new Set())

  const [createOpen, setCreateOpen] = useState(false)
  const [createKind, setCreateKind] = useState<'faq' | 'concepts' | 'entities' | 'policies' | 'root'>('faq')
  const [createCategory, setCreateCategory] = useState<string>(WIKI_FAQ_CATEGORIES[0])
  const [createSlug, setCreateSlug] = useState('')
  const [createTitle, setCreateTitle] = useState('')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
        } else {
          setAuthChecked(true)
        }
      })
      .catch(() => router.push('/admin/login'))
  }, [router])

  const pathFromUrl = searchParams?.get('path')
  useEffect(() => {
    if (!pathFromUrl || !pathFromUrl.endsWith('.md')) return
    setSelectedPath(pathFromUrl)
  }, [pathFromUrl])

  const loadTree = useCallback(() => {
    setLoadingTree(true)
    setBrowseError(null)
    fetch('/api/admin/assistance/wiki')
      .then((res) => res.json())
      .then((data: BrowseResponse | BrowseError) => {
        if ('error' in data && data.error === 'wiki_root_missing') {
          setWikiRoot(null)
          setNodes([])
          setBrowseError(data.message ?? 'Dossier wiki introuvable.')
          return
        }
        if (!resOk(data)) {
          setBrowseError('Impossible de charger l’arborescence.')
          return
        }
        setWikiRoot(data.root)
        setNodes(data.nodes)
      })
      .catch(() => setBrowseError('Erreur réseau lors du chargement du wiki.'))
      .finally(() => setLoadingTree(false))
  }, [])

  useEffect(() => {
    if (!authChecked) return
    loadTree()
  }, [authChecked, loadTree])

  const filteredNodes = useMemo(() => filterTree(nodes, filter), [nodes, filter])

  /** Filtre actif : rouvrir toute la branche pour afficher les correspondances. */
  useEffect(() => {
    if (!filter.trim()) return
    const dirs = collectAllDirPaths(filteredNodes)
    setExpandedFolders((prev) => {
      const n = new Set(prev)
      dirs.forEach((d) => n.add(d))
      return n
    })
  }, [filter, filteredNodes])

  const toggleFolder = useCallback((folderPath: string) => {
    setExpandedFolders((prev) => {
      const n = new Set(prev)
      if (n.has(folderPath)) n.delete(folderPath)
      else n.add(folderPath)
      return n
    })
  }, [])

  const expandAllFolders = useCallback(() => {
    setExpandedFolders(new Set(collectAllDirPaths(nodes)))
  }, [nodes])

  const collapseAllFolders = useCallback(() => {
    setExpandedFolders(() => {
      if (!selectedPath) return new Set()
      const keep = new Set(parentFolderPaths(selectedPath))
      return keep
    })
  }, [selectedPath])

  /** Ouvre les dossiers parents du fichier sélectionné pour le rendre visible. */
  useEffect(() => {
    if (!selectedPath) return
    const parents = parentFolderPaths(selectedPath)
    if (parents.length === 0) return
    setExpandedFolders((prev) => {
      const n = new Set(prev)
      parents.forEach((p) => n.add(p))
      return n
    })
  }, [selectedPath])

  useEffect(() => {
    if (!selectedPath) {
      setContent('')
      setSavedSnapshot('')
      return
    }
    setLoadingFile(true)
    const q = new URLSearchParams({ path: selectedPath })
    fetch(`/api/admin/assistance/wiki/item?${q}`)
      .then((res) => {
        if (!res.ok) throw new Error('load_failed')
        return res.json()
      })
      .then((data: { content: string }) => {
        setContent(data.content)
        setSavedSnapshot(data.content)
      })
      .catch(() => {
        toastError('Impossible de charger ce fichier.')
        setSelectedPath(null)
      })
      .finally(() => setLoadingFile(false))
  }, [selectedPath])

  const dirty = selectedPath != null && content !== savedSnapshot

  const handleSave = async () => {
    if (!selectedPath) return
    setSaving(true)
    try {
      const q = new URLSearchParams({ path: selectedPath })
      const res = await fetch(`/api/admin/assistance/wiki/item?${q}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      })
      if (!res.ok) {
        toastError('Enregistrement refusé par le serveur.')
        return
      }
      setSavedSnapshot(content)
      toastSuccess('Fiche enregistrée.')
    } catch {
      toastError('Erreur réseau.')
    } finally {
      setSaving(false)
    }
  }

  const handleCreate = async () => {
    const slug = createSlug.trim().replace(/\.md$/i, '')
    const title = createTitle.trim() || slug.replace(/-/g, ' ')
    if (!slug) {
      toastError('Indiquez un identifiant (slug) pour le fichier.')
      return
    }
    let relativePath = ''
    let body = ''
    if (createKind === 'faq') {
      relativePath = `faq/${createCategory}/${slug}.md`
      body = buildFaqTemplate(createCategory, slug, title)
    } else if (createKind === 'root') {
      relativePath = `${slug}.md`
      body = `---\ntitle: "${title.replace(/"/g, '\\"')}"\nstatus: draft\n---\n\n# ${title}\n`
    } else {
      relativePath = `${createKind}/${slug}.md`
      body = buildNonFaqTemplate(createKind, slug, title)
    }

    setCreating(true)
    try {
      const res = await fetch('/api/admin/assistance/wiki/item', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: relativePath, content: body }),
      })
      const data = await res.json().catch(() => ({}))
      if (res.status === 409) {
        toastError('Ce fichier existe déjà.')
        return
      }
      if (!res.ok) {
        toastError(data.error === 'invalid_faq_category' ? 'Catégorie FAQ invalide.' : 'Création impossible.')
        return
      }
      toastSuccess('Fiche créée.')
      setCreateOpen(false)
      setCreateSlug('')
      setCreateTitle('')
      await loadTree()
      setSelectedPath(relativePath)
    } catch {
      toastError('Erreur réseau.')
    } finally {
      setCreating(false)
    }
  }

  if (!authChecked) {
    return (
      <div className="flex items-center gap-2 text-gray-600">
        <Loader2 className="w-5 h-5 animate-spin" />
        Vérification de la session…
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <AssistanceAdminHubNav className="mx-6 mt-6" />
      <div>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
          <BookMarked className="w-8 h-8 text-indigo-600" />
          Wiki produit (Markdown)
        </h1>
        <p className="text-gray-600 mt-2 max-w-3xl">
          Fiches lues par le chatbot assistance (
          <code className="text-xs bg-gray-100 px-1 rounded">select_wiki_pages</code> /{' '}
          <code className="text-xs bg-gray-100 px-1 rounded">read_wiki_page</code>
          ). Structure alignée sur{' '}
          <span className="font-medium">faq/&lt;catégorie&gt;/*.md</span>,{' '}
          <span className="font-medium">concepts/</span>,{' '}
          <span className="font-medium">entities/</span>,{' '}
          <span className="font-medium">policies/</span> et fichiers racine (
          <code className="text-xs bg-gray-100 px-1 rounded">index.md</code>, etc.).
        </p>
        <p className="text-sm text-gray-500 mt-2">
          Hub lié :{' '}
          <Link href="/admin/assistance/knowledge" className="text-indigo-600 hover:underline">
            Knowledge agents (SQL)
          </Link>
          {' · '}
          <Link href="/admin/help" className="text-indigo-600 hover:underline">
            Help Center (CMS)
          </Link>
        </p>
      </div>

      {browseError && (
        <Card className="border-amber-200 bg-amber-50">
          <CardHeader className="pb-2">
            <CardTitle className="text-amber-900 text-base flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              Dossier wiki non monté
            </CardTitle>
            <CardDescription className="text-amber-800">
              {browseError} En local, les fichiers se trouvent sous{' '}
              <code className="text-xs break-all">
                services/arquantix/api/services/assistance/data/wiki/
              </code>
              . Vous pouvez définir la variable d’environnement{' '}
              <code className="text-xs">WIKI_MARKDOWN_ROOT</code> pour pointer explicitement vers ce répertoire.
            </CardDescription>
          </CardHeader>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <Card className="lg:col-span-4 xl:col-span-3">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between gap-2">
              <CardTitle className="text-lg">Fichiers</CardTitle>
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => setCreateOpen(true)}
                disabled={!!browseError || loadingTree}
              >
                <FilePlus2 className="w-4 h-4 mr-1" />
                Nouveau
              </Button>
            </div>
            <CardDescription className="truncate text-xs font-mono">
              {wikiRoot ?? '—'}
            </CardDescription>
            <div className="relative mt-2">
              <Search className="absolute left-2 top-2.5 w-4 h-4 text-gray-400" />
              <Input
                className="pl-8 h-9"
                placeholder="Filtrer…"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              />
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-8 text-xs"
                onClick={expandAllFolders}
                disabled={loadingTree || !!browseError || nodes.length === 0}
              >
                <ChevronsDown className="w-3.5 h-3.5 mr-1 shrink-0" />
                Tout déplier
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="h-8 text-xs"
                onClick={collapseAllFolders}
                disabled={loadingTree || !!browseError}
              >
                <ChevronsUp className="w-3.5 h-3.5 mr-1 shrink-0" />
                Tout replier
              </Button>
            </div>
          </CardHeader>
          <CardContent className="pt-0">
            {loadingTree ? (
              <div className="flex items-center gap-2 text-gray-500 text-sm py-8 justify-center">
                <Loader2 className="w-4 h-4 animate-spin" />
                Chargement…
              </div>
            ) : (
              <ScrollArea className="h-[min(70vh,720px)] pr-2">
                {filteredNodes.map((n) => (
                  <WikiTreeRow
                    key={n.path}
                    node={n}
                    depth={0}
                    selectedPath={selectedPath}
                    onSelect={setSelectedPath}
                    expandedPaths={expandedFolders}
                    onToggleFolder={toggleFolder}
                  />
                ))}
                {filteredNodes.length === 0 && !browseError && (
                  <p className="text-sm text-gray-500 py-6">Aucun fichier .md</p>
                )}
              </ScrollArea>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-8 xl:col-span-9 min-h-[480px]">
          <CardHeader className="flex flex-row items-start justify-between gap-4">
            <div className="min-w-0">
              <CardTitle className="text-lg">Éditeur</CardTitle>
              <CardDescription className="font-mono text-xs truncate">
                {selectedPath ?? 'Sélectionnez une fiche à gauche'}
              </CardDescription>
            </div>
            <Button
              type="button"
              onClick={handleSave}
              disabled={!selectedPath || !dirty || saving || loadingFile}
            >
              {saving ? (
                <Loader2 className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <Save className="w-4 h-4 mr-2" />
              )}
              Enregistrer
            </Button>
          </CardHeader>
          <CardContent>
            {!selectedPath && (
              <p className="text-gray-500 text-sm py-12 text-center">
                Choisissez un fichier dans l’arborescence pour l’afficher et l’éditer.
              </p>
            )}
            {selectedPath && loadingFile && (
              <div className="flex justify-center py-12 text-gray-500">
                <Loader2 className="w-8 h-8 animate-spin" />
              </div>
            )}
            {selectedPath && !loadingFile && (
              <Tabs defaultValue="split">
                <TabsList className="mb-3">
                  <TabsTrigger value="split">Côte à côte</TabsTrigger>
                  <TabsTrigger value="edit">Markdown</TabsTrigger>
                  <TabsTrigger value="preview">Aperçu</TabsTrigger>
                </TabsList>
                <TabsContent value="split" className="mt-0">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <Textarea
                      className="min-h-[min(55vh,560px)] font-mono text-sm"
                      value={content}
                      onChange={(e) => setContent(e.target.value)}
                      spellCheck={false}
                    />
                    <ScrollArea className="h-[min(55vh,560px)] rounded-md border bg-white p-4 text-sm prose prose-sm max-w-none dark:prose-invert">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                    </ScrollArea>
                  </div>
                </TabsContent>
                <TabsContent value="edit" className="mt-0">
                  <Textarea
                    className="min-h-[min(60vh,620px)] font-mono text-sm"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    spellCheck={false}
                  />
                </TabsContent>
                <TabsContent value="preview" className="mt-0">
                  <ScrollArea className="h-[min(60vh,620px)] rounded-md border bg-white p-4 text-sm prose prose-sm max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
                  </ScrollArea>
                </TabsContent>
              </Tabs>
            )}
          </CardContent>
        </Card>
      </div>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Nouvelle fiche Markdown</DialogTitle>
            <DialogDescription>
              Le chemin respecte les dossiers du wiki (voir{' '}
              <code className="text-xs">wiki_repo.py</code> côté API).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Emplacement</Label>
              <Select
                value={createKind}
                onValueChange={(v) =>
                  setCreateKind(v as typeof createKind)
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="faq">FAQ — faq/&lt;catégorie&gt;/…</SelectItem>
                  <SelectItem value="concepts">concepts/…</SelectItem>
                  <SelectItem value="entities">entities/…</SelectItem>
                  <SelectItem value="policies">policies/…</SelectItem>
                  <SelectItem value="root">Racine wiki (index.md, …)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {createKind === 'faq' && (
              <div className="space-y-2">
                <Label>Catégorie FAQ</Label>
                <Select value={createCategory} onValueChange={setCreateCategory}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="max-h-60">
                    {WIKI_FAQ_CATEGORIES.map((c) => (
                      <SelectItem key={c} value={c}>
                        {c}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="wiki-slug">
                Slug fichier {createKind === 'root' ? '(ex. ma-fiche)' : '(sans .md)'}
              </Label>
              <Input
                id="wiki-slug"
                value={createSlug}
                onChange={(e) => setCreateSlug(e.target.value)}
                placeholder="my-new-page"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="wiki-title">Titre (frontmatter)</Label>
              <Input
                id="wiki-title"
                value={createTitle}
                onChange={(e) => setCreateTitle(e.target.value)}
                placeholder="Optionnel — défaut dérivé du slug"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              Annuler
            </Button>
            <Button type="button" onClick={handleCreate} disabled={creating}>
              {creating ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Créer'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function resOk(data: unknown): data is BrowseResponse {
  return (
    typeof data === 'object' &&
    data !== null &&
    'nodes' in data &&
    Array.isArray((data as BrowseResponse).nodes) &&
    'root' in data &&
    typeof (data as BrowseResponse).root === 'string'
  )
}
