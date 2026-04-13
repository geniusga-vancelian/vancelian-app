'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

export default function DashboardPage() {
  const router = useRouter()

  useEffect(() => {
    // Redirect /dashboard to /admin using client-side navigation
    router.replace('/admin')
  }, [router])

  // Show loading state while redirecting
  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-gray-500">Redirecting...</div>
    </div>
  )
}
