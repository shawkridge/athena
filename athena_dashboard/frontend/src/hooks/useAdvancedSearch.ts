/**
 * Advanced search hook with full-text search and filtering
 * Supports semantic search, field filtering, and project scoping
 */

import { useState, useCallback } from 'react'
import axios, { AxiosError } from 'axios'

export interface SearchFilter {
  query: string
  type?: string
  dateFrom?: string
  dateTo?: string
  importance?: { min: number; max: number }
  status?: string
  tags?: string[]
  projectId?: number
  sortBy?: 'relevance' | 'date' | 'importance'
  sortOrder?: 'asc' | 'desc'
  limit?: number
  offset?: number
}

export interface SearchResult<T> {
  id: string
  score: number
  item: T
  highlights?: {
    [key: string]: string
  }
}

export interface SearchResponse<T> {
  results: SearchResult<T>[]
  total: number
  queryTime: number
  filters: SearchFilter
}

interface UseAdvancedSearchState<T> {
  results: SearchResult<T>[] | null
  total: number
  loading: boolean
  error: Error | null
  queryTime: number
}

/**
 * Hook for advanced search across memory layers
 * Supports full-text search, filtering, sorting, and semantic search
 */
export function useAdvancedSearch<T = any>(
  searchType: 'episodic' | 'semantic' | 'procedural' | 'all' = 'all'
) {
  const [state, setState] = useState<UseAdvancedSearchState<T>>({
    results: null,
    total: 0,
    loading: false,
    error: null,
    queryTime: 0,
  })

  const search = useCallback(
    async (filters: SearchFilter) => {
      if (!filters.query || filters.query.trim().length === 0) {
        setState((prev) => ({
          ...prev,
          results: [],
          total: 0,
        }))
        return
      }

      setState((prev) => ({ ...prev, loading: true, error: null }))
      const startTime = performance.now()

      try {
        // Build query parameters
        const params = new URLSearchParams()
        params.append('query', filters.query)
        params.append('type', searchType)

        if (filters.type) params.append('filters[type]', filters.type)
        if (filters.dateFrom) params.append('filters[dateFrom]', filters.dateFrom)
        if (filters.dateTo) params.append('filters[dateTo]', filters.dateTo)
        if (filters.importance) {
          params.append(
            'filters[importance]',
            `${filters.importance.min},${filters.importance.max}`
          )
        }
        if (filters.status) params.append('filters[status]', filters.status)
        if (filters.tags && filters.tags.length > 0) {
          params.append('filters[tags]', filters.tags.join(','))
        }
        if (filters.projectId)
          params.append('filters[projectId]', filters.projectId.toString())
        if (filters.sortBy) params.append('sortBy', filters.sortBy)
        if (filters.sortOrder) params.append('sortOrder', filters.sortOrder)
        if (filters.limit) params.append('limit', filters.limit.toString())
        if (filters.offset) params.append('offset', filters.offset.toString())

        const response = await axios.get<SearchResponse<T>>(
          `/api/search?${params.toString()}`,
          {
            baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
            timeout: 30000,
          }
        )

        const queryTime = performance.now() - startTime

        setState({
          results: response.data.results,
          total: response.data.total,
          loading: false,
          error: null,
          queryTime,
        })

        return response.data
      } catch (err) {
        const error = err instanceof AxiosError ? new Error(err.message) : (err as Error)
        setState({
          results: null,
          total: 0,
          loading: false,
          error,
          queryTime: performance.now() - startTime,
        })
        throw error
      }
    },
    [searchType]
  )

  const clearSearch = useCallback(() => {
    setState({
      results: null,
      total: 0,
      loading: false,
      error: null,
      queryTime: 0,
    })
  }, [])

  return {
    ...state,
    search,
    clearSearch,
  }
}

/**
 * Helper hook for search suggestions (autocomplete)
 */
export function useSearchSuggestions(query: string, searchType: string = 'all') {
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const fetchSuggestions = useCallback(async () => {
    if (!query || query.length < 2) {
      setSuggestions([])
      return
    }

    setLoading(true)
    try {
      const response = await axios.get('/api/search/suggestions', {
        params: {
          query,
          type: searchType,
          limit: 5,
        },
        baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
        timeout: 10000,
      })

      setSuggestions(response.data.suggestions || [])
    } catch (error) {
      console.error('Failed to fetch suggestions:', error)
      setSuggestions([])
    } finally {
      setLoading(false)
    }
  }, [query, searchType])

  return { suggestions, loading, fetchSuggestions }
}

/**
 * Helper for relevance highlighting
 */
export function highlightMatches(text: string, query: string): string {
  if (!query) return text
  const regex = new RegExp(`(${query})`, 'gi')
  return text.replace(regex, '<mark>$1</mark>')
}
