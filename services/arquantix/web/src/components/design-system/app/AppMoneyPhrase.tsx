import { cn } from '@/lib/utils'

type Props = {
  prefix?: string
  amount: string
  suffix?: string
  positive?: boolean
  className?: string
}

/** Phrase éditoriale revenu — pattern Webapp4 money-phrase. */
export function AppMoneyPhrase({
  prefix = "You're earning today",
  amount,
  suffix = 'in income.',
  positive = true,
  className,
}: Props) {
  return (
    <p className={cn('money-phrase', className)}>
      {prefix}{' '}
      <span className={cn('money-phrase__amount', !positive && 'text-v-error')}>{amount}</span>{' '}
      {suffix}
    </p>
  )
}
