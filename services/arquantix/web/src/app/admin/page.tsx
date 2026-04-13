'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  FileText,
  Menu,
  Image,
  BookOpen,
  FolderKanban,
  Mail,
  HelpCircle,
  DollarSign,
  ArrowRight,
  Cpu,
  LogOut,
  LayoutGrid,
  Layers,
  Landmark
} from 'lucide-react'

interface User {
  id: string
  email: string
  role: string
  createdAt: string
}

interface FeatureCard {
  title: string
  description: string
  href: string
  icon: React.ElementType
}

interface FeatureSection {
  title: string
  cards: FeatureCard[]
}

const featureSections: FeatureSection[] = [
  {
    title: 'Site Vitrine',
    cards: [
      {
        title: 'Pages',
        description: 'Gérer les pages et sections de votre site',
        href: '/admin/pages',
        icon: FileText
      },
      {
        title: 'Menu',
        description: 'Gérer la navigation et le menu du site',
        href: '/admin/pages/menu',
        icon: Menu
      },
      {
        title: 'Media',
        description: 'Gérer vos images et fichiers multimédias',
        href: '/admin/media',
        icon: Image
      }
    ]
  },
  {
    title: 'Blog',
    cards: [
      {
        title: 'Articles',
        description: 'Créer et gérer vos articles de blog',
        href: '/admin/articles',
        icon: BookOpen
      }
    ]
  },
  {
    title: 'Projects',
    cards: [
      {
        title: 'Projets',
        description: 'Gérer vos projets et portfolios',
        href: '/admin/projects',
        icon: FolderKanban
      }
    ]
  },
  {
    title: 'Emails',
    cards: [
      {
        title: 'Emails',
        description: 'Gérer vos emails et campagnes',
        href: '/admin/emails',
        icon: Mail
      }
    ]
  },
  {
    title: 'FAQ',
    cards: [
      {
        title: 'Help',
        description: 'Gérer les articles d\'aide et la FAQ',
        href: '/admin/help',
        icon: HelpCircle
      }
    ]
  },
  {
    title: 'Finance',
    cards: [
      {
        title: 'Finance',
        description: 'Gérer les données financières et backtests',
        href: '/admin/finance',
        icon: DollarSign
      }
    ]
  },
  {
    title: 'Custody',
    cards: [
      {
        title: 'Custody Fiat',
        description: 'Comptes IBAN, balances, transactions et simulations fiat',
        href: '/admin/custody',
        icon: Landmark
      }
    ]
  },
  {
    title: 'Flutter',
    cards: [
      {
        title: 'Flutter',
        description: 'Layouts, modules et structure de l’app Flutter',
        href: '/admin/flutter',
        icon: LayoutGrid
      },
      {
        title: 'Widget Builder',
        description: 'Créer des widgets composés de modules + feeds DB',
        href: '/admin/widget-builder',
        icon: Layers
      }
    ]
  },
  {
    title: 'Diagnostics',
    cards: [
      {
        title: 'Diagnostics',
        description: 'Diagnostics système et outils de développement',
        href: '/admin/diagnostics',
        icon: Cpu
      }
    ]
  }
]

export default function AdminDashboardPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    // Check if user is authenticated
    fetch('/api/admin/me')
      .then((res) => res.json())
      .then((data) => {
        if (!data.user) {
          // Not authenticated, redirect to login
          router.push('/admin/login')
        }
        // If authenticated, stay on this page (dashboard)
      })
      .catch(() => {
        // Error checking auth, redirect to login
        router.push('/admin/login')
      })
  }, [router])

  const handleLogout = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/admin/logout', {
        method: 'POST',
      })
      
      if (response.ok) {
        router.push('/admin/login')
        router.refresh()
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Dashboard</h1>
          <p className="text-gray-600">
            Bienvenue sur le panneau d'administration Arquantix
          </p>
        </div>
        <Button
          onClick={handleLogout}
          disabled={loading}
          variant="outline"
          className="flex items-center gap-2"
        >
          <LogOut className="h-4 w-4" />
          {loading ? 'Déconnexion...' : 'Déconnexion'}
        </Button>
      </div>

      <div className="space-y-8">
        {featureSections.map((section, sectionIndex) => (
          <div key={sectionIndex}>
            <h2 className="text-xl font-semibold text-gray-900 mb-4">{section.title}</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {section.cards.map((card, cardIndex) => {
                const Icon = card.icon
                return (
                  <Link key={cardIndex} href={card.href}>
                    <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                      <CardHeader>
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-3">
                            <div className="p-2 bg-gray-100 rounded-lg">
                              <Icon className="h-5 w-5 text-gray-700" />
                            </div>
                            <div>
                              <CardTitle className="text-lg">{card.title}</CardTitle>
                            </div>
                          </div>
                          <ArrowRight className="h-5 w-5 text-gray-400" />
                        </div>
                      </CardHeader>
                      <CardContent>
                        <CardDescription className="text-sm">
                          {card.description}
                        </CardDescription>
                      </CardContent>
                    </Card>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
