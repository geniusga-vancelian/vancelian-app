import { cn } from '@/lib/utils'

type Props = {
  direction: 'in' | 'out'
  className?: string
}

/** Avatar flux entrant/sortant — preview/17 (dépôt / retrait). */
export function AppTxFlowAvatar({ direction, className }: Props) {
  const icon = direction === 'in' ? 'arrow-down' : 'arrow-up'
  return (
    <span className={cn('avt avt--52 avt--warm shrink-0', className)}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img className="avt__ic" src={`/icons/kalai/${icon}.svg`} alt="" />
    </span>
  )
}
