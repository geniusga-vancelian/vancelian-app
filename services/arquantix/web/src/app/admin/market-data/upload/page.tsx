'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { Save, ArrowLeft } from 'lucide-react'

export default function MarketDataUploadPage() {
  const router = useRouter()
  
  // Form state for creating instrument
  const [formData, setFormData] = useState({
    symbol: '',
    name: '',
    asset_class: 'crypto',
    weekend_tradable: false,
    provider: 'binance',
    provider_symbol: '',
    is_active: true,
  })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    // Check if user is authenticated
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          router.push('/admin/login')
        }
      })
      .catch(() => {
        router.push('/admin/login')
      })
  }, [router])

  const handleSaveInstrument = async () => {
    if (!formData.symbol.trim()) {
      toastError('Le symbole est obligatoire')
      return
    }

    if (!formData.asset_class) {
      toastError('La catégorie est obligatoire')
      return
    }

    setSaving(true)
    try {
      const response = await fetch('/api/market-data/instruments', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          symbol: formData.symbol.trim().toUpperCase(),
          name: formData.name.trim() || null,
          asset_class: formData.asset_class,
          weekend_tradable: formData.weekend_tradable,
          provider: formData.provider,
          provider_symbol: formData.provider_symbol.trim() || null,
          is_active: formData.is_active,
        }),
      })

      const responseText = await response.text()
      let responseData: any = null

      try {
        responseData = responseText ? JSON.parse(responseText) : null
      } catch {
        responseData = { error: responseText || 'Failed to parse response' }
      }

      if (!response.ok) {
        const errorMsg = responseData.error || responseData.detail || responseData.message || `Save failed (${response.status})`
        toastError(`Échec de l'enregistrement: ${errorMsg}`)
        return
      }

      toastSuccess('Instrument créé avec succès')
      
      // Reset form
      setFormData({
        symbol: '',
        name: '',
        asset_class: 'crypto',
        weekend_tradable: false,
        provider: 'binance',
        provider_symbol: '',
        is_active: true,
      })
    } catch (error: any) {
      console.error('[Market Data] Save error:', error)
      toastError(`Erreur lors de l'enregistrement: ${error.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-4">
          <Button
            onClick={() => router.push('/admin/market-data')}
            variant="ghost"
            size="sm"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            Retour
          </Button>
          <h1 className="text-3xl font-bold text-gray-900">Upload Market Data</h1>
        </div>
      </div>

      {/* Create Instrument Form */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Créer un Instrument</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Symbol */}
            <div>
              <Label htmlFor="symbol">Symbole *</Label>
              <Input
                id="symbol"
                value={formData.symbol}
                onChange={(e) => setFormData({ ...formData, symbol: e.target.value.toUpperCase() })}
                placeholder="Ex: BTC, ETH, QQQ"
                className="mt-1"
              />
            </div>

            {/* Asset Name */}
            <div>
              <Label htmlFor="name">Nom de l'actif</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Ex: Bitcoin, Ethereum"
                className="mt-1"
              />
            </div>

            {/* Asset Class / Category */}
            <div>
              <Label htmlFor="asset_class">Catégorie *</Label>
              <Select
                value={formData.asset_class}
                onValueChange={(value) => setFormData({ ...formData, asset_class: value })}
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="crypto">Crypto</SelectItem>
                  <SelectItem value="etf">ETF</SelectItem>
                  <SelectItem value="equity">Equity</SelectItem>
                  <SelectItem value="forex">Forex</SelectItem>
                  <SelectItem value="index">Index</SelectItem>
                  <SelectItem value="commodities">Commodities</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Provider Symbol */}
            <div>
              <Label htmlFor="provider_symbol">Symbole Provider</Label>
              <Input
                id="provider_symbol"
                value={formData.provider_symbol}
                onChange={(e) => setFormData({ ...formData, provider_symbol: e.target.value })}
                placeholder="Ex: BTCUSDT, ETHUSDT (vide = même que symbole)"
                className="mt-1"
              />
            </div>

            {/* Weekend Tradable */}
            <div className="flex items-center space-x-2 pt-8">
              <input
                type="checkbox"
                id="weekend_tradable"
                checked={formData.weekend_tradable}
                onChange={(e) => setFormData({ ...formData, weekend_tradable: e.target.checked })}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <Label htmlFor="weekend_tradable" className="cursor-pointer">
                Trading le weekend autorisé
              </Label>
            </div>

            {/* Is Active */}
            <div className="flex items-center space-x-2 pt-8">
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
              />
              <Label htmlFor="is_active" className="cursor-pointer">
                Instrument actif
              </Label>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t">
            <Button
              onClick={handleSaveInstrument}
              disabled={saving || !formData.symbol.trim() || !formData.asset_class}
              className="w-full md:w-auto"
            >
              <Save className="w-4 h-4 mr-2" />
              {saving ? 'Enregistrement...' : 'Enregistrer'}
            </Button>
          </div>
        </CardContent>
      </Card>

    </div>
  )
}


