'use client'

import { useEffect, useState, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Search, Command } from 'lucide-react'

interface CommandItem {
  id: string
  label: string
  keywords: string[]
  action: () => void
  category: string
}

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState(false)
  const [search, setSearch] = useState('')
  const router = useRouter()

  const commands: CommandItem[] = useMemo(() => [
    // Navigation
    { id: 'nav-home', label: 'Go to Overview', keywords: ['home', 'dashboard', 'overview'], action: () => router.push('/'), category: 'Navigation' },
    { id: 'nav-episodic', label: 'Go to Episodic Memory', keywords: ['episodic', 'events', 'memory'], action: () => router.push('/episodic'), category: 'Navigation' },
    { id: 'nav-semantic', label: 'Go to Semantic Memory', keywords: ['semantic', 'search', 'facts'], action: () => router.push('/semantic'), category: 'Navigation' },
    { id: 'nav-procedural', label: 'Go to Procedural Memory', keywords: ['procedural', 'procedures', 'workflows'], action: () => router.push('/procedural'), category: 'Navigation' },
    { id: 'nav-prospective', label: 'Go to Prospective Memory', keywords: ['prospective', 'tasks', 'goals'], action: () => router.push('/prospective'), category: 'Navigation' },
    { id: 'nav-graph', label: 'Go to Knowledge Graph', keywords: ['graph', 'entities', 'relations'], action: () => router.push('/graph'), category: 'Navigation' },
    { id: 'nav-meta', label: 'Go to Meta-Memory', keywords: ['meta', 'quality', 'metrics'], action: () => router.push('/meta'), category: 'Navigation' },
    { id: 'nav-consolidation', label: 'Go to Consolidation', keywords: ['consolidation', 'patterns'], action: () => router.push('/consolidation'), category: 'Navigation' },
    { id: 'nav-planning', label: 'Go to Planning', keywords: ['planning', 'plans', 'strategies'], action: () => router.push('/planning'), category: 'Navigation' },
    { id: 'nav-research', label: 'Go to Research', keywords: ['research', 'tasks', 'findings'], action: () => router.push('/research'), category: 'Navigation' },
    { id: 'nav-code', label: 'Go to Code Intelligence', keywords: ['code', 'artifacts', 'files'], action: () => router.push('/code'), category: 'Navigation' },
    { id: 'nav-skills', label: 'Go to Skills & Agents', keywords: ['skills', 'agents', 'library'], action: () => router.push('/skills'), category: 'Navigation' },
    { id: 'nav-context', label: 'Go to Context Awareness', keywords: ['context', 'ide', 'working memory'], action: () => router.push('/context'), category: 'Navigation' },
    { id: 'nav-execution', label: 'Go to Execution Monitoring', keywords: ['execution', 'tasks', 'monitoring'], action: () => router.push('/execution'), category: 'Navigation' },
    { id: 'nav-safety', label: 'Go to Safety Validation', keywords: ['safety', 'validation', 'security'], action: () => router.push('/safety'), category: 'Navigation' },
    { id: 'nav-performance', label: 'Go to Performance Metrics', keywords: ['performance', 'metrics', 'benchmarks'], action: () => router.push('/performance'), category: 'Navigation' },
  ], [router])

  const filteredCommands = useMemo(() => {
    if (!search) return commands

    const query = search.toLowerCase()
    return commands.filter((cmd) =>
      cmd.label.toLowerCase().includes(query) ||
      cmd.keywords.some((kw) => kw.toLowerCase().includes(query))
    )
  }, [commands, search])

  const groupedCommands = useMemo(() => {
    const groups: Record<string, CommandItem[]> = {}
    filteredCommands.forEach((cmd) => {
      if (!groups[cmd.category]) {
        groups[cmd.category] = []
      }
      groups[cmd.category].push(cmd)
    })
    return groups
  }, [filteredCommands])

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.key === 'k' && (e.metaKey || e.ctrlKey)) || (e.key === '/' && e.ctrlKey)) {
        e.preventDefault()
        setIsOpen((open) => !open)
      }

      if (e.key === 'Escape') {
        setIsOpen(false)
      }
    }

    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  const handleSelect = (cmd: CommandItem) => {
    cmd.action()
    setIsOpen(false)
    setSearch('')
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40 animate-in fade-in"
        onClick={() => setIsOpen(false)}
      />

      {/* Command Palette */}
      <div className="fixed top-[20%] left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 animate-in zoom-in-95">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-2xl border dark:border-gray-700 overflow-hidden">
          {/* Search Input */}
          <div className="flex items-center border-b dark:border-gray-700 px-4 py-3">
            <Search className="h-5 w-5 text-muted-foreground mr-3" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Type a command or search..."
              className="flex-1 outline-none bg-transparent text-sm"
              autoFocus
            />
            <kbd className="hidden sm:inline-block px-2 py-1 text-xs font-semibold text-muted-foreground bg-muted rounded">
              ESC
            </kbd>
          </div>

          {/* Commands List */}
          <div className="max-h-96 overflow-y-auto p-2">
            {Object.keys(groupedCommands).length === 0 && (
              <div className="text-center py-8 text-muted-foreground text-sm">
                No commands found
              </div>
            )}

            {Object.entries(groupedCommands).map(([category, items]) => (
              <div key={category} className="mb-4">
                <div className="px-2 py-1 text-xs font-semibold text-muted-foreground uppercase">
                  {category}
                </div>
                {items.map((cmd) => (
                  <button
                    key={cmd.id}
                    onClick={() => handleSelect(cmd)}
                    className="w-full text-left px-3 py-2 text-sm rounded hover:bg-accent dark:hover:bg-gray-700 transition-colors"
                  >
                    {cmd.label}
                  </button>
                ))}
              </div>
            ))}
          </div>

          {/* Footer */}
          <div className="border-t dark:border-gray-700 px-4 py-2 flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center space-x-4">
              <span className="flex items-center">
                <kbd className="px-1.5 py-0.5 bg-muted rounded mr-1">↵</kbd>
                to select
              </span>
              <span className="flex items-center">
                <kbd className="px-1.5 py-0.5 bg-muted rounded mr-1">ESC</kbd>
                to close
              </span>
            </div>
            <div className="flex items-center space-x-1">
              <Command className="h-3 w-3" />
              <span>+</span>
              <kbd className="px-1.5 py-0.5 bg-muted rounded">K</kbd>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
