'use client'

import { ReactNode } from 'react'
import Link from 'next/link'
import { useRouter, usePathname } from 'next/navigation'
import { LogOut, Layout, Image, Settings } from 'lucide-react'

export default function AdminLayout({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()

  const handleLogout = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const response = await fetch('/api/admin/logout', {
        method: 'POST',
      })
      if (response.ok) {
        router.push('/admin/login')
        router.refresh()
      }
    } catch (error) {
      console.error('Logout error:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-gray-900 text-white">
        <div className="flex flex-col h-full">
          {/* Logo/Header */}
          <div className="p-6 border-b border-gray-800">
            <h1 className="text-xl font-bold">Arquantix CMS</h1>
          </div>

          {/* Navigation */}
          <nav className="flex-1 p-4 space-y-2">
            <Link
              href="/admin"
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                pathname === '/admin'
                  ? 'bg-gray-800'
                  : 'hover:bg-gray-800'
              }`}
            >
              <Layout className="w-5 h-5" />
              <span>Dashboard</span>
            </Link>
            <Link
              href="/admin/pages"
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                pathname === '/admin/pages'
                  ? 'bg-gray-800'
                  : 'hover:bg-gray-800'
              }`}
            >
              <Layout className="w-5 h-5" />
              <span>Pages</span>
            </Link>
            <Link
              href="/admin/media"
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                pathname === '/admin/media'
                  ? 'bg-gray-800'
                  : 'hover:bg-gray-800'
              }`}
            >
              <Image className="w-5 h-5" />
              <span>Media</span>
            </Link>
            <Link
              href="/admin/settings"
              className={`flex items-center space-x-3 px-4 py-3 rounded-lg transition-colors ${
                pathname === '/admin/settings'
                  ? 'bg-gray-800'
                  : 'hover:bg-gray-800'
              }`}
            >
              <Settings className="w-5 h-5" />
              <span>Settings</span>
            </Link>
          </nav>

          {/* Logout */}
          <div className="p-4 border-t border-gray-800">
            <button
              onClick={handleLogout}
              className="w-full flex items-center space-x-3 px-4 py-3 rounded-lg hover:bg-gray-800 transition-colors text-red-400"
            >
              <LogOut className="w-5 h-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <main className="p-8">{children}</main>
      </div>
    </div>
  )
}
