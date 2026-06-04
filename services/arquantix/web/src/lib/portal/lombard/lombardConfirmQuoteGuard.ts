import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import type { LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'

/** Dérive relative max sur la garantie (basis points) avant blocage. */
export const LOMBARD_CONFIRM_GUARANTEE_DRIFT_BPS = 100

/** Hausse max de LTV projetée vs snapshot (points de pourcentage). */
export const LOMBARD_CONFIRM_LTV_DRIFT_PP = 0.5

export type LombardConfirmQuoteGuardMode = 'review_confirm' | 'processing_retry'

export type LombardConfirmQuoteAssessment =
  | { ok: true; materialChange: boolean }
  | { ok: false; code: string; message: string }

function assessLombardFreshQuoteHardBlocks(fresh: LombardQuoteResult): LombardConfirmQuoteAssessment | null {
  const maxUserLtvPercent = VANCELIAN_LOMBARD_V1.maxUserLtv * 100

  if (fresh.safetyLevel === 'blocked') {
    return {
      ok: false,
      code: 'safety_blocked',
      message:
        'Cet emprunt n’est plus disponible avec ces paramètres. Modifiez le montant ou le niveau de risque.',
    }
  }

  if (fresh.projectedLtvPercent > maxUserLtvPercent + 1e-9) {
    return {
      ok: false,
      code: 'ltv_cap',
      message: 'Le montant dépasse la limite de sécurité (70 %). Réduisez l’emprunt ou ajustez le curseur.',
    }
  }

  return null
}

function relativeDriftBps(previous: bigint, fresh: bigint): number {
  if (previous <= 0n) return fresh <= 0n ? 0 : 10_000
  const diff = fresh >= previous ? fresh - previous : previous - fresh
  return Number((diff * 10_000n) / previous)
}

export function assessLombardConfirmQuote(args: {
  snapshot: LombardQuoteResult | null
  fresh: LombardQuoteResult
  mode?: LombardConfirmQuoteGuardMode
}): LombardConfirmQuoteAssessment {
  const { fresh, mode = 'review_confirm' } = args
  const snapshot = args.snapshot

  const hardBlock = assessLombardFreshQuoteHardBlocks(fresh)
  if (hardBlock && !hardBlock.ok) return hardBlock

  if (mode === 'processing_retry' || snapshot == null) {
    return { ok: true, materialChange: true }
  }

  if (snapshot.marketId !== fresh.marketId) {
    return {
      ok: false,
      code: 'market_changed',
      message: 'Le marché a changé. Revenez au formulaire et relancez le devis.',
    }
  }

  if (snapshot.borrowAmountRaw !== fresh.borrowAmountRaw) {
    return {
      ok: false,
      code: 'borrow_changed',
      message: 'Le montant emprunté ne correspond plus. Revenez au formulaire et vérifiez votre saisie.',
    }
  }

  const snapshotGuarantee = BigInt(snapshot.guaranteeAmountRaw)
  const freshGuarantee = BigInt(fresh.guaranteeAmountRaw)
  const guaranteeDriftBps = relativeDriftBps(snapshotGuarantee, freshGuarantee)

  if (guaranteeDriftBps > LOMBARD_CONFIRM_GUARANTEE_DRIFT_BPS && freshGuarantee > snapshotGuarantee) {
    return {
      ok: false,
      code: 'guarantee_increased',
      message: `Le marché a évolué : la garantie requise est passée de ${snapshot.guaranteeAmount} à ${fresh.guaranteeAmount} ${fresh.collateral}. Vérifiez le récapitulatif ci-dessous, puis confirmez à nouveau.`,
    }
  }

  const ltvDelta = fresh.projectedLtvPercent - snapshot.projectedLtvPercent
  if (ltvDelta > LOMBARD_CONFIRM_LTV_DRIFT_PP) {
    return {
      ok: false,
      code: 'ltv_increased',
      message: `Le niveau de risque a augmenté (${formatLtv(snapshot.projectedLtvPercent)} → ${formatLtv(fresh.projectedLtvPercent)} LTV projeté). Vérifiez le récapitulatif, puis confirmez à nouveau.`,
    }
  }

  const materialChange =
    guaranteeDriftBps > 0 ||
    Math.abs(ltvDelta) > 0.05 ||
    snapshot.safetyLevel !== fresh.safetyLevel ||
    snapshot.guaranteeAmount !== fresh.guaranteeAmount

  return { ok: true, materialChange }
}

function formatLtv(value: number): string {
  return `${value.toFixed(1).replace('.', ',')} %`
}
