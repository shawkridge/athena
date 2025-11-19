'use client'

import { useQuery } from '@tanstack/react-query'
import { Shield } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import api from '@/lib/api'

export default function SafetyValidationPage() {
  const { data: stats } = useQuery({
    queryKey: ['safety-stats'],
    queryFn: () => api.getSafetyStatistics(),
  })

  const { data: validationsData } = useQuery({
    queryKey: ['safety-validations'],
    queryFn: () => api.getSafetyValidations(50),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-100">
            <Shield className="h-8 w-8 text-red-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Safety Validation</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Code safety checks, vulnerability scanning, and violation tracking
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Validations</div>
          <div className="text-2xl font-bold">{stats?.total_validations || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Vulnerabilities</div>
          <div className="text-2xl font-bold text-red-600">{stats?.vulnerabilities || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Violations</div>
          <div className="text-2xl font-bold text-orange-600">{stats?.violations || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Safety Score</div>
          <div className="text-2xl font-bold text-green-600">
            {stats?.safety_score ? `${(stats.safety_score * 100).toFixed(1)}%` : '0%'}
          </div>
        </div>
      </div>

      {/* Safety Validations Table */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Safety Validations</h3>
        {validationsData?.validations && validationsData.validations.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">ID</th>
                  <th className="pb-3 font-medium">Type</th>
                  <th className="pb-3 font-medium">Severity</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 font-medium">Description</th>
                  <th className="pb-3 font-medium">Detected</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {validationsData.validations.map((validation: any) => (
                  <tr key={validation.id} className="text-sm hover:bg-muted/50 transition-colors">
                    <td className="py-3 font-mono text-xs">{validation.id}</td>
                    <td className="py-3 font-medium">{validation.type || '-'}</td>
                    <td className="py-3">
                      <span
                        className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                          validation.severity === 'critical' || validation.severity === 'high'
                            ? 'bg-red-100 text-red-800'
                            : validation.severity === 'medium'
                            ? 'bg-yellow-100 text-yellow-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {validation.severity || 'low'}
                      </span>
                    </td>
                    <td className="py-3">
                      <span
                        className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                          validation.status === 'resolved'
                            ? 'bg-green-100 text-green-800'
                            : validation.status === 'pending'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {validation.status || 'pending'}
                      </span>
                    </td>
                    <td className="py-3 max-w-md truncate text-muted-foreground">
                      {validation.description || validation.message || '-'}
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {validation.detected_at || validation.created_at
                        ? new Date(validation.detected_at || validation.created_at).toLocaleString()
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No safety validations found</p>
            <p className="text-xs mt-1">Safety validations will appear here once code is scanned</p>
          </div>
        )}
      </div>
    </div>
  )
}
