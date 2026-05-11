'use client'

/**
 * Navigation horizontale partagée entre les pages « hub » assistance admin
 * (architecture, knowledge, wiki, funnel, observabilité).
 */
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ComponentType } from 'react'
import {
  BarChart3,
  BookMarked,
  Bot,
  Layers,
  LineChart,
  ListOrdered,
  MousePointerClick,
} from 'lucide-react'

import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const LINKS: {
  href: string
  label: string
  Icon: ComponentType<{ className?: string }>
  isActive: (path: string) => boolean
}[] = [
  {
    href: '/admin/assistance',
    label: 'Architecture',
    Icon: Layers,
    isActive: (p) => p === '/admin/assistance' || p === '/admin/assistance/',
  },
  {
    href: '/admin/assistance/knowledge',
    label: 'Knowledge agents',
    Icon: Bot,
    isActive: (p) => p.startsWith('/admin/assistance/knowledge'),
  },
  {
    href: '/admin/assistance/wiki',
    label: 'Wiki MD',
    Icon: BookMarked,
    isActive: (p) => p.startsWith('/admin/assistance/wiki'),
  },
  {
    href: '/admin/assistance/cognitive-funnel',
    label: 'Funnel cognitif',
    Icon: BarChart3,
    isActive: (p) => p.startsWith('/admin/assistance/cognitive-funnel'),
  },
  {
    href: '/admin/assistance/cal-playbooks',
    label: 'Playbooks CAL',
    Icon: ListOrdered,
    isActive: (p) => p.startsWith('/admin/assistance/cal-playbooks'),
  },
  {
    href: '/admin/assistance/agent-action-options',
    label: 'Options action',
    Icon: MousePointerClick,
    isActive: (p) =>
      p.startsWith('/admin/assistance/agent-action-options'),
  },
  {
    href: '/admin/assistance/observability',
    label: 'Observabilité (KPI)',
    Icon: LineChart,
    isActive: (p) => p.startsWith('/admin/assistance/observability'),
  },
]

export function AssistanceAdminHubNav({
  className,
}: {
  className?: string
}) {
  const pathname = usePathname() ?? ''

  return (
    <nav
      className={cn(
        'flex flex-wrap gap-2 rounded-lg border border-slate-200 bg-slate-50/80 px-3 py-2.5',
        className,
      )}
      aria-label="Navigation assistance admin"
    >
      {LINKS.map(({ href, label, Icon, isActive }) => {
        const active = isActive(pathname)
        return (
          <Button
            key={href}
            variant={active ? 'secondary' : 'outline'}
            size="sm"
            className={cn(
              'text-xs font-normal',
              active && 'border-indigo-200 bg-indigo-50 text-indigo-900',
            )}
            asChild
          >
            <Link
              href={href}
              className="inline-flex items-center gap-1.5"
              {...(active ? { 'aria-current': 'page' as const } : {})}
            >
              <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" aria-hidden />
              {label}
              <span aria-hidden className="text-slate-400">
                →
              </span>
            </Link>
          </Button>
        )
      })}
    </nav>
  )
}
