'use client'

import { useQuery } from '@tanstack/react-query'
import { Zap } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import api from '@/lib/api'

export default function SkillsAgentsPage() {
  const { data: stats } = useQuery({
    queryKey: ['skills-stats'],
    queryFn: () => api.getSkillsStatistics(),
  })

  const { data: skillsData } = useQuery({
    queryKey: ['skills'],
    queryFn: () => api.getSkills(undefined, 50),
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-amber-100">
            <Zap className="h-8 w-8 text-amber-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Skills & Agents</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Skill library, agent coordination, and execution tracking
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Skills</div>
          <div className="text-2xl font-bold">{stats?.total_skills || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Active Agents</div>
          <div className="text-2xl font-bold text-blue-600">{stats?.active_agents || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Executions</div>
          <div className="text-2xl font-bold text-purple-600">{stats?.total_executions || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Success Rate</div>
          <div className="text-2xl font-bold text-green-600">
            {stats?.success_rate ? `${(stats.success_rate * 100).toFixed(1)}%` : '0%'}
          </div>
        </div>
      </div>

      {/* Skills Library Table */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Skill Library</h3>
        {skillsData?.skills && skillsData.skills.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">ID</th>
                  <th className="pb-3 font-medium">Name</th>
                  <th className="pb-3 font-medium">Domain</th>
                  <th className="pb-3 font-medium">Success Rate</th>
                  <th className="pb-3 font-medium">Usage Count</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {skillsData.skills.map((skill: any) => (
                  <tr key={skill.id} className="text-sm hover:bg-muted/50 transition-colors">
                    <td className="py-3 font-mono text-xs">{skill.id}</td>
                    <td className="py-3 font-medium">{skill.name}</td>
                    <td className="py-3 text-muted-foreground">{skill.domain || '-'}</td>
                    <td className="py-3">
                      <span className={`font-medium ${
                        skill.success_rate >= 0.8 ? 'text-green-600' :
                        skill.success_rate >= 0.5 ? 'text-yellow-600' : 'text-red-600'
                      }`}>
                        {skill.success_rate ? `${(skill.success_rate * 100).toFixed(1)}%` : '-'}
                      </span>
                    </td>
                    <td className="py-3 text-muted-foreground">{skill.usage_count || 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Zap className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No skills found</p>
            <p className="text-xs mt-1">Skills will appear here once added to the library</p>
          </div>
        )}
      </div>
    </div>
  )
}
