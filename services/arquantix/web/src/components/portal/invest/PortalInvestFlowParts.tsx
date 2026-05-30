'use client'

import { useEffect, useRef } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  invFmtMoney,
  type PortalInvestSource,
  type PortalInvestTarget,
} from '@/lib/portal/portalInvestFlowFormat'

type InvestChipAsset = {
  short: string
  unit: string
  glyph: string
  bg: string
  color: string
}

export function PortalInvestChip({
  asset,
  popKey,
  onClick,
  selectable = true,
}: {
  asset: InvestChipAsset
  popKey?: number
  onClick?: () => void
  /** When false, chip is read-only (no chevron, no click). */
  selectable?: boolean
}) {
  const ref = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (popKey == null || !ref.current) return
    ref.current.classList.remove('just-changed')
    void ref.current.offsetWidth
    ref.current.classList.add('just-changed')
  }, [popKey])

  if (!selectable) {
    return (
      <span className="inv-chip inv-chip--static">
        <span
          className="inv-chip__ic"
          style={{
            background: asset.bg,
            color: asset.color,
            ...(asset.glyph ? {} : { fontSize: 0 }),
          }}
        >
          {asset.glyph || null}
        </span>
        <span className="inv-chip__lbl">
          {asset.short}
          <small>{asset.unit}</small>
        </span>
      </span>
    )
  }

  return (
    <button ref={ref} type="button" className="inv-chip" onClick={onClick}>
      <span className="inv-chip__ic" style={{ background: asset.bg, color: asset.color }}>
        {asset.glyph}
      </span>
      <span className="inv-chip__lbl">
        {asset.short}
        <small>{asset.unit}</small>
      </span>
      <span className="inv-chip__chev" aria-hidden="true">
        <KalaiIcon name="chevron-down" size={16} />
      </span>
    </button>
  )
}

export function PortalInvestSelector({
  field,
  source,
  target,
  sources,
  targets,
  onPick,
  onClose,
}: {
  field: 'from' | 'to'
  source: PortalInvestSource
  target: PortalInvestTarget
  sources: PortalInvestSource[]
  targets: PortalInvestTarget[]
  onPick: (asset: PortalInvestSource | PortalInvestTarget) => void
  onClose: () => void
}) {
  const currentKey = field === 'from' ? source.key : target.key
  const groups =
    field === 'from'
      ? [{ title: 'My accounts', items: sources }]
      : Object.entries(
          targets.reduce<Record<string, PortalInvestTarget[]>>((acc, item) => {
            ;(acc[item.group] = acc[item.group] || []).push(item)
            return acc
          }, {}),
        ).map(([title, items]) => ({ title, items }))

  return (
    <div className="inv-pane">
      <header className="inv-sel-head">
        <h3 className="inv-sel-head__title">
          {field === 'from' ? 'Choose an account' : 'Choose a placement'}
        </h3>
        <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Close">
          <KalaiIcon name="close" size={16} />
        </button>
      </header>
      {groups.map((group) => (
        <div key={group.title}>
          <div className="inv-sel-section">{group.title}</div>
          <div className="inv-sel-list">
            {group.items.map((asset, i) => (
              <button
                key={asset.key}
                type="button"
                className={`inv-sel-row${asset.key === currentKey ? ' is-on' : ''}`}
                style={{ animationDelay: `${60 + i * 50}ms` }}
                onClick={() => onPick(asset)}
              >
                <span className="inv-chip__ic" style={{ background: asset.bg, color: asset.color }}>
                  {asset.glyph}
                </span>
                <span className="inv-sel-row__info">
                  <span className="inv-sel-row__name">{asset.name}</span>
                  <span className="inv-sel-row__desc">{asset.desc}</span>
                </span>
                <span className="inv-sel-row__bal">
                  {field === 'from' ? (
                    invFmtMoney((asset as PortalInvestSource).balance, asset.glyph)
                  ) : (
                    <>
                      {(asset as PortalInvestTarget).held}
                      <small>{(asset as PortalInvestTarget).heldLabel}</small>
                    </>
                  )}
                </span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
