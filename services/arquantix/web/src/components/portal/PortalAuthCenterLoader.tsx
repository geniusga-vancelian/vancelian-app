import { Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

type Props = {
  label?: string
  className?: string
}

/** Loader centré pour les écrans auth (verify OTP) — sans shimmer ni faux formulaire. */
export function PortalAuthCenterLoader({
  label = 'Loading',
  className,
}: Props) {
  return (
    <div
      className={cn(
        'flex min-h-[min(360px,50vh)] w-full max-w-[400px] flex-col items-center justify-center',
        className,
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
      aria-label={label}
    >
      <Loader2 className="h-8 w-8 animate-spin text-v-fg-muted" aria-hidden />
      <span className="sr-only">{label}</span>
    </div>
  )
}
