'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatNumber, formatDate, getScoreColor } from '@/lib/utils'
import { Workflow, Filter } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function ProceduralMemoryPage() {
  const [categoryFilter, setCategoryFilter] = useState<string>('')
  const [limit, setLimit] = useState(100)

  const { data: stats } = useQuery({
    queryKey: ['procedural-stats'],
    queryFn: api.getProceduralStatistics,
  })

  const { data: proceduresData, isLoading } = useQuery({
    queryKey: ['procedural-procedures', limit, categoryFilter],
    queryFn: () => api.getProcedures(limit, categoryFilter || undefined),
  })

  // Extract unique categories from procedures
  const categories = proceduresData?.procedures
    ? Array.from(new Set(proceduresData.procedures.map((p) => p.category)))
    : []

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-green-100">
            <Workflow className="h-8 w-8 text-green-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Procedural Memory</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Reusable workflows and learned procedures
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Procedures</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_procedures || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Avg Success Rate</div>
          <div className={`text-2xl font-bold ${getScoreColor(stats?.avg_success_rate || 0)}`}>
            {((stats?.avg_success_rate || 0) * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Executions</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_executions || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Categories</div>
          <div className="text-2xl font-bold">{categories.length || 0}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card border rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-muted-foreground" />
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Category</label>
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="">All Categories</option>
                {categories.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-sm font-medium mb-1 block">Limit</label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value={50}>50 procedures</option>
                <option value={100}>100 procedures</option>
                <option value={500}>500 procedures</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setCategoryFilter('')
                  setLimit(100)
                }}
                className="px-4 py-2 border rounded-md hover:bg-accent transition-colors"
              >
                Clear Filters
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Procedures List */}
      <div className="bg-card border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Procedures ({proceduresData?.total || 0})
          </h3>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : proceduresData?.procedures && proceduresData.procedures.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Category
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Success Rate
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Usage Count
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Last Used
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {proceduresData.procedures.map((procedure) => (
                  <tr key={procedure.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium">{procedure.name}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-green-100 text-green-800">
                        {procedure.category}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className={`text-sm font-medium ${getScoreColor(procedure.success_rate)}`}>
                        {(procedure.success_rate * 100).toFixed(0)}%
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {formatNumber(procedure.usage_count)}
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">
                      {procedure.last_used ? formatDate(procedure.last_used) : 'Never'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Workflow className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No procedures found</p>
          </div>
        )}
      </div>
    </div>
  )
}
