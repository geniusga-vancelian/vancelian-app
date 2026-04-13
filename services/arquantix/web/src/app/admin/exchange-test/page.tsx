'use client'

import { useState, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import {
  ArrowRightLeft,
  Check,
  Loader2,
  RefreshCw,
  Wallet,
  AlertTriangle,
  Radio,
  CircleDot,
} from 'lucide-react'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ClientInfo {
  id: string
  email: string
  eur_balance: string | null
  iban_masked: string | null
  crypto_positions: Record<string, string>
}

interface AssetInfo {
  symbol: string
  precision: number
  fee_bps: number
  spread_bps: number
  bid_price: number | null
  ask_price: number | null
  mid_price: number | null
  bid_price_eur: number | null
  ask_price_eur: number | null
  mid_price_eur: number | null
  quote_time: string | null
  is_fresh: boolean
}

interface OrderResult {
  status: string
  order_id?: string
  asset?: string
  from_asset?: string
  to_asset?: string
  amount_from?: string
  amount_to?: string
  amount_crypto?: string
  volume_raw?: string
  fee_amount?: string
  fee_asset?: string
  fee_bps?: number
  price?: string
  price_eur?: string
  gross_eur?: string
  fee_eur?: string
  net_eur?: string
  currency?: string
  client_eur_balance_after?: string
  crypto_position_after?: string
  error?: string
  detail?: string
  reason?: string
}

type Side = 'buy' | 'sell'
type PriceMode = 'market' | 'manual'

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ExchangeTestPage() {
  const [clients, setClients] = useState<ClientInfo[]>([])
  const [assets, setAssets] = useState<AssetInfo[]>([])
  const [loading, setLoading] = useState(true)

  const [side, setSide] = useState<Side>('buy')
  const [priceMode, setPriceMode] = useState<PriceMode>('market')
  const [selectedClientId, setSelectedClientId] = useState('')
  const [selectedAsset, setSelectedAsset] = useState('BTC')
  const [amount, setAmount] = useState('')
  const [priceOverride, setPriceOverride] = useState('')

  const [executing, setExecuting] = useState(false)
  const [result, setResult] = useState<OrderResult | null>(null)

  const loadContext = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/exchange/context')
      if (!res.ok) throw new Error('Failed to load context')
      const data = await res.json()
      setClients(data.clients || [])
      setAssets(data.supported_assets || [])
      if (data.clients?.length > 0 && !selectedClientId) {
        setSelectedClientId(data.clients[0].id)
      }
    } catch {
      toastError('Impossible de charger le contexte exchange')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadContext() }, [loadContext])

  // Auto-refresh prices every 5s
  useEffect(() => {
    if (priceMode !== 'market') return
    const interval = setInterval(loadContext, 5000)
    return () => clearInterval(interval)
  }, [priceMode, loadContext])

  const selectedClient = clients.find(c => c.id === selectedClientId)
  const maxEur = selectedClient?.eur_balance ? parseFloat(selectedClient.eur_balance) : 0
  const maxCrypto = selectedClient?.crypto_positions?.[selectedAsset]
    ? parseFloat(selectedClient.crypto_positions[selectedAsset])
    : 0
  const assetInfo = assets.find(a => a.symbol === selectedAsset)
  const feeBps = assetInfo?.fee_bps ?? 0
  const precision = assetInfo?.precision ?? 8

  const isFresh = assetInfo?.is_fresh ?? false
  const effectivePrice = priceMode === 'market'
    ? (side === 'buy' ? assetInfo?.ask_price_eur : assetInfo?.bid_price_eur) ?? null
    : (priceOverride && parseFloat(priceOverride) > 0 ? parseFloat(priceOverride) : null)

  // ---------------------------------------------------------------------------
  // Preview
  // ---------------------------------------------------------------------------

  const buyPreview = (() => {
    if (side !== 'buy' || !effectivePrice) return null
    const amt = parseFloat(amount)
    if (!amt || amt <= 0) return null
    const volumeRaw = Math.floor((amt / effectivePrice) * Math.pow(10, precision)) / Math.pow(10, precision)
    const feeCrypto = Math.floor((volumeRaw * feeBps / 10000) * Math.pow(10, precision)) / Math.pow(10, precision)
    const clientReceives = volumeRaw - feeCrypto
    return { volumeRaw, feeCrypto, clientReceives, price: effectivePrice, feeBps }
  })()

  const sellPreview = (() => {
    if (side !== 'sell' || !effectivePrice) return null
    const cryptoAmt = parseFloat(amount)
    if (!cryptoAmt || cryptoAmt <= 0) return null
    const grossEur = Math.floor(cryptoAmt * effectivePrice * 100) / 100
    const feeEur = Math.floor((grossEur * feeBps / 10000) * 100) / 100
    const netEur = grossEur - feeEur
    return { grossEur, feeEur, netEur, price: effectivePrice, feeBps }
  })()

  // ---------------------------------------------------------------------------
  // Max
  // ---------------------------------------------------------------------------

  const handleMax = () => {
    if (side === 'buy' && maxEur > 0) setAmount(maxEur.toString())
    if (side === 'sell' && maxCrypto > 0) setAmount(maxCrypto.toString())
  }

  const currentMax = side === 'buy' ? maxEur : maxCrypto
  const amountVal = parseFloat(amount) || 0
  const overMax = amountVal > currentMax && currentMax > 0

  const canExecute = (() => {
    if (executing || !amount || amountVal <= 0 || overMax) return false
    if (priceMode === 'manual') return !!priceOverride && parseFloat(priceOverride) > 0
    return isFresh
  })()

  // ---------------------------------------------------------------------------
  // Execute
  // ---------------------------------------------------------------------------

  const handleExecute = async () => {
    if (!selectedClientId || !canExecute) return

    setExecuting(true)
    setResult(null)
    try {
      const ref = `test-${side}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

      if (side === 'buy') {
        const body: Record<string, unknown> = {
          client_id: selectedClientId,
          asset: selectedAsset,
          fiat_amount: amountVal,
          currency: 'EUR',
          external_reference: ref,
        }
        if (priceMode === 'manual' && priceOverride && parseFloat(priceOverride) > 0) {
          body.price = parseFloat(priceOverride)
        }
        const res = await fetch('/api/exchange/buy', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        const data = await res.json()
        if (!res.ok) {
          setResult({ status: 'failed', error: data.detail || data.error || `HTTP ${res.status}` })
          toastError(data.detail || data.error || 'Achat echoue')
        } else {
          setResult(data)
          if (data.status === 'completed') {
            toastSuccess(`Achat ${selectedAsset} reussi !`)
            loadContext()
          } else if (data.status === 'failed') {
            toastError(data.error || 'Achat echoue')
          }
        }
      } else {
        const body: Record<string, unknown> = {
          client_id: selectedClientId,
          asset: selectedAsset,
          amount_crypto: amountVal,
          currency: 'EUR',
          external_reference: ref,
        }
        if (priceMode === 'manual' && priceOverride && parseFloat(priceOverride) > 0) {
          body.price = parseFloat(priceOverride)
        }
        const res = await fetch('/api/exchange/sell', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        const data = await res.json()
        if (!res.ok) {
          setResult({ status: 'failed', error: data.detail || data.error || `HTTP ${res.status}` })
          toastError(data.detail || data.error || 'Vente echouee')
        } else {
          setResult(data)
          if (data.status === 'completed') {
            toastSuccess(`Vente ${selectedAsset} reussie !`)
            loadContext()
          } else if (data.status === 'failed') {
            toastError(data.error || 'Vente echouee')
          }
        }
      }
    } catch {
      toastError('Erreur reseau')
    } finally {
      setExecuting(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (loading && clients.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Exchange Test</h1>
          <p className="text-sm text-gray-500">
            {side === 'buy' ? 'EUR → Crypto buy flow' : 'Crypto → EUR sell flow'}
            {' — '}
            {priceMode === 'market' ? 'Market Simulated' : 'Manual Override'}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={loadContext}>
          <RefreshCw className="h-4 w-4 mr-1" /> Refresh
        </Button>
      </div>

      {/* Side toggle */}
      <div className="flex gap-2">
        <Button
          variant={side === 'buy' ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setSide('buy'); setAmount(''); setResult(null) }}
        >
          Buy (EUR → Crypto)
        </Button>
        <Button
          variant={side === 'sell' ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setSide('sell'); setAmount(''); setResult(null) }}
        >
          Sell (Crypto → EUR)
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ---- Left: Order Form ---- */}
        <div className="space-y-4">
          {/* Client */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <Wallet className="h-4 w-4" /> Client
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <select
                className="w-full border rounded-md px-3 py-2 text-sm bg-white"
                value={selectedClientId}
                onChange={e => setSelectedClientId(e.target.value)}
              >
                {clients.map(c => (
                  <option key={c.id} value={c.id}>{c.email}</option>
                ))}
              </select>
              {selectedClient && (
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <span className="text-gray-500">Balance EUR</span>
                    <p className="font-semibold text-lg">{selectedClient.eur_balance ?? '—'} €</p>
                  </div>
                  <div>
                    <span className="text-gray-500">IBAN</span>
                    <p className="font-mono text-xs">{selectedClient.iban_masked ?? '—'}</p>
                  </div>
                  {Object.entries(selectedClient.crypto_positions).length > 0 && (
                    <div className="col-span-2">
                      <span className="text-gray-500">Positions crypto</span>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {Object.entries(selectedClient.crypto_positions).map(([a, bal]) => (
                          <span key={a} className={`text-xs font-mono px-2 py-1 rounded ${side === 'sell' && a === selectedAsset ? 'bg-blue-100 ring-1 ring-blue-300' : 'bg-gray-100'}`}>
                            {a}: {bal}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Order */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <ArrowRightLeft className="h-4 w-4" /> Ordre — {side === 'buy' ? 'Achat' : 'Vente'}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Price mode toggle */}
              <div>
                <label className="text-sm text-gray-500 mb-2 block">Mode de prix</label>
                <div className="flex gap-2">
                  <button
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border transition-colors ${
                      priceMode === 'market'
                        ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                    onClick={() => setPriceMode('market')}
                  >
                    <Radio className="h-3.5 w-3.5" />
                    Market Simulated
                  </button>
                  <button
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm border transition-colors ${
                      priceMode === 'manual'
                        ? 'bg-amber-50 border-amber-300 text-amber-700'
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
                    }`}
                    onClick={() => setPriceMode('manual')}
                  >
                    <CircleDot className="h-3.5 w-3.5" />
                    Manual Override
                  </button>
                </div>
              </div>

              <div>
                <label className="text-sm text-gray-500 mb-1 block">Instrument crypto</label>
                <select
                  className="w-full border rounded-md px-3 py-2 text-sm bg-white"
                  value={selectedAsset}
                  onChange={e => { setSelectedAsset(e.target.value); setAmount('') }}
                >
                  {assets.map(a => (
                    <option key={a.symbol} value={a.symbol}>{a.symbol}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-sm text-gray-500 mb-1 block">
                  {side === 'buy' ? 'Montant EUR' : `Montant ${selectedAsset}`}
                </label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    step={side === 'buy' ? '0.01' : String(Math.pow(10, -precision))}
                    min="0"
                    value={amount}
                    onChange={e => setAmount(e.target.value)}
                    placeholder={side === 'buy' ? '0.00' : `0.${'0'.repeat(Math.min(precision, 8))}`}
                  />
                  <Button variant="outline" size="sm" onClick={handleMax} className="shrink-0">
                    Max
                  </Button>
                </div>
                {overMax && (
                  <p className="text-xs text-red-500 mt-1 flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3" /> Depasse le solde disponible
                  </p>
                )}
              </div>

              {priceMode === 'manual' && (
                <div>
                  <label className="text-sm text-gray-500 mb-1 block">
                    Prix unitaire EUR (override)
                  </label>
                  <Input
                    type="number"
                    step="0.01"
                    min="0"
                    value={priceOverride}
                    onChange={e => setPriceOverride(e.target.value)}
                    placeholder="Ex: 85000 pour BTC"
                  />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Live market quote panel (market mode only) */}
          {priceMode === 'market' && assetInfo && (
            <Card className={isFresh ? 'border-green-200 bg-green-50/30' : 'border-red-200 bg-red-50/30'}>
              <CardContent className="pt-4 space-y-1.5 text-sm">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-medium text-gray-700">Prix live {selectedAsset}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    isFresh ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                  }`}>
                    {isFresh ? 'FRESH' : 'STALE'}
                  </span>
                </div>
                {assetInfo.bid_price_eur != null && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Bid (SELL)</span>
                    <span className="font-mono">{assetInfo.bid_price_eur.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} EUR</span>
                  </div>
                )}
                {assetInfo.mid_price_eur != null && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Mid</span>
                    <span className="font-mono text-gray-400">{assetInfo.mid_price_eur.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} EUR</span>
                  </div>
                )}
                {assetInfo.ask_price_eur != null && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">Ask (BUY)</span>
                    <span className="font-mono">{assetInfo.ask_price_eur.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} EUR</span>
                  </div>
                )}
                <div className="flex justify-between text-xs text-gray-400 pt-1 border-t">
                  <span>Spread: {assetInfo.spread_bps} bps ({((assetInfo.spread_bps || 50) / 100).toFixed(2)}%)</span>
                  <span>Fee: {assetInfo.fee_bps} bps</span>
                </div>
                {assetInfo.quote_time && (
                  <div className="text-xs text-gray-400">
                    Derniere quote : {new Date(assetInfo.quote_time).toLocaleTimeString('fr-FR')}
                  </div>
                )}
                {!isFresh && (
                  <p className="text-xs text-red-600 flex items-center gap-1 pt-1">
                    <AlertTriangle className="h-3 w-3" />
                    Quote perimee — execution bloquee
                  </p>
                )}
              </CardContent>
            </Card>
          )}

          {/* BUY Preview */}
          {buyPreview && (
            <Card className="border-blue-200 bg-blue-50/50">
              <CardContent className="pt-4 space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Prix {side === 'buy' ? 'ask' : 'bid'} utilise</span>
                  <span className="font-mono">{buyPreview.price.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} EUR</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Volume brut</span>
                  <span className="font-mono">{buyPreview.volumeRaw} {selectedAsset}</span>
                </div>
                {buyPreview.feeBps > 0 && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Fee ({buyPreview.feeBps} bps)</span>
                      <span className="font-mono text-amber-600">-{buyPreview.feeCrypto} {selectedAsset}</span>
                    </div>
                    <div className="flex justify-between font-medium">
                      <span className="text-gray-700">Client recoit</span>
                      <span className="font-mono text-green-700">{buyPreview.clientReceives} {selectedAsset}</span>
                    </div>
                  </>
                )}
                {buyPreview.feeBps === 0 && (
                  <div className="flex justify-between text-gray-400 text-xs">
                    <span>Fee</span><span>Aucune (0 bps)</span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* SELL Preview */}
          {sellPreview && (
            <Card className="border-orange-200 bg-orange-50/50">
              <CardContent className="pt-4 space-y-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Prix bid utilise</span>
                  <span className="font-mono">{sellPreview.price.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} EUR</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Gross EUR</span>
                  <span className="font-mono">{sellPreview.grossEur.toFixed(2)} €</span>
                </div>
                {sellPreview.feeBps > 0 && (
                  <div className="flex justify-between">
                    <span className="text-gray-600">Fee ({sellPreview.feeBps} bps)</span>
                    <span className="font-mono text-amber-600">-{sellPreview.feeEur.toFixed(2)} €</span>
                  </div>
                )}
                <div className="flex justify-between font-medium">
                  <span className="text-gray-700">Client recoit</span>
                  <span className="font-mono text-green-700">{sellPreview.netEur.toFixed(2)} €</span>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Execute */}
          <Button
            className="w-full"
            size="lg"
            onClick={handleExecute}
            disabled={!canExecute}
          >
            {executing ? (
              <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Execution…</>
            ) : side === 'buy' ? (
              <>Buy {selectedAsset} {priceMode === 'market' ? '(Market)' : '(Override)'}</>
            ) : (
              <>Sell {selectedAsset} {priceMode === 'market' ? '(Market)' : '(Override)'}</>
            )}
          </Button>
        </div>

        {/* ---- Right: Result ---- */}
        <div>
          {result ? (
            <Card className={
              result.status === 'completed' ? 'border-green-300 bg-green-50/50' :
              result.status === 'failed' ? 'border-red-300 bg-red-50/50' :
              'border-yellow-300 bg-yellow-50/50'
            }>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  {result.status === 'completed' ? (
                    <Check className="h-5 w-5 text-green-600" />
                  ) : (
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                  )}
                  Resultat — {result.status}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  {result.order_id && (
                    <Row label="Order ID" value={result.order_id} mono />
                  )}
                  {result.from_asset && result.to_asset && (
                    <Row label="Paire" value={`${result.from_asset} → ${result.to_asset}`} />
                  )}

                  {/* BUY-specific fields */}
                  {result.amount_from && side === 'buy' && (
                    <Row label="EUR debite" value={`${parseFloat(result.amount_from).toLocaleString()} €`} />
                  )}
                  {result.volume_raw && (
                    <Row label="Volume brut" value={`${result.volume_raw} ${result.to_asset || result.asset}`} mono />
                  )}

                  {/* SELL-specific fields */}
                  {result.amount_crypto && side === 'sell' && (
                    <Row label="Crypto vendu" value={`${result.amount_crypto} ${result.from_asset || result.asset}`} mono />
                  )}
                  {result.gross_eur && (
                    <Row label="Gross EUR" value={`${parseFloat(result.gross_eur).toLocaleString()} €`} />
                  )}
                  {result.fee_eur && parseFloat(result.fee_eur) > 0 && (
                    <Row label={`Fee (${result.fee_bps ?? 0} bps)`} value={`-${result.fee_eur} €`} mono />
                  )}
                  {result.net_eur && (
                    <Row label="Client recoit" value={`${parseFloat(result.net_eur).toLocaleString()} €`} />
                  )}

                  {/* BUY fee (crypto) */}
                  {result.fee_amount && parseFloat(result.fee_amount) > 0 && side === 'buy' && (
                    <Row label={`Fee (${result.fee_bps ?? 0} bps)`} value={`-${result.fee_amount} ${result.fee_asset || result.asset}`} mono />
                  )}
                  {result.amount_to && side === 'buy' && (
                    <Row label="Client recoit" value={`${result.amount_to} ${result.to_asset || result.asset}`} mono />
                  )}

                  {/* Common */}
                  {(result.price || result.price_eur) && (
                    <Row label="Prix execute" value={`${parseFloat(result.price_eur || result.price || '0').toLocaleString()} EUR`} />
                  )}
                  {result.client_eur_balance_after && (
                    <Row label="Balance EUR apres" value={`${parseFloat(result.client_eur_balance_after).toLocaleString()} €`} />
                  )}
                  {result.crypto_position_after != null && (
                    <Row label="Position crypto apres" value={`${result.crypto_position_after} ${result.from_asset === 'EUR' ? result.to_asset : result.from_asset || result.asset}`} mono />
                  )}
                  {result.error && (
                    <Row label="Erreur" value={result.error} error />
                  )}
                  {result.detail && !result.error && (
                    <Row label="Detail" value={result.detail} error />
                  )}
                  {result.reason && (
                    <Row label="Raison" value={result.reason} />
                  )}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-dashed">
              <CardContent className="flex items-center justify-center h-48 text-gray-400 text-sm">
                {side === 'buy'
                  ? "Le resultat de l'achat s'affichera ici"
                  : "Le resultat de la vente s'affichera ici"}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

function Row({ label, value, mono, error }: { label: string; value: string; mono?: boolean; error?: boolean }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-gray-100 last:border-0">
      <span className="text-gray-500">{label}</span>
      <span className={`${mono ? 'font-mono text-xs' : ''} ${error ? 'text-red-600 font-medium' : ''}`}>
        {value}
      </span>
    </div>
  )
}
