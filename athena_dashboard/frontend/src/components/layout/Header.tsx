/**
 * Dashboard Header
 */

import { useState } from 'react'
import { useLocation } from 'react-router-dom'

interface HeaderProps {
  title?: string
  subtitle?: string
  actions?: React.ReactNode
}

export const Header = ({ title = 'Athena Dashboard', subtitle, actions }: HeaderProps) => {
  const location = useLocation()
  const [showNotifications, setShowNotifications] = useState(false)

  return (
    <header className="fixed top-0 right-0 left-64 h-16 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6 z-30">
      {/* Title */}
      <div>
        <h1 className="text-xl font-bold text-gray-50">{title}</h1>
        {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
      </div>

      {/* Actions & Controls */}
      <div className="flex items-center gap-4">
        {actions}

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative p-2 text-gray-400 hover:text-gray-300 hover:bg-gray-700/50 rounded-lg transition-colors"
          >
            🔔
            <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full" />
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 bg-gray-900 border border-gray-700 rounded-lg shadow-xl z-50">
              <div className="p-4 border-b border-gray-700">
                <h3 className="font-semibold text-gray-50">Notifications</h3>
              </div>
              <div className="max-h-96 overflow-y-auto">
                <div className="p-4 text-sm text-gray-400 text-center">
                  No new notifications
                </div>
              </div>
            </div>
          )}
        </div>

        {/* User Menu */}
        <div className="flex items-center gap-3 pl-4 border-l border-gray-700">
          <div className="text-right">
            <p className="text-sm font-medium text-gray-50">System</p>
            <p className="text-xs text-gray-400">Admin</p>
          </div>
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-cyan-500" />
        </div>
      </div>
    </header>
  )
}

export default Header
