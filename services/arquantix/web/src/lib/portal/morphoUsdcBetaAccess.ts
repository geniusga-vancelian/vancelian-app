import { prisma } from '@/lib/prisma'
import {
  getMorphoUsdcBetaEmails,
  getMorphoUsdcBetaPersonIds,
  getMorphoUsdcBetaProfileTag,
  isMorphoUsdcBetaAllowAllUsers,
  isMorphoUsdcBetaEnabled,
  isMorphoUsdcBetaIncludeAdmins,
  isMorphoUsdcDepositsDisabled,
  isMorphoUsdcWithdrawsDisabled,
  getMorphoUsdcBetaLimitsForClient,
} from '@/lib/portal/morphoUsdcBetaConfig'

export class MorphoVaultBetaError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 403) {
    super(message)
    this.name = 'MorphoVaultBetaError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

function readProfileTags(profileJson: unknown): string[] {
  if (!profileJson || typeof profileJson !== 'object') return []
  const row = profileJson as Record<string, unknown>
  const candidates = [row.tags, row.beta_tags, row.morpho_beta_tags]
  const tags: string[] = []
  for (const value of candidates) {
    if (Array.isArray(value)) {
      for (const item of value) {
        if (typeof item === 'string' && item.trim()) tags.push(item.trim().toLowerCase())
      }
    } else if (typeof value === 'string' && value.trim()) {
      tags.push(value.trim().toLowerCase())
    }
  }
  return tags
}

function readEmailFromProfile(profileJson: unknown): string | null {
  if (!profileJson || typeof profileJson !== 'object') return null
  const row = profileJson as Record<string, unknown>
  const collected = row.collected
  if (collected && typeof collected === 'object') {
    const c = collected as Record<string, unknown>
    for (const key of ['email', 'contact_email', 'primary_email']) {
      const value = c[key]
      if (typeof value === 'string' && value.includes('@')) return value.trim().toLowerCase()
    }
  }
  const direct = row.email
  if (typeof direct === 'string' && direct.includes('@')) return direct.trim().toLowerCase()
  return null
}

export type MorphoBetaAccessContext = {
  personId: string
  email: string | null
  profileTags: string[]
  isAdminPerson: boolean
}

export async function loadMorphoBetaAccessContext(personId: string): Promise<MorphoBetaAccessContext> {
  const person = await prisma.persons.findUnique({
    where: { id: personId },
    select: {
      profileJson: true,
      adminUser: { select: { id: true } },
      peClients: { select: { email: true } },
    },
  })

  const email =
    person?.peClients?.email?.trim().toLowerCase() ??
    readEmailFromProfile(person?.profileJson) ??
    null

  return {
    personId,
    email,
    profileTags: readProfileTags(person?.profileJson),
    isAdminPerson: Boolean(person?.adminUser),
  }
}

export async function isMorphoUsdcBetaAllowlisted(personId: string): Promise<boolean> {
  if (!isMorphoUsdcBetaEnabled()) return true
  if (isMorphoUsdcBetaAllowAllUsers()) return true

  const ctx = await loadMorphoBetaAccessContext(personId)
  const personIds = getMorphoUsdcBetaPersonIds()
  if (personIds.has(personId.toLowerCase())) return true

  const emails = getMorphoUsdcBetaEmails()
  if (ctx.email && emails.has(ctx.email)) return true

  const profileTag = getMorphoUsdcBetaProfileTag()
  if (profileTag && ctx.profileTags.includes(profileTag.toLowerCase())) return true

  if (isMorphoUsdcBetaIncludeAdmins() && ctx.isAdminPerson) return true

  return false
}

export async function assertMorphoUsdcBetaAccess(personId: string): Promise<void> {
  if (!(await isMorphoUsdcBetaAllowlisted(personId))) {
    throw new MorphoVaultBetaError(
      'morpho.beta.not_allowlisted',
      'Le vault Morpho USDC est réservé aux utilisateurs beta pour le moment.',
    )
  }
}

export function assertMorphoUsdcDepositsEnabled(): void {
  if (isMorphoUsdcDepositsDisabled()) {
    throw new MorphoVaultBetaError(
      'morpho.deposits_disabled',
      'Les dépôts Morpho USDC sont temporairement suspendus. Les retraits restent possibles.',
      503,
    )
  }
}

export function assertMorphoUsdcWithdrawsEnabled(): void {
  if (isMorphoUsdcWithdrawsDisabled()) {
    throw new MorphoVaultBetaError(
      'morpho.withdraws_disabled',
      'Les retraits Morpho USDC sont temporairement suspendus.',
      503,
    )
  }
}

export type MorphoBetaPortalFlags = {
  enabled: boolean
  allowed: boolean
  depositsDisabled: boolean
  withdrawsDisabled: boolean
  limits: ReturnType<typeof getMorphoUsdcBetaLimitsForClient> | null
  message: string | null
}

export async function getMorphoBetaPortalFlags(personId: string | null): Promise<MorphoBetaPortalFlags> {
  const enabled = isMorphoUsdcBetaEnabled()
  const depositsDisabled = isMorphoUsdcDepositsDisabled()
  const withdrawsDisabled = isMorphoUsdcWithdrawsDisabled()

  if (!enabled) {
    return {
      enabled: false,
      allowed: true,
      depositsDisabled,
      withdrawsDisabled,
      limits: null,
      message: depositsDisabled
        ? 'Les dépôts Morpho USDC sont temporairement suspendus.'
        : null,
    }
  }

  const allowed = personId ? await isMorphoUsdcBetaAllowlisted(personId) : false
  let message: string | null = null
  if (!allowed) {
    message = isMorphoUsdcBetaAllowAllUsers()
      ? null
      : 'Ce produit est en beta privée. Contactez le support pour y accéder.'
  } else if (depositsDisabled) {
    message = 'Les dépôts sont suspendus. Vous pouvez retirer vos fonds.'
  }

  return {
    enabled,
    allowed,
    depositsDisabled,
    withdrawsDisabled,
    limits: allowed ? getMorphoUsdcBetaLimitsForClient() : null,
    message,
  }
}
