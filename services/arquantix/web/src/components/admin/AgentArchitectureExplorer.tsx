'use client'

/**
 * Arborescence admin : architecture multi-agents + prompts Markdown.
 */
import { Fragment, useCallback, useEffect, useMemo, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { ChevronDown, ChevronRight, FileCode2, Loader2 } from 'lucide-react'

import {
  AGENT_ARCHITECTURE_TREE,
  type AgentArchitectureNode,
  RESPONSE_FRAMEWORK_AGENTS_LABEL,
  RESPONSE_FRAMEWORK_FILE,
  flattenArchitecture,
} from '@/lib/admin/agentArchitecture'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { AssistanceAdminHubNav } from '@/components/admin/AssistanceAdminHubNav'

const KIND_STYLE: Record<
  AgentArchitectureNode['kind'],
  { label: string; className: string }
> = {
  orchestrator: {
    label: 'Orchestrateur',
    className: 'border-violet-500/50 bg-violet-500/10 text-violet-700',
  },
  dispatcher: {
    label: 'Dispatcher',
    className: 'border-amber-500/50 bg-amber-500/10 text-amber-800',
  },
  expert: {
    label: 'Expert',
    className: 'border-sky-500/50 bg-sky-500/10 text-sky-800',
  },
  subagent: {
    label: 'Sous-agent',
    className: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-800',
  },
  internal: {
    label: 'Transversal',
    className: 'border-slate-500/50 bg-slate-500/10 text-slate-800',
  },
  memory: {
    label: 'Mémoire',
    className: 'border-rose-500/50 bg-rose-500/10 text-rose-800',
  },
}

function NodeRow({
  node,
  depth,
  expanded,
  toggle,
  selectedId,
  select,
}: {
  node: AgentArchitectureNode
  depth: number
  expanded: Set<string>
  toggle: (id: string) => void
  selectedId: string | null
  select: (id: string) => void
}) {
  const hasKids = Boolean(node.children?.length)
  const isOpen = expanded.has(node.id)
  const isSel = selectedId === node.id

  return (
    <Fragment>
      <button
        type="button"
        onClick={() => {
          select(node.id)
          if (hasKids) toggle(node.id)
        }}
        className={
          'flex w-full items-start gap-2 rounded-md border px-2 py-2 text-left text-sm transition-colors hover:bg-slate-50 ' +
          (isSel ? 'border-indigo-400 bg-indigo-50/90 ' : 'border-transparent ')
        }
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        {hasKids ? (
          isOpen ? (
            <ChevronDown className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
          ) : (
            <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
          )
        ) : (
          <span className="mt-0.5 inline-block w-4 shrink-0" />
        )}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-medium text-slate-900">{node.title}</span>
            <code className="rounded bg-slate-100 px-1.5 py-0.5 text-[11px] text-slate-600">
              {node.id}
            </code>
            <Badge
              variant="outline"
              className={`text-[10px] font-normal ${KIND_STYLE[node.kind].className}`}
            >
              {KIND_STYLE[node.kind].label}
            </Badge>
          </div>
          <p className="mt-0.5 line-clamp-2 text-xs text-slate-600">
            {node.description}
          </p>
        </div>
      </button>
      {hasKids && isOpen
        ? node.children!.map((ch) => (
            <NodeRow
              key={ch.id}
              node={ch}
              depth={depth + 1}
              expanded={expanded}
              toggle={toggle}
              selectedId={selectedId}
              select={select}
            />
          ))
        : null}
    </Fragment>
  )
}

export function AgentArchitectureExplorer() {
  const allNodes = useMemo(
    () => flattenArchitecture(AGENT_ARCHITECTURE_TREE),
    []
  )
  const byId = useMemo(() => {
    const m = new Map<string, AgentArchitectureNode>()
    for (const n of allNodes) m.set(n.id, n)
    return m
  }, [allNodes])

  const [expanded, setExpanded] = useState(() => {
    return new Set([
      'router',
      'compliance',
      'cross-runtime',
      'default',
      'advisor',
      'product',
      'market',
      'trust',
      'summarizer',
    ])
  })
  const [selectedId, setSelectedId] = useState<string>('router')
  const selected = selectedId ? byId.get(selectedId) ?? null : null

  const toggle = useCallback((id: string) => {
    setExpanded((prev) => {
      const n = new Set(prev)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }, [])

  const [manifestOk, setManifestOk] = useState<boolean | null>(null)
  const [missingOnDisk, setMissingOnDisk] = useState<string[]>([])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/admin/assistance/prompts')
        const data = await res.json()
        if (!res.ok) {
          if (!cancelled) {
            setManifestOk(false)
            setMissingOnDisk([])
          }
          return
        }
        const files = new Set<string>((data.files as string[]) ?? [])
        const need = new Set<string>()
        for (const n of allNodes) {
          for (const p of n.prompts) {
            need.add(p.file)
          }
        }
        const miss: string[] = []
        for (const f of need) {
          if (!files.has(f)) miss.push(f)
        }
        if (!cancelled) {
          setManifestOk(true)
          setMissingOnDisk(miss.sort())
        }
      } catch {
        if (!cancelled) {
          setManifestOk(false)
          setMissingOnDisk([])
        }
      }
    })()
    return () => {
      cancelled = true
    }
  }, [allNodes])

  const [mdOpen, setMdOpen] = useState(false)
  const [mdPath, setMdPath] = useState<string | null>(null)
  const [mdLabel, setMdLabel] = useState<string>('')
  const [mdContent, setMdContent] = useState<string>('')
  const [mdLoading, setMdLoading] = useState(false)
  const [mdError, setMdError] = useState<string | null>(null)

  const openMarkdown = useCallback(async (file: string, label: string) => {
    setMdPath(file)
    setMdLabel(label)
    setMdOpen(true)
    setMdLoading(true)
    setMdError(null)
    setMdContent('')
    try {
      const res = await fetch(
        `/api/admin/assistance/prompts/file?path=${encodeURIComponent(file)}`
      )
      const data = await res.json()
      if (!res.ok) {
        setMdError(
          typeof data.error === 'string' ? data.error : `Erreur HTTP ${res.status}`
        )
        return
      }
      setMdContent(String(data.content ?? ''))
    } catch (e) {
      setMdError(e instanceof Error ? e.message : String(e))
    } finally {
      setMdLoading(false)
    }
  }, [])

  return (
    <div className="space-y-6">
      <AssistanceAdminHubNav />

      <Card>
        <CardHeader>
          <CardTitle>Response Framework (auto-injection)</CardTitle>
          <CardDescription>
            Fichier <code className="rounded bg-slate-100 px-1">{RESPONSE_FRAMEWORK_FILE}</code>{' '}
            concaténé automatiquement après le prompt système pour :{' '}
            <span className="font-medium text-slate-800">
              {RESPONSE_FRAMEWORK_AGENTS_LABEL}
            </span>
            . Non appliqué au routeur ni au summarizer.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2">
          <Button variant="secondary" size="sm" onClick={() => openMarkdown(RESPONSE_FRAMEWORK_FILE, RESPONSE_FRAMEWORK_FILE)}>
            <FileCode2 className="mr-2 h-4 w-4" />
            Ouvrir _response_framework.md
          </Button>
        </CardContent>
      </Card>

      {manifestOk === false ? (
        <p className="text-sm text-amber-700">
          Impossible de joindre le dossier des prompts sur ce serveur (voir variable{' '}
          <code className="rounded bg-slate-100 px-1">ASSISTANCE_PROMPTS_ROOT</code> ou monorepo).
        </p>
      ) : null}
      {missingOnDisk.length > 0 ? (
        <p className="text-sm text-rose-700">
          Fichiers attendus par le modèle mais absents du disque :{' '}
          {missingOnDisk.join(', ')}
        </p>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Arborescence</CardTitle>
            <CardDescription>
              Cliquez sur un nœud : détail à droite ; la flèche replie / déplie les enfants.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-1">
            {AGENT_ARCHITECTURE_TREE.map((root) => (
              <NodeRow
                key={root.id}
                node={root}
                depth={0}
                expanded={expanded}
                toggle={toggle}
                selectedId={selectedId}
                select={setSelectedId}
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Détail sélection</CardTitle>
            <CardDescription>
              Prompts sources (fichiers relatifs à{' '}
              <code className="rounded bg-slate-100 px-1">api/services/assistance/prompts/</code>)
              et chemins de décision / choix côté utilisateur.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {selected ? (
              <>
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="text-lg font-semibold text-slate-900">
                    {selected.title}
                  </h3>
                  <Badge variant="outline">{selected.id}</Badge>
                </div>
                <p className="text-sm text-slate-700">{selected.description}</p>

                <div>
                  <h4 className="mb-2 text-sm font-semibold text-slate-800">
                    Routage, tools & choix utilisateur
                  </h4>
                  <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
                    {selected.routingOrChoices.map((line, i) => (
                      <li key={i} className="whitespace-pre-wrap break-words">
                        {line}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <h4 className="mb-2 text-sm font-semibold text-slate-800">
                    Prompts Markdown
                  </h4>
                  {selected.prompts.length === 0 ? (
                    <p className="text-sm text-slate-600">Aucun fichier dédié dans le modèle.</p>
                  ) : (
                    <ul className="space-y-2">
                      {selected.prompts.map((p) => (
                        <li key={p.file}>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-auto w-full justify-start py-2 text-left"
                            onClick={() => openMarkdown(p.file, p.label)}
                          >
                            <FileCode2 className="mr-2 h-4 w-4 shrink-0" />
                            <span className="min-w-0">
                              <span className="block font-medium">{p.label}</span>
                              <code className="text-xs text-slate-600">{p.file}</code>
                            </span>
                          </Button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            ) : (
              <p className="text-sm text-slate-600">Sélectionnez un nœud.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Référence code</CardTitle>
          <CardDescription>
            Fichiers backend utiles pour creuser au-delà des prompts.
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-slate-700 space-y-1">
          <p>
            Registry tools :{' '}
            <code className="rounded bg-slate-100 px-1">services/assistance/agents/tools/registry.py</code>
          </p>
          <p>
            Boucle runtime :{' '}
            <code className="rounded bg-slate-100 px-1">services/assistance/agents/runtime/agent_loop.py</code>
          </p>
          <p>
            Assemblage prompts :{' '}
            <code className="rounded bg-slate-100 px-1">services/assistance/agents/prompt_builder.py</code>
          </p>
          <p>
            Routeur :{' '}
            <code className="rounded bg-slate-100 px-1">services/assistance/agents/router.py</code>
          </p>
        </CardContent>
      </Card>

      <Sheet open={mdOpen} onOpenChange={setMdOpen}>
        <SheetContent side="right" className="flex w-full flex-col sm:max-w-2xl">
          <SheetHeader>
            <SheetTitle className="pr-10">{mdLabel}</SheetTitle>
            <SheetDescription className="flex flex-wrap items-center gap-2 font-mono text-xs break-all">
              {mdPath ? `prompts/${mdPath}` : ''}
              {mdPath ? (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-7 font-sans text-xs"
                  onClick={() => {
                    void navigator.clipboard.writeText(
                      `services/arquantix/api/services/assistance/prompts/${mdPath}`
                    )
                  }}
                >
                  Copier chemin dépôt
                </Button>
              ) : null}
            </SheetDescription>
          </SheetHeader>
          <ScrollArea className="mt-4 min-h-0 flex-1 rounded-md border bg-slate-50/80 p-4">
            {mdLoading ? (
              <div className="flex items-center gap-2 text-slate-600">
                <Loader2 className="h-5 w-5 animate-spin" /> Chargement…
              </div>
            ) : mdError ? (
              <p className="text-sm text-rose-700">{mdError}</p>
            ) : (
              <article className="prose prose-sm max-w-none prose-headings:scroll-mt-20 prose-pre:bg-slate-900 prose-pre:text-slate-100">
                <ReactMarkdown>{mdContent}</ReactMarkdown>
              </article>
            )}
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </div>
  )
}
