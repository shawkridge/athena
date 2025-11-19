'use client'

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatNumber } from '@/lib/utils'
import { Brain, Search as SearchIcon } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function SemanticMemoryPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [limit, setLimit] = useState(10)
  const [debouncedQuery, setDebouncedQuery] = useState('')

  // Debounce search query
  const handleSearch = (query: string) => {
    setSearchQuery(query)
    const timer = setTimeout(() => {
      setDebouncedQuery(query)
    }, 500)
    return () => clearTimeout(timer)
  }

  const { data: searchResults, isLoading } = useQuery({
    queryKey: ['semantic-search', debouncedQuery, limit],
    queryFn: () => api.searchSemanticMemories(debouncedQuery, limit),
    enabled: debouncedQuery.length > 0,
  })

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-purple-100">
            <Brain className="h-8 w-8 text-purple-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Semantic Memory</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Vector + BM25 hybrid search for facts and knowledge
            </p>
          </div>
        </div>
      </div>

      {/* Search Interface */}
      <div className="bg-card border rounded-lg p-6">
        <div className="flex items-center space-x-4">
          <div className="flex-1 relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search semantic memories..."
              className="w-full pl-10 pr-4 py-3 border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <div className="w-48">
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="w-full px-3 py-3 border rounded-md bg-background"
            >
              <option value={10}>10 results</option>
              <option value={25}>25 results</option>
              <option value={50}>50 results</option>
              <option value={100}>100 results</option>
            </select>
          </div>
        </div>

        {searchQuery && (
          <div className="mt-4 text-sm text-muted-foreground">
            {isLoading ? (
              <span>Searching...</span>
            ) : searchResults ? (
              <span>Found {searchResults.total} results for "{searchResults.query}"</span>
            ) : (
              <span>Enter at least 1 character to search</span>
            )}
          </div>
        )}
      </div>

      {/* Results */}
      {searchResults && searchResults.results.length > 0 && (
        <div className="bg-card border rounded-lg overflow-hidden">
          <div className="p-4 border-b">
            <h3 className="text-lg font-semibold">Search Results</h3>
          </div>

          <div className="divide-y divide-border">
            {searchResults.results.map((result) => (
              <div key={result.id} className="p-6 hover:bg-muted/30 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className="text-sm leading-relaxed">{result.content}</p>
                    <div className="flex items-center space-x-4 mt-3">
                      <span className="text-xs text-muted-foreground">ID: {result.id}</span>
                      {result.memory_type && (
                        <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-purple-100 text-purple-800">
                          {result.memory_type}
                        </span>
                      )}
                      {result.usefulness_score !== null && result.usefulness_score !== undefined && (
                        <span className="text-xs text-muted-foreground">
                          Usefulness: {(result.usefulness_score * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!searchQuery && (
        <div className="bg-card border rounded-lg p-12 text-center">
          <Brain className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-lg font-semibold mb-2">Search Semantic Memories</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Use the search bar above to find facts, knowledge, and learned information
            stored in semantic memory.
          </p>
          <div className="max-w-md mx-auto text-left">
            <p className="text-sm text-muted-foreground mb-2">Example searches:</p>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Programming concepts</li>
              <li>API documentation</li>
              <li>Best practices</li>
              <li>Domain knowledge</li>
            </ul>
          </div>
        </div>
      )}

      {/* No Results */}
      {searchQuery && searchResults && searchResults.results.length === 0 && (
        <div className="bg-card border rounded-lg p-12 text-center">
          <SearchIcon className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-lg font-semibold mb-2">No Results Found</h3>
          <p className="text-muted-foreground">
            No semantic memories match your search query "{searchQuery}"
          </p>
        </div>
      )}
    </div>
  )
}
