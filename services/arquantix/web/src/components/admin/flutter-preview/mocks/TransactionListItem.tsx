import { ArrowDownLeft, ArrowUpRight, RefreshCw } from 'lucide-react'

import { colors, spacing, typo, typoStyle } from '@/lib/admin/flutter-preview/tokens'

type Tx = {
  kind: 'in' | 'out' | 'swap'
  merchant: string
  category: string
  date: string
  amount: string
  amountColor?: string
}

const TXS: Tx[] = [
  { kind: 'in', merchant: 'Top up bancaire', category: 'Dépôt', date: 'Aujourd’hui', amount: '+€500.00', amountColor: 'positive' },
  { kind: 'out', merchant: 'Stripe', category: 'Achat', date: 'Hier', amount: '-€89.20' },
  { kind: 'swap', merchant: 'BTC → EUR', category: 'Swap', date: '12 mai', amount: '€420.10' },
  { kind: 'in', merchant: 'Vault yield', category: 'Intérêts', date: '10 mai', amount: '+€12.40', amountColor: 'positive' },
  { kind: 'out', merchant: 'Withdraw', category: 'Retrait', date: '8 mai', amount: '-€1,200.00' },
]

/// Mock d'une liste de transactions (10 dernières). Utilisé sur Compte Euro
/// et All Transactions. Chaque ligne : icône colorée + identité + date + montant.
export function MockTransactionList({ count = 10 }: { count?: number }) {
  const rows = Array.from({ length: count }, (_, i) => TXS[i % TXS.length])
  return (
    <div
      style={{
        margin: `${spacing.s2}px ${spacing.lg}px`,
        backgroundColor: colors.cardBackground,
        borderRadius: 16,
        padding: spacing.s4,
        boxShadow: '0 1px 2px rgba(15, 23, 42, 0.05)',
      }}
    >
      <div
        style={{
          ...typoStyle(typo.sectionTitle),
          color: colors.textPrimary,
          marginBottom: spacing.s3,
        }}
      >
        Transactions
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {rows.map((tx, idx) => (
          <Row key={idx} tx={tx} first={idx === 0} />
        ))}
      </div>
    </div>
  )
}

function Row({ tx, first }: { tx: Tx; first: boolean }) {
  const Icon = tx.kind === 'in' ? ArrowDownLeft : tx.kind === 'out' ? ArrowUpRight : RefreshCw
  const iconBg =
    tx.kind === 'in'
      ? colors.semanticPositiveLight
      : tx.kind === 'out'
        ? colors.semanticNegativeLight
        : colors.semanticInfoLight
  const iconColor =
    tx.kind === 'in'
      ? colors.semanticPositive
      : tx.kind === 'out'
        ? colors.semanticNegative
        : colors.semanticInfo
  const amountColor =
    tx.amountColor === 'positive'
      ? colors.semanticPositive
      : colors.textPrimary
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: spacing.s3,
        padding: `${spacing.s3}px 0`,
        borderTop: first ? 'none' : `1px solid ${colors.separatorOpaque}`,
      }}
    >
      <div
        style={{
          width: 40,
          height: 40,
          borderRadius: 20,
          backgroundColor: iconBg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Icon size={18} color={iconColor} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ ...typoStyle(typo.itemPrimary), color: colors.textPrimary }}>
          {tx.merchant}
        </div>
        <div style={{ ...typoStyle(typo.itemSupporting), color: colors.textSecondary }}>
          {tx.category} · {tx.date}
        </div>
      </div>
      <div style={{ ...typoStyle(typo.itemPrimary), color: amountColor }}>{tx.amount}</div>
    </div>
  )
}
