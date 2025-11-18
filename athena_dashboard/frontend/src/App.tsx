import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense, lazy, useEffect } from 'react'
import { NavigationProvider } from './context/NavigationContext'
import { ProjectProvider } from './context/ProjectContext'
import { MainLayout } from './components/layout/MainLayout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LoadingSpinner } from './components/common/LoadingSpinner'

// Lazy load all pages for code splitting
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const EpisodicMemoryPage = lazy(() => import('./pages/EpisodicMemoryPage'))
const SemanticMemoryPage = lazy(() => import('./pages/SemanticMemoryPage'))
const ProceduralMemoryPage = lazy(() => import('./pages/ProceduralMemoryPage'))
const ProspectiveMemoryPage = lazy(() => import('./pages/ProspectiveMemoryPage'))
const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraphPage'))
const MetaMemoryPage = lazy(() => import('./pages/MetaMemoryPage'))
const ConsolidationPage = lazy(() => import('./pages/ConsolidationPage'))
const SystemHealthPage = lazy(() => import('./pages/SystemHealthPage'))

function App() {
  // Suppress non-critical browser warnings and errors
  useEffect(() => {
    // Store original console methods
    const originalWarn = console.warn
    const originalError = console.error

    // Override console.warn to filter out non-critical warnings
    console.warn = (...args: any[]) => {
      const message = args[0]?.toString() || ''
      // Filter out known non-critical warnings
      const isNonCritical =
        message.includes('WebGL') ||
        message.includes('GroupMarkerNotSet') ||
        message.includes('async pool') ||
        message.includes('AsyncConnectionPool') ||
        message.includes('async pool') ||
        message.includes('opening the async pool')

      if (!isNonCritical) {
        originalWarn(...args)
      }
    }

    // Override console.error to suppress non-critical errors
    console.error = (...args: any[]) => {
      const message = args[0]?.toString() || ''
      // Only suppress async pool errors - they auto-recover
      const isNonCritical =
        message.includes('async pool') ||
        message.includes('AsyncConnectionPool')

      if (!isNonCritical) {
        originalError(...args)
      }
    }

    return () => {
      // Restore original console methods on cleanup
      console.warn = originalWarn
      console.error = originalError
    }
  }, [])

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <NavigationProvider>
          <ProjectProvider>
            <Suspense fallback={<LoadingSpinner message="Loading dashboard..." />}>
              <Routes>
              <Route element={<MainLayout />}>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/overview" element={<DashboardPage />} />
                <Route path="/episodic" element={<EpisodicMemoryPage />} />
                <Route path="/semantic" element={<SemanticMemoryPage />} />
                <Route path="/procedural" element={<ProceduralMemoryPage />} />
                <Route path="/prospective" element={<ProspectiveMemoryPage />} />
                <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
                <Route path="/meta-memory" element={<MetaMemoryPage />} />
                <Route path="/consolidation" element={<ConsolidationPage />} />
                <Route path="/system-health" element={<SystemHealthPage />} />
              </Route>
            </Routes>
            </Suspense>
          </ProjectProvider>
        </NavigationProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
