import { Globe, FolderOpen } from 'lucide-react'

interface ScopeBadgeProps {
  scope: 'project' | 'global'
  projectName?: string
}

export function ScopeBadge({ scope, projectName }: ScopeBadgeProps) {
  if (scope === 'global') {
    return (
      <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-purple-100 text-purple-800 text-xs font-medium">
        <Globe className="h-3 w-3" />
        <span>Global</span>
      </div>
    )
  }

  return (
    <div className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-blue-100 text-blue-800 text-xs font-medium">
      <FolderOpen className="h-3 w-3" />
      <span>Project{projectName ? `: ${projectName}` : ''}</span>
    </div>
  )
}
