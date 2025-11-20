'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, type ReactNode, useEffect } from 'react'
import { ThemeProvider } from '@/providers/theme-provider'
import { ToastProvider } from '@/providers/toast-provider'
import { FavoritesProvider } from '@/providers/favorites-provider'
import { ErrorBoundary } from '@/components/error-boundary'
import { CommandPalette } from '@/components/command-palette'
import { useProjectStore } from '@/stores/project-store'

// Initialize projects on app startup
function ProjectInitializer({ children }: { children: ReactNode }) {
  const fetchProjects = useProjectStore((state) => state.fetchProjects)

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  return <>{children}</>
}

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 10 * 1000, // 10 seconds
            refetchInterval: 30 * 1000, // 30 seconds for live data
            refetchOnWindowFocus: true,
            retry: 2,
          },
        },
      })
  )

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <ToastProvider>
            <FavoritesProvider>
              <ProjectInitializer>
                {children}
                <CommandPalette />
              </ProjectInitializer>
            </FavoritesProvider>
          </ToastProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
