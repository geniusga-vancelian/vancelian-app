'use client'

import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { BarChart3, Package, TrendingUp } from 'lucide-react'
import MarketDataTab from './MarketDataTab'
import BundlesTab from './BundlesTab'
import { BacktestsTab } from '@/components/finance/BacktestsTab'

export default function MarketBacktestPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Market & Backtest</h1>
        <p className="text-gray-600">
          Gérer les données de marché, les bundles et les backtests
        </p>
      </div>

      <Tabs defaultValue="market-data" className="w-full">
        <TabsList className="mb-6">
          <TabsTrigger value="market-data" className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4" />
            <span>Market Data</span>
          </TabsTrigger>
          <TabsTrigger value="bundles" className="flex items-center gap-2">
            <Package className="w-4 h-4" />
            <span>Bundles</span>
          </TabsTrigger>
          <TabsTrigger value="backtests" className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            <span>Backtests</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="market-data" className="mt-6">
          <MarketDataTab />
        </TabsContent>

        <TabsContent value="bundles" className="mt-6">
          <BundlesTab />
        </TabsContent>

        <TabsContent value="backtests" className="mt-6">
          <BacktestsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

