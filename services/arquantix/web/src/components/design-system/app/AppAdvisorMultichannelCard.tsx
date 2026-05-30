import { KalaiIcon } from '@/components/ui/KalaiIcon'

type Channel = {
  id: string
  title: string
  subtitle: string
  icon: string
  online?: boolean
}

const CHANNELS: Channel[] = [
  {
    id: 'chat',
    title: 'Chat online',
    subtitle: 'Instant reply',
    icon: 'support',
    online: true,
  },
  {
    id: 'call',
    title: 'Call us',
    subtitle: '+33 1 86 95 47 91 · toll-free',
    icon: 'phone',
  },
  {
    id: 'mail',
    title: 'Send an email',
    subtitle: 'advisor@vancelian.com',
    icon: 'mail',
  },
]

/** Advisor channels — handoff `.adv-B` (comp 87 · variant B). */
export function AppAdvisorMultichannelCard() {
  return (
    <div className="v-card adv-B">
      <ul className="adv-B__rows">
        {CHANNELS.map((channel, index) => (
          <li key={channel.id}>
            <button type="button" className="adv-B__row">
              <span className="adv-B__row-ic" aria-hidden="true">
                <KalaiIcon name={channel.icon} size={20} />
              </span>
              <span className="adv-B__row-body">
                <span className="adv-B__row-title">{channel.title}</span>
                <span className="adv-B__row-sub">{channel.subtitle}</span>
              </span>
              {channel.online ? (
                <span className="adv-B__row-status" aria-label="Online" />
              ) : null}
              <KalaiIcon name="chevron-right" size={16} className="adv-B__row-chv" aria-hidden />
            </button>
            {index < CHANNELS.length - 1 ? <hr className="hr-thin" /> : null}
          </li>
        ))}
      </ul>
    </div>
  )
}
