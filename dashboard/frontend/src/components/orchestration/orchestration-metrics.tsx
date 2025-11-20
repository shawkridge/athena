'use client'

import { OrchestrationMetrics } from '@/stores/orchestration-store'
import { Users, CheckCircle, Clock, AlertCircle, TrendingUp } from 'lucide-react'

interface OrchestrationMetricsProps {
  metrics: OrchestrationMetrics | null
  isLoading?: boolean
}

export function OrchestrationMetricsComponent({
  metrics,
  isLoading,
}: OrchestrationMetricsProps) {
  if (isLoading || !metrics) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="bg-gray-100 rounded-lg h-24 animate-pulse"
          />
        ))}
      </div>
    )
  }

  const healthColor =
    metrics.health.status === 'healthy'
      ? 'text-green-600 bg-green-50'
      : 'text-orange-600 bg-orange-50'

  return (
    <div className="space-y-4">
      {/* Health Badge */}
      <div className={`p-4 rounded-lg ${healthColor} border-2 border-current`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">System Health</p>
            <p className="text-xs opacity-75 capitalize">
              {metrics.health.status}
            </p>
          </div>
          <span className="text-2xl font-bold capitalize">
            {metrics.health.status === 'healthy' ? '✓' : '⚠'}
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            Task Completion Progress
          </h3>
          <span className="text-sm font-bold text-blue-600">
            {metrics.progress.percent.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
          <div
            className="bg-blue-600 h-full transition-all duration-300"
            style={{ width: `${metrics.progress.percent}%` }}
          />
        </div>
        <p className="text-xs text-gray-600">
          {metrics.progress.completed} of {metrics.progress.total} tasks
          completed
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Agents */}
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <div className="flex items-center gap-2 mb-2">
            <Users className="w-4 h-4 text-blue-600" />
            <p className="text-xs font-semibold text-gray-600">Agents</p>
          </div>
          <p className="text-2xl font-bold text-blue-600">
            {metrics.agents.total}
          </p>
          <div className="text-xs text-gray-600 space-y-1 mt-2">
            <p>
              <span className="text-green-600 font-semibold">
                {metrics.agents.idle}
              </span>{' '}
              idle
            </p>
            <p>
              <span className="text-yellow-600 font-semibold">
                {metrics.agents.busy}
              </span>{' '}
              busy
            </p>
            {metrics.agents.failed > 0 && (
              <p>
                <span className="text-red-600 font-semibold">
                  {metrics.agents.failed}
                </span>{' '}
                failed
              </p>
            )}
          </div>
        </div>

        {/* Pending Tasks */}
        <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-yellow-600" />
            <p className="text-xs font-semibold text-gray-600">Pending</p>
          </div>
          <p className="text-2xl font-bold text-yellow-600">
            {metrics.tasks.pending}
          </p>
          <p className="text-xs text-gray-600 mt-2">
            waiting for agents
          </p>
        </div>

        {/* In Progress */}
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <p className="text-xs font-semibold text-gray-600">In Progress</p>
          </div>
          <p className="text-2xl font-bold text-blue-600">
            {metrics.tasks.in_progress}
          </p>
          <p className="text-xs text-gray-600 mt-2">
            being worked on
          </p>
        </div>

        {/* Completed */}
        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
          <div className="flex items-center gap-2 mb-2">
            <CheckCircle className="w-4 h-4 text-green-600" />
            <p className="text-xs font-semibold text-gray-600">Completed</p>
          </div>
          <p className="text-2xl font-bold text-green-600">
            {metrics.tasks.completed}
          </p>
          <p className="text-xs text-gray-600 mt-2">
            finished tasks
          </p>
        </div>
      </div>

      {/* Issues */}
      {(metrics.health.stale_agents > 0 ||
        metrics.health.failed_agents > 0) && (
        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="w-4 h-4 text-red-600" />
            <p className="text-sm font-semibold text-red-600">Issues Detected</p>
          </div>
          <div className="text-xs text-red-700 space-y-1">
            {metrics.health.stale_agents > 0 && (
              <p>{metrics.health.stale_agents} stale agent(s)</p>
            )}
            {metrics.health.failed_agents > 0 && (
              <p>{metrics.health.failed_agents} failed agent(s)</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
