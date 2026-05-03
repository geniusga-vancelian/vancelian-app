import { NavMenuLinkEditClient } from './NavMenuLinkEditClient'

/**
 * Page serveur : transmet `itemId` au client pour éviter un `useParams()` vide
 * au premier rendu après navigation (écran blanc).
 */
export default function NavMenuLinkPage({ params }: { params: { itemId: string } }) {
  const raw = params?.itemId
  const itemId = typeof raw === 'string' ? raw : Array.isArray(raw) ? raw[0] ?? '' : ''
  return <NavMenuLinkEditClient itemId={itemId} />
}
