import { Card, RefreshButton } from '@/components/common'
import { GaugeChart } from '@/components/charts/GaugeChart'
import { Badge } from '@/components/common/Badge'
import { useRealtimeData } from '@/hooks'
import { useProject } from '@/context/ProjectContext'

interface WorkingItem {
  id: string
  title: string
  type: string
  importance: number
  timestamp: number
}

interface WorkingResponse {
  items: WorkingItem[]
  cognitive: { load: number; capacity: number }
}

export const WorkingMemoryPage = () => {
  const { selectedProject } = useProject()

  // Build API URL with optional project_id parameter
  const apiUrl = selectedProject
    ? `/api/working-memory/current?project_id=${selectedProject.id}`
    : '/api/working-memory/current'

  const { data, loading, refetch, isConnected } = useRealtimeData<WorkingResponse>({
    url: apiUrl,
    dependencies: [selectedProject?.id],
    pollInterval: 3000, // Poll every 3 seconds for working memory (important)
    enabled: true,
  })

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  // Format timestamp to relative time
  const formatAge = (timestamp: number) => {
    if (!timestamp) return 'unknown'
    const now = Date.now()
    const diff = now - timestamp
    const seconds = Math.floor(diff / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)
    const days = Math.floor(hours / 24)

    if (days > 0) return `${days}d ago`
    if (hours > 0) return `${hours}h ago`
    if (minutes > 0) return `${minutes}m ago`
    return 'just now'
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-50">Working Memory</h1>
          <p className="text-gray-400">
            Current 7±2 items, cognitive load
            {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
          </p>
        </div>
        <RefreshButton onRefresh={refetch} isConnected={isConnected} isLoading={loading} />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="flex items-center justify-center">
          <GaugeChart
            value={(data?.cognitive.load || 0) / (data?.cognitive.capacity || 100) * 100}
            title="Cognitive Load"
          />
        </Card>

        <Card header={<h3 className="text-lg font-semibold text-gray-50">Current Items ({data?.items.length || 0}/{data?.cognitive.capacity || 9})</h3>}>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {data?.items && data.items.length > 0 ? (
              data.items.map((item) => (
                <div key={item.id} className="p-3 rounded bg-gray-700/30 text-sm border-l-2 border-blue-500">
                  <div className="flex justify-between items-start gap-2 mb-1">
                    <span className="text-gray-50 font-medium line-clamp-2">{item.title}</span>
                    <Badge variant={item.importance > 70 ? 'error' : item.importance > 40 ? 'warning' : 'info'}>
                      {item.importance}%
                    </Badge>
                  </div>
                  <div className="flex gap-2 text-gray-400 text-xs">
                    <span className="px-2 py-1 bg-gray-600/20 rounded">{item.type}</span>
                    <span>{formatAge(item.timestamp)}</span>
                  </div>
                </div>
              ))
            ) : (
              <div className="p-4 text-center text-gray-400">No working memory items</div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}

export default WorkingMemoryPage
