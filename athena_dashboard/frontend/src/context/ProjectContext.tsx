import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface Project {
  id: number
  name: string
  path: string
  created_at: string
  event_count?: number
}

interface ProjectContextType {
  projects: Project[]
  selectedProject: Project | null
  setSelectedProject: (project: Project | null) => void
  loadingProjects: boolean
  error: string | null
  refreshProjects: () => Promise<void>
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined)

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [loadingProjects, setLoadingProjects] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Load projects from API
  const refreshProjects = async () => {
    setLoadingProjects(true)
    setError(null)
    try {
      const response = await fetch('/api/system/projects')
      if (!response.ok) throw new Error('Failed to load projects')
      const data = await response.json()
      setProjects(data.projects || [])

      // Try to restore previously selected project from localStorage
      const savedProjectId = localStorage.getItem('selectedProjectId')
      if (savedProjectId && data.projects) {
        const savedProject = data.projects.find((p: Project) => p.id === parseInt(savedProjectId, 10))
        if (savedProject) {
          setSelectedProject(savedProject)
          return
        }
      }

      // Fall back to first project with events or first project
      if (data.projects && data.projects.length > 0) {
        const defaultProject = data.projects.find((p: Project) => p.event_count > 0) || data.projects[0]
        setSelectedProject(defaultProject)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load projects')
      console.error('Error loading projects:', err)
    } finally {
      setLoadingProjects(false)
    }
  }

  // Load projects on mount
  useEffect(() => {
    refreshProjects()
  }, [])

  // Persist selected project to localStorage
  useEffect(() => {
    if (selectedProject) {
      localStorage.setItem('selectedProjectId', String(selectedProject.id))
    }
  }, [selectedProject])

  return (
    <ProjectContext.Provider
      value={{
        projects,
        selectedProject,
        setSelectedProject,
        loadingProjects,
        error,
        refreshProjects,
      }}
    >
      {children}
    </ProjectContext.Provider>
  )
}

export function useProject() {
  const context = useContext(ProjectContext)
  if (context === undefined) {
    throw new Error('useProject must be used within ProjectProvider')
  }
  return context
}
