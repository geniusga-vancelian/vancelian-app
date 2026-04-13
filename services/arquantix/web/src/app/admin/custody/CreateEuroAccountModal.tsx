'use client'

import { useCallback, useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { Check, Copy, Loader2 } from 'lucide-react'

/** Aligné sur GET /api/admin/customers/search — téléphone + person_id ; e-mail optionnel uniquement si collecté. */
export type CustodySearchRow = {
  person_id: string
  phone_e164: string | null
  optional_email: string | null
  display_name: string | null
  has_euro_account: boolean
  pe_client_id: string | null
}

type CreatedAccount = {
  iban: string | null
  bic: string | null
  id: string
  account_holder_name: string
}

type CreateResponse = {
  message?: string
  account: CreatedAccount
}

export function CreateEuroAccountModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState<CustodySearchRow[]>([])
  const [selected, setSelected] = useState<CustodySearchRow | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [success, setSuccess] = useState<CreateResponse | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 300)
    return () => clearTimeout(t)
  }, [query])

  const runSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([])
      return
    }
    setLoading(true)
    try {
      const res = await fetch(
        `/api/admin/customers/search?q=${encodeURIComponent(q)}&limit=20`,
      )
      if (!res.ok) throw new Error('Search failed')
      const data = await res.json()
      setResults(data.items ?? [])
    } catch {
      setResults([])
      toastError('Recherche impossible')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void runSearch(debounced)
  }, [debounced, runSearch])

  const handleCreate = async () => {
    if (!selected || selected.has_euro_account) return
    setSubmitting(true)
    try {
      const res = await fetch('/api/admin/custody/accounts/client/simple-create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ person_id: selected.person_id }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(
          typeof data.detail === 'string' ? data.detail : data.error || 'Création impossible',
        )
      }
      setSuccess(data as CreateResponse)
      toastSuccess(data.message || 'Compte EUR créé')
      onCreated()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setSubmitting(false)
    }
  }

  const copyIban = async () => {
    const iban = success?.account?.iban
    if (!iban) return
    await navigator.clipboard.writeText(iban)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  if (success?.account) {
    const a = success.account
    return (
      <div className="space-y-4">
        <p className="text-green-700 font-medium">
          {success.message || 'Compte créé avec succès'}
        </p>
        <div className="rounded-md bg-gray-50 p-3 text-sm space-y-2">
          <div>
            <span className="text-gray-500">IBAN</span>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="font-mono break-all">{a.iban ?? '—'}</span>
              {a.iban ? (
                <button
                  type="button"
                  onClick={() => void copyIban()}
                  className="text-gray-500 hover:text-gray-800"
                  title="Copier"
                >
                  {copied ? <Check className="h-4 w-4 text-green-600" /> : <Copy className="h-4 w-4" />}
                </button>
              ) : null}
            </div>
          </div>
          <div>
            <span className="text-gray-500">BIC</span>
            <p className="font-mono">{a.bic ?? '—'}</p>
          </div>
          <div>
            <span className="text-gray-500">Titulaire</span>
            <p>{a.account_holder_name}</p>
          </div>
          <div>
            <span className="text-gray-500">ID compte</span>
            <p className="font-mono text-xs break-all">{a.id}</p>
          </div>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onClose}>
            Fermer
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Recherche par téléphone (E.164), identifiant person (UUID) ou nom. La création EUR utilise uniquement le{' '}
        <span className="font-medium">person_id</span> — IBAN/BIC générés côté serveur.
      </p>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Recherche</label>
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ex. +33…, UUID person, ou partie du nom"
          autoFocus
        />
      </div>

      <div className="border rounded-md max-h-56 overflow-y-auto divide-y">
        {loading ? (
          <div className="flex justify-center py-6 text-gray-400">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : results.length === 0 ? (
          <p className="text-sm text-gray-500 py-6 text-center">
            {debounced.length < 2 ? 'Saisissez au moins 2 caractères.' : 'Aucun résultat.'}
          </p>
        ) : (
          results.map((row) => {
            const active = selected?.person_id === row.person_id
            return (
              <button
                key={row.person_id}
                type="button"
                onClick={() => setSelected(row)}
                className={`w-full text-left px-3 py-2.5 text-sm hover:bg-gray-50 ${
                  active ? 'bg-blue-50 border-l-2 border-l-blue-600' : ''
                }`}
              >
                <div className="font-medium text-gray-900">{row.phone_e164 ?? '—'}</div>
                <div className="font-mono text-[11px] text-gray-500 mt-0.5 break-all">
                  {row.person_id}
                </div>
                {row.display_name ? (
                  <div className="text-xs text-gray-600 mt-1">{row.display_name}</div>
                ) : null}
                {row.optional_email ? (
                  <div className="text-xs text-gray-600 mt-1 break-all">{row.optional_email}</div>
                ) : null}
                <div className="mt-1.5 space-y-0.5">
                  {row.has_euro_account ? (
                    <span className="inline-block text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded text-[11px]">
                      Compte EUR déjà présent
                    </span>
                  ) : !row.pe_client_id ? (
                    <span className="inline-block text-red-600 text-[11px]">
                      Pas de client PE lié — création impossible
                    </span>
                  ) : null}
                </div>
              </button>
            )
          })
        )}
      </div>

      <div className="flex justify-end gap-2 pt-2">
        <Button variant="outline" onClick={onClose} disabled={submitting}>
          Annuler
        </Button>
        <Button
          onClick={() => void handleCreate()}
          disabled={
            submitting ||
            !selected ||
            selected.has_euro_account ||
            !selected.pe_client_id
          }
        >
          {submitting ? 'Création…' : 'Create Euro Account'}
        </Button>
      </div>
    </div>
  )
}
