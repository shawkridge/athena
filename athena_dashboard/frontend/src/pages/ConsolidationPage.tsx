import { Card } from '@/components/common/Card'
import { BarChartComponent } from '@/components/charts/BarChart'
import { PieChartComponent } from '@/components/charts/PieChart'
import { Tabs, type Tab } from '@/components/common/Tabs'
import { Stat } from '@/components/common/Stat'
import { useAPI } from '@/hooks'
import { useProject } from '@/context/ProjectContext'
import { useState } from 'react'
import { format } from 'date-fns'

interface ConsolidationRun {
  id: string
  startTime: string
  endTime: string
  status: 'completed' | 'running' | 'failed'
  duration: number
  patternsFound: number
  system1Time: number
  system2Time: number
}

interface ConsolidationData {
  currentProgress: number
  lastRun: ConsolidationRun
  runs: ConsolidationRun[]
  statistics: {
    totalRuns: number
    avgPatternsPerRun: number
    successRate: number
    totalPatterns: number
  }
  patternDistribution: Array<{ name: string; value: number }>
}

export const ConsolidationPage = () => {
  const [activeTab, setActiveTab] = useState('overview')
  const { selectedProject } = useProject()

  // Build URL with project_id if a project is selected
  const apiUrl = selectedProject
    ? `/api/consolidation/analytics?project_id=${selectedProject.id}`
    : '/api/consolidation/analytics'

  const { data, loading, error } = useAPI<ConsolidationData>(
    apiUrl,
    [selectedProject?.id]
  )

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-1/3" />
          <div className="h-40 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-gray-50 mb-2">Layer 7: Consolidation</h1>
        <div className="bg-red-900/20 border border-red-700 rounded-lg p-6 text-red-300">
          {error?.message || 'Failed to load consolidation data'}
        </div>
      </div>
    )
  }

  const tabs: Tab[] = [
    {
      id: 'overview',
      label: 'Overview',
      content: (
        <div className="space-y-6">
          {/* Progress */}
          <Card>
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-50">Consolidation Progress</h3>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-gray-400">Current run</span>
                  <span className="text-gray-50 font-semibold">{data.currentProgress}%</span>
                </div>
                <div className="h-3 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-blue-500 to-cyan-500 transition-all"
                    style={{ width: `${data.currentProgress}%` }}
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* Statistics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Stat
              label="Total Runs"
              value={data.statistics.totalRuns.toString()}
            />
            <Stat
              label="Patterns Found"
              value={data.statistics.totalPatterns.toString()}
            />
            <Stat
              label="Avg/Run"
              value={data.statistics.avgPatternsPerRun.toFixed(1)}
            />
            <Stat
              label="Success Rate"
              value={`${Math.round(data.statistics.successRate)}%`}
            />
          </div>

          {/* Last Run Details */}
          <Card
            header={<h3 className="text-lg font-semibold text-gray-50">Last Run</h3>}
          >
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-400">Status</span>
                <span
                  className={`font-semibold ${
                    data.lastRun.status === 'completed'
                      ? 'text-green-400'
                      : data.lastRun.status === 'running'
                        ? 'text-yellow-400'
                        : 'text-red-400'
                  }`}
                >
                  {data.lastRun.status.charAt(0).toUpperCase() + data.lastRun.status.slice(1)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Duration</span>
                <span className="text-gray-50">{data.lastRun.duration}s</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Patterns Found</span>
                <span className="text-gray-50">{data.lastRun.patternsFound}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Completed</span>
                <span className="text-gray-50 text-sm">
                  {format(new Date(data.lastRun.endTime), 'MMM dd, HH:mm:ss')}
                </span>
              </div>
            </div>
          </Card>
        </div>
      ),
    },
    {
      id: 'patterns',
      label: 'Patterns',
      content: (
        <Card>
          <PieChartComponent data={data.patternDistribution} />
        </Card>
      ),
    },
    {
      id: 'history',
      label: 'History',
      content: (
        <Card header={<h3 className="text-lg font-semibold text-gray-50">Run History</h3>}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Status</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Patterns</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Duration</th>
                  <th className="text-left py-2 px-3 text-gray-400 font-medium">Completed</th>
                </tr>
              </thead>
              <tbody>
                {data.runs.map((run) => (
                  <tr
                    key={run.id}
                    className="border-b border-gray-700/50 hover:bg-gray-700/30"
                  >
                    <td className="py-2 px-3">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          run.status === 'completed'
                            ? 'bg-green-900/30 text-green-300'
                            : run.status === 'running'
                              ? 'bg-yellow-900/30 text-yellow-300'
                              : 'bg-red-900/30 text-red-300'
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className="py-2 px-3 text-gray-50">{run.patternsFound}</td>
                    <td className="py-2 px-3 text-gray-50">{run.duration}s</td>
                    <td className="py-2 px-3 text-gray-400 text-xs">
                      {format(new Date(run.endTime), 'MMM dd, HH:mm')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ),
    },
  ]

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Layer 7: Consolidation</h1>
        <p className="text-gray-400">Pattern extraction and dual-process reasoning</p>
      </div>

      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />
    </div>
  )
}

export default ConsolidationPage
