'use client'

import { Badge } from '@/components/ui/badge'

import type { AssistantRoutingTags } from '@/lib/admin/assistanceAssistantTags'

type Props = {
  tags: AssistantRoutingTags
}

/**
 * Trois badges dans l'ordre fixe : agent de réponse · intention client · objectif.
 */
export function AssistanceMessageRoutingTags({ tags }: Props) {
  const { agentLabel, clientIntentLabel, objectiveLabel } = tags
  const items: { key: string; label: string | null; variant: string }[] = [
    {
      key: 'agent',
      label: agentLabel,
      variant:
        'bg-slate-100 text-slate-800 border-slate-300 text-[10px] font-medium',
    },
    {
      key: 'intent',
      label: clientIntentLabel,
      variant:
        'bg-amber-50 text-amber-950 border-amber-200 text-[10px] font-medium',
    },
    {
      key: 'goal',
      label: objectiveLabel,
      variant:
        'bg-emerald-50 text-emerald-900 border-emerald-200 text-[10px] font-medium',
    },
  ]

  if (!items.some((i) => i.label)) {
    return null
  }

  return (
    <div
      className="mb-1.5 flex flex-wrap items-center gap-1"
      aria-label="Routage cognitive : agent, intention, objectif"
    >
      {items.map((i) =>
        i.label ? (
          <Badge
            key={i.key}
            variant="outline"
            className={`${i.variant} py-0 px-1.5 h-5 rounded-sm tracking-tight`}
          >
            {i.label}
          </Badge>
        ) : (
          <Badge
            key={`${i.key}-empty`}
            variant="outline"
            className="border-dashed border-slate-300 text-slate-400 text-[9px] py-0 px-1 h-5"
          >
            —
          </Badge>
        ),
      )}
    </div>
  )
}
