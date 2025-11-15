import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { NavigationProvider } from './context/NavigationContext'
import { MainLayout } from './components/layout/MainLayout'

// Pages - Memory Layers
import OverviewPage from './pages/OverviewPage'
import EpisodicMemoryPage from './pages/EpisodicMemoryPage'
import SemanticMemoryPage from './pages/SemanticMemoryPage'
import ProceduralMemoryPage from './pages/ProceduralMemoryPage'
import ProspectiveMemoryPage from './pages/ProspectiveMemoryPage'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'
import MetaMemoryPage from './pages/MetaMemoryPage'
import ConsolidationPage from './pages/ConsolidationPage'

// Pages - System Monitoring
import SystemHealthPage from './pages/SystemHealthPage'
import HookExecutionPage from './pages/HookExecutionPage'
import WorkingMemoryPage from './pages/WorkingMemoryPage'
import RAGPlanningPage from './pages/RAGPlanningPage'

// Pages - Analytics & Settings
import LearningAnalyticsPage from './pages/LearningAnalyticsPage'
import ResearchPage from './pages/ResearchPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <BrowserRouter>
      <NavigationProvider>
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
      </NavigationProvider>
    </BrowserRouter>
  )
}

export default App
