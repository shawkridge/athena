'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { SystemStatusCard } from '@/components/system-status-card'
import { MemoryLayerCard } from '@/components/memory-layer-card'
import { RecentEventsCard } from '@/components/recent-events-card'
import { ActivityChart } from '@/components/charts/activity-chart'
import { CardSkeleton, ChartSkeleton } from '@/components/skeleton'
import { TrendsChart } from '@/components/trends-chart'
import { QuickStatsCard } from '@/components/quick-stats-card'
import { Database, Brain, Workflow, Calendar, Network, Gauge, Sparkles, Map } from 'lucide-react'

export default function DashboardPage() {
  const { data: systemStatus, isLoading } = useQuery({
    queryKey: ['system-status'],
    queryFn: api.getSystemStatus,
  })

  const { data: recentEvents } = useQuery({
    queryKey: ['episodic-recent'],
    queryFn: () => api.getEpisodicRecent(10),
  })

  const memoryLayers = [
    {
      name: 'Episodic Memory',
      description: 'Event storage with temporal grounding',
      icon: Database,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      href: '/episodic',
      stats: systemStatus?.subsystems?.memory?.episodic,
    },
    {
      name: 'Semantic Memory',
      description: 'Vector + BM25 hybrid search',
      icon: Brain,
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      href: '/semantic',
      stats: systemStatus?.subsystems?.memory?.semantic,
    },
    {
      name: 'Procedural Memory',
      description: 'Reusable workflows and procedures',
      icon: Workflow,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      href: '/procedural',
      stats: systemStatus?.subsystems?.memory?.procedural,
    },
    {
      name: 'Prospective Memory',
      description: 'Tasks, goals, and triggers',
      icon: Calendar,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      href: '/prospective',
      stats: systemStatus?.subsystems?.memory?.prospective,
    },
    {
      name: 'Knowledge Graph',
      description: 'Entities, relations, communities',
      icon: Network,
      color: 'text-cyan-600',
      bgColor: 'bg-cyan-100',
      href: '/graph',
      stats: systemStatus?.subsystems?.memory?.graph,
    },
    {
      name: 'Meta-Memory',
      description: 'Quality tracking and cognitive load',
      icon: Gauge,
      color: 'text-pink-600',
      bgColor: 'bg-pink-100',
      href: '/meta',
      stats: systemStatus?.subsystems?.memory?.meta,
    },
    {
      name: 'Consolidation',
      description: 'Pattern extraction and compression',
      icon: Sparkles,
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-100',
      href: '/consolidation',
      stats: systemStatus?.subsystems?.memory?.consolidation,
    },
    {
      name: 'Planning',
      description: 'Task planning and decomposition',
      icon: Map,
      color: 'text-indigo-600',
      bgColor: 'bg-indigo-100',
      href: '/planning',
      stats: systemStatus?.subsystems?.memory?.planning,
    },
  ]

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-20">
          <CardSkeleton />
        </div>
        <ChartSkeleton height={300} />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      </div>
    )
  }

  // Mock trend data for analytics (replace with real data from API)
  const trendData = [
    { timestamp: new Date(Date.now() - 6000), value: 120 },
    { timestamp: new Date(Date.now() - 5000), value: 135 },
    { timestamp: new Date(Date.now() - 4000), value: 145 },
    { timestamp: new Date(Date.now() - 3000), value: 138 },
    { timestamp: new Date(Date.now() - 2000), value: 152 },
    { timestamp: new Date(Date.now() - 1000), value: 168 },
    { timestamp: new Date(), value: 175 },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Athena Memory System</h1>
          <p className="text-muted-foreground mt-1">
            Real-time monitoring across 8 memory layers and 60+ modules
          </p>
        </div>
        <SystemStatusCard status={systemStatus?.status} />
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <QuickStatsCard
          title="Total Events"
          value={systemStatus?.subsystems?.memory?.episodic?.total_events || 0}
          previousValue={8000}
          format="number"
          icon={Database}
          iconColor="text-blue-600"
          iconBgColor="bg-blue-100 dark:bg-blue-900/30"
        />
        <QuickStatsCard
          title="Active Tasks"
          value={systemStatus?.subsystems?.memory?.prospective?.active_tasks || 0}
          previousValue={35}
          format="number"
          icon={Calendar}
          iconColor="text-orange-600"
          iconBgColor="bg-orange-100 dark:bg-orange-900/30"
        />
        <QuickStatsCard
          title="Graph Entities"
          value={systemStatus?.subsystems?.memory?.graph?.total_entities || 0}
          previousValue={420}
          format="number"
          icon={Network}
          iconColor="text-cyan-600"
          iconBgColor="bg-cyan-100 dark:bg-cyan-900/30"
        />
        <QuickStatsCard
          title="Procedures"
          value={systemStatus?.subsystems?.memory?.procedural?.total_procedures || 0}
          previousValue={95}
          format="number"
          icon={Workflow}
          iconColor="text-green-600"
          iconBgColor="bg-green-100 dark:bg-green-900/30"
        />
      </div>

      {/* System Activity Chart */}
      <div className="grid gap-6">
        <ActivityChart />
      </div>

      {/* Trend Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TrendsChart
          data={trendData}
          title="Memory Activity Trend"
          yAxisLabel="Events"
        />
        <TrendsChart
          data={trendData.map((d) => ({ ...d, value: d.value * 0.8 }))}
          title="Task Completion Trend"
          yAxisLabel="Tasks"
        />
      </div>

      {/* Memory Layers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {memoryLayers.map((layer) => (
          <MemoryLayerCard key={layer.name} {...layer} />
        ))}
      </div>

      {/* Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RecentEventsCard events={recentEvents?.events || []} />

        {/* Consolidation Status */}
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Consolidation Status</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Last Run</span>
              <span className="text-sm font-medium">
                {systemStatus?.subsystems?.memory?.consolidation?.last_run || 'Never'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Patterns Extracted</span>
              <span className="text-sm font-medium">
                {systemStatus?.subsystems?.memory?.consolidation?.total_patterns || 0}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Compression Ratio</span>
              <span className="text-sm font-medium">
                {systemStatus?.subsystems?.memory?.consolidation?.compression_ratio || '0%'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
