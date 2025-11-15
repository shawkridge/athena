/**
 * Custom hook for real-time data refresh via WebSocket + API
 * Listens to WebSocket updates and refetches data automatically
 */

import { useEffect, useCallback } from 'react'
import { useAPI } from './useAPI'
import { useWebSocket } from './useWebSocket'

interface UseRealtimeDataOptions {
  url: string
  wsUrl?: string
  pollInterval?: number
  dependencies?: any[]
  enabled?: boolean
}

/**
 * Hook that combines API fetching with WebSocket updates for real-time data
 *
 * @param url - The API endpoint to fetch from
 * @param wsUrl - WebSocket URL for real-time updates (optional)
 * @param pollInterval - Interval for polling in ms (optional, default: no polling)
 * @param dependencies - Dependencies to trigger refetch
 * @param enabled - Whether real-time updates are enabled (default: true)
 * @returns API data state with automatic refresh on WebSocket updates
 */
export function useRealtimeData<T>({
  url,
  wsUrl,
  pollInterval,
  dependencies = [],
  enabled = true,
}: UseRealtimeDataOptions) {
  const { data, loading, error, refetch } = useAPI<T>(url, dependencies)

  // Parse endpoint to determine WebSocket channel
  const getWebSocketUrl = useCallback(() => {
    if (wsUrl) return wsUrl

    // Extract resource type from URL (e.g., '/api/episodic/events' -> 'episodic')
    const match = url.match(/\/api\/(\w+)/)
    if (!match) return null

    const resourceType = match[1]
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = import.meta.env.VITE_WS_URL || `${wsProtocol}//${window.location.host}`

    return `${wsHost}/ws/updates/${resourceType}`
  }, [url, wsUrl])

  const defaultWsUrl = getWebSocketUrl()

  // Set up WebSocket connection if enabled
  const { isConnected } = useWebSocket({
    url: defaultWsUrl || '',
    onMessage: (update) => {
      // When we receive an update, refetch the data
      if (update.type === 'data_update' || update.type === 'new_event') {
        console.log(`Real-time update received for ${url}, refetching...`)
        refetch()
      }
    },
    onError: (error) => {
      console.warn(`WebSocket error (falling back to polling): ${error.message}`)
    },
    autoReconnect: true,
    maxReconnectAttempts: 5,
  })

  // Set up polling as fallback
  useEffect(() => {
    if (!enabled || !pollInterval || isConnected) return

    const interval = setInterval(() => {
      console.log(`Polling data from ${url}`)
      refetch()
    }, pollInterval)

    return () => clearInterval(interval)
  }, [enabled, pollInterval, isConnected, refetch, url])

  return {
    data,
    loading,
    error,
    refetch,
    isConnected: enabled && (defaultWsUrl ? isConnected : false),
    hasRealtime: enabled && !!defaultWsUrl,
  }
}
