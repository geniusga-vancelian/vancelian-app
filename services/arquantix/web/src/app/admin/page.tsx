'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'

interface User {
  id: string
  email: string
  role: string
  createdAt: string
}

export default function AdminDashboardPage() {
  const router = useRouter()

  useEffect(() => {
    // Check if user is authenticated
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          // Not authenticated, redirect to login
          router.push('/admin/login')
        }
        // If authenticated, stay on this page (dashboard)
      })
      .catch(() => {
        // Error checking auth, redirect to login
        router.push('/admin/login')
      })
  }, [router])

  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Dashboard</h1>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Welcome to Arquantix CMS</h2>
        <p className="text-gray-600 mb-4">
          Manage your site content, pages, and sections from here.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <a
          href="/admin/pages"
          className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition-shadow"
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Pages</h3>
          <p className="text-gray-600 text-sm">
            Manage pages and sections of your site
          </p>
        </a>

        <div className="bg-white rounded-lg shadow p-6 opacity-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Media</h3>
          <p className="text-gray-600 text-sm">Coming soon...</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6 opacity-50">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Settings</h3>
          <p className="text-gray-600 text-sm">Coming soon...</p>
        </div>
      </div>
    </div>
  )
}
