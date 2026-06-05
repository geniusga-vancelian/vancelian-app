import assert from 'node:assert/strict'
import test from 'node:test'

import { lombardCapacityQuerySchema, lombardPrepareSchema } from '@/lib/portal/lombard/lombardValidation'

test('lombardCapacityQuerySchema — accepte portalWalletCollateralBalance absent (null)', () => {
  const parsed = lombardCapacityQuerySchema.parse({
    collateral: 'cbETH',
    walletAddress: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
    targetLtvPercent: '28',
    portalWalletCollateralBalance: null,
  })
  assert.equal(parsed.portalWalletCollateralBalance, undefined)
})

test('lombardCapacityQuerySchema — conserve un solde portail fourni', () => {
  const parsed = lombardCapacityQuerySchema.parse({
    collateral: 'cbBTC',
    walletAddress: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
    targetLtvPercent: 28,
    portalWalletCollateralBalance: '0.01234567',
  })
  assert.equal(parsed.portalWalletCollateralBalance, '0.01234567')
})

test('lombardPrepareSchema — accepte portalWalletCollateralBalance dans le body prepare', () => {
  const parsed = lombardPrepareSchema.parse({
    collateral: 'cbETH',
    borrowAmount: '100',
    walletAddress: '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44',
    targetLtvPercent: 28,
    idempotencyKey: '26e5e348-b250-48d8-9b92-b1d3f9f2a474',
    portalWalletCollateralBalance: '0.01234567',
  })
  assert.equal(parsed.portalWalletCollateralBalance, '0.01234567')
})
