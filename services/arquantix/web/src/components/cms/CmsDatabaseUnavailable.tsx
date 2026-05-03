/** Message serveur quand Prisma ne peut pas joindre PostgreSQL (dev / panne). */
export function CmsDatabaseUnavailable() {
  return (
    <div className="min-h-screen bg-zinc-950 px-6 py-16 text-zinc-100">
      <div className="mx-auto max-w-lg rounded-lg border border-amber-500/30 bg-zinc-900/80 p-8 shadow-lg">
        <h1 className="text-xl font-semibold text-amber-100">Base de données inaccessible</h1>
        <p className="mt-4 text-sm leading-relaxed text-zinc-300">
          Next.js ne parvient pas à joindre PostgreSQL (voir <code className="rounded bg-zinc-800 px-1">DATABASE_URL</code> dans{' '}
          <code className="rounded bg-zinc-800 px-1">services/arquantix/web/.env</code>).
        </p>
      </div>
    </div>
  )
}
