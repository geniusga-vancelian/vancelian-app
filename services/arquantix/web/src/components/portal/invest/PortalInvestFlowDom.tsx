'use client'

import type { ReactNode } from 'react'

type Scene = 'form' | 'selector'

type Props = {
  scene: Scene
  /** Form content — includes inner `.inv-pane` (InvestForm / DeFi form). */
  form: ReactNode
  /** Asset selector — includes inner `.inv-pane` (InvestSelector). */
  selector?: ReactNode | null
}

/**
 * Invest flow shell — handoff `.inv-flow` + `.inv-scene` inside `.ofd-invest-panel`.
 * Root class is `inv-flow` (not `.inv`) to avoid collision with the marketing card `.inv` in vancelian-app-components.css.
 */
export function PortalInvestFlowDom({ scene, form, selector = null }: Props) {
  return (
    <div className="inv-flow">
      <div className="inv-scene">
        <div
          className={`inv-pane${scene === 'form' ? '' : ' is-hidden'}`}
          aria-hidden={scene !== 'form'}
        >
          {form}
        </div>
        {selector ? (
          <div
            className={`inv-pane${scene === 'selector' ? '' : ' is-hidden'}`}
            aria-hidden={scene !== 'selector'}
          >
            {selector}
          </div>
        ) : null}
      </div>
    </div>
  )
}

/** Panel card — handoff `.ofd-invest-panel` / Placer `.placer-invest__panel`. */
export function PortalInvestFlowPanel({ children }: { children: ReactNode }) {
  return <div className="ofd-invest-panel">{children}</div>
}
