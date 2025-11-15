/**
 * Project Selector Dropdown
 * Allows switching between different projects
 */

import { useState } from 'react'
import { useProject, type Project } from '../context/ProjectContext'

export const ProjectSelector = () => {
  const { projects, selectedProject, setSelectedProject, loadingProjects } = useProject()
  const [isOpen, setIsOpen] = useState(false)

  if (loadingProjects) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-400">Loading projects...</span>
      </div>
    )
  }

  if (!selectedProject) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-400">No project selected</span>
      </div>
    )
  }

  const handleSelectProject = (project: Project) => {
    setSelectedProject(project)
    setIsOpen(false)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg transition-colors text-sm text-gray-50 border border-gray-600"
      >
        <span className="text-lg">📁</span>
        <span className="font-medium truncate max-w-xs">{selectedProject.name}</span>
        <span className={`text-xs transition-transform ${isOpen ? 'rotate-180' : ''}`}>▼</span>
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 left-0 w-80 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
          {/* Header */}
          <div className="p-3 border-b border-gray-700">
            <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Available Projects ({projects.length})
            </p>
          </div>

          {/* Project List */}
          <div className="max-h-96 overflow-y-auto">
            {projects.length === 0 ? (
              <div className="p-4 text-center text-sm text-gray-400">
                No projects found
              </div>
            ) : (
              projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => handleSelectProject(project)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-700/50 hover:bg-gray-700/50 transition-colors ${
                    selectedProject.id === project.id ? 'bg-gray-700 border-l-2 border-l-blue-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-50 truncate">{project.name}</p>
                      <p className="text-xs text-gray-400 truncate">{project.path}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {project.event_count || 0} events
                      </p>
                    </div>
                    {selectedProject.id === project.id && (
                      <span className="text-lg">✓</span>
                    )}
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-3 border-t border-gray-700 bg-gray-800/50">
            <p className="text-xs text-gray-500">
              Selected project: <span className="text-gray-50 font-medium">{selectedProject.name}</span>
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectSelector
