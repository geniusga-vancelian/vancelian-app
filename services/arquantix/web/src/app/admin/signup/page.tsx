import Link from 'next/link'

export default function AdminSignupPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md space-y-6 rounded-lg bg-white p-8 shadow-md text-center">
        <h1 className="text-2xl font-bold text-gray-900">Inscription</h1>
        <p className="text-sm text-gray-600">
          La création de compte admin n&apos;est pas encore disponible depuis cette interface.
        </p>
        <Link
          href="/admin/login0"
          className="inline-flex justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50"
        >
          Retour
        </Link>
      </div>
    </div>
  )
}
