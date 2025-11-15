import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense, lazy, useEffect } from 'react'
import { NavigationProvider } from './context/NavigationContext'
import { ProjectProvider } from './context/ProjectContext'
import { MainLayout } from './components/layout/MainLayout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LoadingSpinner } from './components/common/LoadingSpinner'

// Lazy load all pages for code splitting
const OverviewPage = lazy(() => import('./pages/OverviewPage'))
const TaskManagementPage = lazy(() => import('./pages/TaskManagementPage'))
const EpisodicMemoryPage = lazy(() => import('./pages/EpisodicMemoryPage'))
const SemanticMemoryPage = lazy(() => import('./pages/SemanticMemoryPage'))
const ProceduralMemoryPage = lazy(() => import('./pages/ProceduralMemoryPage'))
const ProspectiveMemoryPage = lazy(() => import('./pages/ProspectiveMemoryPage'))
const KnowledgeGraphPage = lazy(() => import('./pages/KnowledgeGraphPage'))
const MetaMemoryPage = lazy(() => import('./pages/MetaMemoryPage'))
const ConsolidationPage = lazy(() => import('./pages/ConsolidationPage'))
const SystemHealthPage = lazy(() => import('./pages/SystemHealthPage'))
const HookExecutionPage = lazy(() => import('./pages/HookExecutionPage'))
const WorkingMemoryPage = lazy(() => import('./pages/WorkingMemoryPage'))
const RAGPlanningPage = lazy(() => import('./pages/RAGPlanningPage'))
const LearningAnalyticsPage = lazy(() => import('./pages/LearningAnalyticsPage'))
const ResearchPage = lazy(() => import('./pages/ResearchPage'))
const PerformanceMonitoringPage = lazy(() => import('./pages/PerformanceMonitoringPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

function App() {
  // Suppress WebGL deprecation warnings and other non-critical browser errors
  useEffect(() => {
    // Store original console methods
    const originalWarn = console.warn
    const originalError = console.error

    // Override console.warn to filter out non-critical warnings
    console.warn = (...args: any[]) => {
      const message = args[0]?.toString() || ''
      // Filter out WebGL deprecation and GroupMarkerNotSet warnings
      if (!message.includes('WebGL') && !message.includes('GroupMarkerNotSet')) {
        originalWarn(...args)
      }
    }

    // Override console.error to suppress Sigma.js initialization errors if they occur
    console.error = (...args: any[]) => {
      const message = args[0]?.toString() || ''
      // Only suppress if it's the async pool deprecation (will auto-recover)
      if (!message.includes('async pool') && !message.includes('AsyncConnectionPool')) {
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
                <Route path="/" element={<OverviewPage />} />
                <Route path="/overview" element={<OverviewPage />} />
                <Route path="/tasks" element={<TaskManagementPage />} />
                <Route path="/episodic" element={<EpisodicMemoryPage />} />
                <Route path="/semantic" element={<SemanticMemoryPage />} />
                <Route path="/procedural" element={<ProceduralMemoryPage />} />
                <Route path="/prospective" element={<ProspectiveMemoryPage />} />
                <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
                <Route path="/meta-memory" element={<MetaMemoryPage />} />
                <Route path="/consolidation" element={<ConsolidationPage />} />
                <Route path="/system-health" element={<SystemHealthPage />} />
                <Route path="/hooks" element={<HookExecutionPage />} />
                <Route path="/working-memory" element={<WorkingMemoryPage />} />
                <Route path="/rag-planning" element={<RAGPlanningPage />} />
                <Route path="/learning-analytics" element={<LearningAnalyticsPage />} />
                <Route path="/research" element={<ResearchPage />} />
                <Route path="/performance" element={<PerformanceMonitoringPage />} />
                <Route path="/settings" element={<SettingsPage />} />
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
