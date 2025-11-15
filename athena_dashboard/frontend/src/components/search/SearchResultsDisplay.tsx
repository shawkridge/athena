/**
 * Search results display component with relevance scoring and highlighting
 */

import { SearchResult } from '@/hooks/useAdvancedSearch'
import { format } from 'date-fns'

interface SearchResultsDisplayProps<T> {
  results: SearchResult<T>[]
  total: number
  loading: boolean
  queryTime: number
  empty?: boolean
  onResultClick?: (item: T) => void
  renderResult?: (item: T, score: number, highlights?: any) => React.ReactNode
}

export const SearchResultsDisplay = <T extends any>({
  results,
  total,
  loading,
  queryTime,
  empty = false,
  onResultClick,
  renderResult,
}: SearchResultsDisplayProps<T>) => {
  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="p-4 bg-gray-700 rounded animate-pulse h-20" />
        ))}
      </div>
    )
  }

  if (empty) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-lg">No search results yet</p>
        <p className="text-sm mt-2">Try searching to see results here</p>
      </div>
    )
  }

  if (results.length === 0) {
    return (
      <div className="text-center py-12 text-gray-400">
        <p className="text-lg">No results found</p>
        <p className="text-sm mt-2">Try adjusting your search query or filters</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Results info */}
      <div className="text-sm text-gray-400">
        Found <span className="text-gray-50 font-semibold">{total}</span> results in{' '}
        <span className="text-gray-50 font-semibold">{queryTime.toFixed(0)}ms</span>
      </div>

      {/* Results list */}
      <div className="space-y-3">
        {results.map((result, index) => (
          <div
            key={`${index}-${result.id}`}
            onClick={() => onResultClick?.(result.item)}
            className={`p-4 rounded-lg border border-gray-700 bg-gray-800/50 hover:bg-gray-800 transition-colors ${
              onResultClick ? 'cursor-pointer' : ''
            }`}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                {renderResult ? (
                  renderResult(result.item, result.score, result.highlights)
                ) : (
                  <DefaultResultItem item={result.item} />
                )}
              </div>

              {/* Relevance score */}
              <div className="flex-shrink-0">
                <div className="text-right">
                  <div className="text-2xl font-bold text-blue-400">
                    {Math.round(result.score * 100)}%
                  </div>
                  <div className="text-xs text-gray-500">relevance</div>
                </div>
              </div>
            </div>

            {/* Relevance bar */}
            <div className="mt-3 h-1 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-cyan-500"
                style={{ width: `${result.score * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/**
 * Default result item renderer
 */
const DefaultResultItem = ({ item }: { item: any }) => {
  if (!item) {
    return <div className="text-gray-50">Unknown result</div>
  }

  const title = item.title || item.description || item.name || 'Untitled'
  const description = item.content || item.summary || ''
  const timestamp = item.timestamp || item.date

  return (
    <div>
      <div className="text-gray-50 font-medium mb-1">{title}</div>
      {description && (
        <div className="text-sm text-gray-400 mb-2 line-clamp-2">{description}</div>
      )}
      {timestamp && (
        <div className="text-xs text-gray-500">
          {format(new Date(timestamp), 'MMM dd, HH:mm:ss')}
        </div>
      )}
    </div>
  )
}

/**
 * Search stats component
 */
export const SearchStats = ({
  total,
  queryTime,
  resultCount,
}: {
  total: number
  queryTime: number
  resultCount: number
}) => {
  return (
    <div className="flex items-center gap-6 text-sm text-gray-400">
      <div>
        <span className="text-gray-50 font-semibold">{resultCount}</span> of{' '}
        <span className="text-gray-50 font-semibold">{total}</span> shown
      </div>
      <div>
        <span className="text-gray-50 font-semibold">{queryTime.toFixed(0)}ms</span> query time
      </div>
      <div>
        <span className="text-gray-50 font-semibold">{(queryTime / resultCount).toFixed(2)}ms</span> per result
      </div>
    </div>
  )
}
