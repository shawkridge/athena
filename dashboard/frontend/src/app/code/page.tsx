'use client'

import { useQuery } from '@tanstack/react-query'
import { Code2 } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import api from '@/lib/api'

export default function CodeIntelligencePage() {
  const { data: stats } = useQuery({
    queryKey: ['code-stats'],
    queryFn: () => api.getCodeStatistics(),
  })

  const { data: artifacts } = useQuery({
    queryKey: ['code-artifacts'],
    queryFn: () => api.getCodeArtifacts(50),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-violet-100">
            <Code2 className="h-8 w-8 text-violet-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Code Intelligence</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Code artifacts, symbol tracking, and dependency analysis
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Files</div>
          <div className="text-2xl font-bold">{stats?.total_files || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Symbols</div>
          <div className="text-2xl font-bold">{stats?.total_symbols || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Languages</div>
          <div className="text-2xl font-bold">
            {stats?.languages ? Object.keys(stats.languages).length : 0}
          </div>
        </div>
      </div>

      {/* Code Artifacts Table */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Code Artifacts</h3>
        {artifacts?.artifacts && artifacts.artifacts.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">Path</th>
                  <th className="pb-3 font-medium">Language</th>
                  <th className="pb-3 font-medium">Size</th>
                  <th className="pb-3 font-medium">Indexed</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {artifacts.artifacts.map((artifact: any, idx: number) => (
                  <tr key={idx} className="text-sm hover:bg-muted/50 transition-colors">
                    <td className="py-3 font-mono text-xs">{artifact.path}</td>
                    <td className="py-3">
                      <span className="inline-flex px-2 py-1 rounded text-xs font-medium bg-violet-100 text-violet-800">
                        {artifact.language || 'Unknown'}
                      </span>
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {artifact.size ? `${(artifact.size / 1024).toFixed(1)} KB` : '-'}
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {artifact.indexed_at
                        ? new Date(artifact.indexed_at).toLocaleString()
                        : 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Code2 className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No code artifacts found</p>
            <p className="text-xs mt-1">Indexed code artifacts will appear here</p>
          </div>
        )}
      </div>
    </div>
  )
}
