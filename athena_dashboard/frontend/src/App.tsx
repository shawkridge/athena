import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Suspense, lazy } from 'react'
import { NavigationProvider } from './context/NavigationContext'
import { MainLayout } from './components/layout/MainLayout'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LoadingSpinner } from './components/common/LoadingSpinner'

// Lazy load all pages for code splitting
const OverviewPage = lazy(() => import('./pages/OverviewPage'))
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
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <NavigationProvider>
          <Suspense fallback={<LoadingSpinner message="Loading dashboard..." />}>
            <Routes>
              <Route element={<MainLayout />}>
                <Route path="/" element={<OverviewPage />} />
                <Route path="/overview" element={<OverviewPage />} />
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
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
            </Routes>
          </Suspense>
        </NavigationProvider>
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
