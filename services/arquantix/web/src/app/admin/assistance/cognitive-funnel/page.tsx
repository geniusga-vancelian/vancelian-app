'use client'

/**
 * Admin — Funnel cognitif (Cognitive Bot v4 — Lot 5/6).
 *
 * Source de vérité : API Python (FastAPI router
 * `services/assistance/admin_cognitive_router.py`). Cette page passe par
 * la route proxy `/api/admin/assistance/cognitive/funnel`.
 *
 * Lecture-only. Affiche les distributions cognitives sur une fenêtre
 * temporelle au choix (7 / 14 / 30 / 90 jours) :
 *
 *   - `conversation_stage`  (discovery / clarification / recommendation / conversion)
 *   - `emotional_intent`    (FEAR_RISK, CURIOSITY, COMPLIANCE_BLOCKED, …)
 *   - `primary_goal`        (reassure / de_escalate / unblock / inform / educate / convert)
 *   - `next_best_action`    (give_proof / give_control / micro_step / …)
 *   - `agent_id`            (router décision finale)
 *   - `trust_level`         (stats avg/min/max sur 0..1)
 *
 * Cf. `docs/arquantix/COGNITIVE_BOT.md` § 5 (Métriques & Funnel).
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import { AlertCircle, Loader2, RefreshCw } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { toastError } from '@/lib/admin/toast'
import { AssistanceAdminHubNav } from '@/components/admin/AssistanceAdminHubNav'

// ─── Types ──────────────────────────────────────────────────────────────────

type CountBucket = {
  label: string
  count: number
  pct: number
}

type TrustLevelStats = {
  avg: number | null
  min: number | null
  max: number | null
  sample_size: number
}

type CognitiveFunnelResponse = {
  period_start: string
  period_end: string
  period_days: number
  total_decisions: number
  by_stage: CountBucket[]
  by_emotional_intent: CountBucket[]
  by_primary_goal: CountBucket[]
  by_next_best_action: CountBucket[]
  by_agent_id: CountBucket[]
  trust_level: TrustLevelStats
}

// ─── Helpers visuels ────────────────────────────────────────────────────────

/**
 * Couleur de Badge cohérente avec la sémantique cognitive. Les emotional
 * intents "négatifs" (peur / colère / blocage) sont en alerte ; les
 * "positifs" (curiosité / opportunité) en succès ; les neutres en
 * outline. Les stages avancés (recommendation / conversion) sont colorés
 * pour visualiser la progression.
 */
function variantForLabel(
  dimension:
    | 'stage'
    | 'emotional'
    | 'primary_goal'
    | 'next_best_action'
    | 'agent',
  label: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  const upper = label.toUpperCase()

  if (dimension === 'emotional') {
    if (
      upper === 'FEAR_RISK' ||
      upper === 'ANGER' ||
      upper === 'COMPLIANCE_BLOCKED'
    )
      return 'destructive'
    if (upper === 'CURIOSITY' || upper === 'OPPORTUNITY') return 'default'
    if (upper === 'NEUTRAL') return 'secondary'
    return 'outline'
  }
  if (dimension === 'stage') {
    if (label === 'conversion') return 'default'
    if (label === 'recommendation') return 'secondary'
    if (label === 'unknown') return 'outline'
    return 'outline'
  }
  if (dimension === 'primary_goal') {
    if (label === 'reassure' || label === 'de_escalate') return 'destructive'
    if (label === 'convert') return 'default'
    return 'outline'
  }
  return 'outline'
}

function formatNumber(n: number): string {
  return new Intl.NumberFormat('fr-FR').format(n)
}

