'use client'

import Link from 'next/link'
import { StrategyChatStudio } from '@/components/finance/StrategyChatStudio'

export default function FinanceStrategyChatPage() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Finance — Strategy Chat</h1>
        <Link
          href="/admin/finance"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Retour Finance
        </Link>
      </div>

      <StrategyChatStudio />
    </div>
  )
}
