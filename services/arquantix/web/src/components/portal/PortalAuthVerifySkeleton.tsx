import { cn } from '@/lib/utils'

function Shimmer({ className }: { className?: string }) {
  return <div className={cn('portal-shimmer', className)} aria-hidden />
}

/** Placeholder écran verify — même structure que le formulaire OTP (sans shell layout). */
export function PortalAuthVerifySkeleton() {
  return (
    <div
      className="portal-auth__form w-full max-w-[400px]"
      aria-busy="true"
      aria-live="polite"
      aria-label="Loading verification"
    >
      <header className="portal-auth__intro">
        <Shimmer className="mb-3 h-8 w-[min(100%,280px)] rounded-v-input" />
        <Shimmer className="h-4 w-[min(100%,320px)] rounded-v-input" />
      </header>

      <div className="portal-auth__otp-placeholder" aria-hidden>
        {Array.from({ length: 6 }, (_, index) => (
          <span key={index} className="portal-auth__otp-placeholder-cell" />
        ))}
      </div>

      <Shimmer className="mx-auto mt-6 h-4 w-[min(100%,200px)] rounded-v-input" />
    </div>
  )
}
