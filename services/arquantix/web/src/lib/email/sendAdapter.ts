import type { RenderedEmail } from './types'

export interface OutboundEmailRecipient {
  email: string
  name?: string
}

export interface OutboundEmail extends RenderedEmail {
  to: OutboundEmailRecipient | OutboundEmailRecipient[]
  from: OutboundEmailRecipient
  replyTo?: OutboundEmailRecipient
  bcc?: OutboundEmailRecipient[]
  /** Identifiant logique de la campagne / lot (utile pour traçabilité). */
  tag?: string
}

export interface SendResult {
  ok: boolean
  /** Identifiant fourni par le provider (si applicable). */
  providerMessageId?: string
  /** Provider effectivement utilisé (`noop`, `console`, `ses`…). */
  provider: string
  error?: string
}

export interface EmailSendAdapter {
  readonly name: string
  send(email: OutboundEmail): Promise<SendResult>
}

/* ------------------------------------------------------------------ */
/* Implémentations actuelles (no-op + console)                         */
/* ------------------------------------------------------------------ */

/**
 * Adaptateur **no-op** : enregistre un succès sans envoyer. Utilisé par défaut
 * tant qu’aucun ESP n’est configuré (pas de risque d’envoi accidentel).
 */
export const noopSendAdapter: EmailSendAdapter = {
  name: 'noop',
  async send(_email) {
    return { ok: true, provider: 'noop' }
  },
}

/**
 * Adaptateur **console** : log structuré (utile en dev pour vérifier le
 * pipeline complet sans connecter de provider).
 */
export const consoleSendAdapter: EmailSendAdapter = {
  name: 'console',
  async send(email) {
    const recipients = Array.isArray(email.to)
      ? email.to.map((r) => r.email).join(', ')
      : email.to.email
    // eslint-disable-next-line no-console
    console.info('[email:send:console]', {
      template: email.templateId,
      locale: email.locale,
      to: recipients,
      from: email.from.email,
      subject: email.subject,
      htmlBytes: Buffer.byteLength(email.html, 'utf8'),
      textBytes: Buffer.byteLength(email.text, 'utf8'),
      tag: email.tag,
    })
    return { ok: true, provider: 'console' }
  },
}

/**
 * Sélectionne l’adaptateur via `EMAIL_SEND_ADAPTER` :
 * - `noop` (défaut) : ne fait rien.
 * - `console` : log seulement.
 *
 * Tout futur provider (`ses`, `resend`, etc.) doit être enregistré ici.
 */
export function getEmailSendAdapter(): EmailSendAdapter {
  const id = (process.env.EMAIL_SEND_ADAPTER || 'noop').toLowerCase()
  switch (id) {
    case 'console':
      return consoleSendAdapter
    case 'noop':
    default:
      return noopSendAdapter
  }
}
