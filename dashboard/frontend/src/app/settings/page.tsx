'use client'

import { Settings as SettingsIcon, Save } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useTheme } from '@/providers/theme-provider'
import { useToast } from '@/providers/toast-provider'

interface UserSettings {
  defaultPageSize: number
  autoRefreshInterval: number
  exportFormat: 'csv' | 'json'
  enableAnimations: boolean
  compactMode: boolean
}

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const { success } = useToast()

  const [settings, setSettings] = useState<UserSettings>({
    defaultPageSize: 25,
    autoRefreshInterval: 30,
    exportFormat: 'csv',
    enableAnimations: true,
    compactMode: false,
  })

  useEffect(() => {
    // Load saved settings
    const saved = localStorage.getItem('athena-settings')
    if (saved) {
      try {
        setSettings(JSON.parse(saved))
      } catch (e) {
        console.error('Failed to load settings:', e)
      }
    }
  }, [])

  const handleSave = () => {
    localStorage.setItem('athena-settings', JSON.stringify(settings))
    success('Settings saved successfully')
  }

  const handleReset = () => {
    const defaultSettings: UserSettings = {
      defaultPageSize: 25,
      autoRefreshInterval: 30,
      exportFormat: 'csv',
      enableAnimations: true,
      compactMode: false,
    }
    setSettings(defaultSettings)
    localStorage.setItem('athena-settings', JSON.stringify(defaultSettings))
    success('Settings reset to defaults')
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-gray-100 dark:bg-gray-800">
            <SettingsIcon className="h-8 w-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
            <p className="text-muted-foreground mt-1">
              Customize your dashboard experience
            </p>
          </div>
        </div>
        <div className="flex space-x-2">
          <button
            onClick={handleReset}
            className="px-4 py-2 border rounded-md hover:bg-accent transition-colors"
          >
            Reset to Defaults
          </button>
          <button
            onClick={handleSave}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            <Save className="h-4 w-4" />
            <span>Save Changes</span>
          </button>
        </div>
      </div>

      {/* Settings Sections */}
      <div className="space-y-6">
        {/* Appearance */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Appearance</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Theme</label>
              <select
                value={theme}
                onChange={(e) => setTheme(e.target.value as any)}
                className="w-full max-w-xs px-3 py-2 border rounded-md dark:bg-gray-800"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System</option>
              </select>
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Enable Animations</div>
                <div className="text-sm text-muted-foreground">
                  Smooth transitions and animations
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.enableAnimations}
                onChange={(e) =>
                  setSettings({ ...settings, enableAnimations: e.target.checked })
                }
                className="w-4 h-4"
              />
            </div>

            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">Compact Mode</div>
                <div className="text-sm text-muted-foreground">
                  Reduce spacing and padding
                </div>
              </div>
              <input
                type="checkbox"
                checked={settings.compactMode}
                onChange={(e) =>
                  setSettings({ ...settings, compactMode: e.target.checked })
                }
                className="w-4 h-4"
              />
            </div>
          </div>
        </div>

        {/* Data & Display */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Data & Display</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Default Page Size
              </label>
              <select
                value={settings.defaultPageSize}
                onChange={(e) =>
                  setSettings({ ...settings, defaultPageSize: Number(e.target.value) })
                }
                className="w-full max-w-xs px-3 py-2 border rounded-md dark:bg-gray-800"
              >
                <option value={10}>10 items per page</option>
                <option value={25}>25 items per page</option>
                <option value={50}>50 items per page</option>
                <option value={100}>100 items per page</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Auto-Refresh Interval
              </label>
              <select
                value={settings.autoRefreshInterval}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    autoRefreshInterval: Number(e.target.value),
                  })
                }
                className="w-full max-w-xs px-3 py-2 border rounded-md dark:bg-gray-800"
              >
                <option value={0}>Disabled</option>
                <option value={10}>Every 10 seconds</option>
                <option value={30}>Every 30 seconds</option>
                <option value={60}>Every minute</option>
                <option value={300}>Every 5 minutes</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Default Export Format
              </label>
              <select
                value={settings.exportFormat}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    exportFormat: e.target.value as 'csv' | 'json',
                  })
                }
                className="w-full max-w-xs px-3 py-2 border rounded-md dark:bg-gray-800"
              >
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
              </select>
            </div>
          </div>
        </div>

        {/* Keyboard Shortcuts */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">Keyboard Shortcuts</h2>
          <div className="space-y-3 text-sm">
            <div className="flex items-center justify-between">
              <span>Open Command Palette</span>
              <kbd className="px-2 py-1 bg-muted rounded font-mono">⌘K / Ctrl+K</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span>Close Modal / Clear Search</span>
              <kbd className="px-2 py-1 bg-muted rounded font-mono">Esc</kbd>
            </div>
            <div className="flex items-center justify-between">
              <span>Navigate Pages</span>
              <kbd className="px-2 py-1 bg-muted rounded font-mono">1-9</kbd>
            </div>
          </div>
        </div>

        {/* About */}
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-lg font-semibold mb-4">About</h2>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>Athena Dashboard v1.0.0</p>
            <p>Built with Next.js 15, React 19, and FastAPI</p>
            <p>© 2025 Athena Memory System</p>
          </div>
        </div>
      </div>
    </div>
  )
}
