/**
 * Main Dashboard Layout Wrapper
 * Works with React Router's Outlet to provide consistent layout across all pages
 */

import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export const MainLayout = () => {
  return (
    <div className="min-h-screen bg-gray-900">
      {/* Header - fixed at top, accounting for sidebar */}
      <Header />

      {/* Sidebar - fixed on left */}
      <Sidebar />

      {/* Main Content - pushed right for fixed sidebar, down for fixed header */}
      <main className="ml-64 mt-16 p-6 min-h-screen bg-gray-900">
        <Outlet />
      </main>
    </div>
  )
}

export default MainLayout
