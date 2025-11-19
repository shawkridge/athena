'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Zap } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import { SearchBar } from '@/components/search-bar'
import { FilterDropdown } from '@/components/filter-dropdown'
import { Pagination } from '@/components/pagination'
import { ExportButton } from '@/components/export-button'
import { DetailModal, DetailField } from '@/components/detail-modal'
import api from '@/lib/api'

export default function SkillsAgentsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [domainFilter, setDomainFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedSkill, setSelectedSkill] = useState<any>(null)

  const { data: stats } = useQuery({
    queryKey: ['skills-stats'],
    queryFn: () => api.getSkillsStatistics(),
  })

  const { data: skillsData } = useQuery({
    queryKey: ['skills'],
    queryFn: () => api.getSkills(undefined, 200), // Fetch more for client-side pagination
  })

  // Client-side filtering and pagination
  const filteredSkills = skillsData?.skills?.filter((skill: any) => {
    const matchesSearch = searchQuery
      ? skill.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        skill.id?.toString().includes(searchQuery) ||
        skill.domain?.toLowerCase().includes(searchQuery.toLowerCase())
      : true
    const matchesDomain = domainFilter
      ? skill.domain?.toLowerCase() === domainFilter.toLowerCase()
      : true
    return matchesSearch && matchesDomain
  }) || []

  const totalPages = Math.ceil(filteredSkills.length / pageSize)
  const paginatedSkills = filteredSkills.slice(
    (currentPage - 1) * pageSize,
    currentPage * pageSize
  )

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handlePageSizeChange = (size: number) => {
    setPageSize(size)
    setCurrentPage(1)
  }

  // Extract unique domains for filter
  const domains = Array.from(new Set(skillsData?.skills?.map((s: any) => s.domain).filter(Boolean) || [])) as string[]
  const domainOptions = domains.map(domain => ({ value: domain, label: domain }))

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
        <ExportButton
          data={filteredSkills}
          filename={`skills-${new Date().toISOString().split('T')[0]}`}
        />
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
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Skill Library</h3>
          <div className="flex items-center space-x-3">
            <SearchBar
              placeholder="Search by name, ID, or domain..."
              onSearch={setSearchQuery}
              className="w-64"
            />
            {domainOptions.length > 0 && (
              <FilterDropdown
                label="Domain"
                options={domainOptions}
                value={domainFilter}
                onChange={setDomainFilter}
              />
            )}
          </div>
        </div>

        {paginatedSkills && paginatedSkills.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b">
                  <tr className="text-left text-sm text-muted-foreground">
                    <th className="pb-3 font-medium">ID</th>
                    <th className="pb-3 font-medium">Name</th>
                    <th className="pb-3 font-medium">Domain</th>
                    <th className="pb-3 font-medium">Success Rate</th>
                    <th className="pb-3 font-medium">Usage Count</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedSkills.map((skill: any) => (
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
                      <td className="py-3">
                        <button
                          onClick={() => setSelectedSkill(skill)}
                          className="text-blue-600 hover:text-blue-800 text-xs font-medium"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                pageSize={pageSize}
                totalItems={filteredSkills.length}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            )}
          </>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Zap className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery || domainFilter
                ? 'No skills match your filters'
                : 'No skills found'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery || domainFilter
                ? 'Try adjusting your search or filters'
                : 'Skills will appear here once added to the library'}
            </p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <DetailModal
        isOpen={!!selectedSkill}
        onClose={() => setSelectedSkill(null)}
        title="Skill Details"
      >
        {selectedSkill && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Skill ID" value={selectedSkill.id} />
              <DetailField label="Domain" value={selectedSkill.domain || '-'} />
            </div>
            <DetailField label="Name" value={selectedSkill.name} />
            <div className="grid grid-cols-2 gap-4">
              <DetailField
                label="Success Rate"
                value={
                  <span className={`font-medium ${
                    selectedSkill.success_rate >= 0.8 ? 'text-green-600' :
                    selectedSkill.success_rate >= 0.5 ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {selectedSkill.success_rate ? `${(selectedSkill.success_rate * 100).toFixed(1)}%` : '-'}
                  </span>
                }
              />
              <DetailField label="Usage Count" value={selectedSkill.usage_count || 0} />
            </div>
            {selectedSkill.description && (
              <DetailField label="Description" value={selectedSkill.description} />
            )}
            {selectedSkill.created_at && (
              <DetailField
                label="Created"
                value={new Date(selectedSkill.created_at).toLocaleString()}
              />
            )}
            {selectedSkill.last_used && (
              <DetailField
                label="Last Used"
                value={new Date(selectedSkill.last_used).toLocaleString()}
              />
            )}
          </div>
        )}
      </DetailModal>
    </div>
  )
}
