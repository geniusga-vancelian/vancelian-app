'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import {
  Plus,
  RefreshCw,
  Landmark,
  Building2,
  Wallet,
  ArrowDownCircle,
  ArrowUpCircle,
  List,
  Radio,
  RotateCcw,
  Shield,
  ChevronRight,
  Copy,
  Check,
  Coins,
  Euro,
} from 'lucide-react'

import { CreateEuroAccountModal } from './CreateEuroAccountModal'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Provider {
  id: string
  name: string
  provider_type: string
  jurisdiction: string | null
  status: string
  created_at: string
}

interface Account {
  id: string
  provider_id: string
  account_type: string
  currency: string
  iban: string | null
  bic: string | null
  account_holder_name: string
  client_id: string | null
  is_master_account: boolean
  status: string
  available_balance: number | null
  pending_balance: number | null
  provider_name: string | null
  client_email: string | null
  person_id?: string | null
  person_email_collected?: string | null
  phone_e164?: string | null
  created_at: string
}

interface Balance {
  id: string
  account_id: string
  available_balance: number
  pending_balance: number
  currency: string
  last_updated_at: string
}

interface Transaction {
  id: string
  account_id: string
  provider_id: string | null
  transaction_type: string
  transaction_kind: string | null
  direction: string
  amount: number
  currency: string
  status: string
  external_reference: string | null
  failure_reason: string | null
  reversal_of_transaction_id: string | null
  metadata_: Record<string, unknown> | null
  client_email: string | null
  provider_name: string | null
  created_at: string
  updated_at: string | null
}

interface WebhookEvent {
  id: string
  provider_id: string
  event_type: string
  external_reference: string | null
  payload_hash: string
  processing_status: string
  error_message: string | null
  linked_transaction_id: string | null
  retry_count: number
  received_at: string
  processed_at: string | null
}

// ---------------------------------------------------------------------------
// Tab definitions
// ---------------------------------------------------------------------------

type TabId = 'providers' | 'accounts' | 'balances' | 'transactions' | 'webhooks' | 'simulate' | 'crypto'

