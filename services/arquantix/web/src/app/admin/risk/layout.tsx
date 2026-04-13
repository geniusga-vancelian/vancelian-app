import Link from 'next/link'

export default function AdminRiskLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <div className="border-b border-gray-200 bg-white px-6 py-4 flex flex-wrap items-center gap-4">
        <h1 className="text-xl font-semibold">Risque dynamique (PR F.5)</h1>
        <nav className="flex gap-3 text-sm">
          <Link className="text-blue-600 hover:underline" href="/admin/risk/rules">
            Règles
          </Link>
          <Link className="text-blue-600 hover:underline" href="/admin/risk/logs">
            Logs
          </Link>
          <Link className="text-gray-500 hover:underline" href="/admin/security/risk-dashboard">
            Dashboard risque
          </Link>
        </nav>
      </div>
      <div className="p-6 max-w-7xl mx-auto">{children}</div>
    </div>
  )
}
