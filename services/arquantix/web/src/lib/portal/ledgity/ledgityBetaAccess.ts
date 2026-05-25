import { prisma } from '@/lib/prisma'
import {
  getLedgityBetaEmails,
  getLedgityBetaLimitsForClient,
  getLedgityBetaPersonIds,
  getLedgityBetaProfileTag,
  isLedgityBetaAllowAllUsers,
  isLedgityBetaEnabled,
  isLedgityBetaIncludeAdmins,
  isLedgityDepositsDisabled,
  isLedgityVaultsEnabled,
  isLedgityWithdrawsDisabled,
} from '@/lib/portal/ledgity/ledgityConfig'

export class LedgityVaultBetaError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 403) {
    super(message)
    this.name = 'LedgityVaultBetaError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

function readProfileTags(profileJson: unknown): string[] {
  if (!profileJson || typeof profileJson !== 'object') return []
  const row = profileJson as Record<string, unknown>
  const candidates = [row.tags, row.beta_tags, row.ledgity_beta_tags]
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

export type LedgityBetaAccessContext = {
  personId: string
  email: string | null
  profileTags: string[]
  isAdminPerson: boolean
}

export async function loadLedgityBetaAccessContext(personId: string): Promise<LedgityBetaAccessContext> {
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

export async function isLedgityBetaAllowlisted(personId: string): Promise<boolean> {
  if (!isLedgityBetaEnabled()) return true
  if (isLedgityBetaAllowAllUsers()) return true

  const ctx = await loadLedgityBetaAccessContext(personId)
  const personIds = getLedgityBetaPersonIds()
  if (personIds.has(personId.toLowerCase())) return true

  const emails = getLedgityBetaEmails()
  if (ctx.email && emails.has(ctx.email)) return true

  const profileTag = getLedgityBetaProfileTag()
  if (profileTag && ctx.profileTags.includes(profileTag.toLowerCase())) return true

  if (isLedgityBetaIncludeAdmins() && ctx.isAdminPerson) return true

  return false
}

export async function assertLedgityBetaAccess(personId: string): Promise<void> {
  if (!isLedgityBetaEnabled()) return
  if (!(await isLedgityBetaAllowlisted(personId))) {
    throw new LedgityVaultBetaError(
      'ledgity.beta.not_allowlisted',
      'Les vaults Ledgity sont réservés aux utilisateurs beta pour le moment.',
    )
  }
}

export function assertLedgityDepositsEnabled(): void {
  if (isLedgityDepositsDisabled()) {
    throw new LedgityVaultBetaError(
      'ledgity.deposits_disabled',
      'Les dépôts Ledgity sont temporairement suspendus. Les retraits restent possibles.',
      503,
    )
  }
}

export function assertLedgityWithdrawsEnabled(): void {
  if (isLedgityWithdrawsDisabled()) {
    throw new LedgityVaultBetaError(
      'ledgity.withdraws_disabled',
      'Les retraits Ledgity sont temporairement suspendus.',
      503,
    )
  }
}

export type LedgityBetaPortalFlags = {
  enabled: boolean
  allowed: boolean
  depositsDisabled: boolean
  withdrawsDisabled: boolean
  limits: ReturnType<typeof getLedgityBetaLimitsForClient> | null
  message: string | null
}

export async function getLedgityBetaPortalFlags(personId: string | null): Promise<LedgityBetaPortalFlags> {
  const enabled = isLedgityBetaEnabled()
  const depositsDisabled = isLedgityDepositsDisabled()
  const withdrawsDisabled = isLedgityWithdrawsDisabled()

  if (!enabled) {
    return {
      enabled: false,
      allowed: true,
      depositsDisabled,
      withdrawsDisabled,
      limits: isLedgityVaultsEnabled() ? getLedgityBetaLimitsForClient() : null,
      message: depositsDisabled ? 'Les dépôts Ledgity sont temporairement suspendus.' : null,
    }
  }

  const allowed = personId ? await isLedgityBetaAllowlisted(personId) : false
  let message: string | null = null
  if (!allowed) {
    message = isLedgityBetaAllowAllUsers()
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
    limits: allowed ? getLedgityBetaLimitsForClient() : null,
    message,
  }
}
