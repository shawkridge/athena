/**
 * Dashboard Sidebar Navigation
 */

import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

interface NavItem {
  label: string
  href: string
  icon: string
  section?: string
}

interface NavSection {
  name: string
  items: NavItem[]
}

const navSections: NavSection[] = [
  {
    name: 'Dashboard',
    items: [
      { label: 'Home', href: '/dashboard', icon: '📊', section: 'home' },
    ],
  },
  {
    name: 'Memory Layers',
    items: [
      { label: 'Layer 1: Episodic', href: '/memory/episodic', icon: '📝' },
      { label: 'Layer 2: Semantic', href: '/memory/semantic', icon: '🧠' },
      { label: 'Layer 3: Procedural', href: '/memory/procedural', icon: '⚙️' },
      { label: 'Layer 4: Prospective', href: '/memory/prospective', icon: '🎯' },
      { label: 'Layer 5: Knowledge Graph', href: '/memory/graph', icon: '🕸️' },
      { label: 'Layer 6: Meta-Memory', href: '/memory/meta', icon: '🔍' },
      { label: 'Layer 7: Consolidation', href: '/memory/consolidation', icon: '📦' },
      { label: 'Layer 8: RAG & Planning', href: '/memory/rag', icon: '🚀' },
    ],
  },
  {
    name: 'System',
    items: [
      { label: 'Hook Execution', href: '/system/hooks', icon: '🔌' },
      { label: 'Working Memory', href: '/system/working', icon: '🧠' },
      { label: 'System Health', href: '/system/health', icon: '💚' },
    ],
  },
  {
    name: 'Analytics',
    items: [
      { label: 'Research Console', href: '/research', icon: '🔬' },
      { label: 'Learning Analytics', href: '/analytics/learning', icon: '📈' },
      { label: 'Custom Dashboards', href: '/analytics/custom', icon: '📊' },
    ],
  },
  {
    name: 'Settings',
    items: [
      { label: 'Configuration', href: '/settings', icon: '⚙️' },
    ],
  },
]

export const Sidebar = () => {
  const [isExpanded, setIsExpanded] = useState(true)
  const [expandedSection, setExpandedSection] = useState<string | null>('Memory Layers')
  const location = useLocation()

  const isActive = (href: string) => location.pathname === href

  return (
    <aside
      className={`fixed left-0 top-0 h-screen bg-gray-900 border-r border-gray-800 transition-all duration-300 z-40 ${
        isExpanded ? 'w-64' : 'w-20'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-800">
        {isExpanded && (
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded bg-gradient-to-br from-blue-500 to-cyan-500" />
            <span className="text-sm font-bold text-gray-50">Athena</span>
          </div>
        )}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1 text-gray-400 hover:text-gray-300 hover:bg-gray-800 rounded"
        >
          {isExpanded ? '←' : '→'}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-4 space-y-6">
        {navSections.map((section) => (
          <div key={section.name}>
            {isExpanded && (
              <button
                onClick={() =>
                  setExpandedSection(
                    expandedSection === section.name ? null : section.name
                  )
                }
                className="flex items-center justify-between w-full px-3 py-2 text-xs font-semibold text-gray-400 hover:text-gray-300 transition-colors"
              >
                <span>{section.name}</span>
                <span className={`transition-transform ${expandedSection === section.name ? 'rotate-180' : ''}`}>
                  ▼
                </span>
              </button>
            )}

            {isExpanded && expandedSection === section.name ? (
              <div className="mt-2 space-y-1">
                {section.items.map((item) => (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all ${
                      isActive(item.href)
                        ? 'bg-blue-900/30 text-blue-300 border-l-2 border-blue-500'
                        : 'text-gray-400 hover:text-gray-300 hover:bg-gray-800/50'
                    }`}
                  >
                    <span className="text-base">{item.icon}</span>
                    <span>{item.label}</span>
                  </Link>
                ))}
              </div>
            ) : !isExpanded ? (
              <div className="space-y-2 mt-2">
                {section.items.map((item) => (
                  <Link
                    key={item.href}
                    to={item.href}
                    className={`flex items-center justify-center p-2 rounded-lg text-lg transition-all ${
                      isActive(item.href)
                        ? 'bg-blue-900/30 text-blue-300'
                        : 'text-gray-400 hover:text-gray-300 hover:bg-gray-800/50'
                    }`}
                    title={section.items.find(i => i.href === item.href)?.label}
                  >
                    {item.icon}
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
        ))}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-800 p-4">
        {isExpanded && (
          <div className="text-xs text-gray-500 space-y-1">
            <p>v1.0.0</p>
            <p>© 2025 Athena</p>
          </div>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
