/**
 * Project Store - Global state for current project selection
 *
 * Manages which project the user is currently viewing.
 * Some data in Athena is project-scoped (episodic, graph), while
 * other data is global (procedural, semantic, meta).
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Project {
  id: number
  name: string
  description?: string
  event_count?: number
}

interface ProjectStore {
  // Current selected project
  currentProjectId: number

  // Available projects (fetched from API)
  projects: Project[]

  // Loading state
  loading: boolean

  // Actions
  setProject: (projectId: number) => void
  addProject: (project: Project) => void
  getCurrentProject: () => Project | undefined
  fetchProjects: () => Promise<void>
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set, get) => ({
      // Will be set after fetching from API
      currentProjectId: 0,

      // Empty until fetched from API
      projects: [],

      loading: false,

      setProject: (projectId: number) => {
        set({ currentProjectId: projectId })
      },

      addProject: (project: Project) => {
        set((state) => ({
          projects: [...state.projects, project],
        }))
      },

      getCurrentProject: () => {
        const { currentProjectId, projects } = get()
        return projects.find((p) => p.id === currentProjectId)
      },

      fetchProjects: async () => {
        set({ loading: true })
        try {
          const response = await fetch('/api/projects')
          const data = await response.json()
          if (data.projects && Array.isArray(data.projects) && data.projects.length > 0) {
            // Set projects and select the first one
            const firstProjectId = data.projects[0].id
            set({ projects: data.projects, currentProjectId: firstProjectId, loading: false })
          }
        } catch (error) {
          console.error('Failed to fetch projects:', error)
          set({ loading: false })
        }
      },
    }),
    {
      name: 'athena-project-storage', // localStorage key
    }
  )
)
