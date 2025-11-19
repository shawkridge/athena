'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layers } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import { SearchBar } from '@/components/search-bar'
import { Pagination } from '@/components/pagination'
import { ExportButton } from '@/components/export-button'
import { DetailModal, DetailField } from '@/components/detail-modal'
import api from '@/lib/api'

export default function ContextAwarenessPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [selectedContext, setSelectedContext] = useState<any>(null)

  const { data: ideContext } = useQuery({
    queryKey: ['ide-context'],
    queryFn: () => api.getIDEContext(100), // Fetch more for client-side pagination
  })

  const { data: workingMemory } = useQuery({
    queryKey: ['working-memory'],
    queryFn: () => api.getWorkingMemory(100), // Fetch more for client-side pagination
  })

  // Client-side filtering and pagination for IDE contexts
  const filteredContexts = ideContext?.contexts?.filter((ctx: any) =>
    searchQuery
      ? ctx.file_path?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ctx.type?.toLowerCase().includes(searchQuery.toLowerCase())
      : true
  ) || []

  const totalPages = Math.ceil(filteredContexts.length / pageSize)
  const paginatedContexts = filteredContexts.slice(
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

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-teal-100">
            <Layers className="h-8 w-8 text-teal-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Context Awareness</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              IDE integration, conversation tracking, and working memory
            </p>
          </div>
        </div>
        <ExportButton
          data={filteredContexts}
          filename={`ide-contexts-${new Date().toISOString().split('T')[0]}`}
        />
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">IDE Contexts</div>
          <div className="text-2xl font-bold">{ideContext?.contexts?.length || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Active Files</div>
          <div className="text-2xl font-bold text-blue-600">{ideContext?.active_files || 0}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Working Memory Items</div>
          <div className="text-2xl font-bold text-purple-600">{workingMemory?.items?.length || 0}</div>
        </div>
      </div>

      {/* IDE Context Table */}
      <div className="bg-card border rounded-lg p-6">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">IDE Contexts</h3>
          <SearchBar
            placeholder="Search by file path or type..."
            onSearch={setSearchQuery}
            className="w-64"
          />
        </div>

        {paginatedContexts && paginatedContexts.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="border-b">
                  <tr className="text-left text-sm text-muted-foreground">
                    <th className="pb-3 font-medium">File Path</th>
                    <th className="pb-3 font-medium">Type</th>
                    <th className="pb-3 font-medium">Last Modified</th>
                    <th className="pb-3 font-medium">Active</th>
                    <th className="pb-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {paginatedContexts.map((ctx: any, idx: number) => (
                    <tr key={idx} className="text-sm hover:bg-muted/50 transition-colors">
                      <td className="py-3 font-mono text-xs">{ctx.file_path || '-'}</td>
                      <td className="py-3 text-muted-foreground">{ctx.type || '-'}</td>
                      <td className="py-3 text-muted-foreground">
                        {ctx.last_modified
                          ? new Date(ctx.last_modified).toLocaleString()
                          : '-'}
                      </td>
                      <td className="py-3">
                        <span
                          className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                            ctx.is_active
                              ? 'bg-green-100 text-green-800'
                              : 'bg-gray-100 text-gray-800'
                          }`}
                        >
                          {ctx.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => setSelectedContext(ctx)}
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
                totalItems={filteredContexts.length}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
              />
            )}
          </>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Layers className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">
              {searchQuery
                ? 'No IDE contexts match your search'
                : 'No IDE contexts found'}
            </p>
            <p className="text-xs mt-1">
              {searchQuery
                ? 'Try adjusting your search'
                : 'IDE contexts will appear here once tracked'}
            </p>
          </div>
        )}
      </div>

      {/* Working Memory Table */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Working Memory</h3>
        {workingMemory?.items && workingMemory.items.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="border-b">
                <tr className="text-left text-sm text-muted-foreground">
                  <th className="pb-3 font-medium">Content</th>
                  <th className="pb-3 font-medium">Importance</th>
                  <th className="pb-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {workingMemory.items.map((item: any, idx: number) => (
                  <tr key={idx} className="text-sm hover:bg-muted/50 transition-colors">
                    <td className="py-3 max-w-md truncate">{item.content || '-'}</td>
                    <td className="py-3">
                      <span className={`font-medium ${
                        item.importance >= 0.8 ? 'text-red-600' :
                        item.importance >= 0.5 ? 'text-yellow-600' : 'text-gray-600'
                      }`}>
                        {item.importance ? item.importance.toFixed(2) : '-'}
                      </span>
                    </td>
                    <td className="py-3 text-muted-foreground">
                      {item.created_at
                        ? new Date(item.created_at).toLocaleString()
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            <Layers className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">No working memory items found</p>
            <p className="text-xs mt-1">Working memory items will appear here during active sessions</p>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      <DetailModal
        isOpen={!!selectedContext}
        onClose={() => setSelectedContext(null)}
        title="IDE Context Details"
      >
        {selectedContext && (
          <div className="space-y-4">
            <DetailField label="File Path" value={selectedContext.file_path || '-'} mono />
            <div className="grid grid-cols-2 gap-4">
              <DetailField label="Type" value={selectedContext.type || '-'} />
              <DetailField
                label="Status"
                value={
                  <span
                    className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                      selectedContext.is_active
                        ? 'bg-green-100 text-green-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {selectedContext.is_active ? 'Active' : 'Inactive'}
                  </span>
                }
              />
            </div>
            <DetailField
              label="Last Modified"
              value={
                selectedContext.last_modified
                  ? new Date(selectedContext.last_modified).toLocaleString()
                  : '-'
              }
            />
            {selectedContext.line_count && (
              <DetailField label="Line Count" value={selectedContext.line_count} />
            )}
            {selectedContext.language && (
              <DetailField label="Language" value={selectedContext.language} />
            )}
          </div>
        )}
      </DetailModal>
    </div>
  )
}
