import { useState } from 'react'
import { Card } from '@/components/common/Card'
import { useLocalStorage } from '@/hooks'

export const SettingsPage = () => {
  const [theme, setTheme] = useLocalStorage<'dark' | 'light'>('dashboard-theme', 'dark')
  const [autoRefresh, setAutoRefresh] = useLocalStorage('auto-refresh', true)
  const [refreshInterval, setRefreshInterval] = useLocalStorage('refresh-interval', 30)
  const [itemsPerPage, setItemsPerPage] = useLocalStorage('items-per-page', 10)
  const [cpuThreshold, setCpuThreshold] = useLocalStorage('perf-cpu-threshold', 80)
  const [memoryThreshold, setMemoryThreshold] = useLocalStorage('perf-memory-threshold', 85)
  const [latencyThreshold, setLatencyThreshold] = useLocalStorage('perf-latency-threshold', 200)
  const [enableAlerts, setEnableAlerts] = useLocalStorage('perf-alerts-enabled', true)

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

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Performance Monitoring</h3>}>
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <label className="text-gray-300">Enable Performance Alerts</label>
            <button
              onClick={() => setEnableAlerts(!enableAlerts)}
              className={`px-4 py-2 rounded font-medium transition-colors ${
                enableAlerts
                  ? 'bg-green-600 text-white hover:bg-green-700'
                  : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {enableAlerts ? 'Enabled' : 'Disabled'}
            </button>
          </div>
          {enableAlerts && (
            <>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-gray-300">CPU Usage Alert Threshold</label>
                  <span className="text-blue-400 font-mono">{cpuThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="100"
                  step="5"
                  value={cpuThreshold}
                  onChange={(e) => setCpuThreshold(parseInt(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-gray-500">Alert when CPU exceeds this percentage</p>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-gray-300">Memory Usage Alert Threshold</label>
                  <span className="text-blue-400 font-mono">{memoryThreshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="100"
                  step="5"
                  value={memoryThreshold}
                  onChange={(e) => setMemoryThreshold(parseInt(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-gray-500">Alert when memory exceeds this percentage</p>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-gray-300">Query Latency Alert Threshold</label>
                  <span className="text-blue-400 font-mono">{latencyThreshold}ms</span>
                </div>
                <input
                  type="range"
                  min="100"
                  max="500"
                  step="50"
                  value={latencyThreshold}
                  onChange={(e) => setLatencyThreshold(parseInt(e.target.value))}
                  className="w-full"
                />
                <p className="text-xs text-gray-500">Alert when query latency exceeds this value</p>
              </div>
            </>
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
