'use client'

import { useQuery } from '@tanstack/react-query'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { Bell, Settings, RefreshCw } from 'lucide-react'
import { formatDate } from '@/lib/utils'
import { ProjectSelector } from '@/components/project-selector'
import { ThemeToggle } from '@/components/theme-toggle'

export function MainNav() {
  const router = useRouter()
  const { data: systemStatus, refetch, isRefetching } = useQuery({
    queryKey: ['system-status'],
    queryFn: api.getSystemStatus,
  })

  return (
    <header className="h-16 border-b bg-card flex items-center justify-between px-6">
      {/* Left: Current time */}
      <div className="flex items-center space-x-4">
        <div className="text-sm text-muted-foreground">
          {systemStatus?.timestamp && formatDate(systemStatus.timestamp)}
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center space-x-4">
        {/* Project Selector */}
        <ProjectSelector />

        {/* Refresh button */}
        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="p-2 rounded-md hover:bg-accent transition-colors"
          title="Refresh data"
        >
          <RefreshCw
            className={`h-5 w-5 text-muted-foreground ${isRefetching ? 'animate-spin' : ''}`}
          />
        </button>

        {/* Theme Toggle */}
        <ThemeToggle />

        {/* Notifications */}
        <button
          className="p-2 rounded-md hover:bg-accent transition-colors relative"
          title="Notifications"
        >
          <Bell className="h-5 w-5 text-muted-foreground" />
          <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full"></span>
        </button>

        {/* Settings */}
        <button
          onClick={() => router.push('/settings')}
          className="p-2 rounded-md hover:bg-accent transition-colors"
          title="Settings"
        >
          <Settings className="h-5 w-5 text-muted-foreground" />
        </button>

        {/* Status indicator */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-full bg-secondary">
          <div
            className={`h-2 w-2 rounded-full ${
              systemStatus?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
            }`}
          ></div>
          <span className="text-xs font-medium capitalize">
            {systemStatus?.status || 'Unknown'}
          </span>
        </div>
      </div>
    </header>
  )
}
