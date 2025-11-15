import { useState } from 'react'
import { Stat } from '@/components/common/Stat'
import { Card } from '@/components/common/Card'
import { GaugeChart } from '@/components/charts/GaugeChart'
import { useAPI } from '@/hooks'

interface SystemStats {
  totalEvents: number
  totalMemories: number
  qualityScore: number
  avgQueryTime: number
  successRate: number
  errorCount: number
  layers: {
    name: string
    health: number
    itemCount: number
  }[]
}

export const OverviewPage = () => {
  const { data: stats, loading, error } = useAPI<SystemStats>(
    '/api/system/overview'
  )

  if (loading) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-50 mb-2">Overview</h1>
        <div className="animate-pulse space-y-4">
          <div className="h-32 bg-gray-800 rounded-lg" />
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-800 rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-50 mb-2">Overview</h1>
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 text-red-300">
          {error?.message || 'Failed to load system overview'}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Overview</h1>
        <p className="text-gray-400">System health summary and key metrics</p>
      </div>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Stat
          label="Total Events"
          value={stats.totalEvents.toLocaleString()}
          trend={5}
        />
        <Stat
          label="Total Memories"
          value={stats.totalMemories.toLocaleString()}
          trend={2}
        />
        <Stat
          label="Quality Score"
          value={`${Math.round(stats.qualityScore)}%`}
          trend={stats.qualityScore > 80 ? 1 : -1}
        />
        <Stat
          label="Avg Query Time"
          value={`${Math.round(stats.avgQueryTime)}ms`}
          trend={stats.avgQueryTime < 100 ? 1 : -1}
        />
      </div>

      {/* System Health Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Overall Health */}
        <Card
          header={<h3 className="text-lg font-semibold text-gray-50">System Health</h3>}
          className="lg:col-span-1"
        >
          <div className="flex justify-center">
            <GaugeChart
              value={stats.qualityScore}
              title="Overall Quality"
              color={
                stats.qualityScore >= 80
                  ? 'success'
                  : stats.qualityScore >= 60
                    ? 'warning'
                    : 'error'
              }
            />
          </div>
        </Card>

        {/* Performance Metrics */}
        <Card
          header={<h3 className="text-lg font-semibold text-gray-50">Performance</h3>}
          className="lg:col-span-2"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Success Rate</span>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-2 bg-gray-700 rounded-full max-w-xs overflow-hidden">
                  <div
                    className="h-full bg-green-500"
                    style={{
                      width: `${Math.min(100, stats.successRate)}%`,
                    }}
                  />
                </div>
                <span className="text-gray-50 font-semibold">
                  {Math.round(stats.successRate)}%
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Errors</span>
              <span
                className={`font-semibold ${
                  stats.errorCount === 0 ? 'text-green-400' : 'text-red-400'
                }`}
              >
                {stats.errorCount}
              </span>
            </div>
          </div>
        </Card>
      </div>

      {/* Memory Layers Health */}
      <Card
        header={<h3 className="text-lg font-semibold text-gray-50">Memory Layers</h3>}
      >
        <div className="space-y-3">
          {stats.layers.map((layer) => (
            <div key={layer.name} className="flex items-center justify-between">
              <div>
                <p className="text-gray-50 font-medium">{layer.name}</p>
                <p className="text-xs text-gray-400">{layer.itemCount} items</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-gray-700 rounded-full w-32 overflow-hidden">
                  <div
                    className={`h-full ${
                      layer.health >= 80
                        ? 'bg-green-500'
                        : layer.health >= 60
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                    }`}
                    style={{ width: `${layer.health}%` }}
                  />
                </div>
                <span className="text-gray-50 font-semibold w-12 text-right">
                  {Math.round(layer.health)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Recent Activity */}
      <Card
        header={<h3 className="text-lg font-semibold text-gray-50">Quick Links</h3>}
      >
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <a
            href="/system-health"
            className="p-4 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-center transition-colors"
          >
            <p className="text-2xl mb-2">💚</p>
            <p className="text-sm text-gray-300">Health Dashboard</p>
          </a>
          <a
            href="/episodic"
            className="p-4 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-center transition-colors"
          >
            <p className="text-2xl mb-2">📝</p>
            <p className="text-sm text-gray-300">Episodic Memory</p>
          </a>
          <a
            href="/consolidation"
            className="p-4 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-center transition-colors"
          >
            <p className="text-2xl mb-2">📦</p>
            <p className="text-sm text-gray-300">Consolidation</p>
          </a>
          <a
            href="/hooks"
            className="p-4 bg-gray-700/50 hover:bg-gray-700 rounded-lg text-center transition-colors"
          >
            <p className="text-2xl mb-2">🔌</p>
            <p className="text-sm text-gray-300">Hooks Monitor</p>
          </a>
        </div>
      </Card>
    </div>
  )
}

export default OverviewPage
