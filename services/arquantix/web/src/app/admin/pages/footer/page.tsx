import Link from 'next/link'
import { ChevronLeft } from 'lucide-react'
import { SiteFooterEditor } from '@/components/admin/SiteFooterEditor'

export default function AdminSiteFooterPage() {
  return (
    <div className="mx-auto max-w-5xl space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/admin/pages"
          className="inline-flex items-center gap-1 text-sm font-medium text-indigo-700 hover:text-indigo-900"
        >
          <ChevronLeft className="h-4 w-4" />
          Structure du site
        </Link>
      </div>
      <SiteFooterEditor />
    </div>
  )
}
