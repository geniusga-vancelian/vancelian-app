'use client'

import * as React from 'react'
import { formatPrivyConfigError } from '@/lib/portal/privyConfigErrors'

type Props = {
  children: React.ReactNode
}

type State = {
  message: string | null
}

export class PortalPrivyErrorBoundary extends React.Component<Props, State> {
  state: State = { message: null }

  static getDerivedStateFromError(error: unknown): State {
    return {
      message: formatPrivyConfigError(error, 'Authentication failed to initialize.'),
    }
  }

  componentDidCatch(error: unknown) {
    console.error('[portal/privy]', error)
  }

  render() {
    if (this.state.message) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-v-bg px-6">
          <div className="max-w-lg rounded-v-card border border-v-fg-10 bg-white p-8 shadow-v-subtle">
            <h1 className="m-0 font-ui text-[20px] font-semibold text-v-fg">
              Configuration Privy requise
            </h1>
            <p className="mt-4 mb-0 font-ui text-[15px] leading-relaxed text-v-fg-body">
              {this.state.message}
            </p>
            <p className="mt-4 mb-0 font-ui text-[13px] leading-relaxed text-v-fg-muted">
              Vérifiez aussi{' '}
              <code className="rounded bg-v-fg-05 px-1">GET /api/portal/health</code> :{' '}
              <code className="rounded bg-v-fg-05 px-1">privyWebClientIdConfigured</code> doit être{' '}
              <strong>true</strong> pour le portail web en local.
            </p>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
