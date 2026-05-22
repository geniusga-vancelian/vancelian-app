import { cn } from '@/lib/utils'

function Shimmer({ className }: { className?: string }) {
  return <div className={cn('portal-shimmer', className)} aria-hidden />
}

/** Placeholder formulaire login — affiché pendant le streaming CMS / boot Privy. */
export function PortalAuthLoginSkeleton() {
  return (
    <div
      className="portal-auth__form w-full max-w-[400px]"
      aria-busy="true"
      aria-live="polite"
      aria-label="Loading sign in"
    >
      <header className="portal-auth__intro mb-8">
        <Shimmer className="mb-3 h-8 w-[min(100%,280px)] rounded-v-input" />
        <Shimmer className="h-4 w-[min(100%,320px)] rounded-v-input" />
        <Shimmer className="mt-2 h-4 w-[min(100%,240px)] rounded-v-input" />
      </header>
      <Shimmer className="mb-6 h-14 w-full rounded-v-input" />
      <Shimmer className="h-12 w-full rounded-v-pill" />
      <div className="mt-8 flex justify-center gap-3">
        <Shimmer className="h-10 w-10 rounded-full" />
        <Shimmer className="h-10 w-10 rounded-full" />
        <Shimmer className="h-10 w-10 rounded-full" />
      </div>
      <Shimmer className="mx-auto mt-8 h-4 w-[min(100%,260px)] rounded-v-input" />
    </div>
  )
}
