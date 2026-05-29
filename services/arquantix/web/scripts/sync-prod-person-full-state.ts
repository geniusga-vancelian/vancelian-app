/**
 * Réconciliation prod complète pour un compte :
 * - Morpho + Ledgity vault positions (on-chain → user_vault_positions)
 * - Nettoyage entrées Lombard market IDs dans user_vault_positions
 * - Lombard Borrow on-chain (cbBTC / cbETH)
 * - Direct PE Mon Trading = wallet Base on-chain − bundle_cash − collateral Lombard locké
 *
 * Usage :
 *   PERSON_ID=... CLIENT_ID=... APPLY=1 npx tsx scripts/sync-prod-person-full-state.ts
 */
import { erc20Abi, getAddress, type Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { fetchLedgityVaultPosition } from '@/lib/portal/ledgity/ledgityVaultAdapter'
import { listPublishedPortalLedgityVaultConfigs } from '@/lib/portal/ledgity/ledgityVaultConfigStore'
import { fetchLombardActivePositionsForWallet } from '@/lib/portal/lombard/lombardPositionService'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { fetchMorphoVaultPosition } from '@/lib/portal/morphoGraphql'
import { MORPHO_CHAIN_ID, normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { listPublishedPortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import { loadPrincipalNetRaw, syncUserVaultPositionFromLedger } from '@/lib/portal/morphoVaultLedger'
import { prisma } from '@/lib/prisma'

const BASE_CHAIN_ID = 8453
const APPLY = process.env.APPLY === '1'
const PERSON_ID = process.env.PERSON_ID?.trim() || '8b0e0044-f1ef-47a5-99d4-370598a77492'
const CLIENT_ID = process.env.CLIENT_ID?.trim() || '080358a8-4519-4acf-b5da-25485446c967'

const LOMBARD_MARKET_IDS = VANCELIAN_LOMBARD_V1.markets.map((m) => m.marketId.toLowerCase())

const BASE_TOKENS: Record<string, { address: Address; decimals: number }> = {
  USDC: { address: getAddress('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'), decimals: 6 },
  CBETH: { address: getAddress('0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22'), decimals: 18 },
  CBBTC: { address: getAddress('0xcbB7c0000aB88B473b1f5aFd9ef808440eed33Bf'), decimals: 8 },
  UNI: { address: getAddress('0xc3de830ea07524a0761646a6a4e4be0e114a3c83'), decimals: 18 },
  AAVE: { address: getAddress('0x63706e401c06ac8513145b7687a14804d17f814b'), decimals: 18 },
}

const MAINNET_ONLY_SYMBOLS = new Set(['ETH', 'USDT'])
const MON_TRADING_SYMBOLS = new Set(['USDC', 'CBETH', 'CBBTC', 'UNI', 'AAVE'])

function rawToHuman(raw: bigint, decimals: number): number {
  return Number(raw) / 10 ** decimals
}

function parseHuman(value: string | undefined): number {
  const n = Number(String(value ?? '').replace(',', '.'))
  return Number.isFinite(n) ? n : 0
}

async function readOnChainBalances(wallet: Address): Promise<Record<string, number>> {
  const client = createBasePublicClient({ side: 'server' })
  const out: Record<string, number> = {}
  for (const [asset, meta] of Object.entries(BASE_TOKENS)) {
    const raw = await client.readContract({
      address: meta.address,
      abi: erc20Abi,
      functionName: 'balanceOf',
      args: [wallet],
    })
    out[asset] = rawToHuman(raw, meta.decimals)
  }
  return out
}

async function sumBundleCash(symbol: string): Promise<number> {
  const rows = await prisma.$queryRawUnsafe<Array<{ s: number | null }>>(
    `SELECT COALESCE(SUM(pa.quantity), 0)::float AS s
     FROM pe_position_atoms pa
     JOIN pe_portfolios p ON p.id = pa.portfolio_id
     JOIN pe_instruments i ON i.id = pa.instrument_id
     JOIN pe_assets a ON a.id = i.asset_id
     WHERE p.client_id = $1::uuid
       AND p.portfolio_type = 'bundle_portfolio'
       AND pa.position_type = 'cash_leg'
       AND pa.status = 'open'
       AND a.symbol = $2`,
    CLIENT_ID,
    symbol,
  )
  return Number(rows[0]?.s ?? 0)
}

async function getDirectPortfolioId(): Promise<string> {
  const rows = await prisma.$queryRawUnsafe<Array<{ id: string }>>(
    `SELECT id::text FROM pe_portfolios WHERE client_id = $1::uuid AND portfolio_type = 'direct_portfolio' LIMIT 1`,
    CLIENT_ID,
  )
  if (!rows[0]?.id) throw new Error('direct_portfolio_not_found')
  return rows[0].id
}

async function resolveInstrumentId(symbol: string): Promise<string> {
  const rows = await prisma.$queryRawUnsafe<Array<{ id: string }>>(
    `SELECT i.id::text FROM pe_instruments i
     JOIN pe_assets a ON a.id = i.asset_id
     WHERE a.symbol = $1 LIMIT 1`,
    symbol,
  )
  if (!rows[0]?.id) throw new Error(`instrument_not_found:${symbol}`)
  return rows[0].id
}

async function upsertDirectAtom(args: {
  portfolioId: string
  instrumentId: string
  quantity: number
}): Promise<void> {
  const qty = Math.max(0, args.quantity)
  await prisma.$executeRawUnsafe(
    `INSERT INTO pe_position_atoms (
       id, portfolio_id, instrument_id, position_type, status,
       quantity, available_quantity, cost_basis, average_entry_price, created_at, updated_at
     )
     SELECT gen_random_uuid(), $1::uuid, $2::uuid, 'spot', 'open',
            $3::numeric, $3::numeric, 0, 0, now(), now()
     WHERE NOT EXISTS (
       SELECT 1 FROM pe_position_atoms
       WHERE portfolio_id = $1::uuid AND instrument_id = $2::uuid
         AND position_type = 'spot' AND status = 'open'
     )`,
    args.portfolioId,
    args.instrumentId,
    qty,
  )
  await prisma.$executeRawUnsafe(
    `UPDATE pe_position_atoms
     SET quantity = $3::numeric, available_quantity = $3::numeric, updated_at = now()
     WHERE portfolio_id = $1::uuid AND instrument_id = $2::uuid
       AND position_type = 'spot' AND status = 'open'`,
    args.portfolioId,
    args.instrumentId,
    qty,
  )
}

async function syncMorphoLedgityVaults(wallets: Address[]): Promise<Record<string, unknown>> {
  const morphoConfigs = await listPublishedPortalMorphoVaultConfigs()
  const ledgityConfigs = await listPublishedPortalLedgityVaultConfigs()
  const vaultSync: Array<Record<string, unknown>> = []

  for (const wallet of wallets) {
    for (const config of morphoConfigs) {
      const vaultAddress = normalizeVaultAddress(config.vaultAddress)
      const row = await fetchMorphoVaultPosition({
        vaultAddress,
        walletAddress: wallet,
        chainId: config.chainId ?? MORPHO_CHAIN_ID,
      })
      if (!row) continue
      const principalNetRaw = await loadPrincipalNetRaw({
        personId: PERSON_ID,
        vaultAddress,
        chainId: config.chainId ?? MORPHO_CHAIN_ID,
        walletAddress: wallet,
      })
      if (APPLY) {
        await syncUserVaultPositionFromLedger({
          personId: PERSON_ID,
          vaultAddress,
          chainId: config.chainId ?? MORPHO_CHAIN_ID,
          walletAddress: wallet,
          assetSymbol: row.asset.symbol,
          assetDecimals: row.asset.decimals,
          lastAssetsRaw: row.assets,
          lastSharesRaw: row.shares,
          costBasisUnknown: principalNetRaw == null,
        })
      }
      vaultSync.push({
        provider: 'morpho',
        vault: vaultAddress,
        wallet,
        assetsRaw: row.assets,
        sharesRaw: row.shares,
      })
    }

    for (const config of ledgityConfigs) {
      const vaultAddress = normalizeVaultAddress(config.vaultAddress)
      const row = await fetchLedgityVaultPosition({
        vaultAddress,
        walletAddress: wallet,
        chainId: config.chainId ?? BASE_CHAIN_ID,
      })
      if (!row) continue
      const principalNetRaw = await loadPrincipalNetRaw({
        personId: PERSON_ID,
        vaultAddress,
        chainId: config.chainId ?? BASE_CHAIN_ID,
        walletAddress: wallet,
      })
      if (APPLY) {
        await syncUserVaultPositionFromLedger({
          personId: PERSON_ID,
          vaultAddress,
          chainId: config.chainId ?? BASE_CHAIN_ID,
          walletAddress: wallet,
          assetSymbol: row.asset.symbol,
          assetDecimals: row.asset.decimals,
          lastAssetsRaw: row.assets,
          lastSharesRaw: row.shares,
          costBasisUnknown: principalNetRaw == null,
        })
      }
      vaultSync.push({
        provider: 'ledgity',
        vault: vaultAddress,
        wallet,
        assetsRaw: row.assets,
        sharesRaw: row.shares,
      })
    }
  }

  return { vaultSync }
}

async function main(): Promise<void> {
  const report: Record<string, unknown> = {
    apply: APPLY,
    personId: PERSON_ID,
    clientId: CLIENT_ID,
    steps: [] as Array<Record<string, unknown>>,
  }

  const wallets = await prisma.personCryptoWallet.findMany({
    where: { personId: PERSON_ID, revokedAt: null, chainType: 'ethereum' },
    select: { address: true, chainId: true, isPrimary: true },
    orderBy: [{ isPrimary: 'desc' }, { createdAt: 'asc' }],
  })
  const walletAddresses = wallets.map((w) => getAddress(w.address))

  // Step A — supprimer faux vaults Lombard market IDs
  const lombardRows = await prisma.userVaultPosition.findMany({
    where: { personId: PERSON_ID, vaultAddress: { in: LOMBARD_MARKET_IDS } },
    select: { id: true, vaultAddress: true, lastAssetsRaw: true },
  })
  if (APPLY && lombardRows.length > 0) {
    await prisma.userVaultPosition.deleteMany({
      where: { personId: PERSON_ID, vaultAddress: { in: LOMBARD_MARKET_IDS } },
    })
  }
  ;(report.steps as Array<Record<string, unknown>>).push({
    step: 'cleanup_lombard_market_vault_rows',
    deleted: lombardRows.length,
    rows: lombardRows,
  })

  // Step B — Morpho + Ledgity on-chain sync
  const vaultResult = await syncMorphoLedgityVaults(walletAddresses)
  ;(report.steps as Array<Record<string, unknown>>).push({
    step: 'sync_morpho_ledgity_vaults',
    ...vaultResult,
  })

  // Step C — Lombard Borrow on-chain
  const lombardByWallet: Record<string, unknown[]> = {}
  const lombardLocked: Record<string, number> = { CBBTC: 0, CBETH: 0 }
  let borrowedUsdcTotal = 0

  for (const wallet of walletAddresses) {
    const positions = await fetchLombardActivePositionsForWallet(wallet)
    lombardByWallet[wallet] = positions
    for (const row of positions) {
      borrowedUsdcTotal += parseHuman(row.borrowAmount)
      const sym = row.collateralSymbol.toUpperCase()
      if (sym === 'CBBTC' || sym === 'CBETH') {
        lombardLocked[sym] = (lombardLocked[sym] ?? 0) + parseHuman(row.collateralAmount)
      }
    }
  }
  ;(report.steps as Array<Record<string, unknown>>).push({
    step: 'lombard_onchain',
    lombardByWallet,
    lombardLocked,
    borrowedUsdcTotal,
  })

  // Step D — on-chain Base wallet + direct PE
  const onChainByWallet: Record<string, Record<string, number>> = {}
  const onChainTotal: Record<string, number> = {}
  for (const wallet of walletAddresses) {
    const balances = await readOnChainBalances(wallet)
    onChainByWallet[wallet] = balances
    for (const [asset, qty] of Object.entries(balances)) {
      onChainTotal[asset] = (onChainTotal[asset] ?? 0) + qty
    }
  }

  const directPortfolioId = await getDirectPortfolioId()
  const peChanges: Array<Record<string, unknown>> = []

  for (const symbol of MAINNET_ONLY_SYMBOLS) {
    const instrumentId = await resolveInstrumentId(symbol).catch(() => null)
    if (!instrumentId) continue
    peChanges.push({ symbol, action: 'zero_mainnet_only', target: 0 })
    if (APPLY) {
      await upsertDirectAtom({ portfolioId: directPortfolioId, instrumentId, quantity: 0 })
    }
  }

  for (const symbol of MON_TRADING_SYMBOLS) {
    const instrumentId = await resolveInstrumentId(symbol)
    const onChain = onChainTotal[symbol] ?? 0
    const bundleCash = await sumBundleCash(symbol)
    let locked = 0
    if (symbol === 'CBBTC' || symbol === 'CBETH') {
      locked = lombardLocked[symbol] ?? 0
    }
    const target = Math.max(0, onChain - bundleCash - locked)
    peChanges.push({
      symbol,
      onChainTotal: onChain,
      bundleCash,
      lombardLocked: locked,
      target,
    })
    if (APPLY) {
      await upsertDirectAtom({
        portfolioId: directPortfolioId,
        instrumentId,
        quantity: target,
      })
    }
  }

  let finalDirect: unknown = null
  if (APPLY) {
    finalDirect = await prisma.$queryRawUnsafe(
      `SELECT a.symbol, pa.quantity::text AS quantity
       FROM pe_position_atoms pa
       JOIN pe_instruments i ON i.id = pa.instrument_id
       JOIN pe_assets a ON a.id = i.asset_id
       WHERE pa.portfolio_id = $1::uuid AND pa.status = 'open' AND pa.quantity <> 0
       ORDER BY a.symbol`,
      directPortfolioId,
    )
    const finalVaults = await prisma.userVaultPosition.findMany({
      where: { personId: PERSON_ID, chainId: BASE_CHAIN_ID },
      select: {
        vaultAddress: true,
        assetSymbol: true,
        lastAssetsRaw: true,
        walletAddress: true,
      },
    })
    report.finalVaults = finalVaults
  }

  report.onChainByWallet = onChainByWallet
  report.onChainTotal = onChainTotal
  report.peChanges = peChanges
  report.finalDirect = finalDirect

  process.stdout.write(`SYNC_PERSON_RESULT ${JSON.stringify(report)}\n`)
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
