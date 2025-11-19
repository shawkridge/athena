'use client'

import { useProjectStore } from '@/stores/project-store'
import { FolderOpen, Check } from 'lucide-react'

export function ProjectSelector() {
  const { currentProjectId, projects, setProject, getCurrentProject } = useProjectStore()
  const currentProject = getCurrentProject()

  return (
    <div className="relative group">
      <button className="flex items-center space-x-2 px-3 py-2 rounded-md hover:bg-accent transition-colors">
        <FolderOpen className="h-4 w-4 text-muted-foreground" />
        <div className="flex flex-col items-start">
          <span className="text-xs text-muted-foreground">Project</span>
          <span className="text-sm font-medium">{currentProject?.name || 'Unknown'}</span>
        </div>
      </button>

      {/* Dropdown menu */}
      <div className="absolute right-0 top-full mt-1 w-64 bg-card border rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
        <div className="p-2">
          <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider border-b mb-2">
            Select Project
          </div>
          {projects.map((project) => (
            <button
              key={project.id}
              onClick={() => setProject(project.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-left transition-colors ${
                currentProjectId === project.id
                  ? 'bg-primary text-primary-foreground'
                  : 'hover:bg-accent'
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{project.name}</div>
                {project.description && (
                  <div className="text-xs text-muted-foreground truncate">
                    {project.description}
                  </div>
                )}
              </div>
              {currentProjectId === project.id && (
                <Check className="h-4 w-4 ml-2 flex-shrink-0" />
              )}
            </button>
          ))}
        </div>

        <div className="border-t p-2">
          <div className="px-3 py-2 text-xs text-muted-foreground">
            Project scope: Episodic, Graph
            <br />
            Global scope: Procedural, Semantic, Meta
          </div>
        </div>
      </div>
    </div>
  )
}
