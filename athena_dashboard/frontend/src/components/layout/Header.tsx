/**
 * Dashboard Header
 */

import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import ProjectSelector from '../ProjectSelector'
import { NotificationCenter } from '../notifications/NotificationCenter'

interface HeaderProps {
  title?: string
  subtitle?: string
  actions?: React.ReactNode
}

export const Header = ({ title = 'Athena Dashboard', subtitle, actions }: HeaderProps) => {
  const location = useLocation()

  return (
    <header className="fixed top-0 right-0 left-64 h-16 bg-gray-800 border-b border-gray-700 flex items-center justify-between px-6 z-30">
      {/* Title & Project Selector */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-xl font-bold text-gray-50">{title}</h1>
          {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
        </div>
        <div className="border-l border-gray-700 pl-4">
          <ProjectSelector />
        </div>
      </div>

      {/* Actions & Controls */}
      <div className="flex items-center gap-4">
        {actions}

        {/* Notification Center */}
        <NotificationCenter />

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
