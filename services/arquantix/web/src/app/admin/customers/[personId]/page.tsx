'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { ArrowLeft, FileText, Info, RefreshCw, Snowflake, Sun, Trash2 } from 'lucide-react'
import { AssistanceConversationsSection } from '@/components/admin/AssistanceConversationsSection'

interface SessionSummary {
  session_id?: string
  status?: string
  progress_percent?: number
  flow_id?: string
  flow_version?: number
  current_step_key?: string
  current_screen_key?: string
  updated_at?: string
}

interface Detail {
  identity: Record<string, unknown>
  registration: { latest_session?: SessionSummary | null; availability?: string }
  registration_progress: {
    stage: string
    label: string
    completion_ratio: number
    completed_steps: string[]
    missing_steps: string[]
    source_notes: string
    legacy_stage?: string
    foundation?: Record<string, unknown>
    registration?: Record<string, unknown>
    lifecycle?: Record<string, unknown>
    session_snapshot?: Record<string, unknown> | null
  }
  kyc: Record<string, unknown>
  wallet: Record<string, unknown>
  transactions: { message: string }
  security: { message: string }
  debug: { person_profile_keys: string[]; collected_slugs_sample: string[]; hints: string }
  raw_profile_excerpt?: Record<string, unknown> | null
}

function Section({
  title,
  id,
  children,
}: {
  title: string
  id?: string
  children: React.ReactNode
}) {
  return (
    <Card id={id} className="border-slate-200 scroll-mt-4 shadow-sm">
      <CardHeader className="border-b border-slate-100 bg-slate-50/80 py-3">
        <CardTitle className="text-sm font-semibold tracking-wide text-slate-800 uppercase">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-4 text-sm text-slate-700">{children}</CardContent>
    </Card>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-1 gap-1 border-b border-slate-100 py-2 sm:grid-cols-[200px_1fr] sm:gap-4">
      <dt className="text-slate-500 font-medium">{label}</dt>
      <dd className="text-slate-900 break-words">{value ?? '—'}</dd>
    </div>
  )
}

function PlaceholderBlock({ title, message }: { title: string; message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50/50 px-4 py-6 text-center">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-2 text-sm text-slate-600">{message}</p>
    </div>
  )
}

