import { notFound } from 'next/navigation'

import { isMorphoSandboxDevRouteAvailable } from '@/lib/portal/morphoLocalSandboxDev'

import { MorphoSandboxDevPanel } from './MorphoSandboxDevPanel'

export default function MorphoSandboxDevPage() {
  if (!isMorphoSandboxDevRouteAvailable()) {
    notFound()
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <MorphoSandboxDevPanel />
    </main>
  )
}
