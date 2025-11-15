import { Card } from '@/components/common/Card'
import { Stat } from '@/components/common/Stat'
import { Badge } from '@/components/common/Badge'
import { useAPI } from '@/hooks'
import { useProject } from '@/context/ProjectContext'

interface Task {
  id: string
  title: string
  status: 'pending' | 'active' | 'completed'
  priority: 'low' | 'medium' | 'high'
  deadline: string
}

interface ProspectiveResponse {
  tasks: Task[]
  stats: {
    total: number
    completed: number
    pending: number
    overdue: number
  }
}

export const ProspectiveMemoryPage = () => {
  const { selectedProject } = useProject()

  const apiUrl = selectedProject
    ? `/api/prospective/tasks?project_id=${selectedProject.id}`
    : '/api/prospective/tasks'

  const { data, loading } = useAPI<ProspectiveResponse>(apiUrl, [selectedProject?.id])

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Layer 4: Prospective Memory</h1>
        <p className="text-gray-400">
          Tasks, goals, and future intentions
          {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Total" value={data?.stats.total.toString() || '0'} />
        <Stat label="Completed" value={data?.stats.completed.toString() || '0'} />
        <Stat label="Pending" value={data?.stats.pending.toString() || '0'} />
        <Stat label="Overdue" value={data?.stats.overdue.toString() || '0'} />
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Tasks</h3>}>
        <div className="space-y-2">
          {data?.tasks.map((task) => (
            <div key={task.id} className="p-3 rounded bg-gray-700/30 flex items-center justify-between">
              <div>
                <p className="text-gray-50">{task.title}</p>
                <p className="text-xs text-gray-400">{task.deadline}</p>
              </div>
              <div className="flex gap-2">
                <Badge variant={task.priority === 'high' ? 'error' : 'info'}>{task.priority}</Badge>
                <Badge variant={task.status === 'completed' ? 'success' : 'warning'}>{task.status}</Badge>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default ProspectiveMemoryPage