export default function CustomerDetailPage() {
  const params = useParams()
  const router = useRouter()
  const personId = (params?.personId as string | undefined) ?? ''
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<Detail | null>(null)
  const [freezeLoading, setFreezeLoading] = useState(false)
  const [unfreezeLoading, setUnfreezeLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [docLoading, setDocLoading] = useState<null | 'month' | 'iban' | 'latest'>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/admin/customers/${encodeURIComponent(personId)}`)
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (res.status === 404) {
        setData(null)
        return
      }
      if (!res.ok) throw new Error('load failed')
      const json: Detail = await res.json()
      setData(json)
    } catch {
      toastError('Impossible de charger la fiche client')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [personId, router])

  useEffect(() => {
    load()
  }, [load])

  async function parseErrorMessage(res: Response): Promise<string> {
    try {
      const j = (await res.json()) as { detail?: unknown }
      const d = j.detail
      if (typeof d === 'string') return d
      if (Array.isArray(d) && d[0] && typeof (d[0] as { msg?: string }).msg === 'string') {
        return (d[0] as { msg: string }).msg
      }
    } catch {
      /* ignore */
    }
    return `Erreur ${res.status}`
  }

  const handleFreeze = async () => {
    setFreezeLoading(true)
    try {
      const res = await fetch(`/api/admin/customers/${encodeURIComponent(personId)}/freeze`, {
        method: 'POST',
      })
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        toastError(await parseErrorMessage(res))
        return
      }
      toastSuccess('Connexion gelée pour ce client.')
      await load()
    } catch {
      toastError('Action impossible')
    } finally {
      setFreezeLoading(false)
    }
  }

  const handleUnfreeze = async () => {
    setUnfreezeLoading(true)
    try {
      const res = await fetch(`/api/admin/customers/${encodeURIComponent(personId)}/unfreeze`, {
        method: 'POST',
      })
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        toastError(await parseErrorMessage(res))
        return
      }
      toastSuccess('Connexion réactivée pour ce client.')
      await load()
    } catch {
      toastError('Action impossible')
    } finally {
      setUnfreezeLoading(false)
    }
  }

  const openPdfInNewTab = (relativePath: string) => {
    const w = window.open(relativePath, '_blank', 'noopener,noreferrer')
    if (w == null) {
      toastError(
        'Impossible d’ouvrir un nouvel onglet. Autorisez les fenêtres pop-up pour ce site ou utilisez Télécharger.'
      )
    }
  }

  const downloadAdminPdf = async (
    kind: 'month' | 'iban' | 'latest',
    relativePath: string,
    filename: string
  ) => {
    setDocLoading(kind)
    try {
      const res = await fetch(relativePath)
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      const ct = res.headers.get('content-type') || ''
      if (!res.ok) {
        let msg = `Erreur ${res.status}`
        if (ct.includes('application/json')) {
          try {
            const j = (await res.json()) as { detail?: unknown }
            if (typeof j.detail === 'string') msg = j.detail
          } catch {
            /* ignore */
          }
        }
        toastError(msg)
        return
      }
      const blob = await res.blob()
      const href = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = href
      a.download = filename
      a.click()
      URL.revokeObjectURL(href)
      toastSuccess('Téléchargement lancé.')
    } catch {
      toastError('Téléchargement impossible.')
    } finally {
      setDocLoading(null)
    }
  }

  const handleDeleteConfirmed = async () => {
    setDeleteLoading(true)
    setShowDeleteConfirm(false)
    try {
      const res = await fetch(`/api/admin/customers/${encodeURIComponent(personId)}`, {
        method: 'DELETE',
      })
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        toastError(await parseErrorMessage(res))
        return
      }
      toastSuccess('Client supprimé définitivement.')
      router.push('/admin/customers')
    } catch {
      toastError('Suppression impossible')
    } finally {
      setDeleteLoading(false)
    }
  }

  if (loading && !data) {
    return (
      <div className="flex justify-center py-24">
        <RefreshCw className="h-8 w-8 animate-spin text-slate-400" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="max-w-lg">
        <Button variant="ghost" asChild className="mb-4 gap-2 text-slate-700">
          <Link href="/admin/customers">
            <ArrowLeft className="h-4 w-4" />
            Retour à la liste
          </Link>
        </Button>
        <p className="text-slate-600">Client introuvable ou non éligible.</p>
      </div>
    )
  }

  const id = data.identity as {
    person_id?: string
    pe_client_id?: string | null
    login_frozen?: boolean
    mobile?: string | null
    email?: string | null
    first_name?: string | null
    last_name?: string | null
    country_of_residence?: string | null
    jurisdiction?: string | null
    person_status?: string
    person_created_at?: string
    person_updated_at?: string
  }

  const adminDocsBase = `/api/admin/customers/${encodeURIComponent(personId)}/documents`
  const monthStatementPdfUrl = `${adminDocsBase}/month-statement.pdf`
  const ibanStatementPdfUrl = `${adminDocsBase}/iban-account-statement.pdf`
  const latestOperationPdfUrl = `${adminDocsBase}/latest-operation-statement.pdf`
  const latestOperationJsonUrl = `${adminDocsBase}/latest-operation.json`
  const latestOperationSamplePdfUrl = `${adminDocsBase}/latest-operation-statement.pdf?debug_sample=true`

  /** Même prérequis que l’API documents : compte investissement lié (données EUR + mouvements). */
  const walletSummary = data.wallet as { availability?: string; pe_client_id?: string | null }
  const hasInvestingAccountLinked =
    walletSummary.availability === 'available' ||
    Boolean(walletSummary.pe_client_id) ||
    Boolean(id.pe_client_id)
  const documentsBusy = docLoading !== null
  const documentsDisabled = !hasInvestingAccountLinked || documentsBusy
  const technicalPortfolioRef = id.pe_client_id ?? walletSummary.pe_client_id ?? null

  return (
    <div className="max-w-5xl space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Button variant="ghost" asChild className="-ml-2 mb-2 gap-2 text-slate-700">
            <Link href="/admin/customers">
              <ArrowLeft className="h-4 w-4" />
              Liste clients
            </Link>
          </Button>
          <h1 className="text-2xl font-semibold text-slate-900">Fiche client</h1>
          <p className="mt-1 font-mono text-xs text-slate-500">{String(id.person_id)}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="gap-2"
            onClick={() =>
              document.getElementById('customer-documents')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
            }
          >
            <FileText className="h-4 w-4" />
            Documents PDF
          </Button>
          <Button variant="outline" size="sm" onClick={() => load()} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </Button>
        </div>
      </div>

      <Card className="border-indigo-100 bg-gradient-to-br from-indigo-50/80 to-white shadow-sm">
        <CardContent className="flex flex-col gap-3 py-5 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-indigo-900/80">Progression d’inscription</p>
            <p className="mt-1 text-lg font-medium text-slate-900">{data.registration_progress.label}</p>
            <p className="text-sm text-slate-600 mt-1">
              {Math.round(data.registration_progress.completion_ratio * 100)}% — stade :{' '}
              <span className="font-mono text-xs">{data.registration_progress.stage}</span>
              {data.registration_progress.legacy_stage ? (
                <span className="ml-2 text-xs text-slate-500">
                  (legacy: {data.registration_progress.legacy_stage})
                </span>
              ) : null}
            </p>
          </div>
          <Badge className="bg-indigo-700 text-white hover:bg-indigo-700 self-start">
            Customer 360
          </Badge>
        </CardContent>
      </Card>

      <Section id="customer-documents" title="Documents PDF (support & conformité)">
        <p className="text-sm text-slate-600 mb-4">
          Même moteur que l’app mobile (<span className="font-mono text-xs">/api/app/*</span>). Relevé mensuel :{' '}
          <strong>mois calendaire en cours (UTC)</strong>. Dernière opération : dernière transaction{' '}
          <span className="font-mono text-xs">completed</span> (custody ou exchange).
        </p>
        {!hasInvestingAccountLinked ? (
          <Alert className="mb-4 border-amber-200 bg-amber-50/90 text-amber-950">
            <Info className="text-amber-800" />
            <AlertTitle>Compte investissement non associé</AlertTitle>
            <AlertDescription>
              Les relevés EUR, le relevé IBAN et les documents d’opération sont générés à partir du compte client
              investissement lié à ce profil. Tant qu’aucun tel compte n’est disponible, les boutons ci-dessous restent
              désactivés. Consultez la section « Portefeuille » pour l’état du lien.
            </AlertDescription>
          </Alert>
        ) : null}
        <div className="space-y-4">
          <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-900">Relevé du mois (EUR)</p>
              <p className="text-xs text-slate-500">Mois calendaire UTC</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="default"
                className="gap-2"
                disabled={documentsDisabled}
                onClick={() =>
                  downloadAdminPdf(
                    'month',
                    monthStatementPdfUrl,
                    `releve-euro-mois-${new Date().toISOString().slice(0, 7)}.pdf`
                  )
                }
              >
                <FileText className="h-4 w-4" />
                {docLoading === 'month' ? 'Génération…' : 'Télécharger'}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="text-slate-800"
                disabled={documentsDisabled}
                onClick={() => openPdfInNewTab(monthStatementPdfUrl)}
              >
                Aperçu
              </Button>
            </div>
          </div>
          <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-900">Relevé compte IBAN</p>
              <p className="text-xs text-slate-500">Fenêtre récente (même pipeline que l’app)</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="button"
                variant="default"
                className="gap-2"
                disabled={documentsDisabled}
                onClick={() =>
                  downloadAdminPdf('iban', ibanStatementPdfUrl, 'releve-compte-eur-iban.pdf')
                }
              >
                <FileText className="h-4 w-4" />
                {docLoading === 'iban' ? 'Génération…' : 'Télécharger'}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="text-slate-800"
                disabled={documentsDisabled}
                onClick={() => openPdfInNewTab(ibanStatementPdfUrl)}
              >
                Aperçu
              </Button>
            </div>
          </div>
          <div className="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-slate-900">Dernière opération</p>
              <p className="text-xs text-slate-500">PDF, JSON debug, ou exemple sans données réelles</p>
            </div>
            <div className="flex flex-wrap gap-2 justify-end">
              <Button
                type="button"
                variant="default"
                className="gap-2"
                disabled={documentsDisabled}
                onClick={() =>
                  downloadAdminPdf('latest', latestOperationPdfUrl, 'releve-derniere-operation.pdf')
                }
              >
                <FileText className="h-4 w-4" />
                {docLoading === 'latest' ? 'Génération…' : 'Télécharger'}
              </Button>
              <Button
                type="button"
                variant="outline"
                className="text-slate-800"
                disabled={documentsDisabled}
                onClick={() => openPdfInNewTab(latestOperationPdfUrl)}
              >
                Aperçu
              </Button>
              <Button
                type="button"
                variant="outline"
                className="text-slate-800"
                disabled={documentsDisabled}
                onClick={() => openPdfInNewTab(latestOperationJsonUrl)}
              >
                Voir le JSON
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="text-slate-800"
                disabled={documentsDisabled}
                onClick={() => openPdfInNewTab(latestOperationSamplePdfUrl)}
              >
                Aperçu (exemple)
              </Button>
            </div>
          </div>
        </div>
      </Section>

      <Section title="Identité & profil">
        <dl>
          <Row label="ID personne" value={id.person_id} />
          <Row
            label="Connexion"
            value={
              id.login_frozen ? (
                <Badge variant="destructive" className="font-normal">
                  Gelée — ne peut pas se connecter
                </Badge>
              ) : (
                <span className="text-emerald-800">Active</span>
              )
            }
          />
          <Row label="Mobile" value={id.mobile} />
          <Row label="E-mail" value={id.email} />
          <Row label="Prénom" value={id.first_name} />
          <Row label="Nom" value={id.last_name} />
          <Row label="Pays de résidence" value={id.country_of_residence} />
          <Row label="Juridiction" value={id.jurisdiction} />
          <Row label="Statut personne" value={id.person_status} />
          <Row label="Créé le" value={id.person_created_at} />
          <Row label="Mis à jour" value={id.person_updated_at} />
        </dl>
        <div className="mt-4 rounded-lg border border-dashed border-slate-200 bg-slate-50/90 px-3 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Références techniques (support)
          </p>
          <dl>
            <Row
              label="Réf. portefeuille (interne)"
              value={
                technicalPortfolioRef ? (
                  <span className="font-mono text-xs break-all">{technicalPortfolioRef}</span>
                ) : (
                  <span className="text-slate-500">—</span>
                )
              }
            />
          </dl>
        </div>
      </Section>

      <Section title="Actions compte">
        <p className="text-sm text-slate-600 mb-4">
          <strong>Geler</strong> : le client ne peut plus s’authentifier (sessions, OTP, passkeys) — les données
          restent en base. <strong>Supprimer</strong> : efface l’identité, l’historique d’activité lié et les
          comptes d’authentification (y compris mobile) — irréversible.
        </p>
        <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
          <Button
            type="button"
            variant="secondary"
            className="gap-2"
            disabled={freezeLoading || Boolean(id.login_frozen)}
            onClick={handleFreeze}
          >
            <Snowflake className="h-4 w-4" />
            {freezeLoading ? 'Gel…' : 'Geler la connexion'}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="gap-2"
            disabled={unfreezeLoading || !id.login_frozen}
            onClick={handleUnfreeze}
          >
            <Sun className="h-4 w-4" />
            {unfreezeLoading ? 'Dégel…' : 'Dégeler la connexion'}
          </Button>
          <Button
            type="button"
            variant="destructive"
            className="gap-2"
            disabled={deleteLoading}
            onClick={() => setShowDeleteConfirm(true)}
          >
            <Trash2 className="h-4 w-4" />
            {deleteLoading ? 'Suppression…' : 'Supprimer définitivement'}
          </Button>
        </div>
      </Section>

      <AlertDialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Supprimer ce client ?</AlertDialogTitle>
            <AlertDialogDescription className="text-left space-y-2">
              <span className="block">
                Cette action supprime définitivement la personne, ses données d’inscription, l’activité
                portefeuille associée et les comptes d’authentification (web et mobile). Il n’y a pas de retour
                arrière.
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Annuler</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirmed}
              className="bg-red-600 hover:bg-red-700 focus:ring-red-600"
            >
              Supprimer définitivement
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Section title="Parcours d’inscription">
        {data.registration.availability === 'placeholder' || !data.registration.latest_session ? (
          <PlaceholderBlock title="Session" message="Aucune session d’inscription enregistrée pour cette personne." />
        ) : (
          <dl>
            <Row label="ID session" value={data.registration.latest_session.session_id} />
            <Row label="Statut" value={data.registration.latest_session.status} />
            <Row label="Progression %" value={data.registration.latest_session.progress_percent} />
            <Row label="Flow ID" value={data.registration.latest_session.flow_id} />
            <Row label="Flow version" value={data.registration.latest_session.flow_version} />
            <Row label="Étape courante (key)" value={data.registration.latest_session.current_step_key} />
            <Row label="Écran courant (key)" value={data.registration.latest_session.current_screen_key} />
            <Row label="Dernière maj session" value={data.registration.latest_session.updated_at} />
          </dl>
        )}
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Étapes complétées</p>
            <ul className="list-disc pl-5 text-slate-800">
              {data.registration_progress.completed_steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-500 uppercase mb-1">Manquantes / à finaliser</p>
            <ul className="list-disc pl-5 text-slate-800">
              {data.registration_progress.missing_steps.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </div>
        </div>
        <p className="mt-3 text-xs text-slate-500 font-mono break-all">{data.registration_progress.source_notes}</p>
        {(data.registration_progress.foundation ||
          data.registration_progress.registration ||
          data.registration_progress.lifecycle) && (
          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {data.registration_progress.foundation && (
              <div className="rounded-lg border border-slate-100 bg-white p-3">
                <p className="text-xs font-semibold uppercase text-slate-500 mb-2">Fondation</p>
                <pre className="text-[11px] text-slate-800 whitespace-pre-wrap break-words">
                  {JSON.stringify(data.registration_progress.foundation, null, 2)}
                </pre>
              </div>
            )}
            {data.registration_progress.registration && (
              <div className="rounded-lg border border-slate-100 bg-white p-3">
                <p className="text-xs font-semibold uppercase text-slate-500 mb-2">Registration</p>
                <pre className="text-[11px] text-slate-800 whitespace-pre-wrap break-words">
                  {JSON.stringify(data.registration_progress.registration, null, 2)}
                </pre>
              </div>
            )}
            {data.registration_progress.lifecycle && (
              <div className="rounded-lg border border-slate-100 bg-white p-3">
                <p className="text-xs font-semibold uppercase text-slate-500 mb-2">Lifecycle</p>
                <pre className="text-[11px] text-slate-800 whitespace-pre-wrap break-words">
                  {JSON.stringify(data.registration_progress.lifecycle, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </Section>

      <Section title="KYC & conformité">
        <dl>
          <Row label="Statut KYC (person)" value={String(data.kyc.kyc_status ?? '—')} />
          <Row label="Notes" value={String(data.kyc.notes ?? '')} />
        </dl>
        <PlaceholderBlock
          title="Extension"
          message="Documents, décisions AML, scores : à brancher sur les modules compliance existants."
        />
      </Section>

      <Section title="Portefeuille">
        {data.wallet.availability === 'available' ? (
          <dl>
            <Row label="E-mail (compte investissement)" value={String(data.wallet.email ?? '')} />
            <Row label="Statut" value={String(data.wallet.client_status ?? '')} />
            <Row label="KYC" value={String(data.wallet.kyc_status ?? '')} />
            <Row label="Devise de référence" value={String(data.wallet.reference_currency ?? '')} />
          </dl>
        ) : (
          <PlaceholderBlock
            title="Aucun compte investissement"
            message="Aucun portefeuille client n’est encore associé à cette personne — les relevés EUR et documents basés sur les mouvements restent indisponibles jusqu’à ce lien."
          />
        )}
      </Section>

      <Section title="Transactions & mouvements">
        <PlaceholderBlock title="Not available yet" message={data.transactions.message} />
      </Section>

      <Section title="Sécurité & sessions">
        <PlaceholderBlock title="Not available yet" message={data.security.message} />
      </Section>

      <AssistanceConversationsSection personId={personId} />

      <Section title="Support & technique">
        <p className="text-xs text-slate-600 mb-2">{data.debug.hints}</p>
        <Row label="Clés profile_json" value={data.debug.person_profile_keys.join(', ') || '—'} />
        <Row label="Échantillon slugs collectés" value={data.debug.collected_slugs_sample.join(', ') || '—'} />
        {data.raw_profile_excerpt && Object.keys(data.raw_profile_excerpt).length > 0 ? (
          <div className="mt-4">
            <p className="text-xs font-semibold text-slate-500 uppercase mb-2">Aperçu champs collectés (limité)</p>
            <pre className="text-xs bg-slate-900 text-slate-100 rounded-lg p-4 overflow-x-auto max-h-64">
              {JSON.stringify(data.raw_profile_excerpt, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="text-sm text-slate-500 mt-2">Aucun extrait collecté à afficher.</p>
        )}
      </Section>
    </div>
  )
}
