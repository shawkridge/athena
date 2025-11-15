/**
 * Notification Center Component
 * Displays real-time notifications with WebSocket support
 */

import { useState, useEffect, useRef } from 'react'
import { useAPI, useWebSocket } from '@/hooks'
import { useProject } from '@/context/ProjectContext'

interface Notification {
  id: number
  type: string
  title: string
  message: string
  level: 'info' | 'warning' | 'critical'
  status: 'sent' | 'read' | 'archived'
  channels: string[]
  metadata: Record<string, any>
  created_at: string
  read_at?: string
}

interface NotificationResponse {
  notifications: Notification[]
  total: number
  unread_count: number
  critical_count: number
}

interface NotificationStats {
  total: number
  unread: number
  critical: number
  by_level: Record<string, number>
  by_type: Record<string, number>
}

const getLevelColor = (level: string) => {
  switch (level) {
    case 'info':
      return 'bg-blue-900/30 border-l-4 border-blue-500'
    case 'warning':
      return 'bg-yellow-900/30 border-l-4 border-yellow-500'
    case 'critical':
      return 'bg-red-900/30 border-l-4 border-red-500'
    default:
      return 'bg-gray-800/30 border-l-4 border-gray-500'
  }
}

const getLevelBadgeColor = (level: string) => {
  switch (level) {
    case 'info':
      return 'bg-blue-600 text-blue-50'
    case 'warning':
      return 'bg-yellow-600 text-yellow-50'
    case 'critical':
      return 'bg-red-600 text-red-50'
    default:
      return 'bg-gray-600 text-gray-50'
  }
}

