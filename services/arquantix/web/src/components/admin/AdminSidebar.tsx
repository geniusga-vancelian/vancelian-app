'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  LayoutDashboard,
  FileText,
  Image,
  Settings,
  BookOpen,
  BookMarked,
  FileCheck,
  ListOrdered,
  Mail,
  MessageSquare,
  FolderKanban,
  Cpu,
  Shield,
  HelpCircle,
  GraduationCap,
  Database,
  Package,
  TrendingUp,
  DollarSign,
  Globe,
  Tags,
  Smartphone,
  Archive,
  Sparkles,
  Palette,
  Coins,
  UserCircle2,
  Landmark,
  ArrowRightLeft,
  NotebookTabs,
  Layers,
  Wand2,
  Bot,
  MousePointerClick,
  Activity,
} from 'lucide-react'

interface NavItem {
  label: string
  href: string
  icon: React.ElementType
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { label: 'Design System', href: '/admin/design-system', icon: Palette },
  { label: 'Pages', href: '/admin/pages', icon: FileText },
  {
    label: 'Gabarit article (blog)',
    href: '/admin/pages/article',
    icon: Layers,
  },
  {
    label: 'Gabarit offre exclusive (projets)',
    href: '/admin/pages/exclusive-offer',
    icon: Layers,
  },
  { label: 'Media', href: '/admin/media', icon: Image },
  { label: 'Content Hub (all)', href: '/admin/content', icon: NotebookTabs },
  { label: 'Articles', href: '/admin/articles', icon: BookOpen },
  {
    label: 'Articles · Collections',
    href: '/admin/articles/collections',
    icon: Layers,
  },
  { label: 'Projects (legacy CMS)', href: '/admin/projects', icon: FolderKanban },
  { label: 'Category', href: '/admin/investment-categories', icon: Tags },
  { label: 'Email — Hub MJML', href: '/admin/email', icon: Mail },
  { label: 'Email · Templates', href: '/admin/email/templates', icon: FileCheck },
  { label: 'Email · Components', href: '/admin/email/components', icon: MessageSquare },
  { label: 'Email · AI Builder', href: '/admin/email/ai-builder', icon: Wand2 },
  { label: 'Email · Design System', href: '/admin/email/design', icon: Palette },
  { label: 'Email · DB drafts (legacy)', href: '/admin/emails', icon: Mail },
  { label: 'Email · DB templates (legacy)', href: '/admin/email-templates', icon: FileCheck },
  { label: 'Email · DB modules (legacy)', href: '/admin/email-modules', icon: MessageSquare },
  { label: 'Finance', href: '/admin/finance', icon: DollarSign },
  { label: 'Market Data', href: '/admin/market-data', icon: Database },
  { label: 'Crypto market', href: '/admin/crypto-market', icon: Coins },
  { label: 'Bundles', href: '/admin/bundles', icon: Package },
  { label: 'Clients', href: '/admin/customers', icon: UserCircle2 },
  { label: 'Custody', href: '/admin/custody', icon: Landmark },
  { label: 'Lending — EO pools', href: '/admin/exclusive-offers', icon: Coins },
  { label: 'Exchange Test', href: '/admin/exchange-test', icon: ArrowRightLeft },
  { label: 'Backtests', href: '/admin/backtests', icon: TrendingUp },
  { label: 'Jurisdiction Configs', href: '/admin/jurisdiction-configs', icon: Globe },
  { label: 'AI Config Builder', href: '/admin/ai/jurisdiction-configs', icon: Globe },
  { label: 'Diagnostics', href: '/admin/diagnostics', icon: Cpu },
  {
    label: 'Architecture agents (assistance)',
    href: '/admin/assistance',
    icon: Layers,
  },
  {
    label: 'Knowledge agents',
    href: '/admin/assistance/knowledge',
    icon: Bot,
  },
  {
    label: 'Wiki MD (assistance)',
    href: '/admin/assistance/wiki',
    icon: BookMarked,
  },
  {
    label: 'Playbooks CAL (assistance)',
    href: '/admin/assistance/cal-playbooks',
    icon: ListOrdered,
  },
  {
    label: 'Options agent action (assistance)',
    href: '/admin/assistance/agent-action-options',
    icon: MousePointerClick,
  },
  {
    label: 'Observabilité assistance',
    href: '/admin/assistance/observability',
    icon: TrendingUp,
  },
  { label: 'Risk dashboard', href: '/admin/security/risk-dashboard', icon: Shield },
  { label: 'Risk rules (F.5)', href: '/admin/risk/rules', icon: Shield },
  { label: 'Flutter', href: '/admin/flutter', icon: Smartphone },
  { label: 'Vault Builder', href: '/admin/vault-builder', icon: Archive },
  { label: 'Morpho Vaults', href: '/admin/morpho-vaults', icon: Coins },
  { label: 'Morpho Monitoring', href: '/admin/morpho-vaults/monitoring', icon: Activity },
  {
    label: 'Exclusive Offers (Vault Builder)',
    href: '/admin/vault-builder/exclusive-offers',
    icon: Sparkles,
  },
  { label: 'Registration', href: '/admin/registration', icon: FileCheck },
  { label: 'Reg. sessions', href: '/admin/registration/sessions', icon: FileCheck },
  { label: 'Help', href: '/admin/help', icon: HelpCircle },
  { label: 'Academy', href: '/admin/academy', icon: GraduationCap },
  { label: 'Guide local', href: '/guide', icon: NotebookTabs },
  { label: 'Intégrité i18n (Lot 1)', href: '/admin/i18n/integrity', icon: Globe },
  { label: 'UI strings (mobile)', href: '/admin/i18n/ui-strings', icon: Globe },
  { label: 'Settings', href: '/admin/settings/translation', icon: Settings },
]

export function AdminSidebar() {
  const pathname = usePathname() ?? '' // SSR / hydration: évite startsWith sur null

  const isActive = (href: string) => {
    if (href === '/admin') {
      return pathname === '/admin'
    }
    if (href === '/guide') {
      return pathname === '/guide'
    }
    if (href === '/admin/articles/collections') {
      return pathname.startsWith('/admin/articles/collections')
    }
    if (href === '/admin/articles') {
      return (
        pathname.startsWith('/admin/articles') &&
        !pathname.startsWith('/admin/articles/collections')
      )
    }
    if (href === '/admin/pages') {
      return (
        pathname.startsWith(href) &&
        pathname !== '/admin/pages/article' &&
        !pathname.startsWith('/admin/pages/article/') &&
        pathname !== '/admin/pages/exclusive-offer' &&
        !pathname.startsWith('/admin/pages/exclusive-offer/')
      )
    }
    if (href === '/admin/assistance') {
      return pathname === '/admin/assistance'
    }
    return pathname.startsWith(href)
  }

  return (
    <aside className="fixed left-0 top-0 h-screen w-64 bg-gray-900 text-white border-r border-gray-800">
      <div className="flex flex-col h-full">
        {/* Logo/Header */}
        <div className="p-6 border-b border-gray-800">
          <h1 className="text-xl font-bold text-white">Arquantix CMS</h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-4">
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = isActive(item.href)
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                      active
                        ? 'bg-gray-800 text-white'
                        : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                    )}
                  >
                    <Icon className="w-5 h-5" />
                    <span>{item.label}</span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* Footer */}
        <div className="p-4 border-t border-gray-800">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
          >
            <span>← Retour au site</span>
          </Link>
        </div>
      </div>
    </aside>
  )
}

