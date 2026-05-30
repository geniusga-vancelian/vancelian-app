'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import {
  formatSwapCryptoAmount,
  swapAssetChipMeta,
  type SwapFromOption,
  type SwapToOption,
} from '@/lib/portal/swapFlowFormat'

type Props = {
  field: 'from' | 'to'
  fromAsset: string
  toAsset: string
  fromOptions: SwapFromOption[]
  toOptions: SwapToOption[]
  onPickFrom: (option: SwapFromOption) => void
  onPickTo: (option: SwapToOption) => void
  onClose: () => void
}

export function PortalSwapAssetSelector({
  field,
  fromAsset,
  toAsset,
  fromOptions,
  toOptions,
  onPickFrom,
  onPickTo,
  onClose,
}: Props) {
  const isFrom = field === 'from'
  const currentAsset = isFrom ? fromAsset : toAsset

  return (
    <div className="inv-pane">
      <header className="inv-sel-head">
        <h3 className="inv-sel-head__title">
          {isFrom ? 'Choose source asset' : 'Choose destination asset'}
        </h3>
        <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Close">
          <KalaiIcon name="close" size={16} />
        </button>
      </header>

      <div className="inv-sel-section">{isFrom ? 'Wallet assets' : 'Available assets'}</div>
      <div className="inv-sel-list">
        {isFrom
          ? fromOptions.map((opt, i) => {
              const chip = swapAssetChipMeta(opt.asset, opt.name)
              return (
                <button
                  key={`${opt.asset}-${opt.chain}`}
                  type="button"
                  className={`inv-sel-row${opt.asset.toUpperCase() === currentAsset.toUpperCase() ? ' is-on' : ''}`}
                  style={{ animationDelay: `${60 + i * 50}ms` }}
                  onClick={() => onPickFrom(opt)}
                >
                  <span className="inv-chip__ic" style={{ background: chip.bg, color: chip.color }}>
                    {chip.glyph}
                  </span>
                  <span className="inv-sel-row__info">
                    <span className="inv-sel-row__name">{opt.name}</span>
                    <span className="inv-sel-row__desc">{chip.desc}</span>
                  </span>
                  <span className="inv-sel-row__bal">
                    {formatSwapCryptoAmount(opt.balance)} {opt.asset}
                  </span>
                </button>
              )
            })
          : toOptions.map((opt, i) => {
              const chip = swapAssetChipMeta(opt.asset, opt.name)
              return (
                <button
                  key={opt.asset}
                  type="button"
                  className={`inv-sel-row${opt.asset.toUpperCase() === currentAsset.toUpperCase() ? ' is-on' : ''}`}
                  style={{ animationDelay: `${60 + i * 50}ms` }}
                  onClick={() => onPickTo(opt)}
                >
                  <span className="inv-chip__ic" style={{ background: chip.bg, color: chip.color }}>
                    {chip.glyph}
                  </span>
                  <span className="inv-sel-row__info">
                    <span className="inv-sel-row__name">{opt.name}</span>
                    <span className="inv-sel-row__desc">{chip.desc}</span>
                  </span>
                  <span className="inv-sel-row__bal">{opt.asset}</span>
                </button>
              )
            })}
      </div>
    </div>
  )
}
