'use client'

import {
  ArticleStepsModule,
  type ArticleStepsItemData,
} from '@/components/design-system/ArticleStepsModule'

export type SwapStepState = 'pending' | 'processing' | 'completed'

export type SwapTransactionStep = {
  number: number
  title: string
  primary?: string
  secondary?: string
  approximate?: boolean
  state: SwapStepState
}

type Props = {
  title?: string
  steps: SwapTransactionStep[]
}

function mapSwapStepsToDsItems(steps: SwapTransactionStep[]): ArticleStepsItemData[] {
  return steps.map((step) => ({
    title: step.title,
    date: step.primary,
    description: step.secondary
      ? `${step.approximate ? '≈ ' : ''}${step.secondary}`
      : undefined,
    isCompleted: step.state === 'completed',
  }))
}

export function PortalSwapTransactionSteps({ title = 'Détail de votre conversion', steps }: Props) {
  const items = mapSwapStepsToDsItems(steps)
  const suppressActiveStep = steps.every((step) => step.state === 'pending')

  return (
    <article className="overflow-hidden card-simple overflow-hidden !w-full">
      <div className="border-b border-v-border px-4 py-3">
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">{title}</h2>
      </div>
      <div className="px-4 py-5">
        <ArticleStepsModule
          embedded
          suppressActiveStep={suppressActiveStep}
          activeLabel="EN COURS"
          content={{ items }}
        />
      </div>
    </article>
  )
}
