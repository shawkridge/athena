/**
 * Advanced search panel with filters, date ranges, and sorting options
 */

import { useState } from 'react'
import { SearchFilter } from '@/hooks/useAdvancedSearch'

interface AdvancedSearchPanelProps {
  onSearch: (filters: SearchFilter) => void
  onClear: () => void
  defaultFilters?: Partial<SearchFilter>
  showTypeFilter?: boolean
  showImportanceFilter?: boolean
  showStatusFilter?: boolean
}

const EVENT_TYPES = [
  'session_start',
  'user_input',
  'tool_execution',
  'memory_update',
  'error',
  'consolidation',
]

const STATUS_OPTIONS = ['active', 'completed', 'failed', 'pending']

const SORT_OPTIONS = [
  { label: 'Most Relevant', value: 'relevance' },
  { label: 'Newest First', value: 'date' },
  { label: 'Oldest First', value: 'date', order: 'asc' },
  { label: 'Highest Importance', value: 'importance' },
  { label: 'Lowest Importance', value: 'importance', order: 'asc' },
]

export const AdvancedSearchPanel = ({
  onSearch,
  onClear,
  defaultFilters = {},
  showTypeFilter = true,
  showImportanceFilter = true,
  showStatusFilter = true,
}: AdvancedSearchPanelProps) => {
  const [query, setQuery] = useState(defaultFilters.query || '')
  const [type, setType] = useState(defaultFilters.type || '')
  const [dateFrom, setDateFrom] = useState(defaultFilters.dateFrom || '')
  const [dateTo, setDateTo] = useState(defaultFilters.dateTo || '')
  const [importanceMin, setImportanceMin] = useState(
    defaultFilters.importance?.min || 0
  )
  const [importanceMax, setImportanceMax] = useState(
    defaultFilters.importance?.max || 1
  )
  const [status, setStatus] = useState(defaultFilters.status || '')
  const [sortBy, setSortBy] = useState(defaultFilters.sortBy || 'relevance')
  const [expanded, setExpanded] = useState(false)

  const handleSearch = () => {
    onSearch({
      query,
      ...(type && { type }),
      ...(dateFrom && { dateFrom }),
      ...(dateTo && { dateTo }),
      ...(importanceMin > 0 || importanceMax < 1
        ? { importance: { min: importanceMin, max: importanceMax } }
        : {}),
      ...(status && { status }),
      sortBy: (sortBy as any) || 'relevance',
    })
  }

  const handleClear = () => {
    setQuery('')
    setType('')
    setDateFrom('')
    setDateTo('')
    setImportanceMin(0)
    setImportanceMax(1)
    setStatus('')
    setSortBy('relevance')
    onClear()
  }

  return (
    <div className="border border-gray-700 rounded-lg bg-gray-800/50 overflow-hidden">
      {/* Main search bar */}
      <div className="p-4">
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="Search across events, patterns, and knowledge..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="flex-1 px-4 py-2 rounded bg-gray-700 text-gray-50 border border-gray-600 focus:outline-none focus:border-blue-500"
          />
          <button
            onClick={handleSearch}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors"
          >
            Search
          </button>
          <button
            onClick={() => setExpanded(!expanded)}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-50 rounded font-medium transition-colors"
            title="Toggle advanced filters"
          >
            {expanded ? '▼' : '▶'} Filters
          </button>
        </div>
      </div>

      {/* Advanced filters */}
      {expanded && (
        <div className="border-t border-gray-700 p-4 space-y-4 bg-gray-900/50">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Type filter */}
            {showTypeFilter && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Event Type</label>
                <select
                  value={type}
                  onChange={(e) => setType(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-gray-700 text-gray-50 border border-gray-600 focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Types</option>
                  {EVENT_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Date range */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">From Date</label>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                className="w-full px-3 py-2 rounded bg-gray-700 text-gray-50 border border-gray-600 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div>
              <label className="block text-sm text-gray-400 mb-2">To Date</label>
              <input
                type="date"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                className="w-full px-3 py-2 rounded bg-gray-700 text-gray-50 border border-gray-600 focus:outline-none focus:border-blue-500"
              />
            </div>

            {/* Importance range */}
            {showImportanceFilter && (
              <>
                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Min Importance: {importanceMin.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={importanceMin}
                    onChange={(e) => setImportanceMin(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>

                <div>
                  <label className="block text-sm text-gray-400 mb-2">
                    Max Importance: {importanceMax.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={importanceMax}
                    onChange={(e) => setImportanceMax(parseFloat(e.target.value))}
                    className="w-full"
                  />
                </div>
              </>
            )}

            {/* Status filter */}
            {showStatusFilter && (
              <div>
                <label className="block text-sm text-gray-400 mb-2">Status</label>
                <select
                  value={status}
                  onChange={(e) => setStatus(e.target.value)}
                  className="w-full px-3 py-2 rounded bg-gray-700 text-gray-50 border border-gray-600 focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Status</option>
                  {STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {/* Sort by */}
            <div>
              <label className="block text-sm text-gray-400 mb-2">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="w-full px-3 py-2 rounded bg-gray-700 text-gray-50 border border-gray-600 focus:outline-none focus:border-blue-500"
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Filter actions */}
          <div className="flex gap-2 pt-2 border-t border-gray-700">
            <button
              onClick={handleSearch}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium transition-colors"
            >
              Apply Filters
            </button>
            <button
              onClick={handleClear}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-50 rounded font-medium transition-colors"
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
