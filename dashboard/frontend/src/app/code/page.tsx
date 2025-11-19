'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Code2 } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import { SearchBar } from '@/components/search-bar'
import { FilterDropdown } from '@/components/filter-dropdown'
import { Pagination } from '@/components/pagination'
import { ExportButton } from '@/components/export-button'
import { DetailModal, DetailField } from '@/components/detail-modal'
import api from '@/lib/api'

export default function CodeIntelligencePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [languageFilter, setLanguageFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedArtifact, setSelectedArtifact] = useState<any>(null)

  const { data: stats } = useQuery({
    queryKey: ['code-stats'],
    queryFn: () => api.getCodeStatistics(),
  })

  const { data: artifacts } = useQuery({
    queryKey: ['code-artifacts'],
    queryFn: () => api.getCodeArtifacts(200), // Fetch more for client-side pagination
  })

  // Client-side filtering and pagination
  const filteredArtifacts = artifacts?.artifacts?.filter((artifact: any) => {
    const matchesSearch = searchQuery
      ? artifact.path?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        artifact.language?.toLowerCase().includes(searchQuery.toLowerCase())
      : true
    const matchesLanguage = languageFilter
      ? artifact.language?.toLowerCase() === languageFilter.toLowerCase()
      : true
    return matchesSearch && matchesLanguage
  }) || []

  const totalPages = Math.ceil(filteredArtifacts.length / pageSize)
  const paginatedArtifacts = filteredArtifacts.slice(
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

  // Extract unique languages for filter
  const languages = Array.from(new Set(artifacts?.artifacts?.map((a: any) => a.language).filter(Boolean) || [])) as string[]
  const languageOptions = languages.map(lang => ({ value: lang, label: lang }))

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
        <ExportButton
          data={filteredArtifacts}
          filename={`code-artifacts-${new Date().toISOString().split('T')[0]}`}
        />
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
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Code Artifacts</h3>
          <div className="flex items-center space-x-3">
            <SearchBar
              placeholder="Search by path or language..."
              onSearch={setSearchQuery}
              className="w-64"
            />
            {languageOptions.length > 0 && (
              <FilterDropdown
                label="Language"
                options={languageOptions}
                value={languageFilter}
                onChange={setLanguageFilter}
              />
            )}
          </div>
        </div>

        {paginatedArtifacts && paginatedArtifacts.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b">
                  <tr className="text-left text-sm text-muted-foreground">
                    <th className="pb-3 font-medium">Path</th>
                    <th className="pb-3 font-medium">Language</th>
                    <th className="pb-3 font-medium">Size</th>
                    <th className="pb-3 font-medium">Indexed</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedArtifacts.map((artifact: any, idx: number) => (
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
                      <td className="py-3">
                        <button
                          onClick={() => setSelectedArtifact(artifact)}
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
                totalItems={filteredArtifacts.length}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            )}
          </>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Code2 className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery || languageFilter
                ? 'No code artifacts match your filters'
                : 'No code artifacts found'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery || languageFilter
                ? 'Try adjusting your search or filters'
                : 'Indexed code artifacts will appear here'}
            </p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <DetailModal
        isOpen={!!selectedArtifact}
        onClose={() => setSelectedArtifact(null)}
        title="Code Artifact Details"
      >
        {selectedArtifact && (
          <div className="space-y-4">
            <DetailField label="Path" value={selectedArtifact.path} mono />
            <div className="grid grid-cols-2 gap-4">
              <DetailField
                label="Language"
                value={
                  <span className="inline-flex px-2 py-1 rounded text-xs font-medium bg-violet-100 text-violet-800">
                    {selectedArtifact.language || 'Unknown'}
                  </span>
                }
              />
              <DetailField
                label="Size"
                value={selectedArtifact.size ? `${(selectedArtifact.size / 1024).toFixed(1)} KB` : '-'}
              />
            </div>
            <DetailField
              label="Indexed At"
              value={
                selectedArtifact.indexed_at
                  ? new Date(selectedArtifact.indexed_at).toLocaleString()
                  : 'N/A'
              }
            />
            {selectedArtifact.symbols && (
              <DetailField
                label="Symbols"
                value={`${selectedArtifact.symbols} symbol(s)`}
              />
            )}
            {selectedArtifact.dependencies && (
              <DetailField
                label="Dependencies"
                value={`${selectedArtifact.dependencies} dependency(ies)`}
              />
            )}
          </div>
        )}
      </DetailModal>
    </div>
  )
}
