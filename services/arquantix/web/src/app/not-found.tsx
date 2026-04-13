import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center">
      <h2 className="text-2xl font-bold text-gray-900 mb-4">Not Found</h2>
      <p className="text-gray-600 mb-6">Could not find requested resource</p>
      <Link
        href="/"
        className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
      >
        Return Home
      </Link>
    </div>
  )
}









