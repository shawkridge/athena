'use client'

import { useEffect, useState } from 'react'
import { RefreshCw, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'

interface RefreshIndicatorProps {
  lastUpdated: Date
  onRefresh: () => void
  refreshInterval?: number
  autoRefresh?: boolean
  className?: string
}

export function RefreshIndicator({
  lastUpdated,
  onRefresh,
  refreshInterval = 30000,
  autoRefresh = false,
  className,
}: RefreshIndicatorProps) {
  const [timeSince, setTimeSince] = useState('')
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(autoRefresh)

  useEffect(() => {
    const updateTimeSince = () => {
      const now = new Date()
      const diffMs = now.getTime() - lastUpdated.getTime()
      const diffSec = Math.floor(diffMs / 1000)
      const diffMin = Math.floor(diffSec / 60)

      if (diffMin > 60) {
        const diffHour = Math.floor(diffMin / 60)
        setTimeSince(`${diffHour}h ${diffMin % 60}m ago`)
      } else if (diffMin > 0) {
        setTimeSince(`${diffMin}m ago`)
      } else if (diffSec > 0) {
        setTimeSince(`${diffSec}s ago`)
      } else {
        setTimeSince('just now')
      }
    }

    updateTimeSince()
    const interval = setInterval(updateTimeSince, 1000)

    return () => clearInterval(interval)
  }, [lastUpdated])

  useEffect(() => {
    if (!autoRefreshEnabled) return

    const interval = setInterval(() => {
      handleRefresh()
    }, refreshInterval)

    return () => clearInterval(interval)
  }, [autoRefreshEnabled, refreshInterval])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setTimeout(() => setIsRefreshing(false), 500)
    }
  }

  const toggleAutoRefresh = () => {
    setAutoRefreshEnabled((prev) => !prev)
  }

  return (
    <div className={cn('flex items-center gap-3', className)}>
      {/* Last updated time */}
      <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
        <Clock className="h-3.5 w-3.5" />
        <span>Updated {timeSince}</span>
      </div>

      {/* Auto-refresh toggle */}
      <button
        onClick={toggleAutoRefresh}
        className={cn(
          'px-2.5 py-1 rounded text-xs font-medium transition-colors',
          autoRefreshEnabled
            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
            : 'bg-muted text-muted-foreground hover:bg-muted/80'
        )}
        aria-label={autoRefreshEnabled ? 'Disable auto-refresh' : 'Enable auto-refresh'}
        title={autoRefreshEnabled ? 'Auto-refresh enabled' : 'Auto-refresh disabled'}
      >
        {autoRefreshEnabled ? 'Auto' : 'Manual'}
      </button>

      {/* Manual refresh button */}
      <button
        onClick={handleRefresh}
        disabled={isRefreshing}
        className={cn(
          'p-1.5 rounded-md transition-colors',
          'hover:bg-muted active:bg-muted/80',
          'disabled:opacity-50 disabled:cursor-not-allowed'
        )}
        aria-label="Refresh data"
        title="Refresh data"
      >
        <RefreshCw
          className={cn('h-4 w-4 text-muted-foreground', isRefreshing && 'animate-spin')}
        />
      </button>
    </div>
  )
}
