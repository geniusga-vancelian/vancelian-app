'use client'

import Link from 'next/link'
import { ExtractedDesignDemo } from '@/components/design-system/extracted/ExtractedDesignDemo'
import { figmaDsButtonLabelClassName } from '@/components/design-system/extracted/tokens/typography'
import { figmaDsColors } from '@/components/design-system/extracted/tokens/colors'
import { figmaDsTypography } from '@/components/design-system/extracted/tokens/typography'
import { cn } from '@/lib/utils'

function flattenColorEntries(
  obj: Record<string, unknown>,
  prefix = '',
): { path: string; hex: string }[] {
  const out: { path: string; hex: string }[] = []
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k
    if (typeof v === 'string' && /^#[0-9A-Fa-f]{3,8}$/i.test(v.trim())) {
      out.push({ path, hex: v.trim() })
    } else if (v !== null && typeof v === 'object' && !Array.isArray(v)) {
      out.push(...flattenColorEntries(v as Record<string, unknown>, path))
    }
  }
  return out
}

function TypographyTokenCard({
  name,
  data,
}: {
  name: string
  data: Record<string, string | number>
}) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h4 className="font-mono text-sm font-semibold text-gray-900">{name}</h4>
      <dl className="mt-3 space-y-1 text-xs text-gray-600">
        {Object.entries(data).map(([key, val]) => (
          <div key={key} className="flex justify-between gap-4">
            <dt className="text-gray-500">{key}</dt>
            <dd className="font-mono text-gray-800">{String(val)}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

const TYPO_BLOCKS: { name: string; data: Record<string, string | number> }[] = [
  { name: 'paragraph', data: figmaDsTypography.paragraph as unknown as Record<string, string | number> },
  { name: 'paragraphLarge', data: figmaDsTypography.paragraphLarge as unknown as Record<string, string | number> },
  { name: 'paragraphLargeBold', data: figmaDsTypography.paragraphLargeBold as unknown as Record<string, string | number> },
  { name: 'links', data: figmaDsTypography.links as unknown as Record<string, string | number> },
  { name: 'tag', data: figmaDsTypography.tag as unknown as Record<string, string | number> },
  { name: 'sectionTitleModule', data: figmaDsTypography.sectionTitleModule as unknown as Record<string, string | number> },
  { name: 'title', data: figmaDsTypography.title as unknown as Record<string, string | number> },
  { name: 'titlepage', data: figmaDsTypography.titlepage as unknown as Record<string, string | number> },
  { name: 'mainTitle', data: figmaDsTypography.mainTitle as unknown as Record<string, string | number> },
  { name: 'buttonLabel', data: figmaDsTypography.buttonLabel as unknown as Record<string, string | number> },
]

export function AdminDesignSystemShowcase() {
  const colorEntries = flattenColorEntries(figmaDsColors as unknown as Record<string, unknown>)

  return (
    <div className="max-w-[1400px]">
      <div className="mb-8 border-b border-gray-200 pb-6">
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">Design System</h1>
        <p className="mt-2 max-w-3xl text-sm text-gray-600">
          Couleurs et typographie (tokens Figma dans{' '}
          <code className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-xs">
            extracted/tokens
          </code>
          ), puis atomes, molécules et organismes extraits du DS.
        </p>
        <div className="mt-4 flex flex-wrap gap-2 text-sm">
          <a
            href="#couleurs"
            className="rounded-md bg-indigo-50 px-3 py-1.5 font-medium text-indigo-800 hover:bg-indigo-100"
          >
            Couleurs
          </a>
          <a
            href="#typographie"
            className="rounded-md bg-indigo-50 px-3 py-1.5 font-medium text-indigo-800 hover:bg-indigo-100"
          >
            Typographie
          </a>
          <a
            href="#composants"
            className="rounded-md bg-indigo-50 px-3 py-1.5 font-medium text-indigo-800 hover:bg-indigo-100"
          >
            Composants (extracted)
          </a>
          <Link
            href="/design"
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 font-medium text-gray-700 hover:bg-gray-50"
          >
            Page publique /design →
          </Link>
        </div>
      </div>

      <section id="couleurs" className="scroll-mt-8 py-8">
        <h2 className="text-lg font-semibold text-gray-900">Couleurs</h2>
        <p className="mt-1 text-sm text-gray-600">
          Palette documentée dans <span className="font-mono text-xs">figmaDsColors</span>.
        </p>
        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {colorEntries.map(({ path, hex }) => (
            <div
              key={path}
              className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm"
            >
              <div
                className="h-20 w-full border-b border-gray-100"
                style={{ backgroundColor: hex }}
              />
              <div className="p-3">
                <p className="font-mono text-xs font-medium text-gray-900">{path}</p>
                <p className="mt-1 font-mono text-xs uppercase text-gray-500">{hex}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section id="typographie" className="scroll-mt-8 border-t border-gray-200 py-8">
        <h2 className="text-lg font-semibold text-gray-900">Typographie</h2>
        <p className="mt-1 text-sm text-gray-600">
          Familles : Avenir Heavy / Roman / Book — voir{' '}
          <span className="font-mono text-xs">figmaDsTypography</span>.
        </p>

        <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-4">
          <h3 className="text-sm font-semibold text-gray-800">Font families (classes)</h3>
          <ul className="mt-2 space-y-2 font-mono text-xs text-gray-700">
            {Object.entries(figmaDsTypography.fontFamily).map(([k, v]) => (
              <li key={k}>
                <span className="text-gray-500">{k}:</span> {v}
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {TYPO_BLOCKS.map(({ name, data }) => (
            <TypographyTokenCard key={name} name={name} data={data} />
          ))}
        </div>

        <div className="mt-8 rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-sm font-semibold text-gray-900">Échantillon Button (libellé)</h3>
          <p className="mt-1 font-mono text-xs text-gray-500">figmaDsButtonLabelClassName</p>
          <div className="mt-4 flex flex-wrap items-center gap-4">
            <span className={cn(figmaDsButtonLabelClassName, 'rounded-full bg-black px-[24px] py-[11px] text-white')}>
              Start a conversation
            </span>
          </div>
        </div>
      </section>

      <section id="composants" className="scroll-mt-8 border-t border-gray-200 py-8">
        <h2 className="text-lg font-semibold text-gray-900">Atomes, molécules, organismes</h2>
        <p className="mt-1 text-sm text-gray-600">
          Prévisualisation des exports Figma (<span className="font-mono text-xs">components/design-system/extracted</span>
          ).
        </p>
        <div className="mt-6 overflow-x-auto rounded-xl border border-gray-200 bg-neutral-100 shadow-inner">
          <div className="min-w-0">
            <ExtractedDesignDemo />
          </div>
        </div>
      </section>
    </div>
  )
}
