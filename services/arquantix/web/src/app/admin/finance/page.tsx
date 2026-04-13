'use client'

import { useState } from 'react'
import Link from 'next/link'
import { MarketDataTab } from '@/components/finance/MarketDataTab'
import { BundlesTab } from '@/components/finance/BundlesTab'
import { BacktestsTab } from '@/components/finance/BacktestsTab'

export default function FinancePage() {
  const [activeTab, setActiveTab] = useState<'market-data' | 'bundles' | 'backtests' | 'strategy-chat'>('market-data')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-gray-900">Finance</h1>
        <Link
          href="/admin"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Dashboard
        </Link>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('market-data')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'market-data'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Market Data
          </button>
          <button
            onClick={() => setActiveTab('bundles')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'bundles'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Bundles
          </button>
          <button
            onClick={() => setActiveTab('backtests')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'backtests'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Backtests
          </button>
          <button
            onClick={() => setActiveTab('strategy-chat')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'strategy-chat'
                ? 'border-indigo-500 text-indigo-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Strategy Chat
          </button>
        </nav>
      </div>

      {/* Content */}
      {activeTab === 'market-data' && <MarketDataTab />}
      {activeTab === 'bundles' && <BundlesTab />}
      {activeTab === 'backtests' && <BacktestsTab />}
      {activeTab === 'strategy-chat' && (
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">Strategy Chat Builder</h2>
              <p className="text-sm text-gray-600">Accéder au parcours de chat stratégique.</p>
            </div>
            <Link
              href="/admin/finance/strategy-chat"
              className="px-4 py-2 text-sm text-white bg-indigo-600 rounded hover:bg-indigo-700"
            >
              Ouvrir
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}

