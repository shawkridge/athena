/**
 * Main Dashboard Layout Wrapper
 */

import { ReactNode } from 'react'
import Sidebar from './Sidebar'
import Header from './Header'

interface MainLayoutProps {
  title: string
  subtitle?: string
  children: ReactNode
  actions?: ReactNode
}

export const MainLayout = ({
  title,
  subtitle,
  children,
  actions,
}: MainLayoutProps) => {
  return (
    <div className="min-h-screen bg-gray-900">
      {/* Sidebar */}
      <Sidebar />

      {/* Header */}
      <Header title={title} subtitle={subtitle} actions={actions} />

      {/* Main Content */}
      <main className="ml-64 mt-16 p-6">
        <div className="max-w-7xl">
          {children}
        </div>
      </main>
    </div>
  )
}

export default MainLayout