const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
  { id: 'providers', label: 'Providers', icon: Building2 },
  { id: 'accounts', label: 'Accounts', icon: Wallet },
  { id: 'balances', label: 'Balances', icon: Landmark },
  { id: 'transactions', label: 'Transactions', icon: List },
  { id: 'webhooks', label: 'Webhook Events', icon: Radio },
  { id: 'simulate', label: 'Simulate', icon: ArrowDownCircle },
  { id: 'crypto', label: 'Crypto Custody', icon: Coins },
]

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function formatAmount(val: number | string | null, currency = 'EUR') {
  if (val == null) return '—'
  const n = typeof val === 'string' ? parseFloat(val) : val
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

function Badge({ label, variant }: { label: string; variant: 'green' | 'blue' | 'gray' | 'red' }) {
  const colors = {
    green: 'bg-green-100 text-green-800',
    blue: 'bg-blue-100 text-blue-800',
    gray: 'bg-gray-100 text-gray-600',
    red: 'bg-red-100 text-red-800',
  }
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${colors[variant]}`}
    >
      {label}
    </span>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CustodyPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState<TabId>('providers')
  const [loading, setLoading] = useState(true)

  // Data
  const [providers, setProviders] = useState<Provider[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [balances, setBalances] = useState<Balance[]>([])
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [webhookEvents, setWebhookEvents] = useState<WebhookEvent[]>([])

  // Modals
  const [showCreateProvider, setShowCreateProvider] = useState(false)
  const [showCreateEuroAccount, setShowCreateEuroAccount] = useState(false)
  const [showCreateSettlementAccount, setShowCreateSettlementAccount] = useState(false)

  // Provider form
  const [provName, setProvName] = useState('')
  const [provType, setProvType] = useState('bank')
  const [provJurisdiction, setProvJurisdiction] = useState('')

  // Account form
  const [accProviderId, setAccProviderId] = useState('')
  const [accCurrency, setAccCurrency] = useState('EUR')
  const [accIban, setAccIban] = useState('')
  const [accBic, setAccBic] = useState('')
  const [accHolderName, setAccHolderName] = useState('')

  // Simulate form
  const [simClientId, setSimClientId] = useState('')
  const [simAmount, setSimAmount] = useState('')
  const [simCurrency, setSimCurrency] = useState('EUR')
  const [simReference, setSimReference] = useState('')
  const [simulating, setSimulating] = useState(false)

  const [submitting, setSubmitting] = useState(false)

  // Reset financial test state
  const [showResetConfirm, setShowResetConfirm] = useState(false)
  const [resetLoading, setResetLoading] = useState(false)
  const [resetReport, setResetReport] = useState<Record<string, unknown> | null>(null)

  // ------------------------------------------------------------------
  // Data fetching
  // ------------------------------------------------------------------

  const fetchProviders = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/custody/providers')
      if (res.status === 401) { router.push('/admin/login'); return }
      const data = await res.json()
      setProviders(data.items ?? [])
    } catch { toastError('Failed to load providers') }
  }, [router])

  const fetchAccounts = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/custody/accounts')
      if (res.status === 401) { router.push('/admin/login'); return }
      const data = await res.json()
      setAccounts(data.items ?? [])
    } catch { toastError('Failed to load accounts') }
  }, [router])

  const fetchBalances = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/custody/balances')
      if (res.status === 401) { router.push('/admin/login'); return }
      const data = await res.json()
      setBalances(data.items ?? [])
    } catch { toastError('Failed to load balances') }
  }, [router])

  const fetchTransactions = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/custody/transactions')
      if (res.status === 401) { router.push('/admin/login'); return }
      const data = await res.json()
      setTransactions(data.items ?? [])
    } catch { toastError('Failed to load transactions') }
  }, [router])

  const fetchWebhookEvents = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/custody/webhook-events')
      if (res.status === 401) { router.push('/admin/login'); return }
      const data = await res.json()
      setWebhookEvents(data.items ?? [])
    } catch { toastError('Failed to load webhook events') }
  }, [router])

  const fetchAll = useCallback(async () => {
    setLoading(true)
    await Promise.all([fetchProviders(), fetchAccounts(), fetchBalances(), fetchTransactions(), fetchWebhookEvents()])
    setLoading(false)
  }, [fetchProviders, fetchAccounts, fetchBalances, fetchTransactions, fetchWebhookEvents])

  useEffect(() => { fetchAll() }, [fetchAll])

  const handleResetFinancialTestState = async () => {
    setShowResetConfirm(false)
    setResetLoading(true)
    try {
      const res = await fetch('/api/admin/custody/reset-financial-test-state?dry_run=false', {
        method: 'POST',
      })
      if (res.status === 401) { router.push('/admin/login'); return }
      const data = await res.json()
      if (!res.ok) throw new Error(data?.error || data?.detail || 'Reset failed')
      setResetReport(data)
      toastSuccess('Reset effectué. Voir le rapport ci-dessous.')
      await fetchAll()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Reset failed')
    } finally {
      setResetLoading(false)
    }
  }

  // ------------------------------------------------------------------
  // Actions
  // ------------------------------------------------------------------

  const handleCreateProvider = async () => {
    if (!provName.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch('/api/admin/custody/providers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: provName.trim(),
          provider_type: provType,
          jurisdiction: provJurisdiction.trim() || null,
          status: 'active',
        }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Failed')
      toastSuccess('Provider created')
      setShowCreateProvider(false)
      setProvName('')
      setProvJurisdiction('')
      await fetchProviders()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Creation failed')
    } finally {
      setSubmitting(false)
    }
  }

  const handleCreateSettlementAccount = async () => {
    if (!accProviderId || !accHolderName.trim()) return
    setSubmitting(true)
    try {
      const res = await fetch('/api/admin/custody/accounts/settlement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: accProviderId,
          account_type: 'company_settlement_account',
          currency: accCurrency,
          iban: accIban.trim() || null,
          bic: accBic.trim() || null,
          account_holder_name: accHolderName.trim(),
          is_master_account: true,
        }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Failed')
      toastSuccess('Settlement account created')
      setShowCreateSettlementAccount(false)
      resetAccountForm()
      await Promise.all([fetchAccounts(), fetchBalances()])
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Creation failed')
    } finally {
      setSubmitting(false)
    }
  }

  const resetAccountForm = () => {
    setAccProviderId('')
    setAccCurrency('EUR')
    setAccIban('')
    setAccBic('')
    setAccHolderName('')
  }

  const handleSimulate = async (type: 'deposit' | 'withdrawal') => {
    if (!simClientId.trim() || !simAmount.trim()) return
    setSimulating(true)
    try {
      const endpoint =
        type === 'deposit'
          ? '/api/admin/custody/simulate-deposit'
          : '/api/admin/custody/simulate-withdrawal'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          client_id: simClientId.trim(),
          amount: parseFloat(simAmount),
          currency: simCurrency,
          reference: simReference.trim() || null,
        }),
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Failed')
      const data = await res.json()
      toastSuccess(data.message || `${type} simulated`)
      setSimAmount('')
      setSimReference('')
      await Promise.all([fetchBalances(), fetchTransactions(), fetchAccounts()])
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Simulation failed')
    } finally {
      setSimulating(false)
    }
  }

  // ------------------------------------------------------------------
  // Render
  // ------------------------------------------------------------------

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Custody</h1>
          <p className="text-gray-600">
            Fiat custody accounts, balances, transactions and BAS provider management.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowResetConfirm(true)}
            disabled={resetLoading}
            className="flex items-center gap-2 text-amber-700 border-amber-300 hover:bg-amber-50"
          >
            <RotateCcw className="h-4 w-4" />
            Reset financial test state
          </Button>
          <Button
            variant="outline"
            onClick={fetchAll}
            className="flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b">
        {tabs.map((tab) => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-gray-900 text-gray-900'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <Icon className="h-4 w-4" />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab Content */}
      {activeTab === 'providers' && (
        <ProvidersTab
          providers={providers}
          onCreateClick={() => setShowCreateProvider(true)}
        />
      )}
      {activeTab === 'accounts' && (
        <AccountsTab
          accounts={accounts}
          onCreateEuroClick={() => setShowCreateEuroAccount(true)}
          onCreateSettlementClick={() => {
            resetAccountForm()
            setShowCreateSettlementAccount(true)
          }}
        />
      )}
      {activeTab === 'balances' && (
        <BalancesTab
          accounts={accounts}
          balances={balances}
          providers={providers}
          router={router}
        />
      )}
      {activeTab === 'transactions' && (
        <TransactionsTab
          transactions={transactions}
          providers={providers}
          accounts={accounts}
          onRefresh={fetchTransactions}
        />
      )}
      {activeTab === 'webhooks' && (
        <WebhookEventsTab
          events={webhookEvents}
          providers={providers}
          onRefresh={fetchWebhookEvents}
        />
      )}
      {activeTab === 'simulate' && (
        <SimulateTab
          clientId={simClientId}
          setClientId={setSimClientId}
          amount={simAmount}
          setAmount={setSimAmount}
          currency={simCurrency}
          setCurrency={setSimCurrency}
          reference={simReference}
          setReference={setSimReference}
          simulating={simulating}
          onDeposit={() => handleSimulate('deposit')}
          onWithdraw={() => handleSimulate('withdrawal')}
          providers={providers}
          onRefreshAll={fetchAll}
        />
      )}

      {activeTab === 'crypto' && <CryptoCustodyTab />}

      {/* Reset financial test state: confirmation */}
      <AlertDialog open={showResetConfirm} onOpenChange={setShowResetConfirm}>
        <AlertDialogContent>
          <AlertDialogTitle>Reset financial test state</AlertDialogTitle>
          <AlertDialogDescription>
            Supprime TOUTE l&apos;activité client : transactions, orders, trades, positions, alertes,
            notifications, envelopes, commitments, intérêts lending, chatbot sessions, audit logs, et remet
            les soldes custody/crypto à zéro. Les comptes, clients, bundles (config), portfolios (structure),
            offres exclusives (métadonnées) et market data sont conservés. Les offres sont remises en
            fundraising avec raised=0. Irréversible. Continuer ?
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleResetFinancialTestState}
              className="bg-amber-600 hover:bg-amber-700"
            >
              Confirmer le reset
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Reset report modal */}
      {resetReport && (
        <Modal
          title="Rapport de reset"
          onClose={() => setResetReport(null)}
        >
          <div className="max-h-[70vh] overflow-y-auto space-y-3 text-sm">
            {resetReport.success !== false && (
              <p className="text-green-700 font-medium">Reset effectué avec succès.</p>
            )}
            {resetReport.before != null && typeof resetReport.before === 'object' ? (
              <div>
                <p className="font-medium text-gray-700 mb-1">Avant</p>
                <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                  {JSON.stringify(resetReport.before, null, 2)}
                </pre>
              </div>
            ) : null}
            {resetReport.after != null && typeof resetReport.after === 'object' ? (
              <div>
                <p className="font-medium text-gray-700 mb-1">Après</p>
                <pre className="bg-gray-100 p-2 rounded text-xs overflow-x-auto">
                  {JSON.stringify(resetReport.after, null, 2)}
                </pre>
              </div>
            ) : null}
            {resetReport.balances_updated != null && (
              <p className="text-gray-600">Balances mises à zéro : {String(resetReport.balances_updated)}</p>
            )}
            <Button variant="outline" onClick={() => setResetReport(null)} className="w-full">
              Fermer
            </Button>
          </div>
        </Modal>
      )}

      {/* Create Provider Modal */}
      {showCreateProvider && (
        <Modal title="Create Provider" onClose={() => setShowCreateProvider(false)}>
          <div className="space-y-4">
            <Field label="Name" required>
              <Input value={provName} onChange={(e) => setProvName(e.target.value)} placeholder="Modular" />
            </Field>
            <Field label="Type">
              <select
                value={provType}
                onChange={(e) => setProvType(e.target.value)}
                className="w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="bank">Bank</option>
                <option value="emi">EMI</option>
              </select>
            </Field>
            <Field label="Jurisdiction">
              <Input
                value={provJurisdiction}
                onChange={(e) => setProvJurisdiction(e.target.value)}
                placeholder="EU / UAE / UK"
              />
            </Field>
          </div>
          <div className="flex justify-end gap-3 mt-6">
            <Button variant="outline" onClick={() => setShowCreateProvider(false)}>Cancel</Button>
            <Button onClick={handleCreateProvider} disabled={submitting || !provName.trim()}>
              {submitting ? 'Creating...' : 'Create'}
            </Button>
          </div>
        </Modal>
      )}

      {showCreateEuroAccount && (
        <Modal title="Create Euro Account" onClose={() => setShowCreateEuroAccount(false)}>
          <CreateEuroAccountModal
            onClose={() => setShowCreateEuroAccount(false)}
            onCreated={() => {
              void Promise.all([fetchAccounts(), fetchBalances()])
            }}
          />
        </Modal>
      )}

      {/* Create Settlement Account Modal */}
      {showCreateSettlementAccount && (
        <AccountFormModal
          title="Create Settlement Account"
          providers={providers}
          providerId={accProviderId}
          setProviderId={setAccProviderId}
          currency={accCurrency}
          setCurrency={setAccCurrency}
          iban={accIban}
          setIban={setAccIban}
          bic={accBic}
          setBic={setAccBic}
          holderName={accHolderName}
          setHolderName={setAccHolderName}
          submitting={submitting}
          onSubmit={handleCreateSettlementAccount}
          onClose={() => setShowCreateSettlementAccount(false)}
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function ProvidersTab({
  providers,
  onCreateClick,
}: {
  providers: Provider[]
  onCreateClick: () => void
}) {
  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Providers ({providers.length})</CardTitle>
        <Button size="sm" onClick={onCreateClick} className="flex items-center gap-1">
          <Plus className="h-4 w-4" /> Add Provider
        </Button>
      </CardHeader>
      <CardContent>
        {providers.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">
            No providers yet. Create your first BAS provider.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3 pr-4">Name</th>
                  <th className="pb-3 pr-4">Type</th>
                  <th className="pb-3 pr-4">Jurisdiction</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Created</th>
                </tr>
              </thead>
              <tbody>
                {providers.map((p) => (
                  <tr key={p.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-3 pr-4 font-medium">{p.name}</td>
                    <td className="py-3 pr-4 uppercase text-xs">{p.provider_type}</td>
                    <td className="py-3 pr-4">{p.jurisdiction ?? '—'}</td>
                    <td className="py-3 pr-4">
                      <Badge label={p.status} variant={p.status === 'active' ? 'green' : 'gray'} />
                    </td>
                    <td className="py-3 pr-4 text-gray-500">{formatDate(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function AccountsTab({
  accounts,
  onCreateEuroClick,
  onCreateSettlementClick,
}: {
  accounts: Account[]
  onCreateEuroClick: () => void
  onCreateSettlementClick: () => void
}) {
  return (
    <Card>
      <CardHeader className="pb-3 flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Accounts ({accounts.length})</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="outline" onClick={onCreateSettlementClick} className="flex items-center gap-1">
            <Building2 className="h-4 w-4" /> Settlement Account
          </Button>
          <Button size="sm" onClick={onCreateEuroClick} className="flex items-center gap-1 bg-emerald-700 hover:bg-emerald-800 text-white">
            <Euro className="h-4 w-4" /> Create Euro Account
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {accounts.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">No accounts yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3 pr-4">Type</th>
                  <th className="pb-3 pr-4">Person</th>
                  <th className="pb-3 pr-4">Contact / PE</th>
                  <th className="pb-3 pr-4">IBAN</th>
                  <th className="pb-3 pr-4">Currency</th>
                  <th className="pb-3 pr-4 text-right">Balance</th>
                  <th className="pb-3 pr-4">Provider</th>
                  <th className="pb-3 pr-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {accounts.map((a) => (
                  <tr key={a.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-3 pr-4">
                      <Badge
                        label={a.is_master_account ? 'Company Settlement' : 'Client Deposit'}
                        variant={a.is_master_account ? 'blue' : 'green'}
                      />
                    </td>
                    <td className="py-3 pr-4 align-top text-xs font-mono text-gray-600 max-w-[140px] break-all">
                      {a.person_id ?? '—'}
                    </td>
                    <td className="py-3 pr-4 align-top max-w-[220px]">
                      {a.person_email_collected ? (
                        <div className="text-xs">
                          <span className="text-gray-500">Business email</span>
                          <div className="font-medium break-all">{a.person_email_collected}</div>
                        </div>
                      ) : null}
                      {a.phone_e164 ? (
                        <div className="text-xs mt-1">
                          <span className="text-gray-500">Phone</span>
                          <div>{a.phone_e164}</div>
                        </div>
                      ) : null}
                      {a.client_email ? (
                        <div className="text-xs mt-1">
                          <span className="text-gray-500">PE / technical login</span>
                          <div className="break-all flex flex-wrap items-center gap-1">
                            <span>{a.client_email}</span>
                          </div>
                        </div>
                      ) : (
                        <span className="font-medium">{a.account_holder_name}</span>
                      )}
                    </td>
                    <td className="py-3 pr-4 font-mono text-xs">{a.iban ?? '—'}</td>
                    <td className="py-3 pr-4">{a.currency}</td>
                    <td className="py-3 pr-4 text-right font-medium">
                      {formatAmount(a.available_balance, a.currency)}
                    </td>
                    <td className="py-3 pr-4">{a.provider_name ?? '—'}</td>
                    <td className="py-3 pr-4">
                      <Badge label={a.status} variant={a.status === 'active' ? 'green' : 'gray'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function CopyableIban({ iban }: { iban: string | null }) {
  const [copied, setCopied] = useState(false)
  if (!iban) return <span className="text-gray-400">—</span>
  const handleCopy = async () => {
    await navigator.clipboard.writeText(iban)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <span className="inline-flex items-center gap-1.5 group">
      <span className="font-mono text-sm">{iban}</span>
      <button
        onClick={handleCopy}
        className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-400 hover:text-gray-700"
        title="Copy IBAN"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-green-600" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
    </span>
  )
}

function txReasonLabel(t: Transaction): string {
  const kind = t.transaction_kind ?? t.transaction_type
  const meta = t.metadata_ ?? {}
  const remitter = (meta.remitter_name as string) || ''
  const narrative = (meta.narrative as string) || ''
  const clientEmail = t.client_email || ''

  let base: string
  switch (kind) {
    case 'bank_transfer_in':
      base = 'Depot client'
      break
    case 'bank_transfer_out':
      base = 'Retrait client'
      break
    case 'internal_transfer':
      base = 'Transfert interne'
      break
    case 'exchange_buy':
      base = 'R/L EUR — achat crypto'
      break
    case 'exchange_sell':
      base = 'R/L EUR — vente crypto'
      break
    case 'deposit':
      base = 'Depot'
      break
    case 'withdrawal':
      base = 'Retrait'
      break
    default:
      base = kind.replace(/_/g, ' ')
  }

  const suffix = remitter || narrative || clientEmail
  return suffix ? `${base} — ${suffix}` : base
}

function BalancesTab({
  accounts,
  balances,
  providers,
  router,
}: {
  accounts: Account[]
  balances: Balance[]
  providers: Provider[]
  router: ReturnType<typeof useRouter>
}) {
  const [selectedAccountId, setSelectedAccountId] = useState<string | null>(null)
  const [acctTransactions, setAcctTransactions] = useState<Transaction[]>([])
  const [loadingTx, setLoadingTx] = useState(false)
  const [txError, setTxError] = useState<string | null>(null)

  const settlementAccount = accounts.find(
    (a) => a.is_master_account && a.account_type === 'company_settlement_account' && a.currency === 'EUR',
  )

  const settlementBalance = balances.find(
    (b) => settlementAccount && b.account_id === settlementAccount.id,
  )

  const providerName = (pid: string) => providers.find((p) => p.id === pid)?.name ?? '—'

  const selectedAccount = accounts.find((a) => a.id === selectedAccountId)
  const selectedBalance = balances.find((b) => b.account_id === selectedAccountId)

  const fetchAccountTransactions = useCallback(async (accountId: string) => {
    setLoadingTx(true)
    setTxError(null)
    try {
      const res = await fetch(`/api/admin/custody/transactions?account_id=${accountId}&limit=100`)
      if (res.status === 401) { router.push('/admin/login'); return }
      const data = await res.json()
      setAcctTransactions(data.items ?? [])
    } catch {
      setTxError('Failed to load transactions')
      setAcctTransactions([])
    } finally {
      setLoadingTx(false)
    }
  }, [router])

  const handleSelectAccount = (accountId: string) => {
    setSelectedAccountId(accountId)
    fetchAccountTransactions(accountId)
  }

  return (
    <div className="space-y-6">
      {/* Settlement Account Card */}
      <Card className="border-blue-200 bg-gradient-to-r from-blue-50 to-slate-50">
        <CardHeader className="pb-3 flex flex-row items-center gap-3">
          <div className="rounded-lg bg-blue-600 p-2">
            <Shield className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <CardTitle className="text-lg">EUR Settlement / Delivery Account</CardTitle>
            <p className="text-xs text-gray-500 mt-0.5">
              Company fiat settlement — future EUR → Crypto operations
            </p>
          </div>
          {settlementAccount && (
            <Badge label="Active" variant={settlementAccount.status === 'active' ? 'green' : 'gray'} />
          )}
        </CardHeader>
        <CardContent>
          {!settlementAccount ? (
            <p className="text-gray-500 text-sm py-4 text-center">
              No EUR settlement account found. Create one via the Accounts tab.
            </p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Holder</p>
                <p className="text-sm font-medium">{settlementAccount.account_holder_name}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Provider</p>
                <p className="text-sm font-medium">{settlementAccount.provider_name ?? providerName(settlementAccount.provider_id)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">IBAN</p>
                <CopyableIban iban={settlementAccount.iban} />
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">BIC</p>
                <p className="text-sm font-mono">{settlementAccount.bic ?? '—'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Available Balance</p>
                <p className="text-xl font-bold text-blue-700">
                  {formatAmount(settlementBalance?.available_balance ?? settlementAccount.available_balance, 'EUR')}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Pending Balance</p>
                <p className="text-sm font-medium text-gray-600">
                  {formatAmount(settlementBalance?.pending_balance ?? settlementAccount.pending_balance, 'EUR')}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Currency</p>
                <p className="text-sm font-medium">{settlementAccount.currency}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Last Updated</p>
                <p className="text-sm text-gray-600">
                  {settlementBalance ? formatDate(settlementBalance.last_updated_at) : '—'}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Split View: Accounts List + Account Detail */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left Panel — Account List (~40%) */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg">Accounts ({accounts.length})</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {accounts.length === 0 ? (
                <p className="text-gray-500 text-sm py-8 text-center">No accounts yet.</p>
              ) : (
                <div className="divide-y">
                  {accounts.map((a) => {
                    const bal = balances.find((b) => b.account_id === a.id)
                    const isSelected = a.id === selectedAccountId
                    const owner = a.client_email ?? (a.is_master_account ? 'Company' : a.account_holder_name)
                    return (
                      <button
                        key={a.id}
                        onClick={() => handleSelectAccount(a.id)}
                        className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-colors ${
                          isSelected
                            ? 'bg-blue-50 border-l-2 border-l-blue-600'
                            : 'hover:bg-gray-50 border-l-2 border-l-transparent'
                        }`}
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge
                              label={a.is_master_account ? 'Settlement' : 'Client'}
                              variant={a.is_master_account ? 'blue' : 'green'}
                            />
                            <span className="text-xs text-gray-400">{a.currency}</span>
                            <Badge label={a.status} variant={a.status === 'active' ? 'green' : 'gray'} />
                          </div>
                          <p className="text-sm font-medium truncate">{owner}</p>
                          <p className="text-xs text-gray-400 font-mono truncate">{a.iban ?? '—'}</p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-sm font-bold">
                            {formatAmount(bal?.available_balance ?? a.available_balance, a.currency)}
                          </p>
                        </div>
                        <ChevronRight className={`h-4 w-4 shrink-0 ${isSelected ? 'text-blue-600' : 'text-gray-300'}`} />
                      </button>
                    )
                  })}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel — Account Detail + Transactions (~60%) */}
        <div className="lg:col-span-3 space-y-4">
          {!selectedAccount ? (
            <Card>
              <CardContent className="py-16 text-center">
                <Wallet className="h-10 w-10 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Select an account to view details</p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* Account Detail Summary */}
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Badge
                      label={selectedAccount.is_master_account ? 'Company Settlement' : 'Client Deposit'}
                      variant={selectedAccount.is_master_account ? 'blue' : 'green'}
                    />
                    {selectedAccount.client_email ?? selectedAccount.account_holder_name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">Account ID</p>
                      <p className="font-mono text-xs truncate" title={selectedAccount.id}>{selectedAccount.id.slice(0, 12)}...</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">Provider</p>
                      <p>{selectedAccount.provider_name ?? providerName(selectedAccount.provider_id)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">IBAN</p>
                      <CopyableIban iban={selectedAccount.iban} />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">BIC</p>
                      <p className="font-mono text-xs">{selectedAccount.bic ?? '—'}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">Available</p>
                      <p className="font-bold text-lg">
                        {formatAmount(selectedBalance?.available_balance ?? selectedAccount.available_balance, selectedAccount.currency)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500 mb-0.5">Pending</p>
                      <p className="text-gray-600">
                        {formatAmount(selectedBalance?.pending_balance ?? selectedAccount.pending_balance, selectedAccount.currency)}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Historical Transactions */}
              <Card>
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-base">Transactions</CardTitle>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => fetchAccountTransactions(selectedAccount.id)}
                    className="flex items-center gap-1 text-xs"
                  >
                    <RefreshCw className="h-3 w-3" /> Refresh
                  </Button>
                </CardHeader>
                <CardContent>
                  {loadingTx ? (
                    <div className="flex justify-center py-8">
                      <RefreshCw className="h-5 w-5 animate-spin text-gray-400" />
                    </div>
                  ) : txError ? (
                    <p className="text-red-500 text-sm py-8 text-center">{txError}</p>
                  ) : acctTransactions.length === 0 ? (
                    <p className="text-gray-500 text-sm py-8 text-center">
                      No transactions for this account yet.
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="border-b text-left text-gray-500">
                            <th className="pb-3 pr-3">Date</th>
                            <th className="pb-3 pr-3">Kind</th>
                            <th className="pb-3 pr-3">Direction</th>
                            <th className="pb-3 pr-3 text-right">Amount</th>
                            <th className="pb-3 pr-3">Status</th>
                            <th className="pb-3 pr-3">Reason</th>
                            <th className="pb-3 pr-3">Reference</th>
                          </tr>
                        </thead>
                        <tbody>
                          {acctTransactions.map((t) => (
                            <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                              <td className="py-2.5 pr-3 text-gray-500 whitespace-nowrap text-xs">
                                {formatDate(t.created_at)}
                              </td>
                              <td className="py-2.5 pr-3 capitalize text-xs">
                                {(t.transaction_kind ?? t.transaction_type).replace(/_/g, ' ')}
                              </td>
                              <td className="py-2.5 pr-3">
                                <Badge label={t.direction} variant={t.direction === 'credit' ? 'green' : 'red'} />
                              </td>
                              <td className={`py-2.5 pr-3 text-right font-medium ${
                                t.direction === 'credit' ? 'text-green-700' : 'text-gray-600'
                              }`}>
                                {t.direction === 'credit' ? '+' : '−'}{formatAmount(t.amount, t.currency)}
                              </td>
                              <td className="py-2.5 pr-3">
                                <Badge label={t.status} variant={txStatusVariant(t.status)} />
                              </td>
                              <td className="py-2.5 pr-3 text-xs max-w-[220px] truncate" title={txReasonLabel(t)}>
                                {txReasonLabel(t)}
                              </td>
                              <td className="py-2.5 pr-3 font-mono text-xs text-gray-400 max-w-[120px] truncate" title={t.external_reference ?? ''}>
                                {t.external_reference ?? '—'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function txStatusVariant(status: string): 'green' | 'blue' | 'gray' | 'red' {
  switch (status) {
    case 'completed': return 'green'
    case 'processing': return 'blue'
    case 'failed': return 'red'
    case 'reversed': return 'red'
    default: return 'gray'
  }
}

function TransactionsTab({
  transactions,
  providers,
  accounts,
  onRefresh,
}: {
  transactions: Transaction[]
  providers: Provider[]
  accounts: Account[]
  onRefresh: () => void
}) {
  const [filterClientId, setFilterClientId] = useState('')
  const [filterProviderId, setFilterProviderId] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filtered, setFiltered] = useState<Transaction[]>(transactions)
  const [loading, setLoading] = useState(false)

  const clientEmails = Array.from(
    new Set(accounts.filter((a) => a.client_id && a.client_email).map((a) => JSON.stringify({ id: a.client_id!, email: a.client_email! })))
  ).map((s) => JSON.parse(s) as { id: string; email: string })

  const applyFilters = useCallback(async () => {
    const params = new URLSearchParams()
    if (filterClientId) params.set('client_id', filterClientId)
    if (filterProviderId) params.set('provider_id', filterProviderId)
    if (filterType) params.set('transaction_type', filterType)
    if (filterStatus) params.set('status', filterStatus)
    const qs = params.toString()
    if (!qs) { setFiltered(transactions); return }
    setLoading(true)
    try {
      const res = await fetch(`/api/admin/custody/transactions?${qs}`)
      const data = await res.json()
      setFiltered(data.items ?? [])
    } catch { setFiltered(transactions) }
    finally { setLoading(false) }
  }, [filterClientId, filterProviderId, filterType, filterStatus, transactions])

  useEffect(() => { applyFilters() }, [applyFilters])

  const clearFilters = () => {
    setFilterClientId('')
    setFilterProviderId('')
    setFilterType('')
    setFilterStatus('')
  }
  const hasFilters = !!(filterClientId || filterProviderId || filterType || filterStatus)

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Transactions ({filtered.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-3 mb-4">
          <select
            value={filterClientId}
            onChange={(e) => setFilterClientId(e.target.value)}
            className="rounded-md border px-3 py-1.5 text-sm"
          >
            <option value="">All Clients</option>
            {clientEmails.map((c) => (
              <option key={c.id} value={c.id}>{c.email}</option>
            ))}
          </select>
          <select
            value={filterProviderId}
            onChange={(e) => setFilterProviderId(e.target.value)}
            className="rounded-md border px-3 py-1.5 text-sm"
          >
            <option value="">All Providers</option>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="rounded-md border px-3 py-1.5 text-sm"
          >
            <option value="">All Types</option>
            <option value="deposit">Deposit</option>
            <option value="withdrawal">Withdrawal</option>
            <option value="transfer_internal">Transfer Internal</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="rounded-md border px-3 py-1.5 text-sm"
          >
            <option value="">All Statuses</option>
            <option value="pending">Pending</option>
            <option value="processing">Processing</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="reversed">Reversed</option>
          </select>
          {hasFilters && (
            <Button size="sm" variant="outline" onClick={clearFilters} className="text-xs">
              Clear filters
            </Button>
          )}
        </div>
        {loading ? (
          <div className="flex justify-center py-8"><RefreshCw className="h-5 w-5 animate-spin text-gray-400" /></div>
        ) : filtered.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">No transactions found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3 pr-4">Date</th>
                  <th className="pb-3 pr-4">Client</th>
                  <th className="pb-3 pr-4">Type</th>
                  <th className="pb-3 pr-4">Direction</th>
                  <th className="pb-3 pr-4 text-right">Amount</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Provider</th>
                  <th className="pb-3 pr-4">Reference</th>
                  <th className="pb-3 pr-4">Remitter</th>
                  <th className="pb-3 pr-4">Narrative</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => {
                  const meta = t.metadata_ ?? {}
                  return (
                    <tr key={t.id} className="border-b last:border-0 hover:bg-gray-50">
                      <td className="py-3 pr-4 text-gray-500 whitespace-nowrap">{formatDate(t.created_at)}</td>
                      <td className="py-3 pr-4 text-sm">{t.client_email ?? '—'}</td>
                      <td className="py-3 pr-4 capitalize">{t.transaction_type.replace('_', ' ')}</td>
                      <td className="py-3 pr-4">
                        <Badge label={t.direction} variant={t.direction === 'credit' ? 'green' : 'red'} />
                      </td>
                      <td className="py-3 pr-4 text-right font-medium">{formatAmount(t.amount, t.currency)}</td>
                      <td className="py-3 pr-4">
                        <Badge label={t.status} variant={txStatusVariant(t.status)} />
                      </td>
                      <td className="py-3 pr-4">{t.provider_name ?? '—'}</td>
                      <td className="py-3 pr-4 font-mono text-xs text-gray-500 max-w-[140px] truncate" title={t.external_reference ?? ''}>
                        {t.external_reference ?? '—'}
                      </td>
                      <td className="py-3 pr-4 text-xs max-w-[140px] truncate" title={String(meta.remitter_name ?? '')}>
                        {(meta.remitter_name as string) ?? '—'}
                      </td>
                      <td className="py-3 pr-4 text-xs text-gray-500 max-w-[180px] truncate" title={String(meta.narrative ?? '')}>
                        {(meta.narrative as string) ?? '—'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function webhookStatusVariant(status: string): 'green' | 'blue' | 'gray' | 'red' {
  switch (status) {
    case 'processed': return 'green'
    case 'processing': return 'blue'
    case 'duplicate': return 'gray'
    case 'ignored': return 'gray'
    case 'failed': return 'red'
    default: return 'gray'
  }
}

function WebhookEventsTab({
  events,
  providers,
  onRefresh,
}: {
  events: WebhookEvent[]
  providers: Provider[]
  onRefresh: () => void
}) {
  const [replaying, setReplaying] = useState<string | null>(null)

  const providerName = (pid: string) => {
    const p = providers.find((pr) => pr.id === pid)
    return p?.name ?? pid.slice(0, 8)
  }

  const handleReplay = async (eventId: string) => {
    setReplaying(eventId)
    try {
      const res = await fetch(`/api/admin/custody/webhook-events/${eventId}/replay`, {
        method: 'POST',
      })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Replay failed')
      const data = await res.json()
      toastSuccess(`Replayed — status: ${data.processing_status}`)
      onRefresh()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Replay failed')
    } finally {
      setReplaying(null)
    }
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Webhook Events ({events.length})</CardTitle>
      </CardHeader>
      <CardContent>
        {events.length === 0 ? (
          <p className="text-gray-500 text-sm py-8 text-center">No webhook events yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3 pr-4">Provider</th>
                  <th className="pb-3 pr-4">Event Type</th>
                  <th className="pb-3 pr-4">Reference</th>
                  <th className="pb-3 pr-4">Status</th>
                  <th className="pb-3 pr-4">Retries</th>
                  <th className="pb-3 pr-4">Error</th>
                  <th className="pb-3 pr-4">Received</th>
                  <th className="pb-3 pr-4">Processed</th>
                  <th className="pb-3 pr-4">Actions</th>
                </tr>
              </thead>
              <tbody>
                {events.map((e) => (
                  <tr key={e.id} className="border-b last:border-0 hover:bg-gray-50">
                    <td className="py-3 pr-4 font-medium">{providerName(e.provider_id)}</td>
                    <td className="py-3 pr-4 capitalize">{e.event_type.replace(/_/g, ' ')}</td>
                    <td className="py-3 pr-4 font-mono text-xs text-gray-500">
                      {e.external_reference ?? '—'}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge label={e.processing_status} variant={webhookStatusVariant(e.processing_status)} />
                    </td>
                    <td className="py-3 pr-4 text-center">{e.retry_count}</td>
                    <td className="py-3 pr-4 text-xs text-red-600 max-w-[200px] truncate" title={e.error_message ?? ''}>
                      {e.error_message ?? '—'}
                    </td>
                    <td className="py-3 pr-4 text-gray-500">{formatDate(e.received_at)}</td>
                    <td className="py-3 pr-4 text-gray-500">{e.processed_at ? formatDate(e.processed_at) : '—'}</td>
                    <td className="py-3 pr-4">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleReplay(e.id)}
                        disabled={replaying === e.id}
                        className="flex items-center gap-1 text-xs"
                      >
                        <RotateCcw className="h-3 w-3" />
                        {replaying === e.id ? '...' : 'Replay'}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

type DepositSimClient = {
  client_id: string
  email: string
  iban: string | null
  account_holder_name: string
  available_balance: string | number | null
  /** Libellé ops (titulaire — e-mail), fourni par l’API */
  label?: string
}

function SimulateTab({
  clientId,
  setClientId,
  amount,
  setAmount,
  currency,
  setCurrency,
  reference,
  setReference,
  simulating,
  onDeposit,
  onWithdraw,
  providers,
  onRefreshAll,
}: {
  clientId: string
  setClientId: (v: string) => void
  amount: string
  setAmount: (v: string) => void
  currency: string
  setCurrency: (v: string) => void
  reference: string
  setReference: (v: string) => void
  simulating: boolean
  onDeposit: () => void
  onWithdraw: () => void
  providers: Provider[]
  onRefreshAll: () => void
}) {
  const WEBHOOK_DEPOSIT_CURRENCY = 'EUR'
  const [depositSimClients, setDepositSimClients] = useState<DepositSimClient[]>([])
  const [depositSimClientsLoading, setDepositSimClientsLoading] = useState(false)
  const [depositSimClientsError, setDepositSimClientsError] = useState<string | null>(null)
  const [whkProviderId, setWhkProviderId] = useState('')
  const [whkClientId, setWhkClientId] = useState('')
  const [whkAmount, setWhkAmount] = useState('')
  const [whkSending, setWhkSending] = useState(false)

  const loadDepositSimClients = useCallback(async () => {
    if (!whkProviderId) {
      setDepositSimClients([])
      setDepositSimClientsError(null)
      return
    }
    setDepositSimClientsLoading(true)
    setDepositSimClientsError(null)
    try {
      const params = new URLSearchParams({
        currency: WEBHOOK_DEPOSIT_CURRENCY,
        provider_id: whkProviderId,
      })
      const res = await fetch(`/api/admin/custody/clients-for-deposit-simulation?${params.toString()}`)
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        const detail = (data as { detail?: unknown }).detail
        const msg =
          typeof detail === 'string'
            ? detail
            : Array.isArray(detail)
              ? 'Validation error'
              : (data as { error?: string }).error || `HTTP ${res.status}`
        throw new Error(msg)
      }
      const items: DepositSimClient[] = data.items ?? []
      setDepositSimClients(items)
      setWhkClientId((prev) => {
        if (!prev) return prev
        if (!items.some((x) => x.client_id === prev)) return ''
        return prev
      })
    } catch (e: unknown) {
      setDepositSimClients([])
      setDepositSimClientsError(e instanceof Error ? e.message : 'Failed to load customers')
    } finally {
      setDepositSimClientsLoading(false)
    }
  }, [whkProviderId])

  useEffect(() => {
    void loadDepositSimClients()
  }, [loadDepositSimClients])

  const selectedWebhookCustomer = useMemo(
    () => depositSimClients.find((x) => x.client_id === whkClientId),
    [depositSimClients, whkClientId],
  )
  const resolvedIban = (selectedWebhookCustomer?.iban ?? '').trim()

  const handleWebhookDeposit = async () => {
    if (!whkProviderId || !whkClientId || !whkAmount || !resolvedIban) return
    setWhkSending(true)
    try {
      const prov = providers.find((p) => p.id === whkProviderId)
      if (!prov) throw new Error('Provider not found')
      const ref = `SIM_DEP_${Math.random().toString(36).slice(2, 10).toUpperCase()}`
      const row = depositSimClients.find((x) => x.client_id === whkClientId)
      const holderName = row?.account_holder_name ?? ''
      const now = new Date().toISOString().slice(0, 10)
      const res = await fetch(`/api/webhooks/custody/${prov.name}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: 'deposit_detected',
          reference: ref,
          iban: resolvedIban,
          amount: parseFloat(whkAmount),
          currency: WEBHOOK_DEPOSIT_CURRENCY,
          account_holder_name: holderName,
          booking_date: now,
          value_date: now,
        }),
      })
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}))
        const detail = (errBody as { detail?: string }).detail
        throw new Error(typeof detail === 'string' ? detail : 'Webhook request failed')
      }
      const data = await res.json()
      toastSuccess(`Webhook deposit sent — status: ${data.processing_status}`)
      setWhkAmount('')
      onRefreshAll()
      await loadDepositSimClients()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Webhook deposit failed')
    } finally {
      setWhkSending(false)
    }
  }

  const amountNum = parseFloat(whkAmount)
  const amountValid = !Number.isNaN(amountNum) && amountNum > 0
  const canSendWebhook =
    !!whkProviderId && !!whkClientId && amountValid && !!resolvedIban && !whkSending

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <Radio className="h-5 w-5 text-purple-600" />
            Simulate Webhook Deposit (BAS)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-600 mb-4 max-w-2xl">
            Simulate a BAS inbound deposit for a specific customer. Choose the provider, the customer with a EUR
            deposit account at that provider, and the amount. The target IBAN is resolved automatically from the
            custody account (EUR).
          </p>
          <div className="space-y-4 max-w-xl">
            <Field label="Provider" required>
              <select
                value={whkProviderId}
                onChange={(e) => {
                  setWhkProviderId(e.target.value)
                  setWhkClientId('')
                }}
                className="w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="">Select provider…</option>
                {providers.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Customer" required>
              <select
                value={whkClientId}
                onChange={(e) => setWhkClientId(e.target.value)}
                disabled={!whkProviderId || depositSimClientsLoading}
                className="w-full rounded-md border px-3 py-2 text-sm"
              >
                <option value="">
                  {!whkProviderId
                    ? 'Select a provider first…'
                    : depositSimClientsLoading
                      ? 'Loading…'
                      : 'Select customer…'}
                </option>
                {depositSimClients.map((c) => (
                  <option key={c.client_id} value={c.client_id}>
                    {c.label ?? `${c.account_holder_name || 'Client'} — ${c.email}`}
                  </option>
                ))}
              </select>
            </Field>
            <Field label={`Amount (${WEBHOOK_DEPOSIT_CURRENCY})`} required>
              <Input
                type="number"
                min="0.01"
                step="0.01"
                value={whkAmount}
                onChange={(e) => setWhkAmount(e.target.value)}
                placeholder="1000.00"
              />
            </Field>
            {depositSimClientsError && (
              <p className="text-sm text-red-600" role="alert">
                {depositSimClientsError}
              </p>
            )}
            {whkProviderId && !depositSimClientsLoading && !depositSimClientsError && depositSimClients.length === 0 && (
              <p className="text-sm text-amber-700">
                No customer with a EUR deposit account for this provider. Create a client deposit account under this
                provider first.
              </p>
            )}
            {whkClientId && !resolvedIban && (
              <p className="text-sm text-red-600">
                This customer has no IBAN on the EUR custody account. Complete the account before simulating.
              </p>
            )}
            <Button
              className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 text-white"
              onClick={handleWebhookDeposit}
              disabled={!canSendWebhook}
            >
              <Radio className="h-4 w-4" />
              {whkSending ? 'Sending…' : 'Send simulated deposit'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <ArrowDownCircle className="h-5 w-5 text-green-600" />
              Direct Simulate Deposit
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <Field label="Client ID" required>
                <Input
                  value={clientId}
                  onChange={(e) => setClientId(e.target.value)}
                  placeholder="UUID of the PE client"
                />
              </Field>
              <div className="grid grid-cols-2 gap-4">
                <Field label="Amount" required>
                  <Input
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="1000.00"
                  />
                </Field>
                <Field label="Currency">
                  <Input value={currency} onChange={(e) => setCurrency(e.target.value)} />
                </Field>
              </div>
              <Field label="Reference">
                <Input
                  value={reference}
                  onChange={(e) => setReference(e.target.value)}
                  placeholder="VIREMENT-001"
                />
              </Field>
              <Button
                className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700"
                onClick={onDeposit}
                disabled={simulating || !clientId.trim() || !amount.trim()}
              >
                <ArrowDownCircle className="h-4 w-4" />
                {simulating ? 'Processing...' : 'Simulate Deposit'}
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <ArrowUpCircle className="h-5 w-5 text-red-600" />
              Direct Simulate Withdrawal
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <p className="text-sm text-gray-500">
                Uses the same Client ID, Amount, Currency and Reference fields from the left panel.
              </p>
              <Button
                className="w-full flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700"
                onClick={onWithdraw}
                disabled={simulating || !clientId.trim() || !amount.trim()}
              >
                <ArrowUpCircle className="h-4 w-4" />
                {simulating ? 'Processing...' : 'Simulate Withdrawal'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Shared UI
// ---------------------------------------------------------------------------

function Modal({
  title,
  onClose,
  children,
}: {
  title: string
  onClose: () => void
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold mb-4">{title}</h2>
        {children}
      </div>
    </div>
  )
}

function Field({
  label,
  required,
  children,
}: {
  label: string
  required?: boolean
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
        {required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  )
}

function AccountFormModal({
  title,
  providers,
  providerId,
  setProviderId,
  currency,
  setCurrency,
  iban,
  setIban,
  bic,
  setBic,
  holderName,
  setHolderName,
  submitting,
  onSubmit,
  onClose,
}: {
  title: string
  providers: Provider[]
  providerId: string
  setProviderId: (v: string) => void
  currency: string
  setCurrency: (v: string) => void
  iban: string
  setIban: (v: string) => void
  bic: string
  setBic: (v: string) => void
  holderName: string
  setHolderName: (v: string) => void
  submitting: boolean
  onSubmit: () => void
  onClose: () => void
}) {
  return (
    <Modal title={title} onClose={onClose}>
      <div className="space-y-4">
        <Field label="Provider" required>
          <select
            value={providerId}
            onChange={(e) => setProviderId(e.target.value)}
            className="w-full rounded-md border px-3 py-2 text-sm"
          >
            <option value="">Select provider...</option>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Account Holder Name" required>
          <Input
            value={holderName}
            onChange={(e) => setHolderName(e.target.value)}
            placeholder="John Doe / Vancelian SA"
          />
        </Field>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Currency">
            <Input value={currency} onChange={(e) => setCurrency(e.target.value)} />
          </Field>
          <Field label="IBAN">
            <Input value={iban} onChange={(e) => setIban(e.target.value)} placeholder="DE123..." />
          </Field>
        </div>
        <Field label="BIC">
          <Input value={bic} onChange={(e) => setBic(e.target.value)} placeholder="MODLXXXX" />
        </Field>
      </div>
      <div className="flex justify-end gap-3 mt-6">
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button onClick={onSubmit} disabled={submitting || !providerId || !holderName.trim()}>
          {submitting ? 'Creating...' : 'Create'}
        </Button>
      </div>
    </Modal>
  )
}


// ==========================================================================
// CryptoCustodyTab
// ==========================================================================

interface CryptoAccount {
  id: string
  type?: string
  account_type?: string
  label: string
  asset: string
  provider: string
  balance: string
  status: string
  actual_balance?: string | null
  expected_balance?: string | null
  mismatch?: string | null
  updated_from_provider_at?: string | null
}

interface CryptoMovement {
  date: string | null
  kind: string
  direction: string
  amount: string
  asset: string
  status: string
  reason: string
  external_reference: string | null
  client_id?: string
}

function CryptoCustodyTab() {
  const [accounts, setAccounts] = useState<CryptoAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [movements, setMovements] = useState<CryptoMovement[]>([])
  const [loadingMvts, setLoadingMvts] = useState(false)
  const [bootstrapLoading, setBootstrapLoading] = useState(false)

  const fetchAccounts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/admin/exchange/crypto-custody')
      if (!res.ok) throw new Error()
      const data = await res.json()
      setAccounts(data.accounts || [])
    } catch {
      /* ignore */
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchHistory = useCallback(async (accountId: string) => {
    setLoadingMvts(true)
    try {
      const res = await fetch(`/api/admin/exchange/crypto-custody?account_id=${accountId}`)
      if (!res.ok) throw new Error()
      const data = await res.json()
      setMovements(data.movements || [])
    } catch {
      setMovements([])
    } finally {
      setLoadingMvts(false)
    }
  }, [])

  useEffect(() => { fetchAccounts() }, [fetchAccounts])

  useEffect(() => {
    if (selectedId) fetchHistory(selectedId)
  }, [selectedId, fetchHistory])

  const handleBootstrap = useCallback(async () => {
    setBootstrapLoading(true)
    try {
      const res = await fetch('/api/admin/exchange/crypto-custody/bootstrap', { method: 'POST' })
      if (res.ok) await fetchAccounts()
    } finally {
      setBootstrapLoading(false)
    }
  }, [fetchAccounts])

  const selected = accounts.find(a => a.id === selectedId)
  const settlements = accounts.filter(a => (a.type === 'crypto_settlement_wallet' || a.account_type === 'settlement_wallet'))
  const allAccounts = accounts

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <RefreshCw className="h-5 w-5 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Bootstrap + Settlement Wallet Cards */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-500">Settlement Wallets — Vancelian</h3>
          <Button
            variant="outline"
            size="sm"
            onClick={handleBootstrap}
            disabled={bootstrapLoading}
          >
            {bootstrapLoading ? '…' : 'Bootstrap comptes'}
          </Button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {settlements.map(w => {
            const hasMismatch = w.mismatch != null && parseFloat(String(w.mismatch)) !== 0
            return (
              <Card
                key={w.id}
                className={`cursor-pointer transition-colors ${hasMismatch ? 'border-amber-300 hover:border-amber-400' : 'hover:border-indigo-300'}`}
                onClick={() => setSelectedId(w.id)}
              >
                <CardContent className="pt-4 pb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded">
                      {w.asset}
                    </span>
                    {hasMismatch && (
                      <span className="text-xs font-medium text-amber-700 bg-amber-100 px-1.5 py-0.5 rounded">
                        Écart
                      </span>
                    )}
                  </div>
                  <p className="font-mono text-sm font-semibold">{w.actual_balance ?? w.balance}</p>
                  {w.expected_balance != null && (
                    <p className="text-xs text-gray-500 mt-0.5">Attendu: {w.expected_balance}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">Settlement Wallet</p>
                </CardContent>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Split View */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Left Panel — Account List */}
        <div className="lg:col-span-2 space-y-1">
          <h3 className="text-sm font-semibold text-gray-500 mb-2">Comptes crypto techniques</h3>
          {allAccounts.map(a => {
            const isPool = a.type === 'crypto_clients_pool' || a.account_type === 'clients_pool'
            return (
              <div
                key={a.id}
                onClick={() => setSelectedId(a.id)}
                className={`flex items-center justify-between px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                  selectedId === a.id ? 'bg-indigo-50 border border-indigo-200' : 'hover:bg-gray-50 border border-transparent'
                }`}
              >
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${isPool ? 'bg-blue-500' : 'bg-indigo-500'}`} />
                  <span className="font-medium">{a.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs">{a.balance}</span>
                  <ChevronRight className="h-3 w-3 text-gray-300" />
                </div>
              </div>
            )
          })}
        </div>

        {/* Right Panel — Detail + History */}
        <div className="lg:col-span-3">
          {selected ? (
            <div className="space-y-4">
              {/* Account detail */}
              <Card>
                <CardContent className="pt-4 space-y-2 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Type</span><span>{selected.type === 'crypto_clients_pool' || selected.account_type === 'clients_pool' ? 'Clients Pool' : 'Settlement Wallet'}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Asset</span><span className="font-semibold">{selected.asset}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Provider</span><span>{selected.provider}</span></div>
                  <div className="flex justify-between"><span className="text-gray-500">Actual balance</span><span className="font-mono font-semibold">{selected.actual_balance ?? selected.balance} {selected.asset}</span></div>
                  {selected.expected_balance != null && (
                    <div className="flex justify-between"><span className="text-gray-500">Expected balance</span><span className="font-mono">{selected.expected_balance} {selected.asset}</span></div>
                  )}
                  {selected.mismatch != null && parseFloat(String(selected.mismatch)) !== 0 && (
                    <div className="flex justify-between items-center">
                      <span className="text-gray-500">Écart (actual − expected)</span>
                      <span className="font-mono font-medium text-amber-700 bg-amber-50 px-2 py-0.5 rounded">{selected.mismatch} {selected.asset}</span>
                    </div>
                  )}
                  {selected.updated_from_provider_at != null && (
                    <div className="flex justify-between"><span className="text-gray-500">Mis à jour provider</span><span className="text-xs text-gray-500">{selected.updated_from_provider_at}</span></div>
                  )}
                  <div className="flex justify-between"><span className="text-gray-500">Status</span><span className="text-green-600">{selected.status}</span></div>
                </CardContent>
              </Card>

              {/* Movement History */}
              <div>
                <h4 className="text-sm font-semibold text-gray-500 mb-2">Historique des mouvements</h4>
                {loadingMvts ? (
                  <div className="flex items-center justify-center h-20">
                    <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />
                  </div>
                ) : movements.length === 0 ? (
                  <p className="text-sm text-gray-400 text-center py-8">Aucun mouvement pour ce compte</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b text-gray-500 text-xs">
                          <th className="text-left py-2 pr-2">Date</th>
                          <th className="text-left py-2 pr-2">Kind</th>
                          <th className="text-left py-2 pr-2">Direction</th>
                          <th className="text-right py-2 pr-2">Amount</th>
                          <th className="text-left py-2 pr-2">Status</th>
                          <th className="text-left py-2">Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {movements.map((m, i) => (
                          <tr key={i} className="border-b border-gray-50 hover:bg-gray-50/50">
                            <td className="py-2 pr-2 text-xs text-gray-600">{m.date ? formatDate(m.date) : '—'}</td>
                            <td className="py-2 pr-2 font-mono text-xs">{m.kind}</td>
                            <td className="py-2 pr-2">
                              <span className={m.direction === 'credit' ? 'text-green-700' : 'text-gray-600'}>
                                {m.direction === 'credit' ? '+' : '−'}
                              </span>
                            </td>
                            <td className="py-2 pr-2 text-right font-mono">
                              <span className={m.direction === 'credit' ? 'text-green-700' : 'text-gray-600'}>
                                {m.amount} {m.asset}
                              </span>
                            </td>
                            <td className="py-2 pr-2">
                              <span className={`text-xs px-1.5 py-0.5 rounded ${
                                m.status === 'completed' || m.status === 'settled' ? 'bg-green-100 text-green-700' :
                                m.status === 'pending' ? 'bg-yellow-100 text-yellow-700' :
                                'bg-gray-100 text-gray-600'
                              }`}>
                                {m.status}
                              </span>
                            </td>
                            <td className="py-2 text-xs text-gray-500">{m.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center h-48 text-gray-400 text-sm border border-dashed rounded-lg">
              Sélectionnez un compte pour voir les détails
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
