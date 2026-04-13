export interface PortfolioBar {
  date: string
  nav_base100: number
  portfolio_return: number
  drawdown: number
  turnover: number
  costs: number
  weights_json?: Record<string, number>
  tradable_json?: Record<string, boolean>
}

export interface InstrumentBar {
  date: string
  base100: number
  instrument_return?: number
}

export interface InstrumentSeries {
  instrument_id: number
  symbol: string
  series: InstrumentBar[]
}

export interface InstrumentInfo {
  id: number
  symbol: string
  name: string | null
  asset_class: string
  weekend_tradable: boolean
  provider: string
  provider_symbol: string | null
  is_active: boolean
  created_at: string
}

export interface Bundle {
  id: string
  name: string
  description: string | null
  instrument_ids: number[]
  instruments?: InstrumentInfo[]
  created_at: string
  updated_at: string
}

export interface BacktestCreateRequest {
  name?: string
  start_date: string
  end_date: string
  instrument_ids?: number[]
  bundle_id?: string
  initial_weights?: Record<number, number>
  strategy: {
    type: 'equal_weight' | 'momentum' | 'bundle_strategy' | 'CPPI' | 'CORE_SATELLITE'
    params?: {
      lookback_days?: number
      floor_ratio?: number
      multiplier?: number
      risky_cap?: number
      core_min?: number
      core_yield?: number
      day_count?: number
      // Core-Satellite params
      target_te?: number
      te_tolerance?: number
      te_max_hard_mult?: number
      lookback_risk_days?: number
      lookback_return_days?: number
      max_weight_per_asset?: number
      core_grid_step?: number
      top_k_satellite?: number
      sat_min?: number
      shrinkage?: boolean
      turnover_penalty?: number
      stability_penalty?: number
      optimization_method?: 'grid' | 'quadratic'
      allocation_mode?: 'te_target' | 'utility_lambda' | 'dynamic_cushion'
      lambda_risk?: number
      floor_rel_ratio?: number
      floor_accrues_with_core?: boolean
      sat_max?: number
      debug?: boolean
    }
  }
  rebalance: 'daily' | 'weekly' | 'monthly'
  fees_bps: number
  slippage_bps: number
  allow_weekend_trading: boolean
}

export interface BacktestRunResponse {
  run_id: number
  status: 'SUCCESS' | 'FAILED' | 'PENDING'
  metrics?: Record<string, number>
  error_message?: string
  effective_start_date?: string
  effective_end_date?: string
  warnings?: string[]
}

// Compare endpoints types
export interface BacktestRunListItem {
  id: number
  name: string
  status: string
  strategy_type: string
  created_at: string | null
  start_date: string
  end_date: string
  effective_start_date: string | null
  effective_end_date: string | null
  rebalance: string
  universe_label: string | null
  instrument_count: number
}

export interface BacktestListResponse {
  runs: BacktestRunListItem[]
  total: number
  limit: number
  offset: number
}

export interface BacktestCompareRunMeta {
  id: number
  name: string
  strategy_type: string
  strategy_params_json: Record<string, any> | null
  universe_label: string | null
  start_date: string
  end_date: string
  effective_start_date: string | null
  effective_end_date: string | null
  rebalance: string
  instrument_ids_json: number[]
  bundle_id: string | null
}

export interface BacktestCompareSeriesItem {
  date: string
  values: Record<string, number | null>  // run_id (string) -> nav_base100
}

export interface BacktestCompareStats {
  annualized_performance: number
  max_drawdown: number
  sharpe_ratio: number
  calmar_ratio: number | null
}

export interface BacktestCompareResponse {
  runs: Record<string, BacktestCompareRunMeta>  // run_id (string) -> meta
  series: BacktestCompareSeriesItem[]
  stats: Record<string, BacktestCompareStats>  // run_id (string) -> stats
}

export interface BacktestDetailResponse {
  run: {
    id: number
    name: string | null
    created_at: string
    start_date: string
    end_date: string
    effective_start_date: string | null
    effective_end_date: string | null
    rebalance: string
    strategy_type: string
    strategy_params_json: any
    fees_bps: number
    slippage_bps: number
    allow_weekend_trading: boolean
    instrument_ids_json: number[]
    status: string
  }
  portfolio_metrics: Record<string, number>
  instrument_metrics: Array<{
    instrument_id: number
    symbol: string
    metrics: Record<string, number>
  }>
}

export interface SeriesResponse {
  portfolio: PortfolioBar[]
  instruments: InstrumentSeries[]
}

export interface PerformanceResponse {
  start: string
  end: string
  base: number
  instruments: Array<{
    instrument_id: number
    symbol: string
    series: Array<{
      date: string
      value: number
    }>
    stats: {
      total_return: number
      max_drawdown: number
      vol_annual: number
    }
  }>
}

export interface PerformanceDataPoint {
  date: string
  value: number
}

export interface PerformanceStats {
  total_return: number
  max_drawdown: number
  vol_annual: number
}

export interface InstrumentPerformance {
  instrument_id: number
  symbol: string
  series: PerformanceDataPoint[]
  stats: PerformanceStats
}
