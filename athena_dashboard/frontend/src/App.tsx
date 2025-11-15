import { useState } from 'react'
import ResearchPage from './pages/ResearchPage'

function App() {
  const [currentPage, setCurrentPage] = useState('research')

  return (
    <div className="min-h-screen bg-gray-900 text-gray-50">
      {/* Header */}
      <header className="border-b border-gray-700 bg-gray-800">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500" />
              <h1 className="text-2xl font-bold">Athena Dashboard</h1>
            </div>
            <nav className="flex gap-4">
              <button
                onClick={() => setCurrentPage('research')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  currentPage === 'research'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                Research
              </button>
              <button
                onClick={() => setCurrentPage('memory')}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  currentPage === 'memory'
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-700'
                }`}
              >
                Memory
              </button>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {currentPage === 'research' && <ResearchPage />}
        {currentPage === 'memory' && (
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-8 text-center">
            <p className="text-gray-400">Memory Dashboard - Coming Soon</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
