import { useState, useEffect, useCallback } from 'react'
import axios, { AxiosError } from 'axios'

interface UseAPIState<T> {
  data: T | null
  loading: boolean
  error: Error | null
}

/**
 * Custom hook for fetching data from the API
 * @param url - The API endpoint
 * @param dependencies - Dependencies to trigger refetch
 * @returns Object with data, loading, and error states
 */
export function useAPI<T>(
  url: string,
  dependencies: any[] = []
): UseAPIState<T> & { refetch: () => Promise<void> } {
  const [state, setState] = useState<UseAPIState<T>>({
    data: null,
    loading: true,
    error: null,
  })

  const fetchData = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }))
      const response = await axios.get<T>(url, {
        baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
        timeout: 30000,
      })
      setState({
        data: response.data,
        loading: false,
        error: null,
      })
    } catch (err) {
      const error = err instanceof AxiosError ? new Error(err.message) : (err as Error)
      setState({
        data: null,
        loading: false,
        error,
      })
    }
  }, [url])

  useEffect(() => {
    fetchData()
  }, [url, ...dependencies])

  return { ...state, refetch: fetchData }
}
