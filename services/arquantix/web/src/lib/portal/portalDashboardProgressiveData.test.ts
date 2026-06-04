import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import type { PortalDashboardPayload } from '@/lib/portal/dashboardTypes'
import {
  hasDashboardCriticalDisplayData,
  hasDashboardPortfolioDisplayData,
  shouldShowDashboardAccountsPending,
  shouldShowDashboardBalancePending,
  shouldShowDashboardFullSkeleton,
} from '@/lib/portal/portalDashboardProgressiveData'

const CORE_ONLY = {
  globalStatistics: { total_balance_eur: 1000 },
} as PortalDashboardPayload

const WITH_PORTFOLIO = {
  ...CORE_ONLY,
  crypto: { summary: { positions_count: 1 } },
} as PortalDashboardPayload

describe('portalDashboardProgressiveData — O2', () => {
  it('skeleton plein écran seulement sans données critiques', () => {
    assert.equal(shouldShowDashboardFullSkeleton(true, null), true)
    assert.equal(shouldShowDashboardFullSkeleton(true, CORE_ONLY), false)
    assert.equal(shouldShowDashboardFullSkeleton(false, null), false)
  })

  it('hasDashboardCriticalDisplayData détecte globalStatistics', () => {
    assert.equal(hasDashboardCriticalDisplayData(CORE_ONLY), true)
    assert.equal(hasDashboardCriticalDisplayData(null), false)
  })

  it('balance pending stale-first avec globalStatistics', () => {
    assert.equal(
      shouldShowDashboardBalancePending({
        portfolioLoading: true,
        refreshing: false,
        data: CORE_ONLY,
      }),
      true,
    )
    assert.equal(
      shouldShowDashboardBalancePending({
        portfolioLoading: true,
        refreshing: false,
        data: WITH_PORTFOLIO,
      }),
      false,
    )
    assert.equal(
      shouldShowDashboardBalancePending({
        portfolioLoading: false,
        refreshing: true,
        data: CORE_ONLY,
      }),
      false,
    )
  })

  it('accounts pending seulement sans portfolio affichable', () => {
    assert.equal(
      shouldShowDashboardAccountsPending({
        portfolioLoading: true,
        refreshing: false,
        data: CORE_ONLY,
      }),
      true,
    )
    assert.equal(
      shouldShowDashboardAccountsPending({
        portfolioLoading: true,
        refreshing: false,
        data: WITH_PORTFOLIO,
      }),
      false,
    )
    assert.equal(hasDashboardPortfolioDisplayData(WITH_PORTFOLIO), true)
  })
})