export const NotificationCenter = () => {
  const { selectedProject } = useProject()
  const [isOpen, setIsOpen] = useState(false)
  const [showPreferences, setShowPreferences] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Fetch notifications
  const apiUrl = selectedProject
    ? `/api/notifications/list?project_id=${selectedProject.id}&limit=10`
    : '/api/notifications/list?limit=10'

  const { data: notificationsData, refetch: refetchNotifications } = useAPI<NotificationResponse>(
    apiUrl,
    [selectedProject?.id]
  )

  // Fetch stats
  const statsUrl = selectedProject
    ? `/api/notifications/stats?project_id=${selectedProject.id}`
    : '/api/notifications/stats'

  const { data: stats } = useAPI<NotificationStats>(statsUrl, [selectedProject?.id])

  // WebSocket disabled - using polling instead
  // TODO: Re-enable when WebSocket server is available
  const isConnected = false

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleMarkAsRead = async (notificationId: number) => {
    try {
      await fetch(`/api/notifications/${notificationId}/read`, {
        method: 'PUT',
      })
      refetchNotifications()
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  }

  const handleArchive = async (notificationId: number) => {
    try {
      await fetch(`/api/notifications/${notificationId}/archive`, {
        method: 'PUT',
      })
      refetchNotifications()
    } catch (error) {
      console.error('Failed to archive notification:', error)
    }
  }

  const unreadCount = notificationsData?.unread_count || 0
  const criticalCount = notificationsData?.critical_count || 0

  return (
    <div ref={dropdownRef} className="relative">
      {/* Bell Icon Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-800 rounded transition-colors"
        title="Notifications"
      >
        <svg
          className="w-6 h-6"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Badge showing unread count */}
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-white transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}

        {/* Critical alert indicator */}
        {criticalCount > 0 && (
          <span className="absolute bottom-0 right-0 block w-3 h-3 bg-red-500 rounded-full animate-pulse" />
        )}

        {/* Connection status indicator */}
        {isOpen && (
          <span
            className={`absolute bottom-0 left-0 w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-gray-500'
            }`}
          />
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-700">
            <h3 className="text-lg font-semibold text-gray-50">Notifications</h3>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowPreferences(true)}
                className="text-gray-400 hover:text-gray-200"
                title="Preferences"
              >
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M10.5 1.5H9.5V.5h1v1zM14 3.5l.707-.707.707.707-.707.707L14 3.5zm-2.5 2.5l-.707.707.707.707.707-.707-.707-.707zM10 7a3 3 0 100 6 3 3 0 000-6zm0 1a2 2 0 110 4 2 2 0 010-4zm0 5a4 4 0 100-8 4 4 0 000 8z" />
                </svg>
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-200"
              >
                ✕
              </button>
            </div>
          </div>

          {/* Stats */}
          {stats && (
            <div className="grid grid-cols-3 gap-2 p-3 bg-gray-800/50 border-b border-gray-700">
              <div className="text-center">
                <p className="text-2xl font-bold text-gray-50">{stats.total}</p>
                <p className="text-xs text-gray-400">Total</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-yellow-400">{stats.unread}</p>
                <p className="text-xs text-gray-400">Unread</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-red-400">{stats.critical}</p>
                <p className="text-xs text-gray-400">Critical</p>
              </div>
            </div>
          )}

          {/* Notifications List */}
          <div className="max-h-96 overflow-y-auto">
            {notificationsData && notificationsData.notifications.length > 0 ? (
              <div className="divide-y divide-gray-700">
                {notificationsData.notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className={`p-4 hover:bg-gray-800/50 transition-colors cursor-pointer ${getLevelColor(
                      notif.level
                    )}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-block px-2 py-1 text-xs font-semibold rounded ${getLevelBadgeColor(
                              notif.level
                            )}`}
                          >
                            {notif.level.toUpperCase()}
                          </span>
                          <h4 className="text-sm font-semibold text-gray-50">{notif.title}</h4>
                        </div>
                        <p className="text-sm text-gray-300 mt-1">{notif.message}</p>
                        <p className="text-xs text-gray-500 mt-2">
                          {new Date(notif.created_at).toLocaleString()}
                        </p>
                      </div>

                      {/* Actions */}
                      {notif.status !== 'read' && (
                        <button
                          onClick={() => handleMarkAsRead(notif.id)}
                          className="ml-2 px-2 py-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          Mark Read
                        </button>
                      )}
                    </div>

                    {/* Archive button */}
                    <button
                      onClick={() => handleArchive(notif.id)}
                      className="mt-2 text-xs text-gray-500 hover:text-gray-400 transition-colors"
                    >
                      Archive
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center text-gray-400">
                <p>No notifications</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-gray-700 bg-gray-800/30">
            <a
              href="/notifications"
              className="block text-center text-sm text-blue-400 hover:text-blue-300 transition-colors"
            >
              View All Notifications
            </a>
          </div>
        </div>
      )}

      {/* Preferences Modal */}
      {showPreferences && (
        <NotificationPreferencesModal
          onClose={() => setShowPreferences(false)}
          onSave={() => {
            setShowPreferences(false)
            refetchNotifications()
          }}
        />
      )}
    </div>
  )
}

interface NotificationPreferencesModalProps {
  onClose: () => void
  onSave: () => void
}

const NotificationPreferencesModal = ({ onClose, onSave }: NotificationPreferencesModalProps) => {
  const { selectedProject } = useProject()
  const [preferences, setPreferences] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchPreferences = async () => {
      try {
        const url = selectedProject
          ? `/api/notifications/preferences?project_id=${selectedProject.id}`
          : '/api/notifications/preferences'
        const res = await fetch(url)
        const data = await res.json()
        setPreferences(data)
      } catch (error) {
        console.error('Failed to fetch preferences:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchPreferences()
  }, [selectedProject])

  const handleSave = async () => {
    try {
      const url = selectedProject
        ? `/api/notifications/preferences?project_id=${selectedProject.id}`
        : '/api/notifications/preferences'

      await fetch(url, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(preferences),
      })
      onSave()
    } catch (error) {
      console.error('Failed to save preferences:', error)
    }
  }

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-gray-900 rounded-lg p-8">
          <p className="text-gray-50">Loading preferences...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-lg max-w-2xl w-full mx-4 max-h-96 overflow-y-auto">
        {/* Modal Header */}
        <div className="sticky top-0 flex items-center justify-between p-6 border-b border-gray-700 bg-gray-900">
          <h2 className="text-xl font-semibold text-gray-50">Notification Preferences</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-200"
          >
            ✕
          </button>
        </div>

        {/* Modal Body */}
        {preferences && (
          <div className="p-6 space-y-6">
            {/* Enable/Disable Toggles */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold text-gray-50">Notification Channels</h3>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferences.enable_in_app}
                  onChange={(e) =>
                    setPreferences({ ...preferences, enable_in_app: e.target.checked })
                  }
                  className="rounded"
                />
                <span className="text-gray-300">In-App Notifications</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferences.enable_email}
                  onChange={(e) =>
                    setPreferences({ ...preferences, enable_email: e.target.checked })
                  }
                  className="rounded"
                />
                <span className="text-gray-300">Email Notifications</span>
              </label>
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferences.enable_webhook}
                  onChange={(e) =>
                    setPreferences({ ...preferences, enable_webhook: e.target.checked })
                  }
                  className="rounded"
                />
                <span className="text-gray-300">Webhook Notifications</span>
              </label>
            </div>

            {/* Minimum Alert Level */}
            <div>
              <h3 className="text-lg font-semibold text-gray-50 mb-3">Minimum Alert Level</h3>
              <select
                value={preferences.min_level}
                onChange={(e) => setPreferences({ ...preferences, min_level: e.target.value })}
                className="px-3 py-2 bg-gray-800 border border-gray-700 rounded text-gray-50"
              >
                <option value="info">Info</option>
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
              </select>
            </div>

            {/* Quiet Hours */}
            <div className="space-y-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={preferences.quiet_hours_enabled}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      quiet_hours_enabled: e.target.checked,
                    })
                  }
                  className="rounded"
                />
                <span className="text-gray-300">Enable Quiet Hours</span>
              </label>
              {preferences.quiet_hours_enabled && (
                <div className="ml-6 space-y-2">
                  <div>
                    <label className="text-gray-400 text-sm">Start Time</label>
                    <input
                      type="time"
                      value={preferences.quiet_hours_start}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          quiet_hours_start: e.target.value,
                        })
                      }
                      className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-gray-50"
                    />
                  </div>
                  <div>
                    <label className="text-gray-400 text-sm">End Time</label>
                    <input
                      type="time"
                      value={preferences.quiet_hours_end}
                      onChange={(e) =>
                        setPreferences({
                          ...preferences,
                          quiet_hours_end: e.target.value,
                        })
                      }
                      className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-gray-50"
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Modal Footer */}
        <div className="sticky bottom-0 flex items-center justify-end gap-3 p-6 border-t border-gray-700 bg-gray-900">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-300 hover:text-gray-100 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
          >
            Save Preferences
          </button>
        </div>
      </div>
    </div>
  )
}

export default NotificationCenter
