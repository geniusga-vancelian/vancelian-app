'use client'

import { Loader2 } from 'lucide-react'

import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

type StepKey = 'preparing' | 'approving' | 'signing' | 'submitting' | 'bridging'

type Step = {
  key: StepKey
  label: string
}

const STEPS: Step[] = [
  { key: 'preparing', label: 'Preparing route' },
  { key: 'approving', label: 'Token approval' },
  { key: 'signing', label: 'Sign swap' },
  { key: 'submitting', label: 'Submit transaction' },
  { key: 'bridging', label: 'Confirm on-chain' },
]

const ORDER: StepKey[] = ['preparing', 'approving', 'signing', 'submitting', 'bridging']

function stepIndex(phase: SwapExecutionPhase): number {
  if (phase === 'idle' || phase === 'failed' || phase === 'completed') return -1
  return ORDER.indexOf(phase as StepKey)
}

type Props = {
  phase: SwapExecutionPhase
}

/** Invest-style execution progress — summary rows instead of vertical timeline. */
export function PortalSwapExecutionProgress({ phase }: Props) {
  if (phase === 'idle' || phase === 'completed') return null

  const activeIndex = stepIndex(phase)

  return (
    <div className="inv-summary inv-summary--progress">
      {STEPS.map((step, index) => {
        const completed = activeIndex > index
        const active = activeIndex === index
        return (
          <div
            key={step.key}
            className={`inv-summary__row${active ? ' inv-summary__row--active' : ''}`}
          >
            <span className="k">{step.label}</span>
            <span className={`v${completed ? ' v--accent' : ''}`}>
              {completed ? (
                'Done'
              ) : active ? (
                <span className="inline-flex items-center gap-1.5">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />
                  In progress
                </span>
              ) : (
                'Pending'
              )}
            </span>
          </div>
        )
      })}
    </div>
  )
}