function formatRange(start: string, end: string): string {
  try {
    const s = new Date(start)
    const e = new Date(end)
    const fmt = new Intl.DateTimeFormat('fr-FR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
    return `${fmt.format(s)} → ${fmt.format(e)}`
  } catch {
    return `${start} → ${end}`
  }
}

// ─── Sous-composant : carte de distribution catégorielle ─────────────────────

type DistributionCardProps = {
  title: string
  description: string
  dimension:
    | 'stage'
    | 'emotional'
    | 'primary_goal'
    | 'next_best_action'
    | 'agent'
  buckets: CountBucket[]
}

function DistributionCard({
  title,
  description,
  dimension,
  buckets,
}: DistributionCardProps) {
  const total = useMemo(
    () => buckets.reduce((sum, b) => sum + b.count, 0),
    [buckets],
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {buckets.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Aucune décision sur la période.
          </p>
        ) : (
          <ul className="space-y-3">
            {buckets.map((b) => (
              <li key={b.label} className="space-y-1">
                <div className="flex items-center justify-between gap-2">
                  <Badge variant={variantForLabel(dimension, b.label)}>
                    {b.label}
                  </Badge>
                  <span className="text-sm tabular-nums text-muted-foreground">
                    {formatNumber(b.count)} · {b.pct.toFixed(1)}%
                  </span>
                </div>
                <Progress value={b.pct} className="h-1.5" />
              </li>
            ))}
          </ul>
        )}
        {total > 0 && (
          <p className="mt-4 text-xs text-muted-foreground">
            Total : {formatNumber(total)} décisions agrégées.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Sous-composant : carte trust_level ──────────────────────────────────────

function TrustLevelCard({ stats }: { stats: TrustLevelStats }) {
  const { avg, min, max, sample_size } = stats
  const noData = sample_size === 0 || avg === null

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Trust level</CardTitle>
        <CardDescription>
          Niveau de confiance perçu côté bot (0 = méfiance, 1 = confiance
          totale).
        </CardDescription>
      </CardHeader>
      <CardContent>
        {noData ? (
          <p className="text-sm text-muted-foreground">
            Aucune décision avec trust_level sur la période.
          </p>
        ) : (
          <div className="space-y-3">
            <div>
              <div className="flex items-baseline justify-between">
                <span className="text-3xl font-semibold tabular-nums">
                  {avg!.toFixed(2)}
                </span>
                <span className="text-xs text-muted-foreground">
                  moyenne · n = {formatNumber(sample_size)}
                </span>
              </div>
              <Progress value={avg! * 100} className="mt-2" />
            </div>
            <div className="grid grid-cols-2 gap-3 pt-2 text-sm">
              <div className="rounded-md border p-2">
                <p className="text-xs uppercase text-muted-foreground">
                  Min
                </p>
                <p className="text-lg tabular-nums">
                  {min !== null ? min.toFixed(2) : '—'}
                </p>
              </div>
              <div className="rounded-md border p-2">
                <p className="text-xs uppercase text-muted-foreground">
                  Max
                </p>
                <p className="text-lg tabular-nums">
                  {max !== null ? max.toFixed(2) : '—'}
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Page principale ────────────────────────────────────────────────────────

const PERIOD_OPTIONS: { value: string; label: string }[] = [
  { value: '7', label: '7 derniers jours' },
  { value: '14', label: '14 derniers jours' },
  { value: '30', label: '30 derniers jours' },
  { value: '90', label: '90 derniers jours' },
]

export default function CognitiveFunnelPage() {
  const [periodDays, setPeriodDays] = useState<string>('7')
  const [data, setData] = useState<CognitiveFunnelResponse | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)

  const fetchFunnel = useCallback(async (days: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(
        `/api/admin/assistance/cognitive/funnel?period_days=${encodeURIComponent(days)}`,
        { cache: 'no-store' },
      )
      if (!res.ok) {
        const body = await res.text().catch(() => '')
        throw new Error(
          body || `HTTP ${res.status} en lisant le funnel cognitif.`,
        )
      }
      const json = (await res.json()) as CognitiveFunnelResponse
      setData(json)
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'Erreur inconnue'
      setError(msg)
      toastError(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void fetchFunnel(periodDays)
  }, [fetchFunnel, periodDays])

  return (
    <div className="space-y-6 p-6">
      <AssistanceAdminHubNav />
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Funnel cognitif
          </h1>
          <p className="text-sm text-muted-foreground">
            Distributions des décisions du router ({' '}
            <code>router_classify</code>) — Cognitive Bot v4. Source :{' '}
            <code>assistance_agent_decisions</code> (colonnes natives ·
            fallback JSONB).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={periodDays} onValueChange={setPeriodDays}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Période" />
            </SelectTrigger>
            <SelectContent>
              {PERIOD_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => void fetchFunnel(periodDays)}
            disabled={loading}
            aria-label="Rafraîchir"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Sommaire */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Sommaire</CardTitle>
          <CardDescription>
            {data ? formatRange(data.period_start, data.period_end) : '—'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="rounded-md border p-3">
              <p className="text-xs uppercase text-muted-foreground">
                Décisions agrégées
              </p>
              <p className="text-2xl font-semibold tabular-nums">
                {data ? formatNumber(data.total_decisions) : '—'}
              </p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-xs uppercase text-muted-foreground">
                Stages distincts
              </p>
              <p className="text-2xl font-semibold tabular-nums">
                {data ? data.by_stage.length : '—'}
              </p>
            </div>
            <div className="rounded-md border p-3">
              <p className="text-xs uppercase text-muted-foreground">
                Intents émotionnels distincts
              </p>
              <p className="text-2xl font-semibold tabular-nums">
                {data ? data.by_emotional_intent.length : '—'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* États de chargement / erreur */}
      {loading && !data && (
        <Card>
          <CardContent className="flex items-center gap-2 py-8 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            Chargement du funnel cognitif…
          </CardContent>
        </Card>
      )}
      {error && (
        <Card className="border-destructive/50">
          <CardContent className="flex items-start gap-2 py-4 text-sm text-destructive">
            <AlertCircle className="mt-0.5 h-4 w-4" />
            <div>
              <p className="font-medium">Échec du chargement</p>
              <p className="text-muted-foreground">{error}</p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Grille des distributions */}
      {data && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-3">
          <DistributionCard
            title="Stage de conversation"
            description="Progression dans le funnel : discovery → clarification → recommendation → conversion."
            dimension="stage"
            buckets={data.by_stage}
          />
          <DistributionCard
            title="Intent émotionnel"
            description="Heuristique keyword + LLM (cf. cognitive_state.py)."
            dimension="emotional"
            buckets={data.by_emotional_intent}
          />
          <TrustLevelCard stats={data.trust_level} />
          <DistributionCard
            title="Primary goal (objectif)"
            description="reassure / de_escalate / unblock / inform / educate / convert."
            dimension="primary_goal"
            buckets={data.by_primary_goal}
          />
          <DistributionCard
            title="Next best action"
            description="give_proof / give_control / micro_step / ask_question / recommend / call_to_action."
            dimension="next_best_action"
            buckets={data.by_next_best_action}
          />
          <DistributionCard
            title="Agent élu"
            description="Décision finale du router (advisor, trust, compliance, product, …)."
            dimension="agent"
            buckets={data.by_agent_id}
          />
        </div>
      )}
    </div>
  )
}
