'use client'

export default function MarketDataTab() {
  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Market Data</h2>
        <p className="text-gray-600">
          Les donnees de marche sont alimentees en temps reel via Binance (WebSocket + REST).
          Consultez l&apos;onglet <strong>Markets</strong> de l&apos;application pour voir les prix live.
        </p>
        <p className="text-sm text-gray-500 mt-4">
          Instruments actifs : BTCUSDT, ETHUSDT, SOLUSDT, XRPUSDT, BNBUSDT, ADAUSDT,
          DOGEUSDT, USDCUSDT, AVAXUSDT, LINKUSDT, DOTUSDT, EURUSDT
        </p>
      </div>
    </div>
  )
}
