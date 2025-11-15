import { useState } from 'react'
import { Card } from '@/components/common/Card'
import { useLocalStorage } from '@/hooks'

export const SettingsPage = () => {
  const [theme, setTheme] = useLocalStorage<'dark' | 'light'>('dashboard-theme', 'dark')
  const [autoRefresh, setAutoRefresh] = useLocalStorage('auto-refresh', true)
  const [refreshInterval, setRefreshInterval] = useLocalStorage('refresh-interval', 30)
  const [itemsPerPage, setItemsPerPage] = useLocalStorage('items-per-page', 10)

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Settings</h1>
        <p className="text-gray-400">Dashboard customization and configuration</p>
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Display</h3>}>
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <label className="text-gray-300">Theme</label>
            <select
              value={theme}
              onChange={(e) => setTheme(e.target.value as 'dark' | 'light')}
              className="px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-50"
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
            </select>
          </div>
          <div className="flex justify-between items-center">
            <label className="text-gray-300">Items Per Page</label>
            <input
              type="number"
              value={itemsPerPage}
              onChange={(e) => setItemsPerPage(parseInt(e.target.value))}
              min="5"
              max="100"
              className="px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-50 w-20"
            />
          </div>
        </div>
      </Card>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Data Refresh</h3>}>
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <label className="text-gray-300">Auto-Refresh</label>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                autoRefresh
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {autoRefresh ? 'Enabled' : 'Disabled'}
            </button>
          </div>
          {autoRefresh && (
            <div className="flex justify-between items-center">
              <label className="text-gray-300">Refresh Interval (seconds)</label>
              <input
                type="number"
                value={refreshInterval}
                onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
                min="5"
                max="300"
                className="px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-50 w-20"
              />
            </div>
          )}
        </div>
      </Card>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Data Management</h3>}>
        <div className="space-y-3">
          <button className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
            Export Dashboard Data
          </button>
          <button className="w-full px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition-colors">
            Clear Cache
          </button>
          <button className="w-full px-4 py-2 bg-gray-700 text-gray-300 rounded hover:bg-gray-600 transition-colors">
            Reset Settings
          </button>
        </div>
      </Card>
    </div>
  )
}

export default SettingsPage
