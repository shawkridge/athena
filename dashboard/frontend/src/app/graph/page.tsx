'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import { Network, Filter, Maximize2 } from 'lucide-react'
import { GraphVisualization } from '@/components/graph/graph-visualization'
import { useProjectStore } from '@/stores/project-store'
import { ScopeBadge } from '@/components/scope-badge'

export default function KnowledgeGraphPage() {
  const [entityTypeFilter, setEntityTypeFilter] = useState<string>('')
  const [limit, setLimit] = useState(100)
  const { currentProjectId, getCurrentProject } = useProjectStore()
  const currentProject = getCurrentProject()

  const { data: stats } = useQuery({
    queryKey: ['graph-stats', currentProjectId],
    queryFn: () => api.getGraphStatistics(currentProjectId),
  })

  const { data: entitiesData, isLoading } = useQuery({
    queryKey: ['graph-entities', entityTypeFilter, limit, currentProjectId],
    queryFn: () => api.getEntities(entityTypeFilter || undefined, limit, currentProjectId),
  })

  const entityTypes = [
    'Project',
    'Phase',
    'Task',
    'File',
    'Function',
    'Concept',
    'Component',
    'Process',
    'Person',
    'Decision',
    'Pattern',
    'Agent',
    'Skill',
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-cyan-100">
            <Network className="h-8 w-8 text-cyan-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Knowledge Graph</h1>
              <ScopeBadge scope="project" projectName={currentProject?.name} />
            </div>
            <p className="text-muted-foreground mt-1">
              Entities, relations, and communities
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Entities</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_entities || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Relations</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_relations || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Communities</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_communities || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Graph Density</div>
          <div className="text-2xl font-bold">
            {((stats?.graph_density || 0) * 100).toFixed(1)}%
          </div>
        </div>
      </div>

      {/* Graph Visualization */}
      <div className="bg-card border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">Graph Visualization</h3>
          <button className="flex items-center space-x-2 px-3 py-2 border rounded-md hover:bg-accent transition-colors text-sm">
            <Maximize2 className="h-4 w-4" />
            <span>Fullscreen</span>
          </button>
        </div>

        <div className="p-4">
          <GraphVisualization entities={entitiesData?.entities || []} />
        </div>
      </div>

      {/* Filters */}
      <div className="bg-card border rounded-lg p-4">
        <div className="flex items-center space-x-4">
          <Filter className="h-5 w-5 text-muted-foreground" />
          <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-1 block">Entity Type</label>
              <select
                value={entityTypeFilter}
                onChange={(e) => setEntityTypeFilter(e.target.value)}
                className="w-full px-3 py-2 border rounded-md bg-background"
              >
                <option value="">All Types</option>
                {entityTypes.map((type) => (
                  <option key={type} value={type}>
                    {type}
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
                <option value={50}>50 entities</option>
                <option value={100}>100 entities</option>
                <option value={500}>500 entities</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setEntityTypeFilter('')
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

      {/* Entities List */}
      <div className="bg-card border rounded-lg overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-lg font-semibold">
            Entities ({entitiesData?.total || 0})
          </h3>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        ) : entitiesData?.entities && entitiesData.entities.length > 0 ? (
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
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Source
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {entitiesData.entities.map((entity) => (
                  <tr key={entity.id} className="hover:bg-muted/30 transition-colors">
                    <td className="px-4 py-3 text-sm font-mono">{entity.id}</td>
                    <td className="px-4 py-3 text-sm font-medium">{entity.name}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-cyan-100 text-cyan-800">
                        {entity.entity_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-muted-foreground">{entity.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Network className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No entities found</p>
          </div>
        )}
      </div>
    </div>
  )
}
