/**
 * Refresh button component with loading state and real-time indicator
 */

import { useState } from 'react'

interface RefreshButtonProps {
  onRefresh: () => Promise<void>
  isConnected?: boolean
  isLoading?: boolean
  className?: string
}

export const RefreshButton = ({
  onRefresh,
  isConnected = false,
  isLoading = false,
  className = '',
}: RefreshButtonProps) => {
  const [isRefreshing, setIsRefreshing] = useState(false)

  const handleRefresh = async () => {
    setIsRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setIsRefreshing(false)
    }
  }

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Real-time indicator */}
      {isConnected && (
        <div className="flex items-center gap-1 text-xs text-emerald-400">
          <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
          <span>Live</span>
        </div>
      )}

      {/* Refresh button */}
      <button
        onClick={handleRefresh}
        disabled={isRefreshing || isLoading}
        className={`
          inline-flex items-center gap-2 px-3 py-2 rounded-lg font-medium
          transition-colors duration-200
          ${
            isRefreshing || isLoading
              ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 text-white cursor-pointer'
          }
        `}
        title={isConnected ? 'Data updates automatically, or click to refresh now' : 'Click to refresh data'}
      >
        <svg
          className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
          />
        </svg>
        {isRefreshing ? 'Refreshing...' : isConnected ? 'Refresh Now' : 'Refresh'}
      </button>
    </div>
  )
}
