'use client'

import { ReactNode } from 'react'
import dynamic from 'next/dynamic'
import { usePathname } from 'next/navigation'
import { AdminEditingLocaleProvider } from '@/components/admin/AdminEditingLocaleContext'

const AdminSidebar = dynamic(
  () => import('@/components/admin/AdminSidebar').then(m => m.AdminSidebar),
  { ssr: false },
)

export default function AdminLayout({
  children,
}: {
  children: ReactNode
}) {
  const pathname = usePathname() ?? ''
  const isPublicAdminShell =
    pathname === '/admin/login' ||
    pathname === '/admin/login0' ||
    pathname === '/admin/signup'

  /// La preview du DS Flutter doit être rendue **sans** sidebar admin et **sans**
  /// le wrapper `AdminEditingLocaleProvider` : elle est consommée dans une iframe
  /// qui ne doit afficher que le device frame + le composant à prévisualiser.
  const isFlutterPreviewIframe = pathname.startsWith('/admin/flutter/preview')

  if (isPublicAdminShell || isFlutterPreviewIframe) {
    return <>{children}</>
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <AdminSidebar />
      <main className="flex-1 ml-64">
        <AdminEditingLocaleProvider>
          <div className="p-8">{children}</div>
        </AdminEditingLocaleProvider>
      </main>
    </div>
  )
}
