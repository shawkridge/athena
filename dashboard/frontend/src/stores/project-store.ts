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
}

interface ProjectStore {
  // Current selected project
  currentProjectId: number

  // Available projects (could be fetched from API in future)
  projects: Project[]

  // Actions
  setProject: (projectId: number) => void
  addProject: (project: Project) => void
  getCurrentProject: () => Project | undefined
}

export const useProjectStore = create<ProjectStore>()(
  persist(
    (set, get) => ({
      // Default to project 1
      currentProjectId: 1,

      // Default projects (in future, fetch from API)
      projects: [
        { id: 1, name: 'Default Project', description: 'Main Athena project' },
        { id: 2, name: 'Development', description: 'Development work' },
        { id: 3, name: 'Research', description: 'Research and experiments' },
      ],

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
    }),
    {
      name: 'athena-project-storage', // localStorage key
    }
  )
)
