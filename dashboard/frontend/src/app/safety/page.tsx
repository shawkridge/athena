'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Shield } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import { SearchBar } from '@/components/search-bar'
import { FilterDropdown } from '@/components/filter-dropdown'
import { Pagination } from '@/components/pagination'
import { ExportButton } from '@/components/export-button'
import { DetailModal, DetailField } from '@/components/detail-modal'
import api from '@/lib/api'

export default function SafetyValidationPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [severityFilter, setSeverityFilter] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedValidation, setSelectedValidation] = useState<any>(null)

  const { data: stats } = useQuery({
    queryKey: ['safety-stats'],
    queryFn: () => api.getSafetyStatistics(),
  })

  const { data: validationsData } = useQuery({
    queryKey: ['safety-validations'],
    queryFn: () => api.getSafetyValidations(200), // Fetch more for client-side pagination
  })

  // Client-side filtering and pagination
  const filteredValidations = validationsData?.validations?.filter((validation: any) => {
    const matchesSearch = searchQuery
      ? validation.type?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        validation.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        validation.message?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        validation.id?.toString().includes(searchQuery)
      : true
    const matchesSeverity = severityFilter
      ? validation.severity?.toLowerCase() === severityFilter.toLowerCase()
      : true
    return matchesSearch && matchesSeverity
  }) || []

  const totalPages = Math.ceil(filteredValidations.length / pageSize)
  const paginatedValidations = filteredValidations.slice(
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

  const severityOptions = [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
  ]

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
        <ExportButton
          data={filteredValidations}
          filename={`safety-validations-${new Date().toISOString().split('T')[0]}`}
        />
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
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Recent Safety Validations</h3>
          <div className="flex items-center space-x-3">
            <SearchBar
              placeholder="Search by type, ID, or description..."
              onSearch={setSearchQuery}
              className="w-64"
            />
            <FilterDropdown
              label="Severity"
              options={severityOptions}
              value={severityFilter}
              onChange={setSeverityFilter}
            />
          </div>
        </div>

        {paginatedValidations && paginatedValidations.length > 0 ? (
          <>
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
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedValidations.map((validation: any) => (
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
                      <td className="py-3">
                        <button
                          onClick={() => setSelectedValidation(validation)}
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
                totalItems={filteredValidations.length}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            )}
          </>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery || severityFilter
                ? 'No safety validations match your filters'
                : 'No safety validations found'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery || severityFilter
                ? 'Try adjusting your search or filters'
                : 'Safety validations will appear here once code is scanned'}
            </p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <DetailModal
        isOpen={!!selectedValidation}
        onClose={() => setSelectedValidation(null)}
        title="Safety Validation Details"
      >
        {selectedValidation && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Validation ID" value={selectedValidation.id} />
              <DetailField
                label="Severity"
                value={
                  <span
                    className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                      selectedValidation.severity === 'critical' || selectedValidation.severity === 'high'
                        ? 'bg-red-100 text-red-800'
                        : selectedValidation.severity === 'medium'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}
                  >
                    {selectedValidation.severity || 'low'}
                  </span>
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Type" value={selectedValidation.type || '-'} />
              <DetailField
                label="Status"
                value={
                  <span
                    className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                      selectedValidation.status === 'resolved'
                        ? 'bg-green-100 text-green-800'
                        : selectedValidation.status === 'pending'
                        ? 'bg-orange-100 text-orange-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {selectedValidation.status || 'pending'}
                  </span>
                }
              />
            </div>
            <DetailField
              label="Description"
              value={selectedValidation.description || selectedValidation.message || '-'}
            />
            <DetailField
              label="Detected At"
              value={
                selectedValidation.detected_at || selectedValidation.created_at
                  ? new Date(selectedValidation.detected_at || selectedValidation.created_at).toLocaleString()
                  : '-'
              }
            />
            {selectedValidation.file_path && (
              <DetailField label="File Path" value={selectedValidation.file_path} mono />
            )}
            {selectedValidation.line_number && (
              <DetailField label="Line Number" value={selectedValidation.line_number} />
            )}
            {selectedValidation.recommendation && (
              <DetailField label="Recommendation" value={selectedValidation.recommendation} />
            )}
          </div>
        )}
      </DetailModal>
    </div>
  )
}
