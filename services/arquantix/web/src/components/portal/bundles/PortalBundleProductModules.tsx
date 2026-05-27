'use client'

import ReactMarkdown from 'react-markdown'

import { AppCard } from '@/components/design-system/app/AppCard'
import { AppMetricsList } from '@/components/design-system/app/AppMetricsList'
import { AppMetricsRow } from '@/components/design-system/app/AppMetricsRow'
import {
  AppPortfolioAllocationDonut,
  type AppPortfolioAllocationSlice,
} from '@/components/design-system/app/AppPortfolioAllocationDonut'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import {
  normalizeVaultModuleType,
  orderBundleBodyModules,
  readAllocationSlices,
} from '@/lib/portal/bundleProductFormat'
import type { PortalBundleVaultModule } from '@/lib/portal/bundleProductTypes'

type Props = {
  modules: PortalBundleVaultModule[]
}

function MarkdownModule({
  title,
  markdown,
}: {
  title?: string
  markdown: string
}) {
  if (!markdown.trim() && !title?.trim()) return null
  return (
    <AppCard className="flex w-full flex-col gap-3 !p-5 sm:!p-6">
      {title?.trim() ? <AppSectionHeader title={title.trim()} /> : null}
      {markdown.trim() ? (
        <div className="font-ui text-[15px] leading-relaxed text-v-fg-body [&_p]:m-0 [&_p+p]:mt-3">
          <ReactMarkdown>{markdown}</ReactMarkdown>
        </div>
      ) : null}
    </AppCard>
  )
}

function renderModule(mod: PortalBundleVaultModule): React.ReactNode {
  const c = mod.content
  const type = normalizeVaultModuleType(mod.type)

  switch (type) {
    case 'allocationmodule': {
      const slices: AppPortfolioAllocationSlice[] = readAllocationSlices(c)
      const title = typeof c.title === 'string' ? c.title.trim() : 'Target allocation'
      const intro = typeof c.introText === 'string' ? c.introText.trim() : ''
      const assetCount = slices.length
      return (
        <AppPortfolioAllocationDonut
          key={mod.id ?? type}
          title={title}
          subtitle={intro || undefined}
          slices={slices}
          centerValue={assetCount > 0 ? String(assetCount) : undefined}
          centerLabel={assetCount === 1 ? 'asset' : 'assets'}
        />
      )
    }

    case 'keyinformationmodule': {
      const title = typeof c.title === 'string' ? c.title.trim() : 'Key information'
      const rowsRaw = Array.isArray(c.rows) ? c.rows : []
      const rows = rowsRaw
        .map((raw) => {
          const row = raw as Record<string, unknown>
          return {
            label: typeof row.label === 'string' ? row.label.trim() : '',
            value: typeof row.value === 'string' ? row.value.trim() : '',
          }
        })
        .filter((r) => r.label || r.value)
      if (!rows.length) return null
      return (
        <section key={mod.id ?? type} className="flex w-full flex-col gap-3">
          <AppSectionHeader title={title} />
          <AppMetricsList variant="plain">
            {rows.map((row, i) => (
              <AppMetricsRow key={`${row.label}-${i}`} label={row.label} value={row.value} />
            ))}
          </AppMetricsList>
        </section>
      )
    }

    case 'simplemarkdowncontentmodule':
    case 'descriptionmodule': {
      const moduleTitle =
        typeof c.moduleTitle === 'string' ? c.moduleTitle.trim() : undefined
      const markdown = typeof c.markdown === 'string' ? c.markdown : ''
      return (
        <MarkdownModule
          key={mod.id ?? type}
          title={moduleTitle}
          markdown={markdown}
        />
      )
    }

    case 'contentbasdepagesansmoduleblanc': {
      const markdown = typeof c.markdown === 'string' ? c.markdown : ''
      return (
        <MarkdownModule
          key={mod.id ?? type}
          markdown={markdown}
        />
      )
    }

    case 'competitiveadvantagesmodule': {
      const title = typeof c.title === 'string' ? c.title.trim() : ''
      const rows = Array.isArray(c.rows) ? c.rows : []
      const cells = rows
        .map((raw, i) => {
          const row = raw as Record<string, unknown>
          const rt = typeof row.title === 'string' ? row.title.trim() : ''
          const rd = typeof row.description === 'string' ? row.description.trim() : ''
          if (!rt && !rd) return null
          return (
            <AppCard key={i} className="space-y-2 !p-5">
              {rt ? (
                <h3 className="m-0 font-ui text-[18px] font-semibold text-v-fg">{rt}</h3>
              ) : null}
              {rd ? (
                <p className="m-0 font-ui text-[15px] leading-relaxed text-v-fg-body">{rd}</p>
              ) : null}
            </AppCard>
          )
        })
        .filter(Boolean)
      if (!cells.length) return null
      return (
        <section key={mod.id ?? type} className="flex w-full flex-col gap-3">
          {title ? <AppSectionHeader title={title} /> : null}
          <div className="grid gap-4 md:grid-cols-2">{cells}</div>
        </section>
      )
    }

    default:
      return null
  }
}

export function PortalBundleProductModules({ modules }: Props) {
  const bodyModules = orderBundleBodyModules(modules)
  if (!bodyModules.length) return null

  return (
    <div className="flex w-full flex-col gap-6">
      {bodyModules.map((mod) => renderModule(mod))}
    </div>
  )
}
