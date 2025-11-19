'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import { Map } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function PlanningPage() {
  const { data: stats } = useQuery({
    queryKey: ['planning-stats'],
    queryFn: api.getPlanningStatistics,
  })

  const { data: plansData } = useQuery({
    queryKey: ['planning-plans'],
    queryFn: () => api.getPlans(50),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-indigo-100">
            <Map className="h-8 w-8 text-indigo-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Planning</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Task planning, decomposition, and validation
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Plans</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_plans || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Active Plans</div>
          <div className="text-2xl font-bold text-blue-600">
            {formatNumber(stats?.active_plans || 0)}
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Completed Plans</div>
          <div className="text-2xl font-bold text-green-600">
            {formatNumber(stats?.completed_plans || 0)}
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Avg Success Rate</div>
          <div className="text-2xl font-bold text-green-600">
            {((stats?.avg_success_rate || 0) * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Planning Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Planning Quality</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Avg Plan Depth</span>
              <span className="text-sm font-medium">{stats?.avg_plan_depth || 0} levels</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Avg Subtasks</span>
              <span className="text-sm font-medium">{formatNumber(stats?.avg_subtasks || 0)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Validation Score</span>
              <span className="text-sm font-medium">
                {((stats?.avg_validation_score || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Plans Validated</span>
              <span className="text-sm font-medium">{formatNumber(stats?.validated_plans || 0)}</span>
            </div>
          </div>
        </div>

        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Execution Insights</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Avg Execution Time</span>
              <span className="text-sm font-medium">{stats?.avg_execution_time || 0} min</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Tasks Completed</span>
              <span className="text-sm font-medium text-green-600">
                {formatNumber(stats?.tasks_completed || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Tasks Pending</span>
              <span className="text-sm font-medium text-blue-600">
                {formatNumber(stats?.tasks_pending || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Tasks Failed</span>
              <span className="text-sm font-medium text-red-600">
                {formatNumber(stats?.tasks_failed || 0)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Plans List */}
      <div className="bg-card border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Plans ({plansData?.total || 0})
          </h3>
        </div>

        {plansData?.plans && plansData.plans.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {plansData.plans.map((plan, index) => (
                  <tr key={plan.id || index} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono">{plan.id || index + 1}</td>
                    <td className="px-4 py-3 text-sm font-medium">{plan.name || 'Unnamed Plan'}</td>
                    <td className="px-4 py-3">
                      {plan.status && (
                        <span className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium ${
                          plan.status === 'completed' ? 'bg-green-100 text-green-800' :
                          plan.status === 'active' ? 'bg-blue-100 text-blue-800' :
                          plan.status === 'pending' ? 'bg-gray-100 text-gray-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {plan.status}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Map className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No plans found</p>
          </div>
        )}
      </div>

      {/* Planning Strategies */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Planning Strategies</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-secondary rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Hierarchical Decomposition</div>
            <div className="text-xl font-bold">{formatNumber(stats?.hierarchical_plans || 0)}</div>
          </div>
          <div className="p-4 bg-secondary rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Sequential Planning</div>
            <div className="text-xl font-bold">{formatNumber(stats?.sequential_plans || 0)}</div>
          </div>
          <div className="p-4 bg-secondary rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Parallel Planning</div>
            <div className="text-xl font-bold">{formatNumber(stats?.parallel_plans || 0)}</div>
          </div>
        </div>
      </div>
    </div>
  )
}
