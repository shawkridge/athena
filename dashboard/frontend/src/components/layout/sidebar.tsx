'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  Home,
  Database,
  Brain,
  Workflow,
  Calendar,
  Network,
  Gauge,
  Sparkles,
  Map,
  Search,
  Code,
  Zap,
  Users,
  MessageSquare,
  PlayCircle,
  Shield,
  TrendingUp,
} from 'lucide-react'

const navigation = [
  { name: 'Overview', href: '/', icon: Home },
  {
    name: 'Memory Layers',
    items: [
      { name: 'Episodic', href: '/episodic', icon: Database },
      { name: 'Semantic', href: '/semantic', icon: Brain },
      { name: 'Procedural', href: '/procedural', icon: Workflow },
      { name: 'Prospective', href: '/prospective', icon: Calendar },
      { name: 'Graph', href: '/graph', icon: Network },
      { name: 'Meta', href: '/meta', icon: Gauge },
      { name: 'Consolidation', href: '/consolidation', icon: Sparkles },
      { name: 'Planning', href: '/planning', icon: Map },
    ],
  },
  {
    name: 'Advanced',
    items: [
      { name: 'Research', href: '/research', icon: Search },
      { name: 'Code Intelligence', href: '/code', icon: Code },
      { name: 'Skills & Agents', href: '/skills', icon: Zap },
      { name: 'Context', href: '/context', icon: MessageSquare },
      { name: 'Execution', href: '/execution', icon: PlayCircle },
      { name: 'Safety', href: '/safety', icon: Shield },
      { name: 'Performance', href: '/performance', icon: TrendingUp },
    ],
  },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="w-64 bg-card border-r flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b">
        <div className="flex items-center space-x-2">
          <Brain className="h-8 w-8 text-primary" />
          <span className="text-xl font-bold">Athena</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-6">
        {navigation.map((section) => (
          <div key={section.name}>
            {section.href ? (
              // Single item
              <Link
                href={section.href}
                className={cn(
                  'flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                  pathname === section.href
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                {section.icon && <section.icon className="h-5 w-5" />}
                <span>{section.name}</span>
              </Link>
            ) : (
              // Section with items
              <div>
                <h3 className="px-3 mb-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                  {section.name}
                </h3>
                <div className="space-y-1">
                  {section.items?.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={cn(
                        'flex items-center space-x-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                        pathname === item.href
                          ? 'bg-primary text-primary-foreground'
                          : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                      )}
                    >
                      {item.icon && <item.icon className="h-4 w-4" />}
                      <span>{item.name}</span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t">
        <div className="text-xs text-muted-foreground">
          <p>Athena v1.0</p>
          <p className="mt-1">8 layers, 60+ modules</p>
        </div>
      </div>
    </aside>
  )
}
